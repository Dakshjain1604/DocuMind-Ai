"""Upload handling and document loading (including the scanned-PDF OCR path).

All of this is synchronous and slow — PyPDFLoader, Unstructured, and
especially pytesseract, which can occupy the CPU for minutes on a large
scanned document. Callers must run load_documents() in a threadpool; it used
to be awaited inline in the /index handler, blocking the whole event loop.
"""
from __future__ import annotations

import logging
import shutil
import uuid
from dataclasses import dataclass
from pathlib import Path

from langchain_core.documents import Document
from langchain_community.document_loaders import (
    PyPDFLoader,
    TextLoader,
    UnstructuredWordDocumentLoader,
)

from app.config.settings import get_settings

logger = logging.getLogger(__name__)


class UnsafeFilename(ValueError):
    """Raised when an uploaded filename cannot be made safe to write."""


@dataclass(frozen=True)
class SavedUpload:
    path: Path
    display_name: str
    suffix: str


def upload_dir() -> Path:
    d = Path(get_settings().upload_dir)
    d.mkdir(parents=True, exist_ok=True)
    return d


def save_upload(content: bytes, filename: str | None) -> SavedUpload:
    """Write an upload under a generated name inside the upload directory.

    UploadFile.filename comes from the Content-Disposition header and Starlette
    does not sanitize it, so `../../etc/x.txt` would otherwise be written
    verbatim. Only the basename is used, and it is prefixed with a uuid so two
    uploads of the same name cannot clobber each other.
    """
    display_name = filename or "upload"
    safe_name = Path(display_name).name
    if not safe_name or safe_name in {".", ".."}:
        safe_name = "upload"

    root = upload_dir()
    path = root / f"{uuid.uuid4().hex}_{safe_name}"
    if root.resolve() not in path.resolve().parents:
        raise UnsafeFilename(f"unsafe filename: {display_name!r}")

    path.write_bytes(content)
    return SavedUpload(path=path, display_name=display_name, suffix=Path(display_name).suffix.lower())


def cleanup_upload(path: Path) -> None:
    """Remove a saved upload once it has been parsed.

    Uploads are only needed until the loader has read them; leaving them in
    place grew the directory without bound and kept user documents on disk
    indefinitely.
    """
    try:
        path.unlink(missing_ok=True)
    except OSError as e:
        logger.warning("could not remove upload %s: %s", path, e)


def _ocr_pdf(path: Path) -> list[Document]:
    """Rasterise and OCR a PDF whose text layer is empty (i.e. a scan)."""
    from pdf2image import convert_from_path
    import pytesseract

    settings = get_settings()
    configured = settings.tesseract_cmd
    if configured:
        pytesseract.pytesseract.tesseract_cmd = configured
    elif not shutil.which("tesseract"):
        raise RuntimeError(
            "tesseract is not on PATH. Install it, or set RAG_TESSERACT_CMD to its location."
        )

    langs = settings.ocr_languages
    try:
        available = set(pytesseract.get_languages(config=""))
        missing = [code for code in langs.split("+") if code not in available]
        if missing:
            logger.warning(
                "OCR languages %s are not installed; falling back to eng", ", ".join(missing)
            )
            langs = "eng"
    except Exception as e:
        logger.warning("could not enumerate tesseract languages (%s); using %s", e, langs)

    docs: list[Document] = []
    for i, img in enumerate(convert_from_path(str(path))):
        text = pytesseract.image_to_string(img, lang=langs)
        if text.strip():
            docs.append(Document(page_content=text, metadata={"source": str(path), "page": i + 1}))
    return docs


def load_documents(path: Path, file_type: str) -> list[Document]:
    """Parse a saved upload into LangChain Documents. Blocking — see module docstring."""
    if file_type == ".pdf":
        docs = PyPDFLoader(str(path)).load()
        if docs and any(d.page_content.strip() for d in docs):
            return docs
        logger.info("no text layer in %s; falling back to OCR", path.name)
        try:
            return _ocr_pdf(path)
        except Exception as e:
            raise RuntimeError(f"OCR extraction failed for scanned PDF: {e}") from e
    if file_type in {".txt", ".md"}:
        return TextLoader(str(path)).load()
    return UnstructuredWordDocumentLoader(str(path)).load()
