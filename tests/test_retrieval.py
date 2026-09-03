from contextlib import closing
import sqlite3

import pytest

from src.offline_assistant.documents import Chunk
from src.offline_assistant.retrieval import IndexedChunk, load_index, search_chunks
from src.offline_assistant.storage import save_index


def test_load_and_rank_top_results(tmp_path):
    database = tmp_path / "assistant.db"
    source = tmp_path / "raw"
    chunks = [
        Chunk("kutuphane.txt", 1, "Kütüphane açıktır."),
        Chunk("yemekhane.txt", 1, "Yemek servisi vardır."),
        Chunk("ders.txt", 1, "Ders kaydı yapılır."),
    ]
    save_index(database, source, "model:1", 600, chunks, [[1, 0], [0, 1], [-1, 0]])
    metadata, loaded = load_index(database)
    results = search_chunks([0.9, 0.1], loaded, metadata.dimension, top_k=2)
    assert metadata.model_id == "model:1"
    assert [(r.source, r.chunk_number) for r in results] == [
        ("kutuphane.txt", 1), ("yemekhane.txt", 1)
    ]
    assert results[0].score > results[1].score


def test_top_k_larger_than_collection_returns_each_chunk_once():
    chunks = [
        IndexedChunk("b.txt", 1, "B", [1, 0]),
        IndexedChunk("a.txt", 1, "A", [1, 0]),
    ]
    results = search_chunks([1, 0], chunks, 2, top_k=20)
    assert [(r.source, r.chunk_number) for r in results] == [("a.txt", 1), ("b.txt", 1)]


@pytest.mark.parametrize("top_k", [0, -1])
def test_invalid_top_k_is_rejected(top_k):
    with pytest.raises(ValueError, match="top_k"):
        search_chunks([1], [IndexedChunk("a", 1, "x", [1])], 1, top_k)


@pytest.mark.parametrize("query", [[], [0, 0], [1], [float("nan"), 1], [True, 0]])
def test_invalid_query_is_rejected(query):
    with pytest.raises(ValueError):
        search_chunks(query, [IndexedChunk("a", 1, "x", [1, 0])], 2)


def test_missing_database_is_clear_error(tmp_path):
    with pytest.raises(ValueError, match="bulunamadı"):
        load_index(tmp_path / "missing.db")


def test_corrupt_embedding_is_rejected(tmp_path):
    database = tmp_path / "assistant.db"
    save_index(database, tmp_path, "model", 600, [Chunk("a.txt", 1, "metin")], [[1, 0]])
    with closing(sqlite3.connect(database)) as connection:
        connection.execute("UPDATE chunks SET embedding_json = '[1]' WHERE source = 'a.txt'")
        connection.commit()
    with pytest.raises(ValueError, match="beklenen boyut 2"):
        load_index(database)


def test_retrieval_preserves_file_metadata(tmp_path):
    database = tmp_path / "assistant.db"
    save_index(database, tmp_path, "model", 600, [Chunk("rehber.pdf", 1, "Metin", "pdf", 2)], [[1]])
    metadata, chunks = load_index(database)
    result = search_chunks([1], chunks, metadata.dimension, 1)[0]
    assert (result.file_type, result.page_number) == ("pdf", 2)
