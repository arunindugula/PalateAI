import json
from pathlib import Path

ORDERS_PATH = Path(__file__).resolve().parent.parent / "data" / "orders.json"


def _load_orders() -> list[dict]:
    with open(ORDERS_PATH) as f:
        return json.load(f)


PRIVATE_FIELDS = ("Email", "PhoneNumber")


def _redact(order: dict) -> dict:
    """Strip PII fields before an order is returned to a caller."""
    return {k: v for k, v in order.items() if k not in PRIVATE_FIELDS}


def _find_order_by_field(field: str, value: str) -> dict | None:
    needle = value.strip().lower()
    for order in _load_orders():
        if order[field].lower() == needle:
            return _redact(order)
    return None


def find_order_by_order_id(order_id: str) -> dict | None:
    return _find_order_by_field("order_id", order_id)


def find_order_by_tracking_id(tracking_id: str) -> dict | None:
    return _find_order_by_field("TrackingId", tracking_id)


def find_order_by_email(email: str) -> dict | None:
    return _find_order_by_field("Email", email)


def find_order_by_phone_number(phone_number: str) -> dict | None:
    return _find_order_by_field("PhoneNumber", phone_number)
