from __future__ import annotations

import json
from hashlib import sha256
from io import BytesIO
from pathlib import Path
from zipfile import ZipFile

from fastapi.testclient import TestClient
from test_application_workflow import (
    FakeCrawler,
    FakePreparationClient,
    _approve_synthetic_tailored_resume,
    _create_preparation,
    _enable_synthetic_openai,
)

from clue_ai.application_workflow import get_packet, run_preparation
from clue_ai.database import connect
from clue_ai.web import create_app

ORIGIN = {"Origin": "http://127.0.0.1"}


def _support_synthetic_assertions(_database, _settings, _request_id, assertions):
    return {
        "status": "complete",
        "model": "jev-test",
        "actual_cost_usd": 0.0,
        "results": [
            {"id": item["id"], "status": "supported", "confidence": 0.9}
            for item in assertions
        ],
    }


def test_local_email_handoff_and_selected_attachment_bundle(settings, database):
    record, *_ = _create_preparation(settings, database)
    enabled = _enable_synthetic_openai(settings, database)
    run_preparation(
        database,
        enabled,
        record["id"],
        client_factory=FakePreparationClient,
        crawler_factory=FakeCrawler,
        claim_support_checker=_support_synthetic_assertions,
        tailored_resume_reviewer=_approve_synthetic_tailored_resume,
    )
    with connect(database) as db:
        packet_id = db.execute(
            "SELECT id FROM preparation_packets WHERE request_id = ? ORDER BY revision DESC LIMIT 1",
            (record["id"],),
        ).fetchone()["id"]
    client = TestClient(create_app(enabled), base_url="http://127.0.0.1")
    approved = client.post(
        f"/preparations/{record['id']}/packets/{packet_id}/approve",
        data={"confirm_review": "on"},
        headers=ORIGIN,
        follow_redirects=False,
    )
    assert approved.status_code == 303

    detail = client.get(f"/applications/{record['id']}")
    assert detail.status_code == 200
    assert "EMAIL DRAFT PREVIEW" in detail.text
    assert "alex@example.org" in detail.text
    assert "Question about the Software Engineer role" in detail.text
    assert "Copy recipient address for" in detail.text
    assert "Copy subject for" in detail.text
    assert "Copy message for" in detail.text
    assert "Open public source" in detail.text
    assert 'role="status" aria-live="polite"' in detail.text
    assert "Attachments to include" in detail.text
    assert "Download selected attachments (.zip)" in detail.text
    assert "Gmail is optional" in detail.text

    packet = get_packet(database, packet_id)
    selected = [
        item for item in packet["artifacts"]
        if item["artifact_type"] in {"resume", "cover_letter"}
    ]
    assert len(selected) == 2
    with connect(database) as db:
        db.executemany(
            "UPDATE packet_artifacts SET filename = ? WHERE id = ?",
            [(f"../{item['filename']}", item["id"]) for item in selected],
        )

    older_bytes = b"Older synthetic attachment"
    older_path = settings.data_dir / "application-packets" / record["id"] / "v0" / "older-resume.txt"
    older_path.parent.mkdir(parents=True, exist_ok=True)
    older_path.write_bytes(older_bytes)
    with connect(database) as db:
        db.execute(
            """INSERT INTO preparation_packets
               (id, request_id, revision, input_revision_sha256, output_json, status, created_at)
               VALUES ('historical-packet', ?, 0, 'older-input-revision', ?, 'obsolete', '2026-10-05T00:00:00Z')""",
            (record["id"], json.dumps({"research": {}, "diagnoser": {}, "recruiter": {}, "rewriter": {}})),
        )
        db.execute(
            """INSERT INTO packet_artifacts
               (id, packet_id, artifact_type, filename, file_path, content_sha256, created_at)
               VALUES ('historical-artifact', 'historical-packet', 'resume', 'older-resume.txt', ?, ?, '2026-10-05T00:00:00Z')""",
            (str(older_path), sha256(older_bytes).hexdigest()),
        )

    bundle_url = f"/applications/{record['id']}/packets/{packet_id}/attachments.zip"
    bundle = client.post(
        bundle_url,
        data={"artifact_id": [item["id"] for item in selected]},
        headers=ORIGIN,
    )
    assert bundle.status_code == 200, bundle.text
    assert bundle.headers["content-type"] == "application/zip"
    assert "application-packet-v1-attachments.zip" in bundle.headers["content-disposition"]
    with ZipFile(BytesIO(bundle.content)) as archive:
        names = archive.namelist()
        assert len(names) == len(selected)
        assert all("/" not in name and "\\" not in name for name in names)
        for item in selected:
            assert archive.read(Path(item["filename"]).name) == Path(item["file_path"]).read_bytes()

    with connect(database) as db:
        db.execute("UPDATE researched_contacts SET public_email = '' WHERE request_id = ?", (record["id"],))
    no_address = client.get(f"/applications/{record['id']}")
    assert "No publicly verified email address is available" in no_address.text
    assert "Clue will not guess one" in no_address.text
    assert "Copy recipient address for" not in no_address.text
    assert "Copy subject for" in no_address.text

    assert client.post(bundle_url, data={}, headers=ORIGIN).status_code == 400
    assert client.post(
        bundle_url, data={"artifact_id": "not-in-this-packet"}, headers=ORIGIN
    ).status_code == 404
    assert client.post(
        bundle_url, data={"artifact_id": "historical-artifact"}, headers=ORIGIN
    ).status_code == 404
    assert client.post(
        f"/applications/{record['id']}/packets/historical-packet/attachments.zip",
        data={"artifact_id": "historical-artifact"},
        headers=ORIGIN,
    ).status_code == 409
    assert client.post(
        f"/applications/another-request/packets/{packet_id}/attachments.zip",
        data={"artifact_id": selected[0]["id"]},
        headers=ORIGIN,
    ).status_code == 404

    selected_path = Path(selected[0]["file_path"])
    selected_content = selected_path.read_bytes()
    selected_path.write_bytes(selected_content + b" changed")
    assert client.post(
        bundle_url, data={"artifact_id": selected[0]["id"]}, headers=ORIGIN
    ).status_code == 409
    selected_path.write_bytes(selected_content)
    selected_path.unlink()
    assert client.post(
        bundle_url, data={"artifact_id": selected[0]["id"]}, headers=ORIGIN
    ).status_code == 404
    selected_path.write_bytes(selected_content)

    elsewhere = settings.data_dir / "application-packets" / "elsewhere" / "resume.docx"
    elsewhere.parent.mkdir(parents=True, exist_ok=True)
    elsewhere.write_bytes(selected_content)
    with connect(database) as db:
        db.execute(
            "UPDATE packet_artifacts SET file_path = ? WHERE id = ?",
            (str(elsewhere), selected[0]["id"]),
        )
    assert client.post(
        bundle_url, data={"artifact_id": selected[0]["id"]}, headers=ORIGIN
    ).status_code == 404
