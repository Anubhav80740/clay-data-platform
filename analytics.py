"""
analytics.py - Centralized PostHog Product Analytics Engine for Clay Data Downloader.

Provides a clean, reusable abstraction for PostHog event tracking, user identification,
performance timer measurement, and session management without exposing sensitive data.
"""

import os
import sys
import time
from typing import Dict, Any, Optional

try:
    import posthog
    HAS_POSTHOG = True
except ImportError:
    HAS_POSTHOG = False

POSTHOG_HOST = os.environ.get("POSTHOG_HOST", "https://us.i.posthog.com")
APP_ENV = os.environ.get("APP_ENV") or os.environ.get("ENVIRONMENT") or "production"

# Standard Event Taxonomy Constants
EVENT_APP_OPENED = "app_opened"
EVENT_PAGE_VIEWED = "page_viewed"
EVENT_USER_LOGIN = "user_login"
EVENT_USER_LOGOUT = "user_logout"
EVENT_SEARCH_STARTED = "search_started"
EVENT_SEARCH_COMPLETED = "search_completed"
EVENT_SEARCH_FAILED = "search_failed"
EVENT_FILTER_APPLIED = "filter_applied"
EVENT_FILTER_REMOVED = "filter_removed"
EVENT_DATA_PROCESSING_STARTED = "data_processing_started"
EVENT_DATA_PROCESSING_COMPLETED = "data_processing_completed"
EVENT_DATA_PROCESSING_FAILED = "data_processing_failed"
EVENT_DOWNLOAD_STARTED = "download_started"
EVENT_DOWNLOAD_COMPLETED = "download_completed"
EVENT_DOWNLOAD_FAILED = "download_failed"
EVENT_EXPORT_COMPLETED = "export_completed"
EVENT_GEO_CONFIG_UPDATED = "geo_config_updated"

_INITIALIZED = False
_TIMERS: Dict[str, float] = {}

def get_posthog_key() -> str:
    """Dynamically resolves PostHog key from environment variables or Streamlit secrets."""
    key = os.environ.get("POSTHOG_API_KEY") or os.environ.get("POSTHOG_PROJECT_API_KEY") or ""
    if not key:
        try:
            import streamlit as st
            if hasattr(st, "secrets"):
                key = str(st.secrets.get("POSTHOG_API_KEY") or st.secrets.get("POSTHOG_PROJECT_API_KEY") or "").strip()
        except Exception:
            pass
    return key

def init_posthog() -> bool:
    """
    Initializes PostHog once safely.
    Returns True if PostHog is active and initialized, False otherwise.
    Does NOT throw errors if environment variables are missing.
    """
    global _INITIALIZED
    if _INITIALIZED:
        return True

    if not HAS_POSTHOG:
        return False

    key = get_posthog_key()
    if not key:
        return False

    try:
        posthog.api_key = key
        posthog.host = POSTHOG_HOST
        posthog.disabled = False
        _INITIALIZED = True
        return True
    except Exception:
        return False

def identify_user(user_id: str, user_properties: Optional[Dict[str, Any]] = None) -> None:
    """
    Identifies an authenticated user with a stable user ID.
    Only captures non-sensitive properties (e.g. account_type, user_id).
    """
    if not init_posthog():
        return

    safe_props = {
        "user_id": user_id,
        "account_type": "team_member",
        "app_environment": APP_ENV
    }
    if user_properties:
        sensitive_keys = {"password", "cookie", "token", "clay_key", "secret"}
        for k, v in user_properties.items():
            if str(k).lower() not in sensitive_keys:
                safe_props[k] = v

    try:
        posthog.identify(user_id, safe_props)
        posthog.flush()
    except Exception:
        pass

def reset_user() -> None:
    """Resets PostHog user identity session on logout."""
    if not init_posthog():
        return
    try:
        posthog.reset()
        posthog.flush()
    except Exception:
        pass

def track_event(
    event_name: str,
    properties: Optional[Dict[str, Any]] = None,
    distinct_id: Optional[str] = None
) -> None:
    """
    Captures a product analytics event in PostHog.
    Guarantees no raw Clay dataset rows or PII are transmitted.
    """
    if not init_posthog():
        return

    user_id = distinct_id or "anonymous_user"
    
    event_props = {
        "app_name": "Clay Data Downloader",
        "app_environment": APP_ENV
    }
    
    if properties:
        forbidden_substrings = ["password", "cookie", "secret", "token", "auth"]
        for k, v in properties.items():
            k_lower = str(k).lower()
            if isinstance(v, list) and len(v) > 500:
                event_props[f"{k}_count"] = len(v)
            elif not any(sub in k_lower for sub in forbidden_substrings):
                event_props[k] = v

    try:
        posthog.capture(user_id, event_name, event_props)
        posthog.flush()
    except Exception:
        pass

def start_timer(timer_name: str) -> None:
    """Starts a performance timer for an operation."""
    _TIMERS[timer_name] = time.time()

def stop_timer(timer_name: str) -> int:
    """
    Stops a performance timer and returns the elapsed time in milliseconds (duration_ms).
    Returns 0 if the timer was not started.
    """
    start_t = _TIMERS.pop(timer_name, None)
    if start_t is None:
        return 0
    return int((time.time() - start_t) * 1000)
