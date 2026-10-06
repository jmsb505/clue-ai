ner_submission_attestation', 'owner_stage_update')
                       ORDER BY event.occurred_at DESC, event.id DESC LIMIT 1) AS application_stage
               FROM preparation_requests ORDER BY updated_at DESC, created_at DESC"""
        ).fetchall()
    result = []
    for row in rows:
        item = dict(row)
        item["snapshot"] = json.loads(item["snapshot_json"])
        result.append(item)
    return result


def get_preparation(database_path: Path, request_id: str) -> dict[str, Any] | None:
    with connect(database_path) as db:
        row = db.execute(
            "SELECT * FROM preparation_requests WHERE id = ?", (request_id,)
        ).fetchone()
        stage = db.execute(
            """SELECT stage FROM application_events
               WHERE request_id = ?
                 AND event_type IN ('owner_submission_attestation', 'owner_stage_update')
               ORDER BY occurred_at DESC, id DESC LIMIT 1""",
            (request_id,),
        ).fetchone()
    if row is None:
        return None
    result = dict(row)
    result["snapshot"] = json.loads(result["snapshot_json"])
    result["application_stage"] = stage["stage"] if stage else ""
    return result


def _claim_candidates(source_text: str) -> list[str]:
    candidates: list[str] = []
    seen: set[str] = set()
    for raw_line in source_text.splitlines():
        line = re.sub(r"^\s*(?:[-*•▪◦]+|\d+[.)])\s*", "", raw_line).strip()
        line = " ".join(line.split())
        if len(line) < 25 or len(line) > 600 or line.endswith(":"):
            continue
        normalized = line.casefold()
        if normalized not in seen:
            candidates.append(line)
            seen.add(normalized)
    if not candidates:
        for paragraph in re.split(r"\n\s*\n", source_text):
            line = " ".join(paragraph.split())
            if 25 <= len(line) <= 600 and line.casefold() not in seen:
                candidates.append(line)
                seen.add(line.casefold())
    return candidates[:500]


def _clean_text(value: str) -> str:
    return "".join(
        character if character in "\n\r\t" or ord(character) >= 32 else " "
        for character in value
    )
