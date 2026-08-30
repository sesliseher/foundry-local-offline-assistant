"""TXT okuma ve kaynak bilgisini koruyan, paragraf temelli parçalama."""

from dataclasses import dataclass
from pathlib import Path
import re


@dataclass(frozen=True)
class Document:
    source: str
    text: str


@dataclass(frozen=True)
class Chunk:
    source: str
    chunk_number: int
    text: str


def read_txt_documents(directory: Path, encoding: str = "utf-8-sig") -> list[Document]:
    """Alt klasörleri tarar; aynı adlı dosyaları göreli yollarıyla ayırt eder."""
    directory = directory.resolve()
    if not directory.is_dir():
        raise ValueError(f"Belge klasörü bulunamadı: {directory}")
    paths = sorted(
        (path for path in directory.rglob("*") if path.is_file() and path.suffix.lower() == ".txt"),
        key=lambda path: path.relative_to(directory).as_posix(),
    )
    documents = []
    for path in paths:
        source = path.relative_to(directory).as_posix()
        try:
            text = path.read_text(encoding=encoding)
        except UnicodeError as exc:
            raise ValueError(
                f"{source} dosyası {encoding} ile okunamadı. Dosyayı UTF-8 kaydedin "
                "veya doğru --encoding seçeneğini kullanın."
            ) from exc
        documents.append(Document(source=source, text=text))
    return documents


def split_document(document: Document, max_chars: int = 600) -> list[Chunk]:
    """Paragrafları mümkün olduğunca korur; sınır karakter sayısıdır, token değil."""
    if max_chars < 1:
        raise ValueError("Parça boyutu sıfırdan büyük olmalıdır.")
    text = document.text.replace("\r\n", "\n").replace("\r", "\n")
    paragraphs = [
        " ".join(paragraph.split())
        for paragraph in re.split(r"\n\s*\n", text)
        if paragraph.strip()
    ]
    pieces = []
    for paragraph in paragraphs:
        # Uzun paragraflarda kelime sınırını tercih et; çok uzun tek kelimeyi böl.
        while len(paragraph) > max_chars:
            boundary = paragraph.rfind(" ", 0, max_chars + 1)
            if boundary <= 0:
                boundary = max_chars
            pieces.append(paragraph[:boundary])
            paragraph = paragraph[boundary:].lstrip()
        if paragraph:
            pieces.append(paragraph)

    texts = []
    current = ""
    for piece in pieces:
        combined = f"{current}\n\n{piece}" if current else piece
        if len(combined) <= max_chars:
            current = combined
        else:
            texts.append(current)
            current = piece
    if current:
        texts.append(current)
    return [Chunk(document.source, number, content) for number, content in enumerate(texts, start=1)]
