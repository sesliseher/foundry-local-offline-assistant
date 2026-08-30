"""TXT parçalarını önizler; --save ile embedding üretip SQLite'a kaydeder."""

import argparse
from pathlib import Path
import sys


PROJECT_ROOT = Path(__file__).resolve().parents[1]
# Proje henüz paket olarak kurulmadığı için src dizinini import yoluna ekliyoruz.
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from offline_assistant.documents import read_txt_documents, split_document
from offline_assistant.storage import save_index


def embed_and_save(chunks, args) -> int:
    # Önizleme çalışırken SDK yüklenmez ve ağ bağlantısı kurulmaz.
    from foundry_local_sdk import Configuration, FoundryLocalManager

    app_data = PROJECT_ROOT / "data" / "foundry"
    cache = args.model_cache_dir.expanduser().resolve() if args.model_cache_dir else app_data / "cache" / "models"
    print("SDK başlatılıyor; katalog sorgusu internet gerektirebilir.", flush=True)
    FoundryLocalManager.initialize(Configuration(
        app_name="offline_assistant", app_data_dir=str(app_data), model_cache_dir=str(cache)
    ))
    model = FoundryLocalManager.instance.catalog.get_model(args.model)
    if model is None:
        raise ValueError(f"Embedding modeli bulunamadı: {args.model}")
    print(f"Embedding modeli: {model.id}", flush=True)
    if not model.is_cached:
        raise ValueError("Model indirilmemiş. Önce embedding_demo.py --download ile hazırlayın.")
    loaded = False
    try:
        print("Önbellekteki model yükleniyor; yeniden indirilmiyor.", flush=True)
        model.load()
        loaded = True
        client = model.get_embedding_client()
        vectors = []
        # Küçük gruplar kullanmak tek isteğin boyutunu sınırlı tutar.
        for offset in range(0, len(chunks), 8):
            batch = chunks[offset:offset + 8]
            response = client.generate_embeddings([chunk.text for chunk in batch])
            items = sorted(response.data, key=lambda item: item.index)
            if [item.index for item in items] != list(range(len(batch))):
                raise RuntimeError("Embedding yanıtı parça sayısı veya indeksleriyle eşleşmiyor.")
            vectors.extend(item.embedding for item in items)
            print(f"Embedding üretildi: {len(vectors)}/{len(chunks)}", flush=True)
        count = save_index(args.db, args.input_dir, model.id, args.max_chars, chunks, vectors)
        print(f"SQLite'a kaydedildi: {count} parça, {len(vectors[0])} boyut.")
        print(f"Veritabanı: {args.db.resolve()}")
        return count
    finally:
        if loaded:
            model.unload()
            print("Model bellekten çıkarıldı.")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input-dir", type=Path, default=PROJECT_ROOT / "data" / "raw")
    parser.add_argument("--max-chars", type=int, default=600, help="Parça başına en fazla karakter.")
    parser.add_argument("--encoding", default="utf-8-sig", help="TXT kodlaması; varsayılan UTF-8/BOM.")
    parser.add_argument("--save", action="store_true", help="Embedding üretip mevcut indeksi atomik yenile.")
    parser.add_argument("--db", type=Path, default=PROJECT_ROOT / "data" / "database" / "assistant.db")
    parser.add_argument("--model", default="qwen3-embedding-0.6b")
    parser.add_argument("--model-cache-dir", type=Path)
    args = parser.parse_args()
    if args.max_chars < 1:
        parser.error("--max-chars sıfırdan büyük olmalıdır.")
    try:
        documents = read_txt_documents(args.input_dir, args.encoding)
    except (ValueError, OSError, LookupError) as exc:
        print(f"Belgeler okunamadı: {exc}", file=sys.stderr)
        return 1
    if not documents:
        print(f"TXT belgesi bulunamadı: {args.input_dir.resolve()}", file=sys.stderr)
        return 1

    total_chunks = 0
    all_chunks = []
    empty_documents = 0
    for document in documents:
        chunks = split_document(document, args.max_chars)
        if not chunks:
            empty_documents += 1
            print(f"Uyarı: Boş belge atlandı: {document.source}", file=sys.stderr)
        for chunk in chunks:
            print(f"\nKaynak: {chunk.source} | Parça: {chunk.chunk_number} | Karakter: {len(chunk.text)}")
            print(chunk.text)
        total_chunks += len(chunks)
        all_chunks.extend(chunks)
    print(f"\nToplam: {len(documents)} TXT belge, {total_chunks} parça, {empty_documents} boş belge.")
    if not total_chunks:
        print("Kaydedilecek parça yok; varsa mevcut veritabanı korunur.", file=sys.stderr)
        return 1
    if not args.save:
        print("Yalnızca önizleme: kaynak dosyalar değiştirilmedi, model veya veritabanı kullanılmadı.")
        return 0
    print(
        "Kayıt modu: bu kaynak klasörünün eski indeks parçaları güncel koleksiyonla "
        "değiştirilecek; kaynak dosyalara dokunulmayacak.", flush=True
    )
    try:
        embed_and_save(all_chunks, args)
    except KeyboardInterrupt:
        print("\nİşlem durduruldu. Kaydın tamamlanıp tamamlanmadığını çıktılardan kontrol edin.", file=sys.stderr)
        return 130
    except Exception as exc:
        print(f"İndeksleme işlemi başarısız: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
