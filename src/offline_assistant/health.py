"""Ağ kullanmadan yerel indeks ve model dosyalarının hazır olup olmadığını denetler."""

from dataclasses import dataclass
import json
from pathlib import Path

from .retrieval import load_index


@dataclass(frozen=True)
class HealthItem:
    name: str
    ok: bool
    detail: str


def _model_directory(cache: Path, metadata: dict) -> Path:
    publisher = metadata.get("publisher") or "Microsoft"
    name = metadata.get("name")
    version = metadata.get("version")
    return cache / publisher / f"{name}-{version}" / f"v{version}"


def check_local_health(database: Path, model_cache: Path, chat_alias: str) -> list[HealthItem]:
    items = []
    try:
        metadata, chunks = load_index(database)
        items.append(HealthItem("SQLite indeksi", True, f"{len(chunks)} parça, {metadata.dimension} boyut"))
        embedding_id = metadata.model_id
    except Exception as exc:
        items.append(HealthItem("SQLite indeksi", False, str(exc)))
        embedding_id = None

    catalog_path = model_cache / "foundry.modelinfo.json"
    try:
        catalog = json.loads(catalog_path.read_text(encoding="utf-8-sig"))
        models = catalog.get("models", [])
    except Exception as exc:
        items.append(HealthItem("Yerel model kataloğu", False, f"Okunamadı: {exc}"))
        return items
    items.append(HealthItem("Yerel model kataloğu", True, f"{len(models)} model kaydı"))

    requirements = [("Embedding modeli", embedding_id, "id"), ("Sohbet modeli", chat_alias, "alias")]
    for label, value, key in requirements:
        model = next((entry for entry in models if entry.get(key) == value), None)
        if not model:
            items.append(HealthItem(label, False, f"Katalog kaydı bulunamadı: {value}"))
            continue
        directory = _model_directory(model_cache, model)
        files = [path for path in directory.rglob("*") if path.is_file()] if directory.is_dir() else []
        size = sum(path.stat().st_size for path in files)
        ok = bool(files) and size > 0
        detail = f"{model.get('id')} · {size / (1024 ** 2):.0f} MiB" if ok else f"Dosyalar eksik: {directory}"
        items.append(HealthItem(label, ok, detail))
    return items
