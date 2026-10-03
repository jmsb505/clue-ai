"""Cheap, explainable relevance screening for this owner's AI engineering search."""

from __future__ import annotations

import re
from collections import Counter
from dataclasses import asdict, dataclass, is_dataclass
from typing import Any

from clue_ai.jobs import plain_text

FOCUS_VERSION = "ai-engineering-v1"
DEFAULT_ROLES = "AI Engineer, Machine Learning Engineer, LLM Engineer, MLOps Engineer"
ROLE_FAMILIES = (
    "AI / ML engineering",
    "LLM, RAG and agent engineering",
    "Computer vision / NLP",
    "ML deployment and inference",
    "AI backend / platform engineering",
    "ML data science / research",
)
_AI = r"(?:ai|ml|artificial intelligence|machine learning|deep learning|llms?|generative ai|genai|rag|nlp|natural language processing|computer vision|mlops|a i|m l)"
_MODEL = rf"(?:{_AI}|(?:predictive|classification|regression|language|neural|quantized) models?|model inference|image (?:registration|segmentation)|object detection|embeddings?|transformers?|pytorch|tensorflow|scikit.learn|xgboost|lightgbm|langchain|langgraph|hugging\s*face|neural networks?|onnx|tensorrt)"
_DIRECT = re.compile(rf"\b{_AI}\b", re.IGNORECASE)
_TECH_TITLE = re.compile(
    r"\b(?:engineer|developer|scientist|researcher|research|technical|programmer|software|architect|consultant|intern|internship|graduate|apprentice)\b",
    re.IGNORECASE,
)
_SENIOR = re.compile(
    r"\b(?:senior|sr\.?|staff|principal|lead|head|director|manager|mid[ -]level|experienced)\b",
    re.IGNORECASE,
)
_ENTRY = re.compile(
    r"\b(?:junior|jr\.?|intern|internship|graduate|entry[ -]level|trainee|apprentice)\b",
    re.IGNORECASE,
)
_NON_ENGINEERING = re.compile(
    r"\b(?:sales|marketing|recruiter|recruiting|recruitment|account executive|"
    r"customer (?:support|success|service)|business development|office|administrative|"
    r"executive assistant|copywriter|content writer|data entry|annotator|annotation|"
    r"data label(?:er|ling|ing)|rater|ai trainer|ai tutor|prompt writer|translator|"
    r"bookkeeper|accountant|business analyst|financial analyst|bi analyst|"
    r"business intelligence analyst|data analyst|product manager|project manager|"
    r"ux researcher|user researcher|chief of staff|revenue architect|"
    r"mechanical engineer|civil engineer)\b",
    re.IGNORECASE,
)
_IMPLEMENTATION = re.compile(
    rf"\b(?:build\w*|develop\w*|implement\w*|integrat\w*|train\w*|fine[ -]?tun\w*|"
    rf"deploy\w*|serv\w*|evaluat\w*|optim[izs]\w*|design\w*|research\w*)\b"
    rf"[^.!?\n]{{0,140}}\b{_MODEL}\b|"
    rf"\b{_MODEL}\b[^.!?\n]{{0,100}}\b(?:development|deployment|training|"
    rf"evaluation|integration|serving|optimization|fine[ -]?tuning|pipelines?)\b",
    re.IGNORECASE,
)
_UNPAID = re.compile(
    r"\bunpaid\s+(?:internship|position|role|opportunity|work)\b|"
    r"\bvolunteer\s+(?:internship|position|role|opportunity)\b|"
    r"\b(?:internship|position|role)\s+(?:is|will be)\s+(?:unpaid|voluntary)\b|"
    r"\b(?:equity[ -]only|no monetary compensation|no remuneration|"
    r"no salary (?:will be )?(?:paid|provided))\b",
    re.IGNORECASE,
)
_WORK_START = re.compile(
    r"\b(?:responsibilities|what you(?: will|['’]ll) (?:do|build|own)|what you['’]ll own|"
    r"your (?:role|impact|mission|tasks)|about (?:the|this) role|the role|"
    r"you (?:will|would|['’]ll) (?:build|develop|implement|integrate|design|deploy|work)|"
    r"what we(?:['’]re| are) looking for|requirements|qualifications)\b",
    re.IGNORECASE,
)
_WORK_END = re.compile(
    r"\b(?:about us|about the company|why join|what we offer|equal opportunity|"
    r"we['’]re not just building|we are not just building)\b",
    re.IGNORECASE,
)


