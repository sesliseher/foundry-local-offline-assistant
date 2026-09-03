"""Streamlit gibi istemcilerden indeksleme betiğini güvenli biçimde çalıştırır."""

from pathlib import Path
import subprocess
from typing import Callable


def run_ingestion(
    python_executable: Path,
    script: Path,
    project_root: Path,
    input_dir: Path,
    database: Path,
    max_chars: int,
    on_line: Callable[[str], None] | None = None,
) -> tuple[int, list[str]]:
    if max_chars < 1:
        raise ValueError("Parça boyutu sıfırdan büyük olmalıdır.")
    if not input_dir.resolve().is_dir():
        raise ValueError(f"Belge klasörü bulunamadı: {input_dir.resolve()}")
    command = [
        str(python_executable), "-X", "utf8", str(script), "--save",
        "--input-dir", str(input_dir), "--db", str(database),
        "--max-chars", str(max_chars),
    ]
    process = subprocess.Popen(
        command, cwd=project_root, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
        text=True, encoding="utf-8", errors="replace", shell=False,
    )
    lines = []
    assert process.stdout is not None
    for raw_line in process.stdout:
        line = raw_line.rstrip()
        if line:
            lines.append(line)
            if on_line:
                on_line(line)
    return process.wait(), lines
