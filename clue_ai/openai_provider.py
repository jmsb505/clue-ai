"""Responses API transport and a separate conservative OpenAI usage ledger."""

from __future__ import annotations

import json
import urllib.error
import urllib.request
import uuid
from datetime import date, datetime, timezone
from http.client import HTTPResponse
from pathlib import Path
from typing import Any

from clue_ai.application_prompts import CRAWL_TOOL
from clue_ai.config import Settings
from clue_ai.database import connect
from clue_ai.domain import utc_now

MODEL_ID = "gpt-6-luna"
REASONING_EFFORT = "max"
RESPONSES_URL = "https://api.openai.com/v1/responses"
MAX_RESPONSE_BYTES = 4 * 1024 * 1024
INPUT_TOKEN_OVERHEAD_RESERVE = 2_048


class OpenAIProviderError(RuntimeError):
    """Sanitized API or local provider error; never includes credentials or response body."""


class OpenAIConfigurationError(OpenAIProviderError):
    pass


class OpenAIBudgetError(OpenAIProviderError):
    pass


class _NoRedirectHandler(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, request, file_pointer, code, message, headers, new_url):
        return None


class ResponsesClient:
    def __init__(self, api_key: str, timeout_seconds: float = 30.0):
        if not api_key.strip():
            raise OpenAIConfigurationError("OpenAI API key is not configured.")
        self._api_key = api_key.strip()
        self._timeout = timeout_seconds
        self._opener = urllib.request.build_opener(_NoRedirectHandler())

    def create(self, payload: dict[str, Any]) -> dict[str, Any]:
        if (
            payload.get("model") != MODEL_ID
            or (payload.get("reasoning") or {}).get("effort") != REASONING_EFFORT
            or payload.get("store") is not False
        ):
            raise OpenAIConfigurationError("The provider request does not match the fixed Clue model and storage policy.")
        tools = payload.get("tools", [])
        if tools and tools != [CRAWL_TOOL]:
            raise OpenAIConfigurationError("Only the bounded public-page Researcher tool is available.")
        if not tools and any(key in payload for key in ("tool_choice", "parallel_tool_calls")):
            raise OpenAIConfigurationError("Tool controls are unavailable without the Researcher tool.")
        body = json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
        request = urllib.request.Request(
            RESPONSES_URL,
            data=body,
            headers={
                "Authorization": f"Bearer {self._api_key}",
                "Content-Type": "application/json",
                "Accept": "application/json",
            },
            method="POST",
        )
        try:
            with self._opener.open(request, timeout=self._timeout) as response:
                raw = _read_limited(response, MAX_RESPONSE_BYTES)
        except urllib.error.HTTPError as exc:
            # Do not include the provider body: diagnostics can echo request data.
            raise OpenAIProviderError(f"OpenAI returned HTTP {exc.code}.") from exc
        except (urllib.error.URLError, TimeoutError, OSError) as exc:
            raise OpenAIProviderError("OpenAI request failed or timed out; usage is unresolved.") from exc
        try:
            result = json.loads(raw)
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise OpenAIProviderError("OpenAI returned an unreadable response; usage is unresolved.") from exc
        if not isinstance(result, dict):
            raise OpenAIProviderError("OpenAI returned an invalid response object.")
        return result


def missing_gate_reasons(settings: Settings, app_settings: dict[str, Any]) -> list[str]:
    reasons = []
    if not settings.openai_api_key:
        reasons.append("Add OPENAI_API_KEY to the local .env file.")
    if not app_settings.get("openai_consent_at"):
        reasons.append("Enable the separate OpenAI data-sharing consent in Settings.")
    if float(app_settings.get("openai_monthly_budget_usd") or 0) <= 0:
        reasons.append("Set an OpenAI monthly spending cap in Settings.")
    if float(app_settings.get("openai_opportunity_budget_usd") or 0) <= 0:
        reasons.append("Set an OpenAI per-opportunity spending cap in Settings.")
    if float(app_settings.get("openai_input_usd_per_million") or 0) <= 0:
        reasons.append("Set the current GPT-6 Luna input rate in Settings.")
    if float(app_settings.get("openai_output_usd_per_million") or 0) <= 0:
        reasons.append("Set the current GPT-6 Luna output rate in Settings.")
    revision = str(app_settings.get("openai_rate_card_revision") or "").strip()
    try:
        checked_date = date.fromisoformat(revision)
        age_days = (datetime.now(timezone.utc).date() - checked_date).days
        if age_days < 0 or age_days > 30:
            reasons.append("Recheck the current OpenAI pricing page and update its date in Settings.")
    except ValueError:
        reasons.append("Record a current YYYY-MM-DD OpenAI pricing-page date in Settings.")
    return reasons


