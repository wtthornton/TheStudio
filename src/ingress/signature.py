"""HMAC-SHA256 webhook signature validation for GitHub webhooks."""

import hashlib
import hmac


def validate_signature(payload: bytes, secret: str, signature_header: str) -> bool:
    """Validate GitHub webhook HMAC-SHA256 signature.

    Args:
        payload: Raw request body bytes.
        secret: Webhook shared secret.
        signature_header: Value of X-Hub-Signature-256 header (e.g., "sha256=abc123...").

    Returns:
        True if the signature is valid.
    """
    if not signature_header.startswith("sha256="):
        return False

    expected_signature = signature_header[7:]  # Strip "sha256=" prefix
    computed = hmac.new(secret.encode(), payload, hashlib.sha256).hexdigest()

    # Constant-time comparison to prevent timing attacks
    return hmac.compare_digest(computed, expected_signature)
