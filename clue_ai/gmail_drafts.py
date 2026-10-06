"""Owner-authorized Gmail OAuth and create-only unsent draft adapter."""

from __future__ import annotations

import base64
import ctypes
import hashlib
import hmac
import json
import os
import re
import secrets
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
from email.message import EmailMessage
from email.policy import SMTP
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from typing import Any

from clue_ai.application_workflow import verify_packet_approval
from clue_ai.config import Settings
from clue_ai.database import connect, set_gmail_connection
from clue_ai.domain import utc_now

GMAIL_SCOPE = "https://www.googleapis.com/auth/gmail.compose"
GOOGLE_AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
GMAIL_DRAFTS_URL = "https://gmail.googleapis.com/gmail/v1/users/me/drafts"
GMAIL_REDIRECT_URI = "http://127.0.0.1:8765/"
_MAX_BODY_BYTES = 2 * 1024 * 1024
_EMAIL = re.compile(r"^[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}$", re.IGNORECASE)


class GmailDraftError(RuntimeError):
    def __init__(self, message: str, *, outcome_unknown: bool = False):
        super().__init__(message)
        self.outcome_unknown = outcome_unknown


class GmailOAuthConfigurationError(GmailDraftError):
    pass


class WindowsDPAPITokenStore:
    """Keep the refresh token encrypted for the current Windows account."""

    def __init__(self, data_dir: Path):
        self.path = (data_dir / "gmail" / "refresh-token.bin").resolve()
        if not self.path.is_relative_to(data_dir.resolve()):
            raise GmailOAuthConfigurationError("Gmail token storage escaped the local data directory.")

    def save(self, token: str) -> None:
        encrypted = _dpapi_protect(token.encode("utf-8"))
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_bytes(encrypted)

    def load(self) -> str:
        if not self.path.is_file():
            raise GmailOAuthConfigurationError("Connect Gmail before creating a draft.")
        try:
            return _dpapi_unprotect(self.path.read_bytes()).decode("utf-8")
        except (OSError, UnicodeDecodeError) as exc:
            raise GmailOAuthConfigurationError("The local Gmail authorization could not be read.") from exc

    def delete(self) -> None:
        self.path.unlink(missing_ok=True)


def build_authorization_url(settings: Settings, state: str, verifier: str) -> str:
    if not settings.gmail_oauth_client_id:
        raise GmailOAuthConfigurationError(
            "Add the Google OAuth Desktop client ID to the local .env file first."
        )
    challenge = base64.urlsafe_b64encode(hashlib.sha256(verifier.encode("ascii")).digest()).decode("ascii").rstrip("=")
    params = {
        "client_id": settings.gmail_oauth_client_id,
        "redirect_uri": GMAIL_REDIRECT_URI,
        "response_type": "code",
        "scope": GMAIL_SCOPE,
        "state": state,
        "code_challenge": challenge,
        "code_challenge_method": "S256",
        "access_type": "offline",
        "prompt": "consent",
    }
    return GOOGLE_AUTH_URL + "?" + urllib.parse.urlencode(params)


def start_local_oauth(database_path: Path, settings: Settings) -> str:
    """Start one loopback callback and return Google's authorization URL."""
    if os.name != "nt":
        raise GmailOAuthConfigurationError("The local Gmail credential store currently requires Windows DPAPI.")
    state = secrets.token_urlsafe(32)
    verifier = secrets.token_urlsafe(64)
    auth_url = build_authorization_url(settings, state, verifier)
    try:
        server = HTTPServer(("127.0.0.1", 8765), _make_callback_handler(database_path, settings, state, verifier))
    except OSError as exc:
        raise GmailOAuthConfigurationError(
            "The local Gmail callback port 8765 is unavailable; close its current owner and try again."
        ) from exc
    server.timeout = 300
    server.daemon_threads = True

    def listen_once() -> None:
        deadline = time.monotonic() + 300
        try:
            while time.monotonic() < deadline and not getattr(server, "oauth_finished", False):
                server.handle_request()
        finally:
            server.server_close()

    threading.Thread(target=listen_once, name="clue-gmail-oauth", daemon=True).start()
    return auth_url


