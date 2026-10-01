# PLAN-005 — Accept same-app loopback form submissions

**Status:** M1 locally validated; direct-to-main push pending
**Created:** 2026-10-01

## Objective

Prevent Clue's local request boundary from rejecting normal browser form posts when the same local app is reached through supported loopback aliases, while continuing to reject external origins.

## Motivation

The owner encountered `Cross-origin form submissions are not accepted.` The response is emitted by Clue's `local_request_boundary` in `clue_ai/web.py`. The guard permits `127.0.0.1`, `localhost`, and `::1` as request hosts, but compares a form's Origin/Referer hostname to the request hostname literally. It also accepts either HTTP scheme without requiring it to match the request. That makes the supported local-host behavior inconsistent.

## Scope

- Treat the three supported loopback hostnames as aliases for this local app only when the form source and request use the same scheme and effective port.
- Require the request source scheme to match the current request scheme.
- Continue rejecting non-loopback source hosts, mismatched ports, malformed origins, and cross-scheme submissions.
- Add regression tests for a same-port loopback alias and cross-scheme rejection.
- Record the boundary rule in the local-app decision and architecture documentation.

## Out of scope

- Enabling general CORS or accepting remote websites.
- Binding the service beyond loopback.
- Changing upload, search, or Jev behavior.

## Milestone M1 — Local origin compatibility

**Acceptance criteria:**

- [x] A form post from `localhost` to the app addressed as `127.0.0.1` is accepted when scheme and port match; equivalent `::1` behavior is covered.
- [x] Requests from an external host, another port, or a different scheme remain rejected.
- [x] Existing local browser routes and the CV upload workflow pass validation.
- [x] Documentation records the exact local-origin boundary.
- [x] No local server was started for this fix; port 8000 remains free.

**Validation:** Run focused boundary tests, the full pytest suite, Ruff, byte-compilation, `git diff --check`, and a temporary local startup/shutdown check if needed. Use Conda `gen`; do not use a real CV or live Jev request.

**Git checkpoint:** Commit the validated M1 fix directly to `main`, push it, and confirm the remote head.

## Progress

- 2026-10-01: Reproduced the reported 403 with same-port `localhost` and `::1` form origins posting to the same app on `127.0.0.1`.
- 2026-10-01: Updated the request boundary to normalize supported loopback aliases while requiring scheme and effective port equality. External host, port mismatch, and scheme mismatch remain rejected.
- 2026-10-01: Conda `gen` validation passed: 95 tests, Ruff, compilation, and `git diff --check`. No real CV or Jev request was used.
