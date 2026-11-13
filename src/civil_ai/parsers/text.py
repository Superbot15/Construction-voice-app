"""Text extraction from source documents."""

from __future__ import annotations

from pathlib import Path


def extract_text(path: str | Path) -> str:
    """Return the plain text of a .txt/.md or (with the ``pdf`` extra) .pdf file."""
    p = Path(path)
    if p.suffix.lower() == ".pdf":
        try:
            from pypdf import PdfReader
        except ImportError as exc:  # pragma: no cover - depends on optional extra
            raise RuntimeError("PDF support needs: pip install 'civil-ai[pdf]'") from exc
        reader = PdfReader(str(p))
        return "\n".join(page.extract_text() or "" for page in reader.pages)
    return p.read_text(encoding="utf-8", errors="replace")
