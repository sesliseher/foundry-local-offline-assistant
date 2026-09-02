"""Üç cümleyi yerel embedding modeliyle soruya benzerliğine göre sıralar."""

import argparse
from pathlib import Path
import sys
from time import perf_counter


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from offline_assistant.retrieval import cosine_similarity

DOCUMENTS = [
    "Kütüphane hafta içi sabah dokuzdan akşam altıya kadar açıktır.",
    "Öğrenciler yemekhanede öğle yemeği yiyebilir.",
    "Ders kayıtları öğrenci bilgi sistemi üzerinden çevrimiçi yapılır.",
]


def ordered_vectors(response, expected_count: int) -> list[list[float]]:
    """Yanıt sırası değişse bile vektörleri giriş metinleriyle eşleştirir."""
    items = sorted(response.data, key=lambda item: item.index)
    if [item.index for item in items] != list(range(expected_count)):
        raise RuntimeError("Model beklenen sayıda ve indekslerde embedding döndürmedi.")
    return [item.embedding for item in items]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model", default="qwen3-embedding-0.6b")
    parser.add_argument(
        "--query", action="append", help="Sıralanacak soru; birden fazla kez verilebilir."
    )
    parser.add_argument("--download", action="store_true", help="Eksik modeli indirmeye izin ver.")
    parser.add_argument("--model-cache-dir", type=Path, help="Mevcut model önbelleği klasörü.")
    args = parser.parse_args()
    queries = args.query if args.query is not None else ["Kütüphane saat kaçta kapanıyor?"]
    if any(not query.strip() for query in queries):
        parser.error("Soru boş olamaz.")

    try:
        from foundry_local_sdk import Configuration, FoundryLocalManager
    except ImportError as exc:
        print(f"SDK yüklenemedi; .venv Python ortamını kullanın. Ayrıntı: {exc}", file=sys.stderr)
        return 1

    app_data_dir = PROJECT_ROOT / "data" / "foundry"
    model_cache_dir = (
        args.model_cache_dir.expanduser().resolve()
        if args.model_cache_dir is not None
        else app_data_dir / "cache" / "models"
    )
    model = None
    loaded = False
    exit_code = 0
    try:
        print(f"Model önbelleği: {model_cache_dir}", flush=True)
        print("SDK başlatılıyor; katalog sorgusu internet gerektirebilir.", flush=True)
        FoundryLocalManager.initialize(Configuration(
            app_name="offline_assistant",
            app_data_dir=str(app_data_dir),
            model_cache_dir=str(model_cache_dir),
        ))
        model = FoundryLocalManager.instance.catalog.get_model(args.model)
        if model is None:
            raise ValueError(f"Model bulunamadı: {args.model}")
        print(f"Seçili varyant: {model.id}", flush=True)
        if model.info.file_size_mb is not None:
            print(f"Katalogdaki boyut: {model.info.file_size_mb} MB", flush=True)
        if not model.is_cached:
            if not args.download:
                raise ValueError("Model indirilmemiş. İlk çalıştırmada --download ekleyin.")
            last_percent = -10

            def report_progress(percent: float) -> None:
                nonlocal last_percent
                if int(percent) >= last_percent + 10 or (percent >= 100 and last_percent < 100):
                    last_percent = int(percent)
                    print(f"  İndirme: %{percent:.0f}", flush=True)

            print("Embedding modeli indiriliyor...", flush=True)
            model.download(report_progress)
        else:
            print("Önbellekteki model kullanılacak; yeniden indirilmiyor.", flush=True)

        print("Model belleğe yükleniyor...", flush=True)
        model.load()
        loaded = True
        client = model.get_embedding_client()
        print("Üç cümle için embedding üretiliyor...", flush=True)
        start = perf_counter()
        document_vectors = ordered_vectors(client.generate_embeddings(DOCUMENTS), len(DOCUMENTS))
        print(f"Cümle embedding süresi: {perf_counter() - start:.2f} saniye", flush=True)
        print(f"Vektör boyutu: {len(document_vectors[0])}")
        print(f"İlk vektörün ilk 5 değeri: {document_vectors[0][:5]}")

        for query in queries:
            query = query.strip()
            print(f"\nSoru: {query}", flush=True)
            # Cümleler ve sorular aynı modelle aynı vektör uzayına dönüştürülür.
            query_vector = ordered_vectors(client.generate_embedding(query), 1)[0]
            scores = [cosine_similarity(query_vector, vector) for vector in document_vectors]
            ranked_indices = sorted(range(len(DOCUMENTS)), key=lambda index: scores[index], reverse=True)
            for rank, index in enumerate(ranked_indices, start=1):
                print(f"  {rank}. [{scores[index]:.4f}] {DOCUMENTS[index]}", flush=True)
            print(f"En yakın cümle: {DOCUMENTS[ranked_indices[0]]}", flush=True)

        print(
            "\nSkor bir doğruluk yüzdesi değildir. İlgisiz sorularda da bir cümle ilk sıraya "
            "gelir; bu deneme cevap üretmez veya 'bilgi yok' kararı vermez."
        )
    except KeyboardInterrupt:
        print("\nİşlem durduruldu.", file=sys.stderr)
        exit_code = 130
    except Exception as exc:
        print(f"Embedding denemesi başarısız: {exc}", file=sys.stderr)
        exit_code = 1
    finally:
        if loaded:
            try:
                model.unload()
                print("Model bellekten çıkarıldı; dosyalar önbellekte kaldı.")
            except Exception as exc:
                print(f"Model bellekten çıkarılamadı: {exc}", file=sys.stderr)
                exit_code = 1
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
