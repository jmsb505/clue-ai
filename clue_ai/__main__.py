from __future__ import annotations

import uvicorn

from clue_ai.config import load_local_environment


def main() -> None:
    # Prefer the local app's configured key over an inherited shell value,
    # which may be stale after key rotation.
    load_local_environment(override_keys={"OPENAI_API_KEY"})
    uvicorn.run(
        "clue_ai.web:app",
        host="127.0.0.1",
        port=8000,
        reload=False,
        access_log=False,
        log_config=None,
    )


if __name__ == "__main__":
    main()
