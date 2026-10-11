"""Razorpay subscription helpers.

The application never receives card or UPI credentials.  Checkout happens on
Razorpay and this module verifies the signed webhook sent back to the API.
"""

import hashlib
import hmac
import os
from typing import Any

import requests


RAZORPAY_API_BASE = "https://api.razorpay.com/v1"


class BillingConfigurationError(RuntimeError):
    pass


def _credentials(*, test_mode: bool = False) -> tuple[str, str]:
    key_id = os.environ.get("RAZORPAY_KEY_ID")
    key_secret = os.environ.get("RAZORPAY_KEY_SECRET")
    if not key_id or not key_secret:
        raise BillingConfigurationError(
            "Razorpay keys are not configured. Set RAZORPAY_KEY_ID and RAZORPAY_KEY_SECRET on the server."
        )
    if test_mode and not key_id.startswith("rzp_test_"):
        raise BillingConfigurationError(
            "Creator plan setup is test-only. Configure Razorpay test keys (rzp_test_...) before creating plans."
        )
    return key_id, key_secret


def create_razorpay_plan(*, name: str, amount_paise: int, description: str, test_mode: bool = False) -> dict[str, Any]:
    """Create a monthly Razorpay plan using server-held credentials."""
    key_id, key_secret = _credentials(test_mode=test_mode)
    response = requests.post(
        f"{RAZORPAY_API_BASE}/plans",
        auth=(key_id, key_secret),
        json={
            "period": "monthly",
            "interval": 1,
            "item": {
                "name": name,
                "amount": amount_paise,
                "currency": "INR",
                "description": description,
            },
        },
        timeout=20,
    )
    if not response.ok:
        try:
            details = response.json().get("error", {}).get("description", response.text)
        except ValueError:
            details = response.text
        raise RuntimeError(f"Razorpay could not create plan '{name}': {details}")
    return response.json()


def create_subscription(*, razorpay_plan_id: str, customer_email: str, customer_name: str) -> dict[str, Any]:
    """Create a Razorpay subscription and return its hosted checkout URL."""
    key_id, key_secret = _credentials()
    response = requests.post(
        f"{RAZORPAY_API_BASE}/subscriptions",
        auth=(key_id, key_secret),
        json={
            "plan_id": razorpay_plan_id,
            "total_count": 120,
            "customer_notify": 1,
            "notes": {"customer_email": customer_email, "customer_name": customer_name},
        },
        timeout=20,
    )
    if not response.ok:
        try:
            details = response.json().get("error", {}).get("description", response.text)
        except ValueError:
            details = response.text
        raise RuntimeError(f"Razorpay could not create the subscription: {details}")
    return response.json()


def verify_webhook_signature(raw_body: bytes, signature: str | None) -> bool:
    secret = os.environ.get("RAZORPAY_WEBHOOK_SECRET")
    if not secret:
        raise BillingConfigurationError("RAZORPAY_WEBHOOK_SECRET is not configured.")
    if not signature:
        return False
    expected = hmac.new(secret.encode("utf-8"), raw_body, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, signature)
