import json
import re
from pathlib import Path

ORDERS_PATH = Path(__file__).resolve().parent.parent / "data" / "orders.json"


def _load_orders() -> list[dict]:
    with open(ORDERS_PATH) as f:
        return json.load(f)


PRIVATE_FIELDS = ("Email", "PhoneNumber")


def _redact(order: dict) -> dict:
    """Strip PII fields before an order is returned to a caller."""
    return {k: v for k, v in order.items() if k not in PRIVATE_FIELDS}


def _normalize_identifier(value: str) -> str:
    """Lowercase and strip non-alphanumerics, e.g. so "ORD1002" == "ORD-1002".

    Voice transcription (and sloppy manual typing) commonly drops hyphens/
    spaces from spoken identifiers, so order/tracking IDs match on
    alphanumerics only. Email and phone number matching stay strict since
    stripping punctuation there would break the format entirely.
    """
    return re.sub(r"[^a-z0-9]", "", value.lower())


def _find_order_by_field(field: str, value: str, normalize: bool = False) -> dict | None:
    transform = _normalize_identifier if normalize else (lambda s: s.strip().lower())
    needle = transform(value)
    for order in _load_orders():
        if transform(order[field]) == needle:
            return _redact(order)
    return None


def find_order_by_order_id(order_id: str) -> dict | None:
    return _find_order_by_field("order_id", order_id, normalize=True)


def find_order_by_tracking_id(tracking_id: str) -> dict | None:
    return _find_order_by_field("TrackingId", tracking_id, normalize=True)


def find_order_by_email(email: str) -> dict | None:
    return _find_order_by_field("Email", email)


def find_order_by_phone_number(phone_number: str) -> dict | None:
    return _find_order_by_field("PhoneNumber", phone_number)
