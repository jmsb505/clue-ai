# PLAN-005 — Accept same-app loopback form submissions

**Status:** M1 implemented, validated, and pushed to `origin/main` at `b3b1bc56843866d0cffd8dc834fd93430956b217`.
**Created:** 2026-10-01

## Objective

Prevent Clue's local request boundary from rejecting normal browser form posts when the same local app is reached through supported loopback aliases, while continuing to reject external origins.

## Motivation

The owner encountered `Cross-origin form submissions are not accepted.` The response is emitted by Clue's `local_request_boundary` in `clue_ai/web.py`. The guard permits `127.0.0.1`, `localhost`, and `::1` as request hosts, but compares a form's Origin/Referer hostname to the request hostname literally. It also accepts either HTTP scheme without requiring it to match the request. That makes the supported local-host behavior inconsistent.

## Scope

- Treat the three supported loopback hostnames as aliases for this local app only when the form source and request use the same scheme and effective port.
- Require the request source scheme to match the current request scheme.
- Honor browser `Sec-Fetch-Site: same-origin` after confirming the request host is local; reject `cross-site` even if another source header appears local.
- Treat `Origin: null` as opaque metadata and fall back to Referer when Fetch Metadata is unavailable.
- Continue rejecting `cross-site` browser requests. When browser metadata is unavailable, reject non-loopback source hosts, mismatched ports, malformed origins, and cross-scheme submissions.
- Add regression tests for a same-port loopback alias and cross-scheme rejection.
- Record the boundary rule in the local-app decision and architecture documentation.

## Out of scope

- Enabling general CORS or accepting remote websites.
- Binding the service beyond loopback.
- Changing upload, search, or Jev behavior.

## Milestone M1 — Local origin compatibility

**Acceptance criteria:**

- [x] A form post from `localhost` to the app addressed as `127.0.0.1` is accepted when scheme and port match; equivalent `::1` behavior is covered.
- [x] Cross-site browser requests are rejected; with Fetch Metadata unavailable, external hosts, other ports, and different schemes remain rejected.
- [x] Existing local browser routes and the CV upload workflow pass validation.
- [x] Documentation records the exact local-origin boundary.
- [x] No local server was started for this fix; port 8000 remains free.

**Validation:** Run focused boundary tests, the full pytest suite, Ruff, byte-compilation, `git diff --check`, and a temporary local startup/shutdown check if needed. Use Conda `gen`; do not use a real CV or live Jev request.

**Git checkpoint:** Initial loopback-alias correction `d2c0a499a62612ad63eece941d0c2289cd6042ee` and the Fetch Metadata follow-up `b3b1bc56843866d0cffd8dc834fd93430956b217` were pushed directly to `origin/main`; `git ls-remote` confirmed the latest SHA.

## Progress

- 2026-10-01: Reproduced the reported 403 with same-port `localhost` and `::1` form origins posting to the same app on `127.0.0.1`.
- 2026-10-01: Updated the request boundary to normalize supported loopback aliases while requiring scheme and effective port equality. External host, port mismatch, and scheme mismatch remain rejected.
- 2026-10-01: Conda `gen` validation passed: 98 tests, Ruff, compilation, and `git diff --check`. No real CV or Jev request was used.
- 2026-10-01: After the owner reported the form still failing, extended the boundary to honor browser `Sec-Fetch-Site: same-origin`, reject `cross-site`, and fall back from `Origin: null` to Referer. Added coverage directly through both CV upload and Find matches actions.
- 2026-10-01: The follow-up passes 98 tests, Ruff, byte-compilation, and `git diff --check` in Conda `gen`. No real CV or Jev request was used.
- 2026-10-01: Follow-up commit `b3b1bc56843866d0cffd8dc834fd93430956b217` was pushed to `origin/main`; `git ls-remote` confirmed the remote head. Port 8000 is free.
- 2026-10-01: Commit `d2c0a499a62612ad63eece941d0c2289cd6042ee` was pushed directly to `origin/main`; `git ls-remote` confirmed the same remote SHA.