def reserve_usage(
    database_path: Path,
    settings: Settings,
    app_settings: dict[str, Any],
    *,
    request_id: str,
    job_id: str,
    stage: str,
    payload: dict[str, Any],
    max_output_tokens: int,
) -> str:
    """Reserve UTF-8 payload bytes plus framing overhead before a Responses API call."""
    if missing_gate_reasons(settings, app_settings):
        raise OpenAIConfigurationError("OpenAI is disabled until all consent and budget gates pass.")
    payload_bytes = len(json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode("utf-8"))
    reserved_input_tokens = payload_bytes + INPUT_TOKEN_OVERHEAD_RESERVE
    input_rate = float(app_settings["openai_input_usd_per_million"])
    output_rate = float(app_settings["openai_output_usd_per_million"])
    search_rate = float(app_settings.get("openai_search_usd_per_thousand") or 0)
    reserved_usd = reserved_input_tokens * input_rate / 1_000_000 + max_output_tokens * output_rate / 1_000_000
    monthly_cap = float(app_settings["openai_monthly_budget_usd"])
    opportunity_cap = float(app_settings["openai_opportunity_budget_usd"])
    month_key = datetime.now(timezone.utc).strftime("%Y-%m")
    now = utc_now()
    usage_id = uuid.uuid4().hex
    with connect(database_path) as db:
        db.execute("BEGIN IMMEDIATE")
        monthly = db.execute(
            """SELECT COALESCE(SUM(CASE WHEN status = 'settled' THEN actual_usd
                         ELSE reserved_usd END), 0) AS used
               FROM openai_usage WHERE month_key = ? AND status IN ('reserved', 'unknown', 'settled')""",
            (month_key,),
        ).fetchone()["used"]
        opportunity = db.execute(
            """SELECT COALESCE(SUM(CASE WHEN status = 'settled' THEN actual_usd
                         ELSE reserved_usd END), 0) AS used
               FROM openai_usage WHERE job_id = ? AND status IN ('reserved', 'unknown', 'settled')""",
            (job_id,),
        ).fetchone()["used"]
        if float(monthly) + reserved_usd > monthly_cap + 1e-12:
            db.execute("ROLLBACK")
            raise OpenAIBudgetError("This request would exceed the OpenAI monthly cap.")
        if float(opportunity) + reserved_usd > opportunity_cap + 1e-12:
            db.execute("ROLLBACK")
            raise OpenAIBudgetError("This request would exceed the OpenAI per-opportunity cap.")
        db.execute(
            """INSERT INTO openai_usage
               (id, request_id, job_id, month_key, stage, model, estimated_input_bytes,
                reserved_input_tokens, max_output_tokens, reserved_usd, input_usd_per_million,
                output_usd_per_million, search_usd_per_thousand, status, created_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'reserved', ?)""",
            (
                usage_id,
                request_id,
                job_id,
                month_key,
                stage,
                MODEL_ID,
                payload_bytes,
                reserved_input_tokens,
                max_output_tokens,
                reserved_usd,
                input_rate,
                output_rate,
                search_rate,
                now,
            ),
        )
        db.execute("COMMIT")
    return usage_id