def _make_callback_handler(database_path: Path, settings: Settings, expected_state: str, verifier: str):
    class OAuthCallbackHandler(BaseHTTPRequestHandler):
        def do_GET(self) -> None:
            parsed = urllib.parse.urlsplit(self.path)
            query = urllib.parse.parse_qs(parsed.query)
            returned_state = (query.get("state") or [""])[0]
            if parsed.path != "/" or not hmac.compare_digest(returned_state, expected_state):
                self._reply(400, "Clue could not validate the Gmail authorization response. Return to Clue and try again.")
                return
            error = (query.get("error") or [""])[0]
            if error:
                self._reply(400, "Gmail authorization was declined or could not be completed. Return to Clue.")
                self.server.oauth_finished = True
                return
            code = (query.get("code") or [""])[0]
            if not code:
                self._reply(400, "Gmail did not return an authorization code. Return to Clue.")
                self.server.oauth_finished = True
                return
            try:
                token_response = _exchange_code(settings, code, verifier)
                refresh_token = str(token_response.get("refresh_token") or "")
                if not refresh_token:
                    raise GmailOAuthConfigurationError("Google did not return an offline refresh token. Disconnect and reconnect with consent.")
                WindowsDPAPITokenStore(settings.data_dir).save(refresh_token)
                set_gmail_connection(database_path, True)
                self._reply(200, "Gmail is connected to Clue. You can close this tab and return to the app.")
            except GmailDraftError:
                self._reply(400, "Gmail authorization did not complete. Return to Clue and review the local setup.")
            finally:
                self.server.oauth_finished = True

        def _reply(self, status: int, message: str) -> None:
            body = (
                "<!doctype html><html><head><meta charset='utf-8'><title>Clue Gmail</title></head>"
                f"<body><main><h1>{message}</h1></main></body></html>"
            ).encode()
            self.send_response(status)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Cache-Control", "no-store")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, format: str, *args: Any) -> None:
            return

    return OAuthCallbackHandler


def create_unsent_draft(settings: Settings, recipient: str, subject: str, body: str) -> str:
    """Create exactly one Gmail draft. This adapter exposes no send operation."""
    if not settings.gmail_oauth_client_id:
        raise GmailOAuthConfigurationError("Gmail OAuth client ID is not configured.")
    if not recipient or len(recipient) > 254 or not _EMAIL.fullmatch(recipient):
        raise GmailDraftError("A verified public recipient email is required.")
    if not subject.strip() or len(subject) > 180 or not body.strip() or len(body) > 5_000:
        raise GmailDraftError("The reviewed subject and body are empty or exceed their limits.")
    token_store = WindowsDPAPITokenStore(settings.data_dir)
    refresh_token = token_store.load()
    access_token = _refresh_access_token(settings, refresh_token, token_store)
    message = EmailMessage(policy=SMTP)
    message["To"] = recipient
    message["Subject"] = subject
    message.set_content(body)
    raw = base64.urlsafe_b64encode(message.as_bytes()).decode("ascii").rstrip("=")
    payload = json_body({"message": {"raw": raw}})
    request = urllib.request.Request(
        GMAIL_DRAFTS_URL,
        data=payload,
        headers={
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        },
        method="POST",
    )
    opener = urllib.request.build_opener(_NoRedirect())
    try:
        with opener.open(request, timeout=30) as response:
            result = json.loads(_read_limited(response, _MAX_BODY_BYTES))
    except urllib.error.HTTPError as exc:
        raise GmailDraftError(
            f"Gmail returned HTTP {exc.code} while creating the unsent draft.",
            outcome_unknown=exc.code >= 500,
        ) from exc
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        raise GmailDraftError("Gmail draft creation timed out; check Gmail Drafts before retrying.", outcome_unknown=True) from exc
    except (json.JSONDecodeError, UnicodeDecodeError) as exc:
        raise GmailDraftError("Gmail returned an unreadable response; check Gmail Drafts before retrying.", outcome_unknown=True) from exc
    draft_id = str(result.get("id") or "") if isinstance(result, dict) else ""
    if not draft_id:
        raise GmailDraftError("Gmail returned no draft ID; check Gmail Drafts before retrying.", outcome_unknown=True)
    return draft_id


