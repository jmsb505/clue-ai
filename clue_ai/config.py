from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
os.environ.setdefault(
    "PLAYWRIGHT_BROWSERS_PATH",
    str(PROJECT_ROOT / ".cache" / "ms-playwright"),
)


def load_local_environment(
    path: Path | None = None,
    *,
    override_keys: set[str] | frozenset[str] = frozenset(),
) -> None:
    """Load simple KEY=value settings, optionally preferring selected local values."""
    env_path = path or PROJECT_ROOT / ".env"
    try:
        lines = env_path.read_text(encoding="utf-8").splitlines()
    except FileNotFoundError:
        return
    for raw_line in lines:
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip("\"'")
        if key and key.replace("_", "").isalnum():
            if key in override_keys:
                os.environ[key] = value
            else:
                os.environ.setdefault(key, value)


def _money(value: str | None, default: float) -> float:
    if not value:
        return default
    try:
        number = float(value)
    except ValueError:
        return default
    return number if 0.0 <= number <= 4.0 else default


@dataclass(frozen=True)
class Settings:
    data_dir: Path
    api_key: str
    model: str
    monthly_jev_budget_usd: float
    openai_api_key: str = ""
    gmail_oauth_client_id: str = ""
    gmail_oauth_client_secret: str = ""
    jev_price_per_million_input_tokens: float = 0.042
    jev_reserved_tokens_per_request: int = 80_000
    max_cv_bytes: int = 12 * 1024 * 1024
    max_cv_pages: int = 50
    max_extracted_chars: int = 120_000
    max_jev_batch_jobs: int = 5
    max_job_description_chars: int = 9_000
    max_feed_bytes: int = 15 * 1024 * 1024
    max_page_bytes: int = 3 * 1024 * 1024
    network_timeout_seconds: float = 20.0
    crawler_user_agent: str = "ClueAI/0.1 (+https://github.com/jmsb505/clue-ai) local personal job-search app"

    @property
    def database_path(self) -> Path:
        return self.data_dir / "clue.sqlite3"

    @property
    def cv_dir(self) -> Path:
        return self.data_dir / "cv"

    @classmethod
    def from_environment(cls) -> Settings:
        load_local_environment()
        configured_data_dir = os.environ.get("CLUE_DATA_DIR", ".data")
        data_dir = Path(configured_data_dir).expanduser()
        if not data_dir.is_absolute():
            data_dir = PROJECT_ROOT / data_dir
        return cls(
            data_dir=data_dir.resolve(),
            api_key=os.environ.get("TYPESAFE_API_KEY", "").strip(),
            model=os.environ.get("TYPESAFE_MODEL", "jev-1.13.0").strip() or "jev-1.13.0",
            monthly_jev_budget_usd=_money(os.environ.get("JEV_MONTHLY_BUDGET_USD"), 4.00),
            openai_api_key=os.environ.get("OPENAI_API_KEY", "").strip(),
            gmail_oauth_client_id=os.environ.get("GMAIL_OAUTH_CLIENT_ID", "").strip(),
            gmail_oauth_client_secret=os.environ.get("GMAIL_OAUTH_CLIENT_SECRET", "").strip(),
        )
