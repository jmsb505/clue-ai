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


_SECTION_HEADINGS = {
    "summary": {
        "summary", "profile", "professional summary", "career summary", "career objective",
        "about me", "objective",
        "obiettivo", "profilo", "profilo professionale",
    },
    "target_roles": {
        "target roles", "desired roles", "target position", "desired position", "desired job titles",
        "position sought", "roles of interest", "ruoli desiderati", "ruolo desiderato",
        "posizione desiderata", "posizioni desiderate", "ruoli di interesse",
    },
    "skills": {
        "skills", "technical skills", "core skills", "competencies", "key competencies",
        "technical competencies", "expertise", "key skills", "competenze", "competenze tecniche",
        "competenze digitali",
    },
    "experience": {
        "experience", "work experience", "employment history", "professional experience",
        "work history", "career history", "professional background", "esperienza",
        "esperienze", "esperienza professionale", "esperienze professionali",
        "esperienza lavorativa", "esperienze lavorative", "storia lavorativa",
    },
    "education": {
        "education", "education and training", "academic background", "academic history",
        "istruzione", "formazione", "istruzione e formazione", "formazione scolastica",
        "titoli di studio",
    },
    "languages": {
        "languages", "language skills", "language", "lingue", "lingue straniere",
        "competenze linguistiche",
    },
}
_SECTION_FOR_HEADING = {
    heading: key for key, values in _SECTION_HEADINGS.items() for heading in values
}
_ROLE_MARKERS = {
    "accountant", "administrator", "analyst", "architect", "artist", "assistant",
    "attorney", "chef", "consultant", "coordinator", "designer", "developer",
    "director", "engineer", "executive", "finance", "founder", "illustrator",
    "lawyer", "lead", "manager", "marketer", "marketing", "nurse", "operations",
    "physician", "planner", "producer", "product", "programmer", "project manager",
    "researcher", "scientist", "specialist", "strategist", "support", "teacher",
    "technician", "therapist", "writer", "ingegnere", "progettista", "sviluppatore",
    "programmatore", "analista", "consulente", "ricercatore", "responsabile",
    "advisor", "adviser", "recruiter", "sales", "security", "devops", "infermiere",
    "insegnante",
}
_ROLE_SENTENCE_VERBS = {
    "built", "created", "delivered", "developed", "improved", "implemented", "led",
    "managed", "partnered", "responsible", "supporting", "worked", "working",
    "connect", "connects", "connecting", "bridge", "bridges", "translate", "translates",
    "combine", "combines", "helps", "drives",
}


def suggest_profile_sections(text: str) -> dict[str, str]:
    """Extract labeled CV sections locally; the owner can edit them after parsing."""
    sections: dict[str, list[str]] = {key: [] for key in _SECTION_HEADINGS}
    active = ""
    for line in text.splitlines():
        cleaned = line.strip(" :\t-•")
        normalized = cleaned.casefold()
        if normalized in _SECTION_FOR_HEADING:
            active = _SECTION_FOR_HEADING[normalized]
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


def parse_candidate_profile(text: str) -> dict[str, str]:
    """Create conservative, editable search-profile fields without a remote CV parser."""
    sections = suggest_profile_sections(text)
    header = _resume_header(text)
    summary = sections.get("summary", "").strip() or _header_summary(header)
    target_roles = _explicit_role_titles(sections.get("target_roles", "")) or _infer_target_roles(
        header, sections.get("experience", "")
    )
    return {
        "summary": summary[:2_500],
        "target_roles": target_roles[:2_000],
        "skills": sections.get("skills", "")[:8_000],
        "experience": sections.get("experience", "")[:8_000],
        "education": sections.get("education", "")[:4_000],
        "languages": sections.get("languages", "")[:2_000],
        "profile_language": infer_profile_language(text),
    }


def infer_profile_language(text: str) -> str:
    """Return a language only when common English or Italian words are decisive."""
    tokens = re.findall(r"[a-zA-ZÀ-ÿ']+", text.casefold())
    if len(tokens) < 25:
        return "unknown"
    english_words = {
        "a", "about", "and", "are", "as", "at", "be", "by", "for", "from", "have",
        "in", "is", "it", "of", "on", "or", "the", "to", "with", "work", "experience",
        "skills", "team", "developed", "responsible", "worked", "across",
    }
    italian_words = {
        "a", "al", "alla", "alle", "con", "da", "del", "della", "di", "e", "gli",
        "il", "in", "la", "le", "lo", "per", "su", "un", "una", "esperienza",
        "competenze", "lavoro", "azienda", "responsabile", "sviluppato",
    }
    english_hits = sum(word in english_words for word in tokens)
    italian_hits = sum(word in italian_words for word in tokens)
    if english_hits >= 4 and english_hits >= max(1, italian_hits * 2):
        return "en"
    if italian_hits >= 4 and italian_hits >= max(1, english_hits * 2):
        return "it"
    return "unknown"


