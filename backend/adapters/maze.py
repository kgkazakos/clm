"""
Maze export adapter.
Maps Maze's session export JSON format to canonical InteractionEvent models.

Maze exports contain a 'recordings' array with typed events. This adapter
normalises Maze-specific field names and event types to the canonical schema.
"""

from models import InteractionEvent


# Maze event type → canonical event type
_EVENT_TYPE_MAP: dict[str, str] = {
    "CLICK":       "click",
    "TAP":         "click",
    "SCROLL":      "scroll",
    "INPUT":       "input",
    "NAVIGATION":  "navigation",
    "SCREEN_VIEW": "navigation",
    "ERROR":       "error",
    "HOVER":       "hover",
    "MISCLICK":    "click",
}

_ERROR_TYPES = {"ERROR", "MISCLICK"}


def parse(raw: dict) -> list[InteractionEvent]:
    """
    Parse a Maze session export dict into canonical InteractionEvent models.

    Expected Maze export structure:
    {
      "session": { "started_at": <ms epoch>, ... },
      "recordings": [
        {
          "type": "CLICK",
          "timestamp": <ms from session start>,
          "x": 0.52,
          "y": 0.31,
          "screen": "screen-id",
          "element": "element-id",
          "duration": 450,
          ...
        }
      ]
    }
    """
    recordings = raw.get("recordings", [])
    events: list[InteractionEvent] = []

    for rec in recordings:
        maze_type = rec.get("type", "").upper()
        canonical_type = _EVENT_TYPE_MAP.get(maze_type, "click")

        events.append(
            InteractionEvent(
                timestamp_ms=float(rec.get("timestamp", 0)),
                event_type=canonical_type,
                element_id=rec.get("element"),
                x=rec.get("x"),
                y=rec.get("y"),
                value=str(rec.get("value", "")) if rec.get("value") else None,
                screen_id=rec.get("screen"),
                duration_ms=float(rec["duration"]) if rec.get("duration") else None,
                is_error=maze_type in _ERROR_TYPES,
                metadata={"maze_type": maze_type},
            )
        )

    return sorted(events, key=lambda e: e.timestamp_ms)
