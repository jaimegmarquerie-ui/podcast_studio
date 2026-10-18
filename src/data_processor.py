"""Step 1 - Data input.

Takes the raw text of a book sheet (pasted, or read from a .txt/.md/.pdf
file), cleans it and organises it in a standard dictionary. Why a dictionary:
the LLM and audio steps always receive the same structure, no matter where
the text came from.
"""

import re
import unicodedata
from pathlib import Path

# Accepted field names (Spanish or English) -> standard metadata key.
FIELD_ALIASES = {
    "titulo": "title",
    "title": "title",
    "autor": "author",
    "autora": "author",
    "author": "author",
    "genero": "genre",
    "genre": "genre",
    "publico": "audience",
    "audience": "audience",
    "tono": "tone",
    "tone": "tone",
    "fuente": "source",
    "source": "source",
}

MIN_LENGTH = 40  # characters; shorter texts are not a real sheet
SUPPORTED_FILES = (".txt", ".md", ".pdf")


def clean_text(text: str) -> str:
    """Remove extra spaces and repeated empty lines.

    Why: pasted text and PDF text often carry irregular spacing that would
    only add noise to the prompt sent to the LLM.
    """
    text = (text or "").strip()
    text = re.sub(r"[ \t]+", " ", text)  # several spaces -> one
    text = re.sub(r"\n{3,}", "\n\n", text)  # many empty lines -> one
    return text


def _normalize(name: str) -> str:
    """Lowercase and remove accents: 'Género' -> 'genero'."""
    name = unicodedata.normalize("NFD", name.lower().strip())
    return "".join(c for c in name if unicodedata.category(c) != "Mn")


def extract_metadata(text: str) -> dict:
    """Find lines like 'Title: ...' or 'Autor: ...' and return them as a dict."""
    metadata = {}
    for line in text.splitlines():
        match = re.match(r"^\s*([^:\n]{2,20}):\s*(.+)$", line)
        if not match:
            continue
        key = FIELD_ALIASES.get(_normalize(match.group(1)))
        if key and key not in metadata:
            metadata[key] = match.group(2).strip()
    return metadata


def read_text_file(path) -> str:
    """Read the text of a .txt, .md or .pdf file.

    Raises:
        ValueError: if the file type is not supported or has no readable text.
    """
    path = Path(path)
    suffix = path.suffix.lower()
    if suffix not in SUPPORTED_FILES:
        raise ValueError(f"Unsupported file type '{suffix}'. Use .txt, .md or .pdf.")
    if suffix == ".pdf":
        try:
            from pypdf import PdfReader
        except ImportError:
            raise ValueError("PDF support needs the 'pypdf' library: pip install pypdf")
        reader = PdfReader(str(path))
        text = "\n".join((page.extract_text() or "") for page in reader.pages)
    else:
        text = path.read_text(encoding="utf-8", errors="replace")
    if not text.strip():
        raise ValueError("The file has no readable text (a scanned PDF has none).")
    return text


def parse_sheet(raw_text: str) -> dict:
    """Turn raw text into the standard sheet dictionary.

    Returns:
        {"metadata": {...}, "text": "<clean text>", "word_count": int}

    Raises:
        ValueError: if the text is too short to be a book sheet.
    """
    text = clean_text(raw_text)
    if len(text) < MIN_LENGTH:
        raise ValueError("The book sheet is too short. Paste a longer text.")
    metadata = extract_metadata(text)
    if "title" not in metadata:  # no "Title:" line: use the first line instead
        first_line = text.splitlines()[0].strip("#*_ \t")
        metadata["title"] = first_line[:80]
    return {
        "metadata": metadata,
        "text": text,
        "word_count": len(text.split()),
    }
