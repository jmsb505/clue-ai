from __future__ import annotations

import uvicorn


def main() -> None:
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
