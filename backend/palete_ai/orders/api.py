from fastapi import APIRouter, HTTPException

from orders.service import (
    find_order_by_email,
    find_order_by_order_id,
    find_order_by_phone_number,
    find_order_by_tracking_id,
)

router = APIRouter(prefix="/orders", tags=["orders"])


def _or_404(order: dict | None, identifier: str) -> dict:
    if order is None:
        raise HTTPException(status_code=404, detail=f"No order found matching '{identifier}'")
    return order


@router.get("/order-id/{order_id}")
def get_order_by_order_id(order_id: str) -> dict:
    """Look up an order by Order ID."""
    return _or_404(find_order_by_order_id(order_id), order_id)


@router.get("/tracking-id/{tracking_id}")
def get_order_by_tracking_id(tracking_id: str) -> dict:
    """Look up an order by Tracking ID."""
    return _or_404(find_order_by_tracking_id(tracking_id), tracking_id)


@router.get("/email/{email}")
def get_order_by_email(email: str) -> dict:
    """Look up an order by customer email."""
    return _or_404(find_order_by_email(email), email)


@router.get("/phone/{phone_number}")
def get_order_by_phone_number(phone_number: str) -> dict:
    """Look up an order by customer phone number."""
    return _or_404(find_order_by_phone_number(phone_number), phone_number)
