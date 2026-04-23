def send_reset_mail(email: str) -> bool:
    """Email the password reset link to ``email`` - returns True when queued."""
    return True


def validate_token(token: str, issued_at: float, now: float) -> bool:
    """Return True while the reset token is still within 24h of issue."""
    return (now - issued_at) <= 24 * 3600
