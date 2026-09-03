"""İndeks ve gerekli modelleri ağ bağlantısı kurmadan kontrol eder."""

import argparse
from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from offline_assistant.health import check_local_health
from offline_assistant.config import Settings


def main() -> int:
    settings = Settings.load(PROJECT_ROOT)
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--db", type=Path, default=settings.database)
    parser.add_argument("--model-cache-dir", type=Path, default=settings.model_cache_dir)
    parser.add_argument("--chat-model", default=settings.chat_model)
    args = parser.parse_args()
    items = check_local_health(args.db, args.model_cache_dir, args.chat_model)
    for item in items:
        print(f"[{'OK' if item.ok else 'HATA'}] {item.name}: {item.detail}")
    ok = bool(items) and all(item.ok for item in items)
    print("\nYerel çalışma dosyaları hazır." if ok else "\nEksik veya bozuk yerel bileşen var.")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
