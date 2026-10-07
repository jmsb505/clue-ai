"""Responses API transport and a separate conservative OpenAI usage ledger."""

from __future__ import annotations

import json
import re
import socket
import ssl
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
REASONING_EFFORT = "high"
RESPONSES_URL = "https://api.openai.com/v1/responses"
INPUT_TOKENS_URL = "https://api.openai.com/v1/responses/input_tokens"
MODEL_CONTEXT_WINDOW_TOKENS = 1_050_000
LONG_CONTEXT_SURCHARGE_THRESHOLD_TOKENS = 272_000
LONG_CONTEXT_INPUT_RATE_MULTIPLIER = 2.0
LONG_CONTEXT_OUTPUT_RATE_MULTIPLIER = 1.5
MAX_RESPONSE_BYTES = 4 * 1024 * 1024
MAX_ERROR_BYTES = 64 * 1024
DEFAULT_GENERATION_TIMEOUT_SECONDS = 600.0
INPUT_TOKEN_COUNT_TIMEOUT_SECONDS = 60.0
_SAFE_API_LABEL = re.compile(r"^[A-Za-z0-9_.:-]{1,80}$")
_SAFE_REQUEST_ID = re.compile(r"^req_[A-Za-z0-9_-]{1,128}$")


class OpenAIProviderError(RuntimeError):
    """Sanitized API or local provider error; never includes credentials or response body."""

    def __init__(
        self,
        message: str,
        *,
        status_code: int | None = None,
        error_type: str | None = None,
        error_code: str | None = None,
        request_id: str | None = None,
        failure_kind: str | None = None,
    ):
        self.status_code = status_code
        self.error_type = _safe_api_label(error_type)
        self.error_code = _safe_api_label(error_code)
        self.request_id = request_id if request_id and _SAFE_REQUEST_ID.fullmatch(request_id) else None
        self.failure_kind = _safe_api_label(failure_kind)
        detail = []
        if self.status_code is not None:
            detail.append(f"HTTP {self.status_code}")
        if self.error_type:
            detail.append(f"type={self.error_type}")
        if self.error_code:
            detail.append(f"code={self.error_code}")
        if self.failure_kind:
            detail.append(f"cause={self.failure_kind}")
        if self.request_id:
            detail.append(f"request_id={self.request_id}")
        suffix = f" ({', '.join(detail)})" if detail else ""
        super().__init__(message + suffix)


class OpenAIConfigurationError(OpenAIProviderError):
    pass


class OpenAIBudgetError(OpenAIProviderError):
    pass


class _NoRedirectHandler(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, request, file_pointer, code, message, headers, new_url):
        return None


class ResponsesClient:
    def __init__(
        self,
        api_key: str,
        timeout_seconds: float = DEFAULT_GENERATION_TIMEOUT_SECONDS,
        token_count_timeout_seconds: float = INPUT_TOKEN_COUNT_TIMEOUT_SECONDS,
    ):
        if not api_key.strip():
            raise OpenAIConfigurationError("OpenAI API key is not configured.")
        self._api_key = api_key.strip()
        self._generation_timeout_seconds = timeout_seconds
        self._token_count_timeout_seconds = token_count_timeout_seconds
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
        return self._post_json(
            RESPONSES_URL,
            payload,
            operation="generation",
            timeout_seconds=self._generation_timeout_seconds,
        )

    def count_input_tokens(self, payload: dict[str, Any]) -> int:
        """Return the exact model input count for the request that will be generated."""
        if (
            payload.get("model") != MODEL_ID
            or (payload.get("reasoning") or {}).get("effort") != REASONING_EFFORT
            or payload.get("store") is not False
        ):
            raise OpenAIConfigurationError("The token-count request does not match the fixed Clue model policy.")
        count_fields = (
            "model",
            "input",
            "instructions",
            "tools",
            "text",
            "reasoning",
            "truncation",
            "tool_choice",
            "parallel_tool_calls",
        )
        count_payload = {key: payload[key] for key in count_fields if key in payload}
        result = self._post_json(
            INPUT_TOKENS_URL,
            count_payload,
            operation="input-token count",
            timeout_seconds=self._token_count_timeout_seconds,
        )
        input_tokens = result.get("input_tokens")
        if isinstance(input_tokens, bool) or not isinstance(input_tokens, int) or input_tokens < 0:
            raise OpenAIProviderError("OpenAI returned an invalid input-token count.")
        return input_tokens

    def _post_json(
        self,
        url: str,
        payload: dict[str, Any],
        *,
        operation: str,
        timeout_seconds: float,
    ) -> dict[str, Any]:
        body = json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
        request = urllib.request.Request(
            url,
            data=body,
            headers={
                "Authorization": f"Bearer {self._api_key}",
                "Content-Type": "application/json",
                "Accept": "application/json",
            },
            method="POST",
        )
        request_id = None
        try:
            with self._opener.open(request, timeout=timeout_seconds) as response:
                headers = getattr(response, "headers", None)
                request_id = _safe_request_id(headers.get("x-request-id") if headers else None)
                raw = _read_limited(response, MAX_RESPONSE_BYTES)
        except urllib.error.HTTPError as exc:
            error_type, error_code = _http_error_labels(exc)
            request_id = _safe_request_id(exc.headers.get("x-request-id") if exc.headers else None)
            raise OpenAIProviderError(
                f"OpenAI rejected the {operation} request; the provider error body was omitted.",
                status_code=exc.code,
                error_type=error_type,
                error_code=error_code,
                request_id=request_id,
            ) from exc
        except (urllib.error.URLError, TimeoutError, OSError) as exc:
            reason = exc.reason if isinstance(exc, urllib.error.URLError) else exc
            failure_kind = _transport_failure_kind(reason)
            message = (
                "OpenAI transport failed; generation usage is unresolved."
                if operation == "generation"
                else "OpenAI input-token counting failed; generation was not sent."
            )
            raise OpenAIProviderError(
                message,
                failure_kind=failure_kind,
                request_id=request_id,
            ) from exc
        try:
            result = json.loads(raw)
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            message = (
                "OpenAI returned an unreadable generation response; usage is unresolved."
                if operation == "generation"
                else "OpenAI returned an unreadable input-token count; generation was not sent."
            )
            raise OpenAIProviderError(message) from exc
        if not isinstance(result, dict):
            message = (
                "OpenAI returned an invalid generation response object."
                if operation == "generation"
                else "OpenAI returned an invalid input-token count object; generation was not sent."
            )
            raise OpenAIProviderError(message)
        return result


