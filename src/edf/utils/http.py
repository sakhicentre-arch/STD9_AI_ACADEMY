"""
EDF-L1 HTTP Utilities.

Provides a requests.Session wrapper with retry logic,
timeout configuration, and exponential backoff interface.
"""

from __future__ import annotations

import logging
import os
import time
from typing import Optional

_logger = logging.getLogger(__name__)

# Default HTTP configuration
DEFAULT_USER_AGENT = "STD9-AI-Academy/EDF-L1 (educational download)"
DEFAULT_TIMEOUT_SECONDS = 120
DEFAULT_MAX_RETRIES = 3
DEFAULT_BACKOFF_BASE = 1.0
DEFAULT_CHUNK_SIZE = 8192


class HTTPError(Exception):
    """Raised when an HTTP request fails after all retries."""
    pass


class RetryExhaustedError(HTTPError):
    """Raised when all retry attempts have been exhausted."""
    pass


def create_session(
    user_agent: str = DEFAULT_USER_AGENT,
    timeout: int = DEFAULT_TIMEOUT_SECONDS,
) -> dict:
    """
    Create a configured requests session.

    Placeholder — returns a configuration dict instead of a session
    to avoid requiring ``requests`` at module import time.

    Args:
        user_agent: User-Agent header string.
        timeout: Default request timeout in seconds.

    Returns:
        Configuration dict for the session.
    """
    import requests

    session = requests.Session()
    session.headers.update({"User-Agent": user_agent})
    # Store timeout on the session object for later retrieval by callers.
    # (requests.Session has no native timeout attribute; we attach one.)
    session.timeout = timeout  # type: ignore[attr-defined]
    return session


def compute_backoff(
    attempt: int,
    base: float = DEFAULT_BACKOFF_BASE,
    max_backoff: float = 60.0,
) -> float:
    """
    Compute exponential backoff delay for a given retry attempt.

    Args:
        attempt: The current attempt number (0-based).
        base: Base delay in seconds.
        max_backoff: Maximum backoff delay in seconds.

    Returns:
        Delay in seconds before the next retry.
    """
    delay = base * (2 ** attempt)
    return min(delay, max_backoff)


def should_retry(status_code: int) -> bool:
    """
    Determine if an HTTP response status code warrants a retry.

    Retries are appropriate for:
        - 429 (Too Many Requests)
        - 500, 502, 503, 504 (Server errors)

    Args:
        status_code: HTTP response status code.

    Returns:
        True if the request should be retried.
    """
    retryable = {429, 500, 502, 503, 504}
    return status_code in retryable


def download_stream(
    url: str,
    dest_path: str,
    chunk_size: int = DEFAULT_CHUNK_SIZE,
    timeout: int = DEFAULT_TIMEOUT_SECONDS,
    max_retries: int = DEFAULT_MAX_RETRIES,
    backoff_base: float = DEFAULT_BACKOFF_BASE,
    user_agent: str = DEFAULT_USER_AGENT,
) -> dict:
    """
    Download a file from a URL to a local path with retry logic.

    Streams the response to disk in chunks to handle large files.
    Retries on recoverable HTTP errors with exponential backoff.

    Args:
        url: URL to download from.
        dest_path: Local file path to write to.
        chunk_size: Download chunk size in bytes.
        timeout: Request timeout in seconds.
        max_retries: Maximum number of retry attempts.
        backoff_base: Base delay for exponential backoff.
        user_agent: User-Agent header string.

    Returns:
        Dictionary with keys:
            - success (bool)
            - status_code (int)
            - size_bytes (int)
            - error (str or None)

    Raises:
        RetryExhaustedError: If all retries are exhausted.
    """
    import requests

    # Ensure parent directory exists for the destination file.
    dest_dir = os.path.dirname(os.path.abspath(dest_path))
    if dest_dir:
        os.makedirs(dest_dir, exist_ok=True)

    session = create_session(user_agent=user_agent, timeout=timeout)
    last_error: Optional[str] = None
    last_status: int = 0

    for attempt in range(1, max_retries + 1):
        try:
            _logger.debug(
                "download attempt %d/%d for %s", attempt, max_retries, url
            )
            response = session.get(
                url, stream=True, timeout=timeout, allow_redirects=True
            )
            last_status = response.status_code

            # Non-retryable client errors (except 429) -> fail fast.
            if (
                response.status_code >= 400
                and response.status_code != 429
                and not should_retry(response.status_code)
            ):
                last_error = f"HTTP {response.status_code}"
                _logger.error(
                    "download failed (client error): %s -> %s",
                    url, last_error,
                )
                return {
                    "success": False,
                    "status_code": response.status_code,
                    "size_bytes": 0,
                    "error": last_error,
                }

            # Retryable server/rate-limit errors -> back off and retry.
            if should_retry(response.status_code):
                last_error = f"HTTP {response.status_code} (retryable)"
                if attempt < max_retries:
                    delay = compute_backoff(attempt - 1, base=backoff_base)
                    _logger.warning(
                        "download retryable failure %s; retry %d/%d after %.1fs",
                        last_error, attempt, max_retries, delay,
                    )
                    time.sleep(delay)
                    continue
                break  # retries exhausted

            # Success path: stream body to disk.
            response.raise_for_status()
            written = 0
            with open(dest_path, "wb") as fh:
                for chunk in response.iter_content(chunk_size=chunk_size):
                    if chunk:
                        fh.write(chunk)
                        written += len(chunk)

            _logger.info(
                "download success: %s -> %s (%d bytes, attempt %d)",
                url, dest_path, written, attempt,
            )
            return {
                "success": True,
                "status_code": response.status_code,
                "size_bytes": written,
                "error": None,
            }

        except (requests.exceptions.Timeout,
                requests.exceptions.ConnectionError) as e:
            last_error = f"{type(e).__name__}: {e}"
            if attempt < max_retries:
                delay = compute_backoff(attempt - 1, base=backoff_base)
                _logger.warning(
                    "download network error %s; retry %d/%d after %.1fs",
                    last_error, attempt, max_retries, delay,
                )
                time.sleep(delay)
                continue
            break  # retries exhausted
        except requests.exceptions.RequestException as e:
            last_error = f"{type(e).__name__}: {e}"
            _logger.error("download failed (non-retryable): %s", last_error)
            break

    # All retries exhausted.
    _logger.error(
        "download exhausted retries: %s -> %s (%s)",
        url, dest_path, last_error,
    )
    return {
        "success": False,
        "status_code": last_status,
        "size_bytes": 0,
        "error": last_error or "Retries exhausted",
    }


def head_request(
    url: str,
    timeout: int = DEFAULT_TIMEOUT_SECONDS,
    user_agent: str = DEFAULT_USER_AGENT,
) -> Optional[dict]:
    """
    Perform a HEAD request to check URL availability.

    Args:
        url: URL to check.
        timeout: Request timeout in seconds.
        user_agent: User-Agent header string.

    Returns:
        Dict with status_code and headers, or None on failure.
    """
    import requests

    session = create_session(user_agent=user_agent, timeout=timeout)
    try:
        response = session.head(
            url, timeout=timeout, allow_redirects=True
        )
        return {
            "status_code": response.status_code,
            "headers": dict(response.headers),
        }
    except requests.exceptions.RequestException as e:
        _logger.debug("HEAD request failed for %s: %s", url, e)
        return None
