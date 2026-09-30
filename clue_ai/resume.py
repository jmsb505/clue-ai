from __future__ import annotations

import io
import re
import unicodedata
import zipfile
from pathlib import Path

from docx import Document
from pypdf import PdfReader

from clue_ai.config import Settings


class ResumeError(ValueError):
    pass


def extract_resume_text(filename: str, content: bytes, settings: Settings) -> str:
    suffix = Path(filename).suffix.lower()
    if not content:
        raise ResumeError("The selected file is empty.")
    if len(content) > settings.max_cv_bytes:
        raise ResumeError("CV files must be 12 MB or smaller.")
    if suffix == ".pdf":
        text = _extract_pdf(content, settings)
    elif suffix == ".docx":
        text = _extract_docx(content)
    else:
        raise ResumeError("Use a PDF or DOCX file.")
    text = _clean_text(text)[: settings.max_extracted_chars]
    if len(text.strip()) < 40:
        raise ResumeError(
            "The file has no usable selectable text. For a scanned PDF, use a text-based PDF or DOCX; this app does not send your CV to an OCR service."
        )
    return text


def _extract_pdf(content: bytes, settings: Settings) -> str:
    if not content.startswith(b"%PDF-"):
        raise ResumeError("The file extension says PDF, but the file is not a PDF document.")
    try:
        reader = PdfReader(io.BytesIO(content), strict=False)
        if reader.is_encrypted:
            raise ResumeError("Password-protected PDFs are not supported. Save an unlocked copy first.")
        if len(reader.pages) > settings.max_cv_pages:
            raise ResumeError(f"CVs can contain up to {settings.max_cv_pages} pages.")
        text_parts: list[str] = []
        for page in reader.pages:
            contents = page.get_contents()
            if contents is not None and len(contents.get_data()) > 1_500_000:
                raise ResumeError("A PDF page is too large to process safely. Try exporting a smaller CV.")
            text_parts.append(page.extract_text(extraction_mode="layout") or "")
        return "\n".join(text_parts)
    except ResumeError:
        raise
    except Exception as exc:
        raise ResumeError("The PDF could not be read. Try exporting it again as a standard PDF.") from exc


def _extract_docx(content: bytes) -> str:
    try:
        with zipfile.ZipFile(io.BytesIO(content)) as archive:
            members = archive.infolist()
            if len(members) > 800 or sum(item.file_size for item in members) > 25_000_000:
                raise ResumeError("This DOCX expands beyond the local extraction limit.")
            if "word/document.xml" not in archive.namelist():
                raise ResumeError("The file is not a valid DOCX document.")
        document = Document(io.BytesIO(content))
        text_parts: list[str] = []
        for item in document.iter_inner_content():
            if hasattr(item, "text"):
                text_parts.append(item.text)
            else:
                for row in item.rows:
                    text_parts.append(" | ".join(cell.text for cell in row.cells))
        return "\n".join(text_parts)
    except ResumeError:
        raise
    except (zipfile.BadZipFile, ValueError, KeyError) as exc:
        raise ResumeError("The DOCX could not be read. Try saving it again as a standard DOCX.") from exc
    except Exception as exc:
        raise ResumeError("The DOCX could not be read. Try saving it again as a standard DOCX.") from exc


def _clean_text(value: str) -> str:
    value = unicodedata.normalize("NFKC", value)
    value = value.replace("\x00", " ")
    value = re.sub(r"[\t\u00a0]+", " ", value)
    value = re.sub(r"[ \t]+\n", "\n", value)
    value = re.sub(r"\n{3,}", "\n\n", value)
    return "\n".join(line.strip() for line in value.splitlines()).strip()


def suggest_profile_sections(text: str) -> dict[str, str]:
    """Conservative local section suggestions; every value remains editable by the owner."""
    headings = {
        "summary": {"summary", "profile", "professional summary", "about me", "objective"},
        "skills": {"skills", "technical skills", "core skills", "competencies", "expertise"},
        "experience": {"experience", "work experience", "employment history", "professional experience"},
        "education": {"education", "education and training", "academic background"},
        "languages": {"languages", "language skills"},
    }
    section_for_heading = {heading: key for key, values in headings.items() for heading in values}
    sections: dict[str, list[str]] = {key: [] for key in headings}
    active = ""
    for line in text.splitlines():
        cleaned = line.strip(" :\t-•")
        normalized = cleaned.casefold()
        if normalized in section_for_heading:
            active = section_for_heading[normalized]
            continue
        if not cleaned:
            continue
        if active:
            sections[active].append(cleaned)
    return {
        key: "\n".join(lines)[:25_000]
        for key, lines in sections.items()
        if lines
    }
