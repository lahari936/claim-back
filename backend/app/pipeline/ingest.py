"""Step 1: file -> text. Digital PDFs via PyMuPDF; scans and photos via the vision model."""
from pathlib import Path

import pymupdf

from app.llm.client import transcribe_image

MIN_CHARS_PER_PAGE = 50  # below this a PDF page is treated as a scan


def ingest(path: Path, case_id: str | None) -> str:
    if path.suffix.lower() != ".pdf":
        return transcribe_image(path.read_bytes(), case_id)
    pages = []
    with pymupdf.open(path) as doc:
        for page in doc:
            text = page.get_text()
            if len(text.strip()) < MIN_CHARS_PER_PAGE:
                text = transcribe_image(page.get_pixmap(dpi=150).tobytes("png"), case_id)
            pages.append(text)
    return "\n".join(pages)
