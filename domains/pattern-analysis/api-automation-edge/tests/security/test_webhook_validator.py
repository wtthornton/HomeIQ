"""Tests for WebhookValidator (Epic H2: HMAC signing and replay protection)."""

import time

from src.security.webhook_validator import WebhookValidator


def _validator() -> WebhookValidator:
    return WebhookValidator(secret_key=b"test-secret")


def test_forged_signature_does_not_burn_nonce():
    """A forged-signature request must be rejected on the signature, and must
    not consume the nonce — otherwise a legitimate request that later reuses
    that nonce gets rejected as a replay it never actually was."""
    validator = _validator()
    payload = "payload"
    timestamp = str(time.time())
    nonce = "abc"

    headers = {
        "X-Webhook-Signature": "forged-signature",
        "X-Webhook-Timestamp": timestamp,
        "X-Webhook-Nonce": nonce,
    }

    is_valid, error = validator.validate_webhook(payload, headers)

    assert is_valid is False
    assert error == "Invalid signature"
    assert nonce not in validator.used_nonces


def test_legit_request_succeeds_after_forged_attempt_reused_the_nonce():
    """A legitimate request must still succeed even if an earlier forged
    request (with a fresh but not-yet-used nonce) was rejected first."""
    validator = _validator()
    payload = "payload"
    timestamp = str(time.time())
    nonce = "abc"

    forged_headers = {
        "X-Webhook-Signature": "forged-signature",
        "X-Webhook-Timestamp": timestamp,
        "X-Webhook-Nonce": nonce,
    }
    validator.validate_webhook(payload, forged_headers)

    valid_signature = validator.generate_signature(payload, timestamp, nonce)
    legit_headers = {
        "X-Webhook-Signature": valid_signature,
        "X-Webhook-Timestamp": timestamp,
        "X-Webhook-Nonce": nonce,
    }

    is_valid, error = validator.validate_webhook(payload, legit_headers)

    assert is_valid is True
    assert error is None


def test_valid_signature_replaying_an_already_used_nonce_is_still_rejected():
    """A genuinely valid, previously-accepted request must still be rejected
    as a replay if resubmitted with the same nonce."""
    validator = _validator()
    payload = "payload"
    timestamp = str(time.time())
    nonce = "abc"
    signature = validator.generate_signature(payload, timestamp, nonce)
    headers = {
        "X-Webhook-Signature": signature,
        "X-Webhook-Timestamp": timestamp,
        "X-Webhook-Nonce": nonce,
    }

    first_valid, _ = validator.validate_webhook(payload, headers)
    assert first_valid is True

    second_valid, second_error = validator.validate_webhook(payload, headers)

    assert second_valid is False
    assert second_error == "Nonce already used (replay attack)"
