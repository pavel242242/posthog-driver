"""
PostHog Driver for Claude Agent SDK

A Python client implementing the driver contract for PostHog analytics platform.
Enables AI agents to perform analytics tracking, data export/ETL, and information lookup.

Based on PostHog's comprehensive API:
- Event capture (real-time and batch)
- HogQL queries (SQL-like analytics)
- Data warehouse access
- Cohort management
- Insights and funnels
- Session replay access
- Experimentation results
"""

import os
import requests
from typing import List, Dict, Any, Optional, Union
from datetime import datetime, timedelta
from .exceptions import (
    PostHogError,
    AuthenticationError,
    ObjectNotFoundError,
    QueryError,
    ConnectionError,
    RateLimitError,
    ValidationError
)


class PostHogClient:
    """
    PostHog API client compatible with Claude Agent SDK driver pattern.

    Implements the standard driver contract:
    - list_objects() - Discover available entity types
    - get_fields(object_name) - Get schema for entity
    - query(query_string) - Execute HogQL queries

    Plus PostHog-specific methods for analytics, ETL, and data lookup.
    """

    def __init__(
        self,
        api_url: Optional[str] = None,
        api_key: Optional[str] = None,  # Personal API key
        project_id: Optional[str] = None,
        project_api_key: Optional[str] = None,  # For event capture
        timeout: int = 30,
        max_retries: int = 3,
        **kwargs
    ):
        """
        Initialize PostHog client.

        Args:
            api_url: Base URL (default: https://us.posthog.com or POSTHOG_API_URL env var)
            api_key: Personal API key for analytics/query endpoints (required)
            project_id: PostHog project ID (required)
            project_api_key: Project API key for event capture (optional)
            timeout: Request timeout in seconds
            max_retries: Maximum retry attempts for failed requests
        """
        self.api_url = (api_url or
                       os.getenv('POSTHOG_API_URL', 'https://us.posthog.com')).rstrip('/')
        self.api_key = api_key or os.getenv('POSTHOG_PERSONAL_API_KEY')
        self.project_id = project_id or os.getenv('POSTHOG_PROJECT_ID')
        self.project_api_key = project_api_key or os.getenv('POSTHOG_PROJECT_API_KEY')
        self.timeout = timeout
        self.max_retries = max_retries

        # Validation
        if not self.api_key:
            raise AuthenticationError(
                "Personal API key required. Set via api_key parameter or "
                "POSTHOG_PERSONAL_API_KEY environment variable."
            )
        if not self.project_id:
            raise PostHogError(
                "Project ID required. Set via project_id parameter or "
                "POSTHOG_PROJECT_ID environment variable."
            )

        # Setup HTTP session
        self.session = requests.Session()
        self.session.headers.update({
            'Authorization': f'Bearer {self.api_key}',
            'Content-Type': 'application/json'
        })

        # Determine capture endpoint (US vs EU)
        self.capture_url = self.api_url.replace('posthog.com', 'i.posthog.com')

    def _make_request(
        self,
        endpoint: str,
        method: str = 'GET',
        use_capture_url: bool = False,
        **kwargs
    ) -> Dict[str, Any]:
        """
        HTTP request wrapper with error handling and retries.

        Args:
            endpoint: API endpoint path
            method: HTTP method (GET, POST, PATCH, DELETE)
            use_capture_url: Use capture endpoint instead of main API
            **kwargs: Additional arguments for requests

        Returns:
            JSON response as dictionary

        Raises:
            AuthenticationError: Invalid credentials
            RateLimitError: Rate limit exceeded
            ObjectNotFoundError: Resource not found
            ConnectionError: Network issues
            PostHogError: Other API errors
        """
        base_url = self.capture_url if use_capture_url else self.api_url
        url = f"{base_url}{endpoint}"

        for attempt in range(self.max_retries):
            try:
                response = self.session.request(
                    method,
                    url,
                    timeout=self.timeout,
                    **kwargs
                )

                # Handle specific status codes
                if response.status_code == 401:
                    raise AuthenticationError(
                        "Authentication failed. Check your Personal API key."
                    )
                if response.status_code == 403:
                    raise AuthenticationError(
                        "Access forbidden. Check API key permissions."
                    )
                if response.status_code == 404:
                    raise ObjectNotFoundError(
                        f"Resource not found: {endpoint}"
                    )
                if response.status_code == 429:
                    raise RateLimitError(
                        "Rate limit exceeded. PostHog limits: 240/min, 1200/hour for "
                        "analytics; 2400/hour for queries. Consider using batch exports."
                    )

                response.raise_for_status()

                # Return JSON if available, otherwise return success indicator
                try:
                    return response.json()
                except ValueError:
                    return {'success': True, 'status_code': response.status_code}

            except requests.ConnectionError as e:
                if attempt == self.max_retries - 1:
                    raise ConnectionError(
                        f"Failed to connect to PostHog API after {self.max_retries} "
                        f"attempts: {str(e)}"
                    )
            except requests.Timeout:
                if attempt == self.max_retries - 1:
                    raise PostHogError(
                        f"Request timeout after {self.timeout} seconds"
                    )
            except requests.HTTPError as e:
                # Don't retry for client errors (4xx)
                if 400 <= response.status_code < 500:
                    raise PostHogError(f"API error: {response.text}")
                if attempt == self.max_retries - 1:
                    raise PostHogError(f"HTTP error: {str(e)}")

    # ==================== DRIVER CONTRACT METHODS ====================

    def list_objects(self) -> List[str]:
        """
        Returns available PostHog entity types (driver contract method).

        PostHog entities mapped to "objects":
        - events: User actions tracked in applications
        - insights: Pre-configured analytics (trends, funnels, retention)
        - persons: User profiles with properties
        - cohorts: User segments/groups
        - feature_flags: Feature toggle configurations
        - sessions: User session data with replays
        - annotations: Timeline markers for releases/changes
        - experiments: A/B test configurations and results

        Returns:
            List of available object type names
        """
        return [
            'events',
            'insights',
            'persons',
            'cohorts',
            'feature_flags',
            'sessions',
            'annotations',
            'experiments'
        ]

    def get_fields(self, object_name: str) -> Dict[str, Any]:
        """
        Returns schema/field definitions for a PostHog entity type.

        Args:
            object_name: Entity type name (from list_objects())

        Returns:
            Dictionary of field definitions with types and descriptions

        Raises:
            ObjectNotFoundError: Unknown object type
        """
        schemas = {
            'events': {
                'event': {
                    'type': 'string',
                    'description': 'Event name (e.g., "User Signup", "Button Click")'
                },
                'timestamp': {
                    'type': 'datetime',
                    'description': 'When the event occurred (ISO 8601 format)'
                },
                'distinct_id': {
                    'type': 'string',
                    'description': 'Unique user identifier'
                },
                'properties': {
                    'type': 'object',
                    'description': 'Event properties (custom key-value pairs)'
                },
                'person': {
                    'type': 'object',
                    'description': 'Associated person object with user properties'
                }
            },
            'insights': {
                'id': {'type': 'string', 'description': 'Unique insight ID'},
                'name': {'type': 'string', 'description': 'Insight name'},
                'filters': {
                    'type': 'object',
                    'description': 'Insight configuration (events, date ranges, filters)'
                },
                'result': {
                    'type': 'array',
                    'description': 'Computed insight results (trends, funnel steps, etc.)'
                },
                'insight': {
                    'type': 'string',
                    'description': 'Insight type: TRENDS, FUNNELS, RETENTION, PATHS'
                },
                'created_at': {'type': 'datetime', 'description': 'Creation timestamp'}
            },
            'persons': {
                'id': {'type': 'string', 'description': 'Person UUID'},
                'distinct_ids': {
                    'type': 'array',
                    'description': 'List of distinct IDs for this person'
                },
                'properties': {
                    'type': 'object',
                    'description': 'Person properties (email, name, custom attributes)'
                },
                'created_at': {
                    'type': 'datetime',
                    'description': 'First seen timestamp'
                }
            },
            'cohorts': {
                'id': {'type': 'number', 'description': 'Cohort ID'},
                'name': {'type': 'string', 'description': 'Cohort name'},
                'description': {'type': 'string', 'description': 'Cohort description'},
                'filters': {
                    'type': 'object',
                    'description': 'Cohort definition (behavioral/property filters)'
                },
                'count': {
                    'type': 'number',
                    'description': 'Number of persons in cohort'
                }
            },
            'feature_flags': {
                'id': {'type': 'number', 'description': 'Flag ID'},
                'key': {'type': 'string', 'description': 'Flag key (identifier)'},
                'name': {'type': 'string', 'description': 'Flag name'},
                'active': {'type': 'boolean', 'description': 'Whether flag is active'},
                'rollout_percentage': {
                    'type': 'number',
                    'description': 'Percentage of users with flag enabled'
                },
                'filters': {
                    'type': 'object',
                    'description': 'Targeting rules and conditions'
                }
            },
            'sessions': {
                'session_id': {'type': 'string', 'description': 'Unique session ID'},
                'distinct_id': {'type': 'string', 'description': 'User identifier'},
                'start_time': {'type': 'datetime', 'description': 'Session start'},
                'end_time': {'type': 'datetime', 'description': 'Session end'},
                'events_count': {
                    'type': 'number',
                    'description': 'Number of events in session'
                },
                'recording_url': {
                    'type': 'string',
                    'description': 'URL to session replay (if available)'
                }
            },
            'annotations': {
                'id': {'type': 'number', 'description': 'Annotation ID'},
                'content': {'type': 'string', 'description': 'Annotation text'},
                'date_marker': {
                    'type': 'datetime',
                    'description': 'Date marked on timeline'
                },
                'scope': {
                    'type': 'string',
                    'description': 'organization or project'
                }
            },
            'experiments': {
                'id': {'type': 'number', 'description': 'Experiment ID'},
                'name': {'type': 'string', 'description': 'Experiment name'},
                'feature_flag_key': {
                    'type': 'string',
                    'description': 'Associated feature flag'
                },
                'variants': {
                    'type': 'array',
                    'description': 'Experiment variants (control, test)'
                },
                'results': {
                    'type': 'object',
                    'description': 'Statistical analysis results'
                }
            }
        }

        if object_name not in schemas:
            available = ', '.join(self.list_objects())
            raise ObjectNotFoundError(
                f"Unknown object type '{object_name}'. "
                f"Available types: {available}"
            )

        return schemas[object_name]

    def query(self, hogql_query: str) -> List[Dict[str, Any]]:
        """
        Execute HogQL query (PostHog's SQL-like query language).

        HogQL allows querying events, persons, and data warehouse tables using
        SQL syntax. Examples:
        - SELECT * FROM events WHERE event = 'User Signup' LIMIT 100
        - SELECT distinct_id, count() FROM events GROUP BY distinct_id
        - SELECT * FROM events WHERE properties.$current_url LIKE '%/blog%'

        Args:
            hogql_query: HogQL query string (SQL-like syntax)

        Returns:
            List of result rows as dictionaries

        Raises:
            QueryError: Invalid query syntax or execution error
            RateLimitError: Query rate limit exceeded (2400/hour)
        """
        if not hogql_query or not hogql_query.strip():
            raise ValidationError("Query cannot be empty")

        try:
            endpoint = f'/api/projects/{self.project_id}/query/'
            result = self._make_request(
                endpoint,
                method='POST',
                json={
                    'query': {
                        'kind': 'HogQLQuery',
                        'query': hogql_query
                    }
                }
            )

            return result.get('results', [])

        except PostHogError:
            raise
        except Exception as e:
            raise QueryError(f"Query execution failed: {str(e)}")

    # ==================== EVENT CAPTURE & TRACKING ====================

    def capture_event(
        self,
        event: str,
        distinct_id: str,
        properties: Optional[Dict[str, Any]] = None,
        timestamp: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Capture a single event (real-time tracking).

        Args:
            event: Event name (e.g., "User Signup", "Button Click")
            distinct_id: Unique user identifier
            properties: Optional event properties
            timestamp: Optional ISO 8601 timestamp (defaults to now)

        Returns:
            Response dictionary with success status

        Example:
            client.capture_event(
                event="Feature Used",
                distinct_id="user_123",
                properties={"feature_name": "dark_mode", "value": True}
            )
        """
        if not self.project_api_key:
            raise AuthenticationError(
                "Project API key required for event capture. "
                "Set via project_api_key parameter or POSTHOG_PROJECT_API_KEY env var."
            )

        payload = {
            'api_key': self.project_api_key,
            'event': event,
            'distinct_id': distinct_id,
            'properties': properties or {},
        }

        if timestamp:
            payload['timestamp'] = timestamp

        return self._make_request(
            '/i/v0/e/',
            method='POST',
            use_capture_url=True,
            json=payload
        )

    def capture_batch(
        self,
        events: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Capture multiple events in a single request (batch ingestion).

        More efficient than individual captures. Max 20MB request size.
        PostHog recommends batching for high-volume event ingestion.

        Args:
            events: List of event dictionaries, each containing:
                - event: Event name
                - distinct_id: User identifier
                - properties: Optional event properties
                - timestamp: Optional ISO timestamp

        Returns:
            Response dictionary with success status

        Example:
            client.capture_batch([
                {
                    "event": "Page View",
                    "distinct_id": "user_123",
                    "properties": {"page": "/home"}
                },
                {
                    "event": "Button Click",
                    "distinct_id": "user_123",
                    "properties": {"button": "signup"}
                }
            ])
        """
        if not self.project_api_key:
            raise AuthenticationError("Project API key required for event capture")

        if not events:
            raise ValidationError("Events list cannot be empty")

        # Add API key to each event
        batch_payload = {
            'api_key': self.project_api_key,
            'batch': events
        }

        return self._make_request(
            '/batch/',
            method='POST',
            use_capture_url=True,
            json=batch_payload
        )

    # ==================== ANALYTICS & INSIGHTS ====================

    def get_insights(
        self,
        insight_type: Optional[str] = None,
        limit: int = 100,
        offset: int = 0
    ) -> List[Dict[str, Any]]:
        """
        List insights with optional filtering by type.

        Args:
            insight_type: Filter by type (TRENDS, FUNNELS, RETENTION, PATHS)
            limit: Maximum number of results (default: 100)
            offset: Offset for pagination

        Returns:
            List of insight objects

        Example:
            # Get all funnel insights
            funnels = client.get_insights(insight_type='FUNNELS')
        """
        endpoint = f'/api/projects/{self.project_id}/insights/'
        params = {'limit': limit, 'offset': offset}

        if insight_type:
            params['insight'] = insight_type.upper()

        result = self._make_request(endpoint, params=params)
        return result.get('results', [])

    def create_insight(
        self,
        name: str,
        insight_type: str,
        filters: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Create a new insight (trend, funnel, retention, etc.).

        Args:
            name: Insight name
            insight_type: Type (TRENDS, FUNNELS, RETENTION, PATHS)
            filters: Insight configuration (events, date range, etc.)

        Returns:
            Created insight object
        """
        endpoint = f'/api/projects/{self.project_id}/insights/'
        payload = {
            'name': name,
            'filters': {
                'insight': insight_type.upper(),
                **filters
            }
        }

        return self._make_request(endpoint, method='POST', json=payload)

    # ==================== EVENTS & DATA EXPORT ====================

    def get_events(
        self,
        event_name: Optional[str] = None,
        after: Optional[str] = None,
        before: Optional[str] = None,
        distinct_id: Optional[str] = None,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """
        Query events with filters (uses HogQL internally).

        Note: PostHog's /api/events endpoint is deprecated.
        This method uses HogQL queries for better performance.

        Args:
            event_name: Filter by event name
            after: ISO date string (events after this date)
            before: ISO date string (events before this date)
            distinct_id: Filter by user ID
            limit: Maximum results (default: 100)

        Returns:
            List of event objects

        Example:
            # Get recent signups
            signups = client.get_events(
                event_name="User Signup",
                after="2024-01-01",
                limit=50
            )
        """
        conditions = []

        if event_name:
            conditions.append(f"event = '{event_name}'")
        if after:
            conditions.append(f"timestamp >= '{after}'")
        if before:
            conditions.append(f"timestamp <= '{before}'")
        if distinct_id:
            conditions.append(f"distinct_id = '{distinct_id}'")

        where_clause = f"WHERE {' AND '.join(conditions)}" if conditions else ""
        hogql = f"SELECT * FROM events {where_clause} LIMIT {limit}"

        return self.query(hogql)

    def export_events(
        self,
        start_date: str,
        end_date: str,
        event_names: Optional[List[str]] = None,
        properties_filter: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """
        Export events for ETL/data warehouse sync.

        For large exports, consider using PostHog's native batch export
        feature (to S3, BigQuery, Snowflake) instead of the Query API.

        Args:
            start_date: ISO date string (inclusive)
            end_date: ISO date string (inclusive)
            event_names: Optional list of specific events to export
            properties_filter: Optional property filters

        Returns:
            List of events (may be large - consider pagination for production)

        Example:
            # Export all events for January 2024
            events = client.export_events(
                start_date="2024-01-01",
                end_date="2024-01-31"
            )
        """
        conditions = [
            f"timestamp >= '{start_date}'",
            f"timestamp <= '{end_date}'"
        ]

        if event_names:
            # Escape single quotes and join
            names = "', '".join(event_names)
            conditions.append(f"event IN ('{names}')")

        if properties_filter:
            for key, value in properties_filter.items():
                conditions.append(f"properties.{key} = '{value}'")

        where_clause = f"WHERE {' AND '.join(conditions)}"
        hogql = f"SELECT * FROM events {where_clause}"

        return self.query(hogql)

    # ==================== PERSONS & COHORTS ====================

    def get_persons(
        self,
        search: Optional[str] = None,
        cohort_id: Optional[int] = None,
        properties: Optional[Dict[str, Any]] = None,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """
        Query person profiles.

        Args:
            search: Search by email or distinct_id
            cohort_id: Filter to specific cohort
            properties: Filter by person properties
            limit: Maximum results

        Returns:
            List of person objects
        """
        endpoint = f'/api/projects/{self.project_id}/persons/'
        params = {'limit': limit}

        if search:
            params['search'] = search
        if cohort_id:
            params['cohort'] = cohort_id
        if properties:
            params['properties'] = properties

        result = self._make_request(endpoint, params=params)
        return result.get('results', [])

    def get_cohorts(
        self,
        search: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        List all cohorts (user segments).

        Cohorts are reusable groups of users defined by behavior or properties.
        Common cohorts: power users, churn risk, new users, paid customers.

        Args:
            search: Optional search term

        Returns:
            List of cohort objects with filters and counts

        Example:
            cohorts = client.get_cohorts()
            for cohort in cohorts:
                print(f"{cohort['name']}: {cohort['count']} users")
        """
        endpoint = f'/api/projects/{self.project_id}/cohorts/'
        params = {}

        if search:
            params['search'] = search

        result = self._make_request(endpoint, params=params)
        return result.get('results', [])

    def create_cohort(
        self,
        name: str,
        description: str = "",
        filters: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Create a new cohort.

        Args:
            name: Cohort name
            description: Cohort description
            filters: Cohort definition (behavioral/property filters)

        Returns:
            Created cohort object
        """
        endpoint = f'/api/projects/{self.project_id}/cohorts/'
        payload = {
            'name': name,
            'description': description,
            'filters': filters or {}
        }

        return self._make_request(endpoint, method='POST', json=payload)

    # ==================== FEATURE FLAGS & EXPERIMENTS ====================

    def get_feature_flags(self) -> List[Dict[str, Any]]:
        """
        List all feature flags.

        Returns:
            List of feature flag configurations
        """
        endpoint = f'/api/projects/{self.project_id}/feature_flags/'
        result = self._make_request(endpoint)
        return result.get('results', [])

    def evaluate_flag(
        self,
        key: str,
        distinct_id: str,
        person_properties: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Evaluate a feature flag for a specific user.

        Args:
            key: Feature flag key
            distinct_id: User identifier
            person_properties: Optional user properties for targeting

        Returns:
            Flag evaluation result (boolean or multivariate value)
        """
        if not self.project_api_key:
            raise AuthenticationError("Project API key required for flag evaluation")

        payload = {
            'api_key': self.project_api_key,
            'distinct_id': distinct_id,
            'key': key
        }

        if person_properties:
            payload['person_properties'] = person_properties

        return self._make_request(
            '/flags/',
            method='POST',
            use_capture_url=True,
            json=payload
        )

    def get_experiments(self) -> List[Dict[str, Any]]:
        """
        List all experiments (A/B tests).

        Returns:
            List of experiment objects with results and statistical analysis
        """
        endpoint = f'/api/projects/{self.project_id}/experiments/'
        result = self._make_request(endpoint)
        return result.get('results', [])

    # ==================== ANNOTATIONS ====================

    def get_annotations(
        self,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        List annotations (timeline markers for releases/changes).

        Args:
            start_date: Optional ISO date string
            end_date: Optional ISO date string

        Returns:
            List of annotation objects
        """
        endpoint = f'/api/projects/{self.project_id}/annotations/'
        params = {}

        if start_date:
            params['after'] = start_date
        if end_date:
            params['before'] = end_date

        result = self._make_request(endpoint, params=params)
        return result.get('results', [])

    def create_annotation(
        self,
        content: str,
        date_marker: Optional[str] = None,
        scope: str = 'project'
    ) -> Dict[str, Any]:
        """
        Create an annotation to mark important events on timeline.

        Args:
            content: Annotation text (e.g., "v2.0 released")
            date_marker: ISO date (defaults to now)
            scope: 'project' or 'organization'

        Returns:
            Created annotation object
        """
        endpoint = f'/api/projects/{self.project_id}/annotations/'
        payload = {
            'content': content,
            'scope': scope
        }

        if date_marker:
            payload['date_marker'] = date_marker

        return self._make_request(endpoint, method='POST', json=payload)

    # ==================== HELPER METHODS ====================

    def get_project_info(self) -> Dict[str, Any]:
        """
        Get information about the current project.

        Returns:
            Project details including name, timezone, settings
        """
        endpoint = f'/api/projects/{self.project_id}/'
        return self._make_request(endpoint)

    def health_check(self) -> bool:
        """
        Check if API connection is working.

        Returns:
            True if connection successful, False otherwise
        """
        try:
            self.get_project_info()
            return True
        except Exception:
            return False

    # ==================== CONTEXT MANAGER SUPPORT ====================

    def __enter__(self):
        """Context manager entry."""
        return self

    def __exit__(self, *args):
        """Context manager exit - cleanup session."""
        self.session.close()

    def __repr__(self) -> str:
        """String representation."""
        return (
            f"PostHogClient(project_id={self.project_id}, "
            f"api_url={self.api_url})"
        )
