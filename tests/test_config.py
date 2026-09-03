import pytest

from src.offline_assistant.config import Settings


def test_default_settings_are_resolved_from_project_root(tmp_path, monkeypatch):
    for name in list(__import__("os").environ):
        if name.startswith("OFFLINE_ASSISTANT_"):
            monkeypatch.delenv(name)
    settings = Settings.load(tmp_path)
    assert settings.database == (tmp_path / "data/database/assistant.db").resolve()
    assert settings.chat_model == "qwen2.5-1.5b"
    assert settings.min_source_margin == 0.02


def test_environment_overrides_are_validated(tmp_path, monkeypatch):
    monkeypatch.setenv("OFFLINE_ASSISTANT_TOP_K", "7")
    monkeypatch.setenv("OFFLINE_ASSISTANT_DATABASE", "custom/index.db")
    settings = Settings.load(tmp_path)
    assert settings.top_k == 7
    assert settings.database == (tmp_path / "custom/index.db").resolve()

    monkeypatch.setenv("OFFLINE_ASSISTANT_MIN_SCORE", "2")
    with pytest.raises(ValueError, match="OFFLINE_ASSISTANT_MIN_SCORE"):
        Settings.load(tmp_path)
