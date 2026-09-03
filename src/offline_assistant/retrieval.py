"""SQLite indeksini yükleme ve kosinüs benzerliğiyle küçük ölçekli arama."""

from contextlib import closing
from dataclasses import dataclass
import json
import math
from pathlib import Path
import sqlite3


@dataclass(frozen=True)
class IndexMetadata:
    source_root: str
    model_id: str
    dimension: int
    max_chars: int


@dataclass(frozen=True)
class IndexedChunk:
    source: str
    chunk_number: int
    text: str
    embedding: list[float]
    file_type: str = "txt"
    page_number: int | None = None


@dataclass(frozen=True)
class SearchResult:
    source: str
    chunk_number: int
    text: str
    score: float
    file_type: str = "txt"
    page_number: int | None = None


def _validate_vector(vector: list[float], dimension: int, label: str) -> None:
    if len(vector) != dimension:
        raise ValueError(f"{label} boyutu {len(vector)}; beklenen boyut {dimension}.")
    if not all(type(value) in (int, float) and math.isfinite(value) for value in vector):
        raise ValueError(f"{label} yalnızca sonlu sayılar içermelidir.")
    if not any(value != 0 for value in vector):
        raise ValueError(f"{label} sıfır vektörü olamaz.")


def cosine_similarity(left: list[float], right: list[float]) -> float:
    if not left or len(left) != len(right):
        raise ValueError("Vektörler boş olmamalı ve aynı boyutta olmalıdır.")
    if not all(math.isfinite(value) for value in (*left, *right)):
        raise ValueError("Vektörler yalnızca sonlu sayılar içermelidir.")
    left_norm = math.sqrt(sum(value * value for value in left))
    right_norm = math.sqrt(sum(value * value for value in right))
    if not left_norm or not right_norm:
        raise ValueError("Sıfır vektörü için kosinüs benzerliği tanımsızdır.")
    score = sum(a * b for a, b in zip(left, right)) / (left_norm * right_norm)
    return max(-1.0, min(1.0, score))


def load_index(database: Path) -> tuple[IndexMetadata, list[IndexedChunk]]:
    """Veritabanını salt okunur açar ve saklanan vektörleri doğrular."""
    database = database.resolve()
    if not database.is_file():
        raise ValueError(f"İndeks veritabanı bulunamadı: {database}")
    try:
        with closing(sqlite3.connect(database.as_uri() + "?mode=ro", uri=True)) as connection:
            metadata_rows = connection.execute(
                "SELECT source_root, model_id, dimension, max_chars FROM index_metadata"
            ).fetchall()
            if len(metadata_rows) != 1:
                raise ValueError("İndeks tam olarak bir metadata kaydı içermelidir.")
            metadata = IndexMetadata(*metadata_rows[0])
            if not metadata.model_id or metadata.dimension < 1 or metadata.max_chars < 1:
                raise ValueError("İndeks metadata bilgileri geçersiz.")
            columns = {row[1] for row in connection.execute("PRAGMA table_info(chunks)")}
            metadata_select = (
                "file_type, page_number" if {"file_type", "page_number"} <= columns
                else "'txt' AS file_type, NULL AS page_number"
            )
            rows = connection.execute(
                f"SELECT source, chunk_number, text, embedding_json, {metadata_select} "
                "FROM chunks ORDER BY source, chunk_number"
            ).fetchall()
    except sqlite3.Error as exc:
        raise ValueError(f"SQLite indeksi okunamadı: {exc}") from exc
    if not rows:
        raise ValueError("İndekste aranacak parça yok.")

    chunks = []
    for source, chunk_number, text, embedding_json, file_type, page_number in rows:
        try:
            embedding = json.loads(embedding_json)
        except (json.JSONDecodeError, TypeError) as exc:
            raise ValueError(f"Embedding JSON bozuk: {source} parça {chunk_number}.") from exc
        if not isinstance(embedding, list):
            raise ValueError(f"Embedding liste değil: {source} parça {chunk_number}.")
        _validate_vector(embedding, metadata.dimension, f"{source} parça {chunk_number} embedding'i")
        if not source or not isinstance(chunk_number, int) or chunk_number < 1 or not text.strip():
            raise ValueError("İndekste geçersiz kaynak, parça numarası veya metin var.")
        chunks.append(IndexedChunk(source, chunk_number, text, embedding, file_type, page_number))
    return metadata, chunks


def search_chunks(
    query_embedding: list[float], chunks: list[IndexedChunk], dimension: int, top_k: int = 3
) -> list[SearchResult]:
    """Bütün küçük indeksi bellekte tarar; eşit skorlarda sonuç kararlıdır."""
    if top_k < 1:
        raise ValueError("top_k sıfırdan büyük olmalıdır.")
    if not chunks:
        raise ValueError("Aranacak parça yok.")
    _validate_vector(query_embedding, dimension, "Sorgu embedding'i")
    results = []
    for chunk in chunks:
        _validate_vector(chunk.embedding, dimension, f"{chunk.source} embedding'i")
        results.append(SearchResult(
            chunk.source, chunk.chunk_number, chunk.text,
            cosine_similarity(query_embedding, chunk.embedding), chunk.file_type, chunk.page_number,
        ))
    results.sort(key=lambda item: (-item.score, item.source, item.chunk_number))
    return results[:top_k]
