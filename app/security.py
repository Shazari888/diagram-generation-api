"""
Security middleware and utilities for the Diagram Generation API.

Covers:
- HTTPS enforcement (via X-Forwarded-Proto when behind a proxy)
- Safe log filtering to scrub secrets and payment signatures
- Rate limiting per IP and per wallet address (via slowapi + Redis)
- Anomaly logging for repeated failed payment verifications
"""

import logging
import re
import time
from collections import defaultdict
from typing import Callable

from fastapi import Request, Response
from fastapi.responses import JSONResponse
from slowapi import Limiter
from slowapi.util import get_remote_address

from app.config import settings

log = logging.getLogger(__name__)
anomaly_log = logging.getLogger("security.anomaly")

# ---------------------------------------------------------------------------
# Safe log filter — scrubs secrets and payment signatures from log records
# ---------------------------------------------------------------------------

_SCRUB_PATTERNS = [
    # OpenAI / generic API keys
    (re.compile(r"(sk-[A-Za-z0-9\-_]{20,})", re.IGNORECASE), "sk-***"),
    # Hex private keys / signatures (0x + 64+ hex chars)
    (re.compile(r"(0x[0-9a-fA-F]{64,})", re.IGNORECASE), "0x***"),
    # PAYMENT-SIGNATURE header value (base64-ish long strings)
    (re.compile(r"(PAYMENT.SIGNATURE['\"]?\s*[:=]\s*['\"]?)([A-Za-z0-9+/=_\-]{40,})", re.IGNORECASE), r"\g<1>***"),
    # Bearer tokens
    (re.compile(r"(Bearer\s+)[A-Za-z0-9\-._~+/]+=*", re.IGNORECASE), r"\g<1>***"),
]


class ScrubSecretsFilter(logging.Filter):
    """Removes secrets and payment data from log messages before emission."""

    def filter(self, record: logging.LogRecord) -> bool:
        try:
            msg = record.getMessage()
            for pattern, replacement in _SCRUB_PATTERNS:
                msg = pattern.sub(replacement, msg)
            # Replace the pre-formatted message so handlers emit the clean version
            record.msg = msg
            record.args = ()
        except Exception:
            pass
        return True


def install_log_filter() -> None:
    """Attach the scrubbing filter to the root logger and uvicorn access logger."""
    filt = ScrubSecretsFilter()
    for name in ("", "uvicorn", "uvicorn.access", "uvicorn.error", "app"):
        logging.getLogger(name).addFilter(filt)


# ---------------------------------------------------------------------------
# HTTPS enforcement middleware
# ---------------------------------------------------------------------------

async def https_redirect_middleware(request: Request, call_next: Callable) -> Response:
    """
    Reject non-HTTPS requests when running behind a TLS-terminating proxy
    (Railway sets X-Forwarded-Proto). Health checks are allowed over HTTP
    so Railway's internal probe can still reach /health.
    """
    if not settings.enforce_https:
        return await call_next(request)

    proto = request.headers.get("x-forwarded-proto", "https")
    if proto != "https" and request.url.path != "/health":
        return JSONResponse(
            status_code=400,
            content={"detail": "HTTPS is required"},
        )
    return await call_next(request)


# ---------------------------------------------------------------------------
# Rate limiter (slowapi)
# ---------------------------------------------------------------------------

def _get_ip(request: Request) -> str:
    """Return the real client IP, respecting Railway's proxy headers."""
    forwarded_for = request.headers.get("x-forwarded-for")
    if forwarded_for:
        return forwarded_for.split(",")[0].strip()
    return get_remote_address(request)


limiter = Limiter(key_func=_get_ip)


# ---------------------------------------------------------------------------
# Anomaly detection — repeated failed payment verifications
# ---------------------------------------------------------------------------

# In-memory sliding window: ip -> list of failure timestamps.
# This is per-process and resets on redeploy, which is acceptable —
# it catches burst abuse within a single deployment lifetime.
# For multi-replica deployments, move this to Redis.
_payment_failures: dict[str, list[float]] = defaultdict(list)

ANOMALY_WINDOW_SECONDS = 60
ANOMALY_THRESHOLD = 5  # failures in window before logging an anomaly


def record_payment_failure(ip: str, path: str, detail: str = "") -> None:
    """
    Record a payment verification failure for anomaly detection.
    Logs a warning when an IP exceeds ANOMALY_THRESHOLD failures within
    ANOMALY_WINDOW_SECONDS.
    """
    now = time.monotonic()
    window = _payment_failures[ip]
    # Prune old entries
    _payment_failures[ip] = [t for t in window if now - t < ANOMALY_WINDOW_SECONDS]
    _payment_failures[ip].append(now)

    count = len(_payment_failures[ip])
    if count >= ANOMALY_THRESHOLD:
        anomaly_log.warning(
            "ANOMALY: ip=%s path=%s failures_in_%ds=%d detail=%s",
            ip,
            path,
            ANOMALY_WINDOW_SECONDS,
            count,
            detail[:120] if detail else "",
        )
