from contextlib import closing
import json
import sqlite3

import pytest

from src.offline_assistant.documents import Chunk
from src.offline_assistant.storage import save_index


def read_rows(database):
    with closing(sqlite3.connect(database)) as connection:
        return connection.execute("SELECT * FROM chunks ORDER BY source, chunk_number").fetchall()


def test_reopen_and_repeat_do_not_duplicate(tmp_path):
    database = tmp_path / "assistant.db"
    chunks = [Chunk("öğrenci.txt", 1, "Türkçe içerik")]
    for _ in range(2):
        save_index(database, tmp_path, "embedding-model:1", 600, chunks, [[0.5, 0.2]])
    rows = read_rows(database)
    assert len(rows) == 1
    assert rows[0][:3] == ("öğrenci.txt", 1, "Türkçe içerik")
    assert json.loads(rows[0][3]) == [0.5, 0.2]
    with closing(sqlite3.connect(database)) as connection:
        assert connection.execute("SELECT model_id, dimension, max_chars FROM index_metadata").fetchone() == (
            "embedding-model:1", 2, 600
        )


def test_refresh_removes_old_chunks_and_replaces_model_metadata(tmp_path):
    database = tmp_path / "assistant.db"
    save_index(database, tmp_path, "old", 600,
               [Chunk("a.txt", 1, "eski"), Chunk("b.txt", 1, "silinen")], [[1, 0], [0, 1]])
    save_index(database, tmp_path, "new", 350, [Chunk("a.txt", 1, "güncel")], [[1, 0, 0]])
    assert [row[:3] for row in read_rows(database)] == [("a.txt", 1, "güncel")]
    with closing(sqlite3.connect(database)) as connection:
        assert connection.execute("SELECT model_id, dimension FROM index_metadata").fetchone() == ("new", 3)


@pytest.mark.parametrize("vectors", [[], [[]], [[0, 0]], [[float("nan")]]])
def test_invalid_vectors_preserve_existing_index(tmp_path, vectors):
    database = tmp_path / "assistant.db"
    chunks = [Chunk("a.txt", 1, "orijinal")]
    save_index(database, tmp_path, "model", 600, chunks, [[1, 0]])
    before = read_rows(database)
    with pytest.raises(ValueError):
        save_index(database, tmp_path, "model", 600, chunks, vectors)
    assert read_rows(database) == before


def test_sql_error_rolls_back_delete_and_metadata(tmp_path):
    database = tmp_path / "assistant.db"
    save_index(database, tmp_path, "old", 600, [Chunk("a.txt", 1, "eski")], [[1]])
    before = read_rows(database)
    with closing(sqlite3.connect(database)) as connection:
        connection.execute("""CREATE TRIGGER fail_insert BEFORE INSERT ON chunks
                              BEGIN SELECT RAISE(ABORT, 'test failure'); END""")
    with pytest.raises(sqlite3.IntegrityError):
        save_index(database, tmp_path, "new", 600, [Chunk("a.txt", 1, "yeni")], [[2]])
    assert read_rows(database) == before
    with closing(sqlite3.connect(database)) as connection:
        assert connection.execute("SELECT model_id FROM index_metadata").fetchone()[0] == "old"


def test_other_source_root_cannot_overwrite_index(tmp_path):
    database = tmp_path / "assistant.db"
    chunks = [Chunk("a.txt", 1, "metin")]
    save_index(database, tmp_path / "one", "model", 600, chunks, [[1]])
    before = read_rows(database)
    with pytest.raises(ValueError, match="başka bir kaynak"):
        save_index(database, tmp_path / "two", "model", 600, chunks, [[1]])
    assert read_rows(database) == before
