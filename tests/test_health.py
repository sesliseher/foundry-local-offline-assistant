import json

from src.offline_assistant.documents import Chunk
from src.offline_assistant.health import check_local_health
from src.offline_assistant.storage import save_index


def _catalog(cache, model_id="embedding:1", chat_alias="chat"):
    models = [
        {"id": model_id, "alias": "embedding", "publisher": "Microsoft", "name": "embedding", "version": 1},
        {"id": "chat:1", "alias": chat_alias, "publisher": "Microsoft", "name": "chat", "version": 1},
    ]
    cache.mkdir(parents=True)
    (cache / "foundry.modelinfo.json").write_text(json.dumps({"models": models}), encoding="utf-8")
    for name in ("embedding", "chat"):
        folder = cache / "Microsoft" / f"{name}-1" / "v1"
        folder.mkdir(parents=True)
        (folder / "model.onnx").write_bytes(b"model")


def test_health_passes_with_index_and_both_models(tmp_path):
    database = tmp_path / "assistant.db"
    save_index(database, tmp_path, "embedding:1", 600, [Chunk("a.txt", 1, "metin")], [[1]])
    cache = tmp_path / "models"
    _catalog(cache)
    items = check_local_health(database, cache, "chat")
    assert items and all(item.ok for item in items)


def test_health_reports_missing_chat_model(tmp_path):
    database = tmp_path / "assistant.db"
    save_index(database, tmp_path, "embedding:1", 600, [Chunk("a.txt", 1, "metin")], [[1]])
    cache = tmp_path / "models"
    _catalog(cache)
    items = check_local_health(database, cache, "missing")
    assert next(item for item in items if item.name == "Sohbet modeli").ok is False