def _safe_api_label(value: Any) -> str | None:
    return value if isinstance(value, str) and _SAFE_API_LABEL.fullmatch(value) else None


def _safe_request_id(value: Any) -> str | None:
    if not isinstance(value, str):
        return None
    value = value.strip()
    return value if _SAFE_REQUEST_ID.fullmatch(value) else None


def _http_error_labels(error: urllib.error.HTTPError) -> tuple[str | None, str | None]:
    """Read only allowlisted error labels; never retain or display provider messages."""
    try:
        raw = error.read(MAX_ERROR_BYTES + 1)
    except OSError:
        return None, None
    if len(raw) > MAX_ERROR_BYTES:
        return None, None
    try:
        payload = json.loads(raw)
    except (UnicodeDecodeError, json.JSONDecodeError):
        return None, None
    details = payload.get("error") if isinstance(payload, dict) else None
    if not isinstance(details, dict):
        return None, None
    return _safe_api_label(details.get("type")), _safe_api_label(details.get("code"))


def _transport_failure_kind(reason: Any) -> str:
    if isinstance(reason, TimeoutError):
        return "timeout"
    if isinstance(reason, socket.gaierror):
        return "dns_lookup_failed"
    if isinstance(reason, ssl.SSLError):
        return "tls_error"
    if isinstance(reason, ConnectionRefusedError):
        return "connection_refused"
    if isinstance(reason, ConnectionResetError):
        return "connection_reset"
    return "network_error"


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
    input_token_count: int,
    max_output_tokens: int,
) -> str:
    """Reserve exact counted input tokens and the full configured output allowance."""
    if missing_gate_reasons(settings, app_settings):
        raise OpenAIConfigurationError("OpenAI is disabled until all consent and budget gates pass.")
    if isinstance(input_token_count, bool) or not isinstance(input_token_count, int) or input_token_count < 0:
        raise OpenAIProviderError("OpenAI input-token count is invalid; generation was not sent.")
    payload_bytes = len(json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode("utf-8"))
    reserved_input_tokens = input_token_count
    input_rate = float(app_settings["openai_input_usd_per_million"])
    output_rate = float(app_settings["openai_output_usd_per_million"])
    if input_token_count > LONG_CONTEXT_SURCHARGE_THRESHOLD_TOKENS:
        input_rate *= LONG_CONTEXT_INPUT_RATE_MULTIPLIER
        output_rate *= LONG_CONTEXT_OUTPUT_RATE_MULTIPLIER
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


def ensure_context_fits(input_tokens: int, max_output_tokens: int) -> None:
    """Fail before generation when counted input plus its output allowance exceeds context."""
    if (
        isinstance(input_tokens, bool)
        or not isinstance(input_tokens, int)
        or input_tokens < 0
        or isinstance(max_output_tokens, bool)
        or not isinstance(max_output_tokens, int)
        or max_output_tokens < 0
    ):
        raise OpenAIProviderError("OpenAI context-token counts are invalid; generation was not sent.")
    total = input_tokens + max_output_tokens
    if total > MODEL_CONTEXT_WINDOW_TOKENS:
        raise OpenAIProviderError(
            f"This stage needs {input_tokens:,} input tokens plus up to {max_output_tokens:,} output tokens "
            f"({total:,} total), above GPT-6 Luna's {MODEL_CONTEXT_WINDOW_TOKENS:,}-token context window. "
            "No profile content was shortened; remove an unneeded selected reference and trigger this listing again."
        )


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


def release_usage(database_path: Path, usage_id: str, summary: str) -> None:
    """Release a reservation only when local validation proves no request was sent."""
    with connect(database_path) as db:
        db.execute(
            """UPDATE openai_usage SET status = 'released', reserved_usd = 0,
               actual_usd = 0, error_summary = ?, settled_at = ?
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