def create_approved_packet_draft(
    database_path: Path,
    settings: Settings,
    request_id: str,
    packet_id: str,
    draft_index: int,
    *,
    confirmed: bool,
    create_draft: Any = create_unsent_draft,
) -> tuple[str, str]:
    """Create one unsent draft bound to an exact approved packet message and public address."""
    if not confirmed:
        raise GmailDraftError("Confirm the exact recipient, subject, and message before creating a draft.")
    packet = verify_packet_approval(database_path, settings, packet_id)
    if packet["request_id"] != request_id:
        raise GmailDraftError("The approved packet does not belong to this opportunity.")
    messages = packet["output"].get("rewriter", {}).get("outreach_drafts", [])
    if draft_index < 0 or draft_index >= len(messages):
        raise GmailDraftError("That outreach draft is not part of the approved packet.")
    message = messages[draft_index]
    with connect(database_path) as db:
        contact = db.execute(
            """SELECT * FROM researched_contacts WHERE request_id = ? AND source_url = ?
               AND name = ? AND suppressed = 0 LIMIT 1""",
            (request_id, message["contact_source_url"], message["recipient_name"]),
        ).fetchone()
    if contact is None or not contact["public_email"] or not _EMAIL.fullmatch(contact["public_email"]):
        raise GmailDraftError("A publicly sourced recipient email is required; Clue never guesses one.")
    recipient = contact["public_email"]
    subject = str(message.get("subject") or "")
    body = str(message.get("body") or "")
    approved_sha = hashlib.sha256(
        json.dumps(
            {"request_id": request_id, "recipient": recipient, "subject": subject, "body": body},
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
    ).hexdigest()
    draft_record_id = secrets.token_hex(16)
    now = utc_now()
    with connect(database_path) as db:
        db.execute("BEGIN IMMEDIATE")
        existing = db.execute(
            """SELECT state FROM gmail_drafts WHERE approved_sha256 = ?
               AND state IN ('creating', 'created', 'unknown') LIMIT 1""",
            (approved_sha,),
        ).fetchone()
        if existing:
            db.execute("ROLLBACK")
            raise GmailDraftError(
                "A draft with this approved content is already created or unresolved. Check Gmail Drafts before retrying."
            )
        db.execute(
            """INSERT INTO gmail_drafts
               (id, request_id, packet_id, recipient, subject, body, approved_sha256,
                state, created_at, updated_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, 'creating', ?, ?)""",
            (draft_record_id, request_id, packet_id, recipient, subject, body, approved_sha, now, now),
        )
        db.execute("COMMIT")
    try:
        gmail_id = create_draft(settings, recipient, subject, body)
    except GmailDraftError as exc:
        status = "unknown" if exc.outcome_unknown else "failed"
        with connect(database_path) as db:
            db.execute(
                "UPDATE gmail_drafts SET state = ?, error_summary = ?, updated_at = ? WHERE id = ?",
                (status, str(exc)[:240], utc_now(), draft_record_id),
            )
        raise
    except Exception as exc:
        with connect(database_path) as db:
            db.execute(
                "UPDATE gmail_drafts SET state = 'unknown', error_summary = ?, updated_at = ? WHERE id = ?",
                ("The result of Gmail draft creation is unknown.", utc_now(), draft_record_id),
            )
        raise GmailDraftError("Gmail draft outcome is unknown; check Gmail Drafts before retrying.", outcome_unknown=True) from exc
    with connect(database_path) as db:
        db.execute(
            """UPDATE gmail_drafts SET state = 'created', gmail_draft_id = ?, updated_at = ?
               WHERE id = ?""",
            (gmail_id, utc_now(), draft_record_id),
        )
    return draft_record_id, gmail_id


def _exchange_code(settings: Settings, code: str, verifier: str) -> dict[str, Any]:
    values = {
        "client_id": settings.gmail_oauth_client_id,
        "code": code,
        "code_verifier": verifier,
        "grant_type": "authorization_code",
        "redirect_uri": GMAIL_REDIRECT_URI,
    }
    if settings.gmail_oauth_client_secret:
        values["client_secret"] = settings.gmail_oauth_client_secret
    return _post_form(GOOGLE_TOKEN_URL, values)


def _refresh_access_token(
    settings: Settings,
    refresh_token: str,
    token_store: WindowsDPAPITokenStore | None = None,
) -> str:
    values = {
        "client_id": settings.gmail_oauth_client_id,
        "refresh_token": refresh_token,
        "grant_type": "refresh_token",
    }
    if settings.gmail_oauth_client_secret:
        values["client_secret"] = settings.gmail_oauth_client_secret
    token = _post_form(GOOGLE_TOKEN_URL, values)
    rotated_refresh_token = str(token.get("refresh_token") or "")
    if rotated_refresh_token and token_store:
        token_store.save(rotated_refresh_token)
    access = str(token.get("access_token") or "")
    if not access:
        raise GmailOAuthConfigurationError("Google did not return an access token.")
    return access


def _post_form(url: str, values: dict[str, str]) -> dict[str, Any]:
    request = urllib.request.Request(
        url,
        data=urllib.parse.urlencode(values).encode("ascii"),
        headers={"Content-Type": "application/x-www-form-urlencoded", "Accept": "application/json"},
        method="POST",
    )
    opener = urllib.request.build_opener(_NoRedirect())
    try:
        with opener.open(request, timeout=30) as response:
            value = json.loads(_read_limited(response, _MAX_BODY_BYTES))
    except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError, OSError, json.JSONDecodeError) as exc:
        raise GmailOAuthConfigurationError("Google OAuth could not complete. Check local OAuth setup and try again.") from exc
    if not isinstance(value, dict) or value.get("error"):
        raise GmailOAuthConfigurationError("Google OAuth returned an error.")
    return value


