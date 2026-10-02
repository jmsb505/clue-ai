# ADR 0011 — Stop crawl work with the local app

**Status:** Accepted
**Date:** 2026-10-02

## Context

Clue runs feed collection, Scrapling spiders, and Jev scoring in background work owned by its local Python server. The PowerShell stop helper previously force-terminated only the Python listener PID. That did not explicitly stop child browser processes and could leave the corresponding `search_runs` record in `queued`, `running`, or `scoring` state after the server exited.

## Decision

1. The supported stop path validates that the port 8000 listener is Python from Conda `gen`, then uses Windows `taskkill /T /F` to terminate that process and its child process tree.
2. The helper confirms that the managed listener and port have stopped before updating run state.
3. Once the server is gone, mark remaining queued/running/scoring runs as `failed`, use stage `interrupted`, and tell the owner to start a new search. Apply the same recovery before a managed server start to handle unexpected prior exits.
4. Do not delete profile, CV, source, or listing data. Results already saved before shutdown stay in the local index; source refresh state for completed fetches remains intact.
5. Use `scripts/clue.ps1 stop` from another PowerShell window as the documented way to stop Clue and its crawler/browser processes.

## Consequences

- Search and crawl work owned by the server process tree stops when the helper stops Clue.
- Interrupted runs no longer appear as live work or block a new search after a managed restart.
- If a connector completed and persisted data before shutdown, those local records remain available. This operation does not attempt rollback or immediate source refresh.
- This force-stop path does not attempt graceful per-connector cancellation or resumable crawls.

## Evidence

- FastAPI background work is registered from the Clue request flow and invokes synchronous search/scoring workers in the server process.
- Scrapling's spider API exposes `start()` and spider pause semantics; the app's process-tree stop also terminates descendant processes.
- The local stop helper now applies process-tree termination only after verifying the listener executable belongs to Conda `gen`.
