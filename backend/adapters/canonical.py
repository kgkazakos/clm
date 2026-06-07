"""
Canonical schema adapter.
Researchers using custom logging instrument against this schema directly.
No mapping required — validates and returns events as-is.
"""

from models import InteractionEvent


def parse(raw: list[dict]) -> list[InteractionEvent]:
    """
    Parse a list of raw event dicts into canonical InteractionEvent models.
    Raises ValidationError if required fields are missing or malformed.
    """
    return [InteractionEvent(**event) for event in raw]


# ─── Canonical schema reference ───────────────────────────────────────────────
# Researchers instrumenting custom logging should emit events in this format:
#
# {
#   "timestamp_ms": 1234.5,       required — ms from session start
#   "event_type": "click",        required — click|scroll|input|navigation|error|hover
#   "element_id": "submit-btn",   optional — UI element identifier
#   "x": 0.52,                    optional — normalised cursor x (0–1)
#   "y": 0.31,                    optional — normalised cursor y (0–1)
#   "value": "search term",       optional — input value or scroll delta (px)
#   "screen_id": "checkout",      optional — current screen/page identifier
#   "duration_ms": 450.0,         optional — dwell or hold duration
#   "is_error": false,            optional — true if action failed
#   "metadata": {}                optional — any additional researcher-defined fields
# }
