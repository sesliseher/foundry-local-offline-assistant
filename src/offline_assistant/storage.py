"""Küçük bir belge koleksiyonunu SQLite'a atomik olarak kaydeder."""

from contextlib import closing
import json
import math
from pathlib import Path
import sqlite3

from .documents import Chunk


def save_index(
    database: Path,
    source_root: Path,
    model_id: str,
    max_chars: int,
    chunks: list[Chunk],
    vectors: list[list[float]],
) -> int:
    """Tüm yeni veriyi doğrular, sonra eski indeksi tek transaction ile yeniler.

    İndeks bir kaynak klasörüne aittir. Her başarılı kayıt o klasörün güncel
    görüntüsüdür; eski parçalar ve silinmiş belgeler indeks içinde tutulmaz.
    """
    if not chunks or len(chunks) != len(vectors):
        raise ValueError("Parçalar boş olamaz; her parçanın bir embedding'i olmalıdır.")
    if not model_id.strip() or max_chars < 1:
        raise ValueError("Model kimliği ve parça boyutu geçerli olmalıdır.")
    dimension = len(vectors[0])
    if not dimension:
        raise ValueError("Embedding boş olamaz.")
    keys = [(chunk.source, chunk.chunk_number) for chunk in chunks]
    if len(set(keys)) != len(keys):
        raise ValueError("Aynı kaynak ve parça numarası birden fazla kez kullanılamaz.")
    rows = []
    for chunk, vector in zip(chunks, vectors):
        if not chunk.source or chunk.chunk_number < 1 or not chunk.text.strip():
            raise ValueError("Parçanın kaynağı, numarası ve metni geçerli olmalıdır.")
        if len(vector) != dimension or not all(math.isfinite(value) for value in vector):
            raise ValueError("Embedding boyutları eşit, değerleri sonlu olmalıdır.")
        if not any(value != 0 for value in vector):
            raise ValueError("Sıfır embedding kaydedilemez.")
        rows.append((chunk.source, chunk.chunk_number, chunk.text, json.dumps(vector, allow_nan=False)))

    database = database.resolve()
    source_root = str(source_root.resolve())
    database.parent.mkdir(parents=True, exist_ok=True)
    with closing(sqlite3.connect(database)) as connection:
        # DDL dahil bütün yenileme aynı transaction içindedir.
        with connection:
            connection.execute("BEGIN IMMEDIATE")
            connection.execute("""
                CREATE TABLE IF NOT EXISTS index_metadata (
                    id INTEGER PRIMARY KEY CHECK (id = 1),
                    source_root TEXT NOT NULL,
                    model_id TEXT NOT NULL,
                    dimension INTEGER NOT NULL,
                    max_chars INTEGER NOT NULL
                )
            """)
            connection.execute("""
                CREATE TABLE IF NOT EXISTS chunks (
                    source TEXT NOT NULL,
                    chunk_number INTEGER NOT NULL,
                    text TEXT NOT NULL,
                    embedding_json TEXT NOT NULL,
                    PRIMARY KEY (source, chunk_number)
                )
            """)
            existing = connection.execute("SELECT source_root FROM index_metadata WHERE id = 1").fetchone()
            if existing and Path(existing[0]) != Path(source_root):
                raise ValueError("Bu veritabanı başka bir kaynak klasörüne ait. Farklı --db yolu seçin.")
            connection.execute("DELETE FROM chunks")
            connection.executemany(
                "INSERT INTO chunks (source, chunk_number, text, embedding_json) VALUES (?, ?, ?, ?)", rows
            )
            connection.execute(
                "INSERT OR REPLACE INTO index_metadata VALUES (1, ?, ?, ?, ?)",
                (source_root, model_id, dimension, max_chars),
            )
    return len(rows)
