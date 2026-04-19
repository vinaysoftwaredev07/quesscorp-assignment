from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from app.core.config import get_settings
from app.events.broker import get_event_broker


def publish_domain_event(
    *,
    domain: str,
    action: str,
    payload: dict[str, Any],
    source: str | None = None,
) -> None:
    settings = get_settings()
    broker = get_event_broker()
    event_name = f"{domain}.{action}"
    resolved_source = source or settings.event_source
    base_event = {
        "event_id": str(uuid4()),
        "event_name": event_name,
        "source": resolved_source,
        "occurred_at": datetime.now(timezone.utc).isoformat(),
        "payload": payload,
    }

    print(f"Publishing event: {event_name} with payload: {payload}")

    broker.publish(f"internal.{event_name}", {**base_event, "topic": "internal"})
    broker.publish(f"activity.{event_name}", {**base_event, "topic": "activity"})