def _resume_header(text: str) -> list[str]:
    header: list[str] = []
    for line in text.splitlines():
        cleaned = line.strip(" :\t-•")
        if cleaned.casefold() in _SECTION_FOR_HEADING:
            break
        if cleaned:
            header.append(cleaned)
        if len(header) >= 20:
            break
    return header


def _header_summary(lines: list[str]) -> str:
    candidates = []
    for line in lines:
        if _role_title_candidate(line):
            continue
        if len(line) < 45 or len(line) > 300 or re.search(r"@|https?://|www\.", line, re.IGNORECASE):
            continue
        if re.search(r"(?=(?:\D*\d){9,})\+?\d[\d\s().-]{7,}\d", line):
            continue
        candidates.append(line)
        if len(candidates) == 2:
            break
    return " ".join(candidates)


def _infer_target_roles(header: list[str], experience: str) -> str:
    candidates: list[str] = []
    for line in [*header, *experience.splitlines()]:
        title = _role_title_candidate(line)
        if title and title.casefold() not in {value.casefold() for value in candidates}:
            candidates.append(title)
        if len(candidates) >= 3:
            break
    return ", ".join(candidates)


def _explicit_role_titles(value: str) -> str:
    titles = []
    for candidate in re.split(r"[,;|\n•]+", value):
        cleaned = candidate.strip(" \t-•|:;,.\n")
        cleaned = re.sub(
            r"^(?:seeking|looking for|targeting)\s+(?:a|an|the)?\s*",
            "",
            cleaned,
            flags=re.IGNORECASE,
        )
        words = re.findall(r"[\w+#./'-]+", cleaned, flags=re.UNICODE)
        if not cleaned or len(words) > 10 or len(cleaned) > 90 or re.search(r"[!?]", cleaned):
            continue
        if any(word.casefold() in _ROLE_SENTENCE_VERBS for word in words[:3]):
            continue
        if cleaned.casefold() not in {title.casefold() for title in titles}:
            titles.append(cleaned)
        if len(titles) >= 5:
            break
    return ", ".join(titles)


def _role_title_candidate(line: str) -> str:
    cleaned = line.strip(" \t-•|:;,.")
    cleaned = re.sub(
        r"^(?:\d{4}\s*[-–—]\s*(?:\d{4}|present|current)\s*)",
        "",
        cleaned,
        flags=re.IGNORECASE,
    )
    cleaned = re.sub(r"\s*\(?\b(?:19|20)\d{2}\s*[-–—].*$", "", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"\s*\((?:present|current|today)\)\s*$", "", cleaned, flags=re.IGNORECASE)
    for separator in (" | ", " • ", " — ", " – ", ", ", " at ", " @ "):
        if separator in cleaned:
            pieces = [piece.strip() for piece in cleaned.split(separator) if piece.strip()]
            marked = next((piece for piece in pieces if _has_role_marker(piece)), "")
            if marked:
                cleaned = marked
                break
    if " as " in cleaned.casefold():
        cleaned = re.split(r"\s+as\s+", cleaned, maxsplit=1, flags=re.IGNORECASE)[-1]
    words = re.findall(r"[\w+#./'-]+", cleaned, flags=re.UNICODE)
    if not 1 < len(words) <= 10 or len(cleaned) > 90:
        return ""
    normalized_words = [word.casefold().strip(".,;:") for word in words]
    if not _has_role_marker(" ".join(normalized_words)):
        return ""
    if any(word in _ROLE_SENTENCE_VERBS for word in normalized_words[:3]) or re.search(r"[.!?]", cleaned):
        return ""
    return " ".join(words).strip("-–—|,;: ")


def _has_role_marker(value: str) -> bool:
    words = set(re.findall(r"[a-zA-ZÀ-ÿ]+", value.casefold()))
    return any(marker in words or " ".join(marker.split()) in value.casefold() for marker in _ROLE_MARKERS)
