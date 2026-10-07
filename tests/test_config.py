from __future__ import annotations

import os

import clue_ai.__main__ as entrypoint
from clue_ai import config
from clue_ai.config import load_local_environment


def test_local_environment_preserves_process_values_by_default(tmp_path, monkeypatch):
    env_file = tmp_path / ".env"
    env_file.write_text("OPENAI_API_KEY=file-key\nOTHER_SETTING=file-value\n", encoding="utf-8")
    monkeypatch.setenv("OPENAI_API_KEY", "inherited-key")
    monkeypatch.setenv("OTHER_SETTING", "inherited-value")

    load_local_environment(env_file)

    assert os.environ["OPENAI_API_KEY"] == "inherited-key"
    assert os.environ["OTHER_SETTING"] == "inherited-value"


def test_selected_local_key_overrides_stale_process_value(tmp_path, monkeypatch):
    env_file = tmp_path / ".env"
    env_file.write_text("OPENAI_API_KEY=current-key\nOTHER_SETTING=file-value\n", encoding="utf-8")
    monkeypatch.setenv("OPENAI_API_KEY", "stale-key")
    monkeypatch.setenv("OTHER_SETTING", "inherited-value")

    load_local_environment(env_file, override_keys={"OPENAI_API_KEY"})

    assert os.environ["OPENAI_API_KEY"] == "current-key"
    assert os.environ["OTHER_SETTING"] == "inherited-value"


def test_application_launcher_loads_local_key_before_starting_server(tmp_path, monkeypatch):
    (tmp_path / ".env").write_text("OPENAI_API_KEY=current-key\n", encoding="utf-8")
    monkeypatch.setattr(config, "PROJECT_ROOT", tmp_path)
    monkeypatch.setenv("OPENAI_API_KEY", "stale-key")
    started_with = {}
    monkeypatch.setattr(
        entrypoint.uvicorn,
        "run",
        lambda *_args, **_kwargs: started_with.update(key=os.environ.get("OPENAI_API_KEY")),
    )

    entrypoint.main()

    assert started_with["key"] == "current-key"
