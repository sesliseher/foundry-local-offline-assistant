"""Yerel RAG: SQLite'tan bağlam bulur ve yerel sohbet modeliyle kaynaklı cevap üretir."""

import argparse
from pathlib import Path
import sys
from time import perf_counter


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from offline_assistant.rag import (
    FALLBACK_ANSWER, build_messages, citation_warnings, ensure_citation, has_sufficient_context,
    select_context, source_lines, source_score_margin,
)
from offline_assistant.retrieval import load_index, search_chunks
from offline_assistant.config import Settings


def main() -> int:
    settings = Settings.load(PROJECT_ROOT)
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("query", help="Belgeler kullanılarak cevaplanacak soru.")
    parser.add_argument("--top-k", type=int, default=3)
    parser.add_argument(
        "--min-score", type=float, default=settings.min_score,
        help="Sohbet modelini çağırmak için gereken en iyi skor.",
    )
    parser.add_argument(
        "--min-source-margin", type=float, default=settings.min_source_margin,
        help="En iyi kaynak ile rakip kaynak arasında gereken fark.",
    )
    parser.add_argument(
        "--max-score-drop", type=float, default=settings.max_score_drop,
        help="Bağlamın en iyi sonuçtan en fazla skor farkı.",
    )
    parser.add_argument("--chat-model", default=settings.chat_model)
    parser.add_argument("--max-tokens", type=int, default=settings.max_tokens)
    parser.add_argument("--db", type=Path, default=settings.database)
    parser.add_argument("--model-cache-dir", type=Path, default=settings.model_cache_dir)
    parser.add_argument("--app-data-dir", type=Path, default=settings.app_data_dir, help=argparse.SUPPRESS)
    args = parser.parse_args()
    question = args.query.strip()
    if not question:
        parser.error("Soru boş olamaz.")
    if args.top_k < 1:
        parser.error("--top-k sıfırdan büyük olmalıdır.")
    if not -1 <= args.min_score <= 1:
        parser.error("--min-score -1 ile 1 arasında olmalıdır.")
    if not 0 <= args.max_score_drop <= 2:
        parser.error("--max-score-drop 0 ile 2 arasında olmalıdır.")
    if not 0 <= args.min_source_margin <= 2:
        parser.error("--min-source-margin 0 ile 2 arasında olmalıdır.")
    if args.max_tokens < 1:
        parser.error("--max-tokens sıfırdan büyük olmalıdır.")

    embedding_model = None
    chat_model = None
    embedding_loaded = False
    chat_loaded = False
    try:
        metadata, chunks = load_index(args.db)
        from foundry_local_sdk import Configuration, FoundryLocalManager
        app_data = args.app_data_dir
        cache = args.model_cache_dir.expanduser().resolve() if args.model_cache_dir else app_data / "cache" / "models"
        print(f"İndeks: {len(chunks)} parça | Embedding modeli: {metadata.model_id}")
        print("SDK başlatılıyor; katalog sorgusu internet gerektirebilir.", flush=True)
        FoundryLocalManager.initialize(Configuration(
            app_name="offline_assistant", app_data_dir=str(app_data), model_cache_dir=str(cache)
        ))
        catalog = FoundryLocalManager.instance.catalog
        embedding_model = catalog.get_model_variant(metadata.model_id)
        if embedding_model is None or not embedding_model.is_cached:
            raise ValueError("İndeksin embedding modeli bu önbellekte bulunamadı.")

        retrieval_start = perf_counter()
        embedding_model.load()
        embedding_loaded = True
        response = embedding_model.get_embedding_client().generate_embedding(question)
        if len(response.data) != 1 or response.data[0].index != 0:
            raise RuntimeError("Model sorgu için beklenen tek embedding'i döndürmedi.")
        results = search_chunks(response.data[0].embedding, chunks, metadata.dimension, args.top_k)
        embedding_model.unload()
        embedding_loaded = False
        retrieval_elapsed = perf_counter() - retrieval_start

        margin = source_score_margin(results)
        print(
            f"En iyi benzerlik: {results[0].score:.4f} | Eşik: {args.min_score:.4f} | "
            f"Kaynak farkı: {margin:.4f}"
        )
        print(f"Arama süresi: {retrieval_elapsed:.2f} saniye")
        if not has_sufficient_context(results, args.min_score, args.min_source_margin):
            print(f"\nCevap: {FALLBACK_ANSWER}")
            print("\nKaynaklar: Eşik üzerinde bağlam bulunamadı; sohbet modeli çağrılmadı.")
            return 0

        context_results = select_context(results, args.min_score, args.max_score_drop)
        print(f"Sohbet modeline verilen eşik üstü parça: {len(context_results)} / {len(results)}")

        chat_model = catalog.get_model(args.chat_model)
        if chat_model is None:
            raise ValueError(f"Sohbet modeli katalogda bulunamadı: {args.chat_model}")
        if not chat_model.is_cached:
            raise ValueError("Sohbet modeli önbellekte yok; önce hello_model.py --download çalıştırın.")
        print(f"Sohbet modeli: {chat_model.id}", flush=True)
        chat_model.load()
        chat_loaded = True
        client = chat_model.get_chat_client()
        client.settings.max_tokens = args.max_tokens
        client.settings.temperature = 0.1
        generation_start = perf_counter()
        completion = client.complete_chat(build_messages(question, context_results))
        generation_elapsed = perf_counter() - generation_start
        if not completion.choices or not (completion.choices[0].message.content or "").strip():
            raise RuntimeError("Sohbet modeli boş cevap döndürdü.")
        model_answer = completion.choices[0].message.content.strip()
        answer, citation_added = ensure_citation(model_answer, len(context_results))
        chat_model.unload()
        chat_loaded = False
        print(f"\nCevap: {answer}")
        if citation_added:
            print("Kaynak etiketi doğrulanmış ilk retrieval sonucundan uygulama tarafından eklendi.")
        warnings = citation_warnings(answer, len(context_results))
        for warning in warnings:
            print(f"Kaynak etiketi uyarısı: {warning}")
        print(f"\nCevap üretme süresi: {generation_elapsed:.2f} saniye")
        print("\nGetirilen kaynaklar (uygulama tarafından doğrulandı):")
        for line in source_lines(context_results):
            print(f"  {line}")
        print(
            "\nUyarı: Kaynak listesi getirilen bağlamı gösterir; model cevabındaki her "
            "ifadenin gerçekten desteklendiği ayrıca değerlendirilmelidir."
        )
        return 0
    except KeyboardInterrupt:
        print("\nİşlem durduruldu.", file=sys.stderr)
        return 130
    except Exception as exc:
        print(f"Kaynaklı cevap üretimi başarısız: {exc}", file=sys.stderr)
        return 1
    finally:
        if embedding_loaded:
            try:
                embedding_model.unload()
            except Exception as exc:
                print(f"Embedding modeli bellekten çıkarılamadı: {exc}", file=sys.stderr)
        if chat_loaded:
            try:
                chat_model.unload()
            except Exception as exc:
                print(f"Sohbet modeli bellekten çıkarılamadı: {exc}", file=sys.stderr)


if __name__ == "__main__":
    raise SystemExit(main())