def json_body(value: dict[str, Any]) -> bytes:
    return json.dumps(value, ensure_ascii=False, separators=(",", ":")).encode("utf-8")


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, request, file_pointer, code, message, headers, new_url):
        return None


def _read_limited(response, limit: int) -> bytes:
    value = response.read(limit + 1)
    if len(value) > limit:
        raise GmailDraftError("Google returned a response larger than the local safety limit.")
    return value


class _DataBlob(ctypes.Structure):
    _fields_ = [("cbData", ctypes.c_ulong), ("pbData", ctypes.POINTER(ctypes.c_ubyte))]


def _dpapi_protect(value: bytes) -> bytes:
    return _dpapi(value, decrypt=False)


def _dpapi_unprotect(value: bytes) -> bytes:
    return _dpapi(value, decrypt=True)


def _dpapi(value: bytes, *, decrypt: bool) -> bytes:
    if os.name != "nt":
        raise GmailOAuthConfigurationError("The local Gmail credential store currently requires Windows DPAPI.")
    buffer = ctypes.create_string_buffer(value)
    source = _DataBlob(len(value), ctypes.cast(buffer, ctypes.POINTER(ctypes.c_ubyte)))
    target = _DataBlob()
    crypt = ctypes.WinDLL("crypt32", use_last_error=True)
    kernel = ctypes.WinDLL("kernel32", use_last_error=True)
    function = crypt.CryptUnprotectData if decrypt else crypt.CryptProtectData
    if decrypt:
        function.argtypes = [ctypes.POINTER(_DataBlob), ctypes.c_void_p, ctypes.c_void_p, ctypes.c_void_p, ctypes.c_void_p, ctypes.c_ulong, ctypes.POINTER(_DataBlob)]
        ok = function(ctypes.byref(source), None, None, None, None, 0x1, ctypes.byref(target))
    else:
        function.argtypes = [ctypes.POINTER(_DataBlob), ctypes.c_wchar_p, ctypes.c_void_p, ctypes.c_void_p, ctypes.c_void_p, ctypes.c_ulong, ctypes.POINTER(_DataBlob)]
        ok = function(ctypes.byref(source), "Clue Gmail refresh token", None, None, None, 0x1, ctypes.byref(target))
    if not ok:
        raise GmailOAuthConfigurationError("Windows could not protect or read the local Gmail credential.")
    try:
        return ctypes.string_at(target.pbData, target.cbData)
    finally:
        kernel.LocalFree.argtypes = [ctypes.c_void_p]
        kernel.LocalFree(target.pbData)