def settle_usage(
    database_path: Path,
    usage_id: str,
    *,
    input_tokens: int,
    output_tokens: int,
    search_calls: int = 0,
) -> float:
    with connect(database_path) as db:
        row = db.execute("SELECT * FROM openai_usage WHERE id = ?", (usage_id,)).fetchone()
        if row is None:
            raise OpenAIProviderError("OpenAI usage reservation was not found.")
        if input_tokens < 0 or output_tokens < 0 or search_calls < 0:
            raise OpenAIProviderError("OpenAI returned invalid usage values; usage is unresolved.")
        actual = (
            input_tokens * row["input_usd_per_million"] / 1_000_000
            + output_tokens * row["output_usd_per_million"] / 1_000_000
            + search_calls * row["search_usd_per_thousand"] / 1_000
        )
        input_limit = int(row["reserved_input_tokens"] or row["estimated_input_bytes"])
        token_cost_upper_bound = (
            input_limit * row["input_usd_per_million"] / 1_000_000
            + row["max_output_tokens"] * row["output_usd_per_million"] / 1_000_000
            + search_calls * row["search_usd_per_thousand"] / 1_000
        )
        if input_tokens > input_limit or output_tokens > row["max_output_tokens"]:
            db.execute(
                """UPDATE openai_usage SET status = 'unknown', error_summary = ?, settled_at = ?
                   WHERE id = ?""",
                ("Provider usage exceeded the reserved token limit.", utc_now(), usage_id),
            )
            raise OpenAIProviderError("Provider usage exceeded its reservation; retry is blocked.")
        if actual > token_cost_upper_bound + 1e-12:
            db.execute(
                """UPDATE openai_usage SET status = 'unknown', error_summary = ?, settled_at = ?
                   WHERE id = ?""",
                ("Usage exceeded the reserved amount.", utc_now(), usage_id),
            )
            raise OpenAIProviderError("Provider cost exceeded its reservation; retry is blocked.")
        db.execute(
            """UPDATE openai_usage SET input_tokens = ?, output_tokens = ?, search_calls = ?,
               actual_usd = ?, status = 'settled', settled_at = ?, error_summary = '' WHERE id = ?""",
            (input_tokens, output_tokens, search_calls, actual, utc_now(), usage_id),
        )
    return actual


def mark_usage_unknown(database_path: Path, usage_id: str, summary: str) -> None:
    with connect(database_path) as db:
        db.execute(
            """UPDATE openai_usage SET status = 'unknown', error_summary = ?, settled_at = ?
               WHERE id = ? AND status = 'reserved'""",
            (summary[:240], utc_now(), usage_id),
        )


def monthly_usage(database_path: Path) -> dict[str, float]:
    month_key = datetime.now(timezone.utc).strftime("%Y-%m")
    with connect(database_path) as db:
        row = db.execute(
            """SELECT COALESCE(SUM(CASE WHEN status = 'settled' THEN actual_usd
                         ELSE reserved_usd END), 0) AS used,
                      COALESCE(SUM(CASE WHEN status IN ('reserved', 'unknown')
                                        THEN reserved_usd ELSE 0 END), 0) AS reserved,
                      SUM(CASE WHEN status = 'unknown' THEN 1 ELSE 0 END) AS unknown_count
               FROM openai_usage WHERE month_key = ?
                 AND status IN ('reserved', 'unknown', 'settled')""",
            (month_key,),
        ).fetchone()
    return {
        "used_usd": float(row["used"] or 0),
        "reserved_usd": float(row["reserved"] or 0),
        "unknown_count": int(row["unknown_count"] or 0),
    }


def mark_request_usage_unresolved(database_path: Path, request_id: str, reason: str) -> None:
    with connect(database_path) as db:
        db.execute(
            """UPDATE openai_usage SET status = 'unknown', error_summary = ?, settled_at = ?
               WHERE request_id = ? AND status = 'reserved'""",
            (reason[:240], utc_now(), request_id),
        )


def _read_limited(response: HTTPResponse, limit: int) -> bytes:
    chunks = response.read(limit + 1)
    if len(chunks) > limit:
        raise OpenAIProviderError("OpenAI response exceeded the local response-size limit.")
    return chunks
