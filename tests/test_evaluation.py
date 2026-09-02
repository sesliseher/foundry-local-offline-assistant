import json
from pathlib import Path

import pytest

from src.offline_assistant.evaluation import (
    expected_source_rank,
    load_cases,
    normalize_text,
    summarize,
    term_coverage,
)


def _valid_cases():
    return [
        {
            "id": "A-01",
            "category": "library",
            "question": "Kütüphane ne zaman açık?",
            "answerable": True,
            "expected_sources": ["library.txt"],
            "expected_term_groups": [["09.00", "09:00"]],
        },
        {
            "id": "N-01",
            "category": "unknown",
            "question": "Yurt ücreti nedir?",
            "answerable": False,
            "expected_sources": [],
            "expected_term_groups": [],
        },
    ]


def _mock_case_file(monkeypatch, cases):
    payload = json.dumps(cases, ensure_ascii=False)
    monkeypatch.setattr(Path, "read_text", lambda self, encoding=None: payload)


def test_load_cases_validates_and_loads_records(monkeypatch):
    _mock_case_file(monkeypatch, _valid_cases())

    cases = load_cases(Path("cases.json"))

    assert [case.id for case in cases] == ["A-01", "N-01"]
    assert cases[0].answerable is True


@pytest.mark.parametrize(
    "change, message",
    [
        (lambda cases: cases.append(cases[0].copy()), "Tekrarlanan"),
        (lambda cases: cases[0].update(expected_sources=[]), "kaynak ve beklenen"),
        (lambda cases: cases[1].update(expected_sources=["x.txt"]), "kaynak veya beklenen"),
    ],
)
def test_load_cases_rejects_invalid_datasets(monkeypatch, change, message):
    cases = _valid_cases()
    change(cases)
    _mock_case_file(monkeypatch, cases)

    with pytest.raises(ValueError, match=message):
        load_cases(Path("cases.json"))


def test_text_metrics_handle_turkish_characters_and_alternatives():
    assert normalize_text("  KÜTÜPHANE   İÇİN ") == "kutuphane icin"
    assert term_coverage("Saat 09:00 ile 17:00 arasında açıktır.", [["09.00", "09:00"], ["17:00"]]) == 1
    assert term_coverage("Saat 09:00'da açılır.", [["09:00"], ["17:00"]]) == 0.5
    assert term_coverage("Bilmiyorum", []) is None


def test_expected_source_rank_returns_first_match():
    assert expected_source_rank(["a.txt", "b.txt"], ["b.txt"]) == 2
    assert expected_source_rank(["a.txt"], ["b.txt"]) is None


def test_summarize_calculates_retrieval_and_generation_metrics():
    rows = [
        {
            "answerable": True, "expected_source_rank": 1, "accepted": True,
            "retrieval_seconds": 0.1, "term_coverage": 1.0,
            "used_chat_model": True, "citation_warnings": [],
        },
        {
            "answerable": True, "expected_source_rank": 2, "accepted": False,
            "retrieval_seconds": 0.2, "term_coverage": 0.0,
            "used_chat_model": False, "citation_warnings": [],
        },
        {
            "answerable": False, "expected_source_rank": None, "accepted": False,
            "retrieval_seconds": 0.3, "term_coverage": None,
            "used_chat_model": False, "citation_warnings": [],
        },
    ]

    summary = summarize(rows, with_generation=True)

    assert summary["hit_at_1"] == 0.5
    assert summary["hit_at_k"] == 1
    assert summary["mrr"] == 0.75
    assert summary["routing_accuracy"] == pytest.approx(2 / 3)
    assert summary["average_term_coverage"] == 0.5
    assert summary["valid_citation_rate"] == 1
    assert summary["generation_case_count"] == 1
    assert summary["p95_retrieval_seconds"] == 0.3


def test_summarize_requires_both_question_classes():
    row = {"answerable": True, "expected_source_rank": 1, "accepted": True, "retrieval_seconds": 0.1}
    with pytest.raises(ValueError, match="hem cevaplanabilir hem de yanıtsız"):
        summarize([row], with_generation=False)
