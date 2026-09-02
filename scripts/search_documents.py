"""Bir soruyla SQLite indeksindeki en benzer belge parçalarını bulur."""

import argparse
from pathlib import Path
import sys
from time import perf_counter


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from offline_assistant.retrieval import load_index, search_chunks


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("query", help="Belgelerde aranacak soru veya ifade.")
    parser.add_argument("--top-k", type=int, default=3, help="Gösterilecek sonuç sayısı; varsayılan 3.")
    parser.add_argument("--db", type=Path, default=PROJECT_ROOT / "data" / "database" / "assistant.db")
    parser.add_argument("--model-cache-dir", type=Path)
    args = parser.parse_args()
    query = args.query.strip()
    if not query:
        parser.error("Soru boş olamaz.")
    if args.top_k < 1:
        parser.error("--top-k sıfırdan büyük olmalıdır.")

    try:
        metadata, chunks = load_index(args.db)
        print(f"İndeks: {args.db.resolve()}")
        print(f"Kayıtlı parça: {len(chunks)} | Boyut: {metadata.dimension}")
        print(f"İndeks modeli: {metadata.model_id}", flush=True)

        from foundry_local_sdk import Configuration, FoundryLocalManager
        app_data = PROJECT_ROOT / "data" / "foundry"
        cache = args.model_cache_dir.expanduser().resolve() if args.model_cache_dir else app_data / "cache" / "models"
        print("SDK başlatılıyor; katalog sorgusu internet gerektirebilir.", flush=True)
        FoundryLocalManager.initialize(Configuration(
            app_name="offline_assistant", app_data_dir=str(app_data), model_cache_dir=str(cache)
        ))
        # Alias yerine indekste kayıtlı tam varyant kullanılır; sürümler karışmaz.
        model = FoundryLocalManager.instance.catalog.get_model_variant(metadata.model_id)
        if model is None:
            raise ValueError(f"İndekste kullanılan model katalogda bulunamadı: {metadata.model_id}")
        if not model.is_cached:
            raise ValueError("İndeksin embedding modeli bu önbellekte yok; modeli yeniden hazırlayın.")

        loaded = False
        try:
            model.load()
            loaded = True
            client = model.get_embedding_client()
            start = perf_counter()
            response = client.generate_embedding(query)
            if len(response.data) != 1 or response.data[0].index != 0:
                raise RuntimeError("Model sorgu için beklenen tek embedding'i döndürmedi.")
            results = search_chunks(response.data[0].embedding, chunks, metadata.dimension, args.top_k)
            elapsed = perf_counter() - start
        finally:
            if loaded:
                model.unload()

        print(f"\nSoru: {query}")
        print(f"Sorgu embedding ve arama süresi: {elapsed:.2f} saniye")
        print(f"Gösterilen sonuç: {len(results)} / istenen {args.top_k}\n")
        for rank, result in enumerate(results, start=1):
            print(f"{rank}. Skor: {result.score:.4f}")
            print(f"   Kaynak: {result.source} | Parça: {result.chunk_number}")
            print(f"   Metin: {result.text}\n")
        print(
            "Skor doğruluk yüzdesi değildir. Her sorgu için en yakın parçalar sıralanır; "
            "henüz 'bilgi yok' kararı veya sohbet cevabı üretilmez."
        )
        return 0
    except KeyboardInterrupt:
        print("\nArama durduruldu.", file=sys.stderr)
        return 130
    except Exception as exc:
        print(f"Belge araması başarısız: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
