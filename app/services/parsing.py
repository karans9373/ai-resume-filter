from io import BytesIO
from pathlib import Path

from docx import Document
from pypdf import PdfReader


SUPPORTED_EXTENSIONS = {".pdf", ".docx", ".txt"}


def extract_text_from_upload(filename: str, content: bytes) -> str:
    extension = Path(filename).suffix.lower()

    if extension not in SUPPORTED_EXTENSIONS:
        raise ValueError(f"Unsupported file type: {extension}")

    if extension == ".pdf":
        reader = PdfReader(BytesIO(content))
        text = "\n".join((page.extract_text() or "").strip() for page in reader.pages).strip()
        if not text:
            raise ValueError(
                f"{filename} does not contain selectable text. Add OCR support for image-only PDFs."
            )
        return text

    if extension == ".docx":
        document = Document(BytesIO(content))
        return "\n".join(paragraph.text for paragraph in document.paragraphs).strip()

    return content.decode("utf-8", errors="ignore").strip()
