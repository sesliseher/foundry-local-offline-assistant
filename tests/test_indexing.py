from io import StringIO
from pathlib import Path

import pytest

from src.offline_assistant.indexing import run_ingestion


class FakeProcess:
    def __init__(self):
        self.stdout = StringIO("Hazırlanıyor\nEmbedding üretildi: 2/2\n")

    def wait(self):
        return 0


def test_run_ingestion_uses_argument_list_and_streams_output(tmp_path, monkeypatch):
    captured = {}

    def fake_popen(command, **kwargs):
        captured.update(command=command, kwargs=kwargs)
        return FakeProcess()

    monkeypatch.setattr("src.offline_assistant.indexing.subprocess.Popen", fake_popen)
    lines_seen = []
    code, lines = run_ingestion(
        Path("python"), Path("ingest.py"), tmp_path, tmp_path, tmp_path / "db.sqlite",
        600, lines_seen.append,
    )
    assert code == 0
    assert lines == lines_seen == ["Hazırlanıyor", "Embedding üretildi: 2/2"]
    assert captured["kwargs"]["shell"] is False
    assert "--save" in captured["command"]


def test_run_ingestion_rejects_missing_source_directory(tmp_path):
    with pytest.raises(ValueError, match="Belge klasörü bulunamadı"):
        run_ingestion(Path("python"), Path("script"), tmp_path, tmp_path / "missing", Path("db"), 600)
