"""Yerel RAG sistemini sabit soru kümesiyle ölçer ve JSON/CSV raporu üretir."""

import argparse
import csv
from datetime import datetime, timezone
import json
from pathlib import Path
import sys
from time import perf_counter


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from offline_assistant.evaluation import (
    expected_source_rank, load_cases, summarize, term_coverage,
)
from offline_assistant.rag import (
    FALLBACK_ANSWER, build_messages, citation_warnings, ensure_citation, has_sufficient_context,
    select_context, source_score_margin,
)
from offline_assistant.retrieval import load_index, search_chunks
from offline_assistant.config import Settings


def write_reports(rows: list[dict], summary: dict, config: dict, output_dir: Path) -> tuple[Path, Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    mode = "full" if config["with_generation"] else "retrieval"
    json_path = output_dir / f"{mode}-{stamp}.json"
    csv_path = output_dir / f"{mode}-{stamp}.csv"
    payload = {
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "config": config,
        "summary": summary,
        "results": rows,
    }
    json_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    fieldnames = list(rows[0].keys())
    with csv_path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow({
                key: json.dumps(value, ensure_ascii=False) if isinstance(value, (list, dict)) else value
                for key, value in row.items()
            })
    return json_path, csv_path


def main() -> int:
    settings = Settings.load(PROJECT_ROOT)
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cases", type=Path, default=PROJECT_ROOT / "evaluation" / "questions.json")
    parser.add_argument("--db", type=Path, default=settings.database)
    parser.add_argument("--output-dir", type=Path, default=PROJECT_ROOT / "evaluation" / "results")
    parser.add_argument("--top-k", type=int, default=settings.top_k)
    parser.add_argument("--min-score", type=float, default=settings.min_score)
    parser.add_argument("--min-source-margin", type=float, default=settings.min_source_margin)
    parser.add_argument("--max-score-drop", type=float, default=settings.max_score_drop)
    parser.add_argument("--with-generation", action="store_true", help="Yerel sohbet cevabını da değerlendir.")
    parser.add_argument("--chat-model", default=settings.chat_model)
    parser.add_argument("--max-tokens", type=int, default=128)
    parser.add_argument("--model-cache-dir", type=Path, default=settings.model_cache_dir)
    parser.add_argument("--app-data-dir", type=Path, default=settings.app_data_dir, help=argparse.SUPPRESS)
    args = parser.parse_args()
    if args.top_k < 1 or args.max_tokens < 1:
        parser.error("--top-k ve --max-tokens sıfırdan büyük olmalıdır.")
    if not -1 <= args.min_score <= 1:
        parser.error("--min-score -1 ile 1 arasında olmalıdır.")
    if not 0 <= args.max_score_drop <= 2:
        parser.error("--max-score-drop 0 ile 2 arasında olmalıdır.")
    if not 0 <= args.min_source_margin <= 2:
        parser.error("--min-source-margin 0 ile 2 arasında olmalıdır.")

    embedding_model = None
    chat_model = None
    embedding_loaded = False
    chat_loaded = False
    try:
        cases = load_cases(args.cases)
        metadata, chunks = load_index(args.db)
        from foundry_local_sdk import Configuration, FoundryLocalManager

        app_data = args.app_data_dir
        cache = args.model_cache_dir.expanduser().resolve() if args.model_cache_dir else app_data / "cache" / "models"
        print(f"Değerlendirme: {len(cases)} soru | İndeks: {len(chunks)} parça")
        print(f"Embedding modeli: {metadata.model_id}", flush=True)
        FoundryLocalManager.initialize(Configuration(
            app_name="offline_assistant", app_data_dir=str(app_data), model_cache_dir=str(cache)
        ))
        catalog = FoundryLocalManager.instance.catalog
        embedding_model = catalog.get_model_variant(metadata.model_id)
        if embedding_model is None or not embedding_model.is_cached:
            raise ValueError("İndeksin embedding modeli önbellekte bulunamadı.")
        embedding_model.load()
        embedding_loaded = True
        embedding_client = embedding_model.get_embedding_client()

        rows = []
        contexts = []
        for index, case in enumerate(cases, start=1):
            if not case.valid_input:
                rows.append({
                    "id": case.id, "category": case.category, "question_type": case.question_type,
                    "question": case.question, "valid_input": False, "input_rejected": not case.question.strip(),
                    "answerable": False, "expected_sources": [], "expected_answer": case.expected_answer,
                    "found_sources": [], "scores": [], "source_margin": None,
                    "expected_source_rank": None, "accepted": False, "routing_correct": True,
                    "retrieval_seconds": 0.0, "generated_answer": None, "used_chat_model": False,
                    "term_coverage": None, "citation_warnings": [], "citation_added_by_app": False,
                    "generation_seconds": None,
                })
                contexts.append([])
                print(f"[{index:02}/{len(cases)}] {case.id}: OK | geçersiz giriş reddedildi")
                continue
            start = perf_counter()
            response = embedding_client.generate_embedding(case.question)
            if len(response.data) != 1 or response.data[0].index != 0:
                raise RuntimeError(f"{case.id}: sorgu embedding yanıtı geçersiz.")
            results = search_chunks(response.data[0].embedding, chunks, metadata.dimension, args.top_k)
            retrieval_seconds = perf_counter() - start
            found_sources = [result.source for result in results]
            rank = expected_source_rank(found_sources, case.expected_sources) if case.answerable else None
            margin = source_score_margin(results)
            accepted = has_sufficient_context(results, args.min_score, args.min_source_margin)
            contexts.append(select_context(results, args.min_score, args.max_score_drop) if accepted else [])
            rows.append({
                "id": case.id,
                "category": case.category,
                "question_type": case.question_type,
                "question": case.question,
                "valid_input": True,
                "input_rejected": False,
                "answerable": case.answerable,
                "expected_sources": case.expected_sources,
                "expected_answer": case.expected_answer,
                "found_sources": found_sources,
                "scores": [round(result.score, 6) for result in results],
                "source_margin": round(margin, 6),
                "expected_source_rank": rank,
                "accepted": accepted,
                "routing_correct": accepted == case.answerable,
                "retrieval_seconds": round(retrieval_seconds, 6),
                "generated_answer": None,
                "used_chat_model": None,
                "term_coverage": None,
                "citation_warnings": [],
                "citation_added_by_app": None,
                "generation_seconds": None,
            })
            status = "OK" if rows[-1]["routing_correct"] and (not case.answerable or rank is not None) else "KONTROL"
            print(f"[{index:02}/{len(cases)}] {case.id}: {status} | skor={results[0].score:.4f} | sıra={rank}")

        embedding_model.unload()
        embedding_loaded = False

        if args.with_generation:
            if any(row["accepted"] for row in rows):
                chat_model = catalog.get_model(args.chat_model)
                if chat_model is None or not chat_model.is_cached:
                    raise ValueError("Sohbet modeli önbellekte bulunamadı.")
                chat_model.load()
                chat_loaded = True
                client = chat_model.get_chat_client()
                client.settings.max_tokens = args.max_tokens
                client.settings.temperature = 0.1
            for case, row, context in zip(cases, rows, contexts):
                if not row["accepted"]:
                    row["generated_answer"] = FALLBACK_ANSWER
                    row["used_chat_model"] = False
                    row["term_coverage"] = 0.0 if case.answerable else None
                    row["generation_seconds"] = 0.0
                    row["citation_added_by_app"] = False
                    continue
                start = perf_counter()
                completion = client.complete_chat(build_messages(case.question, context))
                elapsed = perf_counter() - start
                if not completion.choices or not (completion.choices[0].message.content or "").strip():
                    raise RuntimeError(f"{case.id}: sohbet modeli boş cevap döndürdü.")
                model_answer = completion.choices[0].message.content.strip()
                answer, citation_added = ensure_citation(model_answer, len(context))
                row["generated_answer"] = answer
                row["used_chat_model"] = True
                row["term_coverage"] = term_coverage(answer, case.expected_term_groups)
                row["citation_warnings"] = citation_warnings(answer, len(context))
                row["citation_added_by_app"] = citation_added
                row["generation_seconds"] = round(elapsed, 6)
            if chat_loaded:
                chat_model.unload()
                chat_loaded = False

        config = {
            "cases_path": str(args.cases.resolve()),
            "database_path": str(args.db.resolve()),
            "embedding_model_id": metadata.model_id,
            "chat_model_alias": args.chat_model if args.with_generation else None,
            "top_k": args.top_k,
            "min_score": args.min_score,
            "min_source_margin": args.min_source_margin,
            "max_score_drop": args.max_score_drop,
            "max_tokens": args.max_tokens if args.with_generation else None,
            "with_generation": args.with_generation,
        }
        summary = summarize(rows, args.with_generation)
        json_path, csv_path = write_reports(rows, summary, config, args.output_dir)
        print("\nÖzet:")
        for key, value in summary.items():
            print(f"  {key}: {value:.4f}" if isinstance(value, float) else f"  {key}: {value}")
        print(f"\nJSON: {json_path.resolve()}\nCSV:  {csv_path.resolve()}")
        return 0
    except KeyboardInterrupt:
        print("\nDeğerlendirme durduruldu.", file=sys.stderr)
        return 130
    except Exception as exc:
        print(f"Değerlendirme başarısız: {exc}", file=sys.stderr)
        return 1
    finally:
        if embedding_loaded:
            try:
                embedding_model.unload()
            except Exception as exc:
                print(f"Embedding modeli çıkarılamadı: {exc}", file=sys.stderr)
        if chat_loaded:
            try:
                chat_model.unload()
            except Exception as exc:
                print(f"Sohbet modeli çıkarılamadı: {exc}", file=sys.stderr)


if __name__ == "__main__":
    raise SystemExit(main())
