"""Ortam değişkenlerinden doğrulanmış ortak proje ayarları."""

from dataclasses import dataclass
import os
from pathlib import Path

from dotenv import load_dotenv

DEFAULT_CHAT_MODEL = "qwen2.5-1.5b"
DEFAULT_EMBEDDING_MODEL = "qwen3-embedding-0.6b"
DEFAULT_TOP_K = 3
DEFAULT_MIN_SCORE = 0.35
DEFAULT_MIN_SOURCE_MARGIN = 0.02
DEFAULT_MAX_SCORE_DROP = 0.15
DEFAULT_MAX_CHARS = 600
DEFAULT_MAX_TOKENS = 256


def _number(name: str, default, cast, low: float, high: float):
    raw = os.getenv(name)
    try:
        value = default if raw is None else cast(raw)
    except ValueError as exc:
        raise ValueError(f"{name} sayısal olmalıdır.") from exc
    if not low <= value <= high:
        raise ValueError(f"{name}, {low} ile {high} arasında olmalıdır.")
    return value


@dataclass(frozen=True)
class Settings:
    project_root: Path
    source_dir: Path
    database: Path
    app_data_dir: Path
    model_cache_dir: Path
    chat_model: str
    embedding_model: str
    top_k: int
    min_score: float
    min_source_margin: float
    max_score_drop: float
    max_chars: int
    max_tokens: int

    @classmethod
    def load(cls, project_root: Path) -> "Settings":
        root = project_root.resolve()
        load_dotenv(root / ".env", override=False)

        def path(name: str, default: str) -> Path:
            value = Path(os.getenv(name, default)).expanduser()
            return value.resolve() if value.is_absolute() else (root / value).resolve()

        chat = os.getenv("OFFLINE_ASSISTANT_CHAT_MODEL", DEFAULT_CHAT_MODEL).strip()
        embedding = os.getenv("OFFLINE_ASSISTANT_EMBEDDING_MODEL", DEFAULT_EMBEDDING_MODEL).strip()
        if not chat or not embedding:
            raise ValueError("Model adları boş olamaz.")
        app_data = path("OFFLINE_ASSISTANT_APP_DATA_DIR", "data/foundry")
        return cls(
            root, path("OFFLINE_ASSISTANT_SOURCE_DIR", "data/raw"),
            path("OFFLINE_ASSISTANT_DATABASE", "data/database/assistant.db"), app_data,
            path("OFFLINE_ASSISTANT_MODEL_CACHE_DIR", "data/foundry/cache/models"), chat, embedding,
            _number("OFFLINE_ASSISTANT_TOP_K", DEFAULT_TOP_K, int, 1, 100),
            _number("OFFLINE_ASSISTANT_MIN_SCORE", DEFAULT_MIN_SCORE, float, -1, 1),
            _number("OFFLINE_ASSISTANT_MIN_SOURCE_MARGIN", DEFAULT_MIN_SOURCE_MARGIN, float, 0, 2),
            _number("OFFLINE_ASSISTANT_MAX_SCORE_DROP", DEFAULT_MAX_SCORE_DROP, float, 0, 2),
            _number("OFFLINE_ASSISTANT_MAX_CHARS", DEFAULT_MAX_CHARS, int, 1, 100000),
            _number("OFFLINE_ASSISTANT_MAX_TOKENS", DEFAULT_MAX_TOKENS, int, 1, 8192),
        )
