"""Person B: mocked Slack search with prompt-injection fixture."""

from __future__ import annotations

import json
from typing import Any

from dolt_store import connect


def search_slack(channel_id: str) -> dict[str, Any]:
    conn = connect()
    with conn.cursor() as cur:
        cur.execute(
            "SELECT payload_json FROM slack_fixtures WHERE channel_id = %s LIMIT 1",
            (channel_id,),
        )
        row = cur.fetchone()
    conn.close()
    if not row:
        return {"channel": channel_id, "messages": [], "prompt_injection": None}
    return json.loads(row["payload_json"])
