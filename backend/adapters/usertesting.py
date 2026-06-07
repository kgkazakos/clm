"""
UserTesting export adapter.
Maps UserTesting's session export JSON format to canonical InteractionEvent models.

UserTesting exports interaction data as a 'clips' array containing
typed interaction events per task. This adapter normalises to the
canonical schema.

Note: UserTesting's export format varies by plan tier. This adapter
targets the standard JSON session export available on all paid plans.
Enterprise plan exports include additional fields (eye_tracking,
think_aloud_transcript) which are ignored here — CLM operates on
interaction telemetry only.
"""

from models import InteractionEvent


_EVENT_TYPE_MAP: dict[str, str] = {
    "click":         "click",
    "tap":           "click",
    "double_click":  "click",
    "right_click":   "click",
    "scroll":        "scroll",
    "key_press":     "input",
    "text_input":    "input",
    "form_submit":   "input",
    "page_visit":    "navigation",
    "url_change":    "navigation",
    "back":          "navigation",
    "forward":       "navigation",
    "mouseover":     "hover",
    "mouse_enter":   "hover",
    "error":         "error",
    "js_error":      "error",
    "network_error": "error",
}

_ERROR_TYPES = {"error", "js_error", "network_error"}


def parse(raw: dict) -> list[InteractionEvent]:
    """
    Parse a UserTesting session export dict into canonical InteractionEvent models.

    Expected UserTesting export structure:
    {
      "session": {
        "id": "...",
        "task_id": "...",
        "started_at": <ms epoch>,
        ...
      },
      "clips": [
        {
          "type": "click",
          "timestamp": <ms from session start>,
          "x": 0.52,
          "y": 0.31,
          "page_url": "https://...",
          "element_selector": "#submit-btn",
          "scroll_y": null,
          "input_value": null,
          "duration_ms": null,
          "is_rage_click": false,
          ...
        }
      ]
    }
    """
    clips = raw.get("clips", [])
    events: list[InteractionEvent] = []

    for clip in clips:
        ut_type = clip.get("type", "").lower()
        canonical_type = _EVENT_TYPE_MAP.get(ut_type, "click")

        # UserTesting flags rage clicks explicitly — map to click
        # but mark as error for error_recovery signal calculator
        is_rage = clip.get("is_rage_click", False)

        scroll_y = clip.get("scroll_y")
        input_val = clip.get("input_value")
        value = (
            str(scroll_y) if scroll_y is not None
            else str(input_val) if input_val is not None
            else None
        )

        # UserTesting uses page_url as screen identifier
        screen_id = clip.get("page_url")

        events.append(
            InteractionEvent(
                timestamp_ms=float(clip.get("timestamp", 0)),
                event_type=canonical_type,
                element_id=clip.get("element_selector"),
                x=clip.get("x"),
                y=clip.get("y"),
                value=value,
                screen_id=screen_id,
                duration_ms=float(clip["duration_ms"]) if clip.get("duration_ms") else None,
                is_error=ut_type in _ERROR_TYPES or is_rage,
                metadata={
                    "ut_type": ut_type,
                    "is_rage_click": is_rage,
                    "page_url": screen_id,
                },
            )
        )

    return sorted(events, key=lambda e: e.timestamp_ms)