def _work_evidence(description: str) -> str:
    """Ignore an introductory company/product pitch when a role section is available."""
    start = _WORK_START.search(description)
    if start:
        work = description[start.start() :]
        end = _WORK_END.search(work)
        return work[: end.start()] if end else work
    # Sparse postings without headings can pass on an actual instruction to the applicant.
    return " ".join(
        sentence
        for sentence in re.split(r"[.!?\n]", description)
        if re.search(
            r"\b(?:you|your|responsible|must|experience|proficiency)\b", sentence, re.IGNORECASE
        )
        or re.match(
            r"\s*(?:build|develop|implement|integrate|train|deploy|evaluate|design)\b",
            sentence,
            re.IGNORECASE,
        )
    )


@dataclass(frozen=True)
class FocusDecision:
    accepted: bool
    reason: str


def assess_focus(job: Any) -> FocusDecision:
    """Use title and work evidence, never company name or candidate contact fields."""
    values = asdict(job) if is_dataclass(job) else job
    title = re.sub(r"[\/_-]+", " ", str(values.get("title") or ""))
    description = plain_text(values.get("description"), 30_000)
    employment = str(values.get("employment_type") or "")
    if _SENIOR.search(title) and not _ENTRY.search(title):
        return FocusDecision(False, "explicit senior title")
    # Do not turn 'not unpaid' or a reference to past volunteer work into an exclusion.
    pay_text = re.sub(
        r"\b(?:not|never)\s+(?:be\s+)?(?:an?\s+)?unpaid\b", "paid", description, flags=re.IGNORECASE
    )
    if (
        re.search(r"\b(?:unpaid|volunteer)\b", title, re.IGNORECASE)
        or employment.casefold() == "volunteer"
        or _UNPAID.search(pay_text)
    ):
        return FocusDecision(False, "explicit unpaid work")
    if _NON_ENGINEERING.search(title):
        return FocusDecision(False, "non-engineering role")
    if (_DIRECT.search(title) and _TECH_TITLE.search(title)) or re.search(
        r"\bprompt engineer\b", title, re.IGNORECASE
    ):
        return FocusDecision(True, "AI engineering title")
    if re.search(r"\bdata scientist\b", title, re.IGNORECASE) and len(description) < 200:
        return FocusDecision(True, "model-building role; Jev verifies scope")
    if _TECH_TITLE.search(title) and _IMPLEMENTATION.search(_work_evidence(description)):
        return FocusDecision(True, "technical role with model implementation evidence")
    return FocusDecision(False, "no AI engineering evidence")


def focused_jobs(jobs: list[Any]) -> tuple[list[Any], Counter[str]]:
    accepted: list[Any] = []
    excluded: Counter[str] = Counter()
    for job in jobs:
        decision = assess_focus(job)
        if decision.accepted:
            accepted.append(job)
        else:
            excluded[decision.reason] += 1
    return accepted, excluded


def focus_note(excluded: Counter[str]) -> str:
    return "; ".join(f"{reason}: {count}" for reason, count in sorted(excluded.items())) or "none"


def focused_roles(raw_roles: str) -> str:
    """Keep requested AI technical titles; omit CV prose and past unrelated roles."""
    roles = []
    for value in re.split(r"[,;\n]+", raw_roles or ""):
        title = value.strip()
        if title.casefold() in {"ai/ml engineer", "ai / ml engineer", "ai-ml engineer"}:
            title = "AI Engineer"
        if (
            len(title) <= 80
            and assess_focus({"title": title}).accepted
            and title.casefold() not in {role.casefold() for role in roles}
        ):
            roles.append(title)
    for title in DEFAULT_ROLES.split(", "):
        if title.casefold() not in {role.casefold() for role in roles}:
            roles.append(title)
    return ", ".join(roles)[:500]
