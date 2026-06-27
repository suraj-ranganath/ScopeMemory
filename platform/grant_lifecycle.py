"""Pure grant lifetime helpers shared by Dolt and graph fallback code."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any


def grant_row_is_active(grant: dict[str, Any], now: datetime | None = None) -> bool:
    """Return whether a persisted grant can authorize another call."""
    count = grant.get("call_count_remaining")
    if count is not None:
        try:
            if int(count) <= 0:
                return False
        except (TypeError, ValueError):
            return False

    expires_at = grant.get("expires_at")
    if expires_at in (None, ""):
        return True

    parsed = _parse_time(expires_at)
    if parsed is None:
        return False
    current = now or datetime.now(UTC)
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=UTC)
    if current.tzinfo is None:
        current = current.replace(tzinfo=UTC)
    return parsed > current


def _parse_time(value: Any) -> datetime | None:
    if isinstance(value, datetime):
        return value
    if isinstance(value, str):
        normalized = value.replace("Z", "+00:00")
        try:
            return datetime.fromisoformat(normalized)
        except ValueError:
            return None
    return None
