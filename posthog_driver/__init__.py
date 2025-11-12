"""
PostHog Driver for Claude Agent SDK

A Python client library for integrating PostHog analytics with AI agents
running in E2B sandboxes.

Usage:
    from posthog_driver import PostHogClient

    client = PostHogClient(
        api_key='your_personal_api_key',
        project_id='your_project_id'
    )

    # Query events
    events = client.get_events(event_name="User Signup", limit=100)

    # Export data
    data = client.export_events(start_date="2024-01-01", end_date="2024-01-31")

    # Run HogQL queries
    results = client.query("SELECT * FROM events WHERE event = 'Page View' LIMIT 10")
"""

from .client import PostHogClient
from .exceptions import (
    PostHogError,
    AuthenticationError,
    ObjectNotFoundError,
    QueryError,
    ConnectionError,
    RateLimitError,
    ValidationError
)

__version__ = '1.0.0'
__all__ = [
    'PostHogClient',
    'PostHogError',
    'AuthenticationError',
    'ObjectNotFoundError',
    'QueryError',
    'ConnectionError',
    'RateLimitError',
    'ValidationError'
]
