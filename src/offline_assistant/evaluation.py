"""Değerlendirme veri kümesi doğrulama ve metrik hesaplama yardımcıları."""

from dataclasses import dataclass
import json
import math
from pathlib import Path
import unicodedata


@dataclass(frozen=True)
class EvaluationCase:
    id: str
    category: str
    question_type: str
    question: str
    valid_input: bool
    answerable: bool
    expected_sources: list[str]
    expected_term_groups: list[list[str]]
    expected_answer: str


def load_cases(path: Path) -> list[EvaluationCase]:
    try:
        raw = json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"Değerlendirme dosyası okunamadı: {exc}") from exc
    if not isinstance(raw, list) or not raw:
        raise ValueError("Değerlendirme dosyası boş olmayan bir JSON listesi olmalıdır.")
    cases = []
    seen_ids = set()
    for index, item in enumerate(raw, start=1):
        try:
            case = EvaluationCase(
                id=item["id"].strip(), category=item["category"].strip(),
                question_type=item["question_type"].strip(),
                question=item["question"], valid_input=item["valid_input"],
                answerable=item["answerable"],
                expected_sources=item["expected_sources"],
                expected_term_groups=item["expected_term_groups"],
                expected_answer=item["expected_answer"].strip(),
            )
        except (KeyError, AttributeError, TypeError) as exc:
            raise ValueError(f"Değerlendirme kaydı {index} geçersiz: {exc}") from exc
        if (
            not case.id or not case.category or not case.question_type
            or not case.expected_answer or type(case.answerable) is not bool
            or type(case.valid_input) is not bool or not isinstance(case.question, str)
        ):
            raise ValueError(f"Değerlendirme kaydı {index} temel alanları geçersiz.")
        if case.id in seen_ids:
            raise ValueError(f"Tekrarlanan değerlendirme kimliği: {case.id}")
        seen_ids.add(case.id)
        if not isinstance(case.expected_sources, list) or not all(
            isinstance(source, str) and source.strip() for source in case.expected_sources
        ):
            raise ValueError(f"{case.id}: expected_sources geçersiz.")
        groups = case.expected_term_groups
        if not isinstance(groups, list) or not all(
            isinstance(group, list) and group and all(isinstance(term, str) and term.strip() for term in group)
            for group in groups
        ):
            if groups != []:
                raise ValueError(f"{case.id}: expected_term_groups geçersiz.")
        if case.valid_input and not case.question.strip():
            raise ValueError(f"{case.id}: geçerli giriş sorusu boş olamaz.")
        if not case.valid_input and case.question.strip():
            raise ValueError(f"{case.id}: geçersiz giriş testi boşluk dışında metin içeremez.")
        if case.answerable and (not case.valid_input or not case.expected_sources or not groups):
            raise ValueError(f"{case.id}: cevaplanabilir soru kaynak ve beklenen terimler içermelidir.")
        if not case.answerable and (case.expected_sources or groups):
            raise ValueError(f"{case.id}: yanıtsız soru kaynak veya beklenen terim içermemelidir.")
        cases.append(case)
    return cases


def normalize_text(text: str) -> str:
    decomposed = unicodedata.normalize("NFKD", text.casefold())
    return " ".join("".join(char for char in decomposed if not unicodedata.combining(char)).split())


def term_coverage(answer: str, groups: list[list[str]]) -> float | None:
    if not groups:
        return None
    normalized = normalize_text(answer)
    matched = sum(any(normalize_text(term) in normalized for term in group) for group in groups)
    return matched / len(groups)


def expected_source_rank(found_sources: list[str], expected_sources: list[str]) -> int | None:
    expected = set(expected_sources)
    return next((index for index, source in enumerate(found_sources, start=1) if source in expected), None)


def summarize(rows: list[dict], with_generation: bool) -> dict:
    if not rows:
        raise ValueError("Özetlenecek değerlendirme sonucu yok.")
    valid = [row for row in rows if row.get("valid_input", True)]
    invalid = [row for row in rows if not row.get("valid_input", True)]
    answerable = [row for row in valid if row["answerable"]]
    unanswerable = [row for row in valid if not row["answerable"]]
    if not answerable or not unanswerable:
        raise ValueError("Özet için hem cevaplanabilir hem de yanıtsız soru bulunmalıdır.")
    latencies = sorted(row["retrieval_seconds"] for row in valid)
    percentile_index = max(0, math.ceil(len(latencies) * 0.95) - 1)
    summary = {
        "case_count": len(rows),
        "invalid_input_count": len(invalid),
        "answerable_count": len(answerable),
        "unanswerable_count": len(unanswerable),
        "hit_at_1": sum(row["expected_source_rank"] == 1 for row in answerable) / len(answerable),
        "hit_at_k": sum(row["expected_source_rank"] is not None for row in answerable) / len(answerable),
        "mrr": sum(1 / row["expected_source_rank"] if row["expected_source_rank"] else 0 for row in answerable)
        / len(answerable),
        "answerable_accept_rate": sum(row["accepted"] for row in answerable) / len(answerable),
        "unanswerable_reject_rate": sum(not row["accepted"] for row in unanswerable) / len(unanswerable),
        "routing_accuracy": sum(row["accepted"] == row["answerable"] for row in valid) / len(valid),
        "invalid_input_reject_rate": (
            sum(row.get("input_rejected", False) for row in invalid) / len(invalid) if invalid else None
        ),
        "average_retrieval_seconds": sum(latencies) / len(latencies),
        "p95_retrieval_seconds": latencies[percentile_index],
    }
    if with_generation:
        scored_answers = [row for row in answerable if row.get("term_coverage") is not None]
        model_answers = [row for row in rows if row.get("used_chat_model")]
        model_citations = [row for row in model_answers if not row.get("citation_added_by_app")]
        summary.update({
            "average_term_coverage": (
                sum(row["term_coverage"] for row in scored_answers) / len(scored_answers)
                if scored_answers else None
            ),
            "valid_citation_rate": (
                sum(not row["citation_warnings"] for row in model_answers) / len(model_answers)
                if model_answers else None
            ),
            "generation_case_count": len(model_answers),
            "model_citation_rate": len(model_citations) / len(model_answers) if model_answers else None,
            "citation_repair_rate": (
                sum(bool(row.get("citation_added_by_app")) for row in model_answers) / len(model_answers)
                if model_answers else None
            ),
        })
    return summary
