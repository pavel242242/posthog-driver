# Test Examples and Implementation Guide

This document provides concrete examples of tests needed to fill critical gaps in the PostHog Driver test suite.

## Test Infrastructure Examples

### conftest.py - Shared Fixtures
```python
# tests/conftest.py
import pytest
from unittest.mock import Mock, MagicMock, patch
from posthog_driver import PostHogClient
import json
from datetime import datetime

@pytest.fixture
def mock_session():
    """Mock requests.Session for all tests."""
    with patch('posthog_driver.client.requests.Session') as mock:
        yield mock.return_value

@pytest.fixture
def client_with_mocks(mock_session):
    """Create PostHogClient with mocked session."""
    with patch.dict('os.environ', {
        'POSTHOG_PERSONAL_API_KEY': 'test_key',
        'POSTHOG_PROJECT_ID': '12345',
        'POSTHOG_PROJECT_API_KEY': 'test_project_key'
    }):
        client = PostHogClient()
        client.session = mock_session
        return client

@pytest.fixture
def mock_response():
    """Create a mock HTTP response."""
    response = MagicMock()
    response.status_code = 200
    response.json.return_value = {'results': []}
    response.text = '{"results": []}'
    return response

@pytest.fixture
def sample_event():
    """Sample event data."""
    return {
        'event': 'User Signup',
        'distinct_id': 'user_123',
        'timestamp': datetime.now().isoformat(),
        'properties': {
            'email': 'test@example.com',
            'source': 'api'
        }
    }

@pytest.fixture
def sample_batch_events():
    """Sample batch of events."""
    return [
        {
            'event': 'Page View',
            'distinct_id': 'user_1',
            'properties': {'page': '/home'}
        },
        {
            'event': 'Button Click',
            'distinct_id': 'user_1',
            'properties': {'button': 'signup'}
        },
        {
            'event': 'Page View',
            'distinct_id': 'user_2',
            'properties': {'page': '/pricing'}
        }
    ]

@pytest.fixture
def mock_error_response():
    """Create mock error responses."""
    def _make_error(status_code, message):
        response = MagicMock()
        response.status_code = status_code
        response.text = json.dumps({'detail': message})
        response.raise_for_status.side_effect = Exception(f'HTTP {status_code}')
        return response
    return _make_error
```

### factories.py - Test Data Builders
```python
# tests/fixtures/factories.py
from datetime import datetime, timedelta
import json

class EventFactory:
    """Build realistic test events."""

    @staticmethod
    def create(event_name='Test Event', distinct_id='user_1', **properties):
        return {
            'event': event_name,
            'distinct_id': distinct_id,
            'timestamp': datetime.now().isoformat(),
            'properties': properties or {'source': 'test'}
        }

    @staticmethod
    def create_batch(count=5, event_name='Test Event'):
        return [
            EventFactory.create(
                event_name=f"{event_name}_{i}",
                distinct_id=f"user_{i}"
            )
            for i in range(count)
        ]

class ResponseFactory:
    """Build realistic API responses."""

    @staticmethod
    def events_list(count=3):
        return {
            'results': [
                {
                    'id': str(i),
                    'event': f'Event {i}',
                    'distinct_id': f'user_{i}',
                    'timestamp': (datetime.now() - timedelta(hours=i)).isoformat(),
                    'properties': {'source': 'api'}
                }
                for i in range(count)
            ]
        }

    @staticmethod
    def persons_list(count=3):
        return {
            'results': [
                {
                    'id': f'person_{i}',
                    'distinct_ids': [f'user_{i}', f'email_{i}@example.com'],
                    'properties': {'name': f'User {i}', 'email': f'user{i}@example.com'},
                    'created_at': datetime.now().isoformat()
                }
                for i in range(count)
            ]
        }

    @staticmethod
    def error(status_code, message):
        return {
            'status_code': status_code,
            'detail': message
        }

class QueryResultFactory:
    """Build HogQL query results."""

    @staticmethod
    def basic_aggregation():
        return {
            'results': [
                {'event': 'User Signup', 'count': 100},
                {'event': 'Button Click', 'count': 250},
                {'event': 'Page View', 'count': 1500}
            ]
        }

    @staticmethod
    def empty():
        return {'results': []}

    @staticmethod
    def large(rows=1000):
        return {
            'results': [
                {
                    'id': str(i),
                    'event': f'Event {i % 10}',
                    'count': 100 * (i % 5 + 1)
                }
                for i in range(rows)
            ]
        }
```

---

## Phase 1: Critical Path Tests

### HTTP Error Handling Tests

```python
# tests/unit/test_http_layer.py
import pytest
from unittest.mock import Mock, patch, MagicMock
from posthog_driver import PostHogClient
from posthog_driver.exceptions import (
    AuthenticationError,
    ObjectNotFoundError,
    RateLimitError,
    ConnectionError as PHConnectionError,
    PostHogError
)

class TestHTTPErrorHandling:
    """Test HTTP error status codes and handling."""

    def test_401_authentication_error(self, client_with_mocks, mock_response):
        """HTTP 401 should raise AuthenticationError."""
        mock_response.status_code = 401
        mock_response.text = '{"detail": "Invalid API key"}'
        client_with_mocks.session.request.return_value = mock_response

        with pytest.raises(AuthenticationError) as exc_info:
            client_with_mocks.query("SELECT * FROM events")

        assert "Authentication failed" in str(exc_info.value)

    def test_403_forbidden_error(self, client_with_mocks, mock_response):
        """HTTP 403 should raise AuthenticationError (permissions)."""
        mock_response.status_code = 403
        mock_response.text = '{"detail": "Access forbidden"}'
        client_with_mocks.session.request.return_value = mock_response

        with pytest.raises(AuthenticationError) as exc_info:
            client_with_mocks.query("SELECT * FROM events")

        assert "Access forbidden" in str(exc_info.value)

    def test_404_not_found_error(self, client_with_mocks, mock_response):
        """HTTP 404 should raise ObjectNotFoundError."""
        mock_response.status_code = 404
        mock_response.text = '{"detail": "Endpoint not found"}'
        client_with_mocks.session.request.return_value = mock_response

        with pytest.raises(ObjectNotFoundError) as exc_info:
            client_with_mocks.query("SELECT * FROM events")

        assert "Resource not found" in str(exc_info.value)

    def test_429_rate_limit_error(self, client_with_mocks, mock_response):
        """HTTP 429 should raise RateLimitError."""
        mock_response.status_code = 429
        mock_response.text = '{"detail": "Rate limit exceeded"}'
        client_with_mocks.session.request.return_value = mock_response

        with pytest.raises(RateLimitError) as exc_info:
            client_with_mocks.query("SELECT * FROM events LIMIT 1000")

        assert "Rate limit exceeded" in str(exc_info.value)

    def test_500_server_error_retries(self, client_with_mocks, mock_response):
        """HTTP 500 should retry, then fail."""
        mock_response.status_code = 500
        mock_response.text = '{"detail": "Internal server error"}'
        mock_response.raise_for_status.side_effect = Exception("500 Error")
        client_with_mocks.session.request.return_value = mock_response

        with pytest.raises(PostHogError):
            client_with_mocks.query("SELECT * FROM events")

        # Should have been called 3 times (max_retries=3)
        assert client_with_mocks.session.request.call_count == 3

    def test_connection_timeout(self, client_with_mocks):
        """Connection timeout should raise ConnectionError."""
        import requests
        client_with_mocks.session.request.side_effect = requests.Timeout("Connection timeout")

        with pytest.raises(PostHogError) as exc_info:
            client_with_mocks.query("SELECT * FROM events")

        assert "timeout" in str(exc_info.value).lower()

    def test_connection_refused(self, client_with_mocks):
        """Connection refused should retry then fail."""
        import requests
        client_with_mocks.session.request.side_effect = requests.ConnectionError("Connection refused")

        with pytest.raises(PHConnectionError):
            client_with_mocks.query("SELECT * FROM events")

        # Should retry 3 times
        assert client_with_mocks.session.request.call_count == 3

    def test_malformed_json_response(self, client_with_mocks, mock_response):
        """Malformed JSON should be handled gracefully."""
        mock_response.status_code = 200
        mock_response.json.side_effect = ValueError("Invalid JSON")
        mock_response.text = "Not JSON"
        client_with_mocks.session.request.return_value = mock_response

        result = client_with_mocks.query("SELECT * FROM events")

        # Should return success indicator when JSON parsing fails
        assert result is not None or isinstance(result, dict)

    def test_empty_response_body(self, client_with_mocks, mock_response):
        """Empty response body should be handled."""
        mock_response.status_code = 204
        mock_response.json.side_effect = ValueError("No JSON in 204 response")
        client_with_mocks.session.request.return_value = mock_response

        # Should not raise an error
        client_with_mocks.health_check()
```

### Retry Logic Tests

```python
# tests/unit/test_http_layer.py (continued)
class TestRetryLogic:
    """Test request retry behavior."""

    def test_retry_on_connection_error(self, client_with_mocks):
        """Should retry on connection errors."""
        import requests

        # Fail twice, then succeed
        responses = [
            requests.ConnectionError("Connection failed"),
            requests.ConnectionError("Connection failed"),
            MagicMock(status_code=200, json=lambda: {'results': []})
        ]
        client_with_mocks.session.request.side_effect = responses

        result = client_with_mocks.query("SELECT * FROM events")

        assert client_with_mocks.session.request.call_count == 3
        assert result == []

    def test_retry_on_timeout(self, client_with_mocks):
        """Should retry on timeout errors."""
        import requests

        responses = [
            requests.Timeout("Request timeout"),
            requests.Timeout("Request timeout"),
            MagicMock(status_code=200, json=lambda: {'results': []})
        ]
        client_with_mocks.session.request.side_effect = responses

        result = client_with_mocks.query("SELECT * FROM events")

        assert client_with_mocks.session.request.call_count == 3

    def test_no_retry_on_client_error(self, client_with_mocks, mock_response):
        """Should NOT retry on 4xx client errors."""
        mock_response.status_code = 400
        mock_response.text = '{"detail": "Bad request"}'
        mock_response.raise_for_status.side_effect = Exception("400 Error")
        client_with_mocks.session.request.return_value = mock_response

        with pytest.raises(PostHogError):
            client_with_mocks.query("SELECT * FROM events")

        # Should only be called once, no retries
        assert client_with_mocks.session.request.call_count == 1

    def test_max_retries_exhaustion(self, client_with_mocks):
        """Should fail after max retries."""
        import requests
        client_with_mocks.session.request.side_effect = requests.ConnectionError("Connection failed")

        with pytest.raises(PHConnectionError):
            client_with_mocks.query("SELECT * FROM events")

        # Should equal max_retries (default 3)
        assert client_with_mocks.session.request.call_count == client_with_mocks.max_retries

    def test_custom_max_retries(self):
        """Custom max_retries should be respected."""
        import requests

        with patch.dict('os.environ', {
            'POSTHOG_PERSONAL_API_KEY': 'test_key',
            'POSTHOG_PROJECT_ID': '12345'
        }):
            client = PostHogClient(max_retries=5)

            with patch.object(client.session, 'request') as mock_request:
                mock_request.side_effect = requests.ConnectionError("Connection failed")

                with pytest.raises(PHConnectionError):
                    client.query("SELECT * FROM events")

                assert mock_request.call_count == 5
```

### Query Error Handling Tests

```python
# tests/unit/test_query.py
class TestQueryErrorHandling:
    """Test HogQL query error scenarios."""

    def test_query_syntax_error(self, client_with_mocks):
        """Invalid HogQL syntax should raise QueryError."""
        from posthog_driver.exceptions import QueryError

        # Mock _make_request to simulate API error
        with patch.object(client_with_mocks, '_make_request') as mock_request:
            mock_request.side_effect = QueryError("Syntax error in query")

            with pytest.raises(QueryError) as exc_info:
                client_with_mocks.query("SELECT * FORM events")  # FORM instead of FROM

            assert "Syntax error" in str(exc_info.value)

    def test_query_invalid_column(self, client_with_mocks):
        """Invalid column reference should raise QueryError."""
        from posthog_driver.exceptions import QueryError

        with patch.object(client_with_mocks, '_make_request') as mock_request:
            mock_request.side_effect = QueryError("Unknown column 'nonexistent'")

            with pytest.raises(QueryError):
                client_with_mocks.query("SELECT nonexistent FROM events")

    def test_query_timeout(self, client_with_mocks):
        """Query timeout should raise appropriate error."""
        with patch.object(client_with_mocks, '_make_request') as mock_request:
            mock_request.side_effect = PostHogError("Request timeout after 30 seconds")

            with pytest.raises(PostHogError) as exc_info:
                client_with_mocks.query("SELECT * FROM events WHERE timestamp > now() - interval 365 day")

            assert "timeout" in str(exc_info.value).lower()

    def test_query_rate_limit(self, client_with_mocks):
        """Query rate limit should raise RateLimitError."""
        with patch.object(client_with_mocks, '_make_request') as mock_request:
            mock_request.side_effect = RateLimitError("Rate limit exceeded: 2400/hour")

            with pytest.raises(RateLimitError):
                client_with_mocks.query("SELECT * FROM events")

    def test_query_large_result_set(self, client_with_mocks):
        """Large result sets should be handled."""
        with patch.object(client_with_mocks, '_make_request') as mock_request:
            # Simulate large result set
            large_results = [{'id': str(i), 'event': f'Event {i}'} for i in range(10000)]
            mock_request.return_value = {'results': large_results}

            result = client_with_mocks.query("SELECT * FROM events LIMIT 10000")

            assert len(result) == 10000

    def test_query_empty_result(self, client_with_mocks):
        """Empty result should return empty list."""
        with patch.object(client_with_mocks, '_make_request') as mock_request:
            mock_request.return_value = {'results': []}

            result = client_with_mocks.query("SELECT * FROM events WHERE event = 'NonExistent'")

            assert result == []

    @pytest.mark.parametrize("query", [
        "SELECT * FROM events WHERE event='Test' AND timestamp > now() - interval 1 day",
        "SELECT distinct_id, count() FROM events GROUP BY distinct_id",
        "SELECT * FROM events WHERE properties.$browser = 'Chrome'",
    ])
    def test_query_various_syntaxes(self, client_with_mocks, query):
        """Various valid HogQL syntaxes should work."""
        with patch.object(client_with_mocks, '_make_request') as mock_request:
            mock_request.return_value = {'results': [{'count': 100}]}

            result = client_with_mocks.query(query)

            assert isinstance(result, list)
```

---

## Phase 2: Complete API Coverage Tests

### Data Retrieval Methods

```python
# tests/unit/test_events.py
class TestGetEvents:
    """Test get_events() method."""

    def test_get_events_basic(self, client_with_mocks):
        """Basic get_events() should return events."""
        events_data = [
            {'event': 'User Signup', 'distinct_id': 'user_1'},
            {'event': 'Button Click', 'distinct_id': 'user_1'},
        ]

        with patch.object(client_with_mocks, 'query') as mock_query:
            mock_query.return_value = events_data

            result = client_with_mocks.get_events()

            assert result == events_data
            mock_query.assert_called_once()

    def test_get_events_with_event_filter(self, client_with_mocks):
        """get_events() with event_name filter."""
        with patch.object(client_with_mocks, 'query') as mock_query:
            mock_query.return_value = [{'event': 'User Signup'}]

            client_with_mocks.get_events(event_name='User Signup')

            # Verify the query includes the filter
            call_args = mock_query.call_args[0][0]
            assert "event = 'User Signup'" in call_args

    def test_get_events_with_date_range(self, client_with_mocks):
        """get_events() with date range filters."""
        with patch.object(client_with_mocks, 'query') as mock_query:
            mock_query.return_value = []

            client_with_mocks.get_events(
                after='2024-01-01',
                before='2024-01-31'
            )

            call_args = mock_query.call_args[0][0]
            assert "2024-01-01" in call_args
            assert "2024-01-31" in call_args

    def test_get_events_with_distinct_id(self, client_with_mocks):
        """get_events() filtered by distinct_id."""
        with patch.object(client_with_mocks, 'query') as mock_query:
            mock_query.return_value = [{'distinct_id': 'user_123'}]

            client_with_mocks.get_events(distinct_id='user_123')

            call_args = mock_query.call_args[0][0]
            assert "user_123" in call_args

    def test_get_events_pagination(self, client_with_mocks):
        """get_events() respects limit parameter."""
        with patch.object(client_with_mocks, 'query') as mock_query:
            mock_query.return_value = []

            client_with_mocks.get_events(limit=50)

            call_args = mock_query.call_args[0][0]
            assert "LIMIT 50" in call_args

# tests/unit/test_persons_cohorts.py
class TestGetPersons:
    """Test get_persons() method."""

    def test_get_persons_basic(self, client_with_mocks, mock_response):
        """Basic get_persons() should return persons."""
        persons_data = ResponseFactory.persons_list(3)
        mock_response.json.return_value = persons_data
        client_with_mocks.session.request.return_value = mock_response

        result = client_with_mocks.get_persons()

        assert len(result) == 3
        assert all('id' in p for p in result)
        assert all('distinct_ids' in p for p in result)

    def test_get_persons_search(self, client_with_mocks, mock_response):
        """get_persons() with search query."""
        persons_data = ResponseFactory.persons_list(1)
        mock_response.json.return_value = persons_data
        client_with_mocks.session.request.return_value = mock_response

        result = client_with_mocks.get_persons(search='user@example.com')

        # Verify search parameter was passed
        call_args = client_with_mocks.session.request.call_args
        assert call_args[1]['params']['search'] == 'user@example.com'

    def test_get_persons_pagination(self, client_with_mocks, mock_response):
        """get_persons() pagination with limit and offset."""
        mock_response.json.return_value = ResponseFactory.persons_list(10)
        client_with_mocks.session.request.return_value = mock_response

        result = client_with_mocks.get_persons(limit=25, offset=50)

        call_args = client_with_mocks.session.request.call_args
        assert call_args[1]['params']['limit'] == 25
        # offset might not be implemented, adjust based on API
```

### Creation Methods

```python
# tests/unit/test_insights.py
class TestCreateInsight:
    """Test create_insight() method."""

    def test_create_insight_basic(self, client_with_mocks, mock_response):
        """Basic insight creation."""
        mock_response.json.return_value = {
            'id': 123,
            'name': 'Test Insight',
            'insight': 'TRENDS'
        }
        client_with_mocks.session.request.return_value = mock_response

        result = client_with_mocks.create_insight(
            name='Test Insight',
            insight_type='TRENDS',
            filters={}
        )

        assert result['id'] == 123
        assert result['name'] == 'Test Insight'

        # Verify POST was used
        call_args = client_with_mocks.session.request.call_args
        assert call_args[0][0] == 'POST'

    def test_create_insight_with_filters(self, client_with_mocks, mock_response):
        """Create insight with complex filters."""
        mock_response.json.return_value = {'id': 124, 'name': 'Funnel Insight'}
        client_with_mocks.session.request.return_value = mock_response

        filters = {
            'events': [{'name': 'User Signup'}, {'name': 'Button Click'}],
            'date_from': '2024-01-01',
            'date_to': '2024-01-31'
        }

        result = client_with_mocks.create_insight(
            name='Funnel Insight',
            insight_type='FUNNELS',
            filters=filters
        )

        # Verify filters were passed
        call_args = client_with_mocks.session.request.call_args
        assert 'events' in call_args[1]['json']['filters']

class TestCreateCohort:
    """Test create_cohort() method."""

    def test_create_cohort_basic(self, client_with_mocks, mock_response):
        """Basic cohort creation."""
        mock_response.json.return_value = {
            'id': 42,
            'name': 'Power Users',
            'count': 500
        }
        client_with_mocks.session.request.return_value = mock_response

        result = client_with_mocks.create_cohort(
            name='Power Users',
            description='Users with >10 events',
            filters={}
        )

        assert result['id'] == 42
        assert result['name'] == 'Power Users'

        call_args = client_with_mocks.session.request.call_args
        assert call_args[0][0] == 'POST'
```

---

## Phase 3: Advanced Testing

### Performance Tests

```python
# tests/performance/test_benchmarks.py
import pytest
import time
from unittest.mock import patch

class TestPerformance:
    """Performance and load tests."""

    def test_bulk_event_capture_throughput(self, client_with_mocks):
        """Measure bulk event capture throughput."""
        with patch.object(client_with_mocks, '_make_request') as mock_request:
            mock_request.return_value = {'success': True}

            # Create batch of 100 events
            events = EventFactory.create_batch(100)

            start = time.time()
            client_with_mocks.capture_batch(events)
            elapsed = time.time() - start

            # Should complete in < 1 second
            assert elapsed < 1.0

            # Verify it was batched (single request)
            assert mock_request.call_count == 1

    def test_query_response_time_sla(self, client_with_mocks):
        """Query should respond within SLA."""
        with patch.object(client_with_mocks, '_make_request') as mock_request:
            mock_request.return_value = ResponseFactory.basic_aggregation()

            start = time.time()
            result = client_with_mocks.query("SELECT event, count() FROM events GROUP BY event")
            elapsed = time.time() - start

            # Should complete in < 100ms
            assert elapsed < 0.1
            assert len(result) == 3

    def test_memory_efficiency_large_batch(self, client_with_mocks):
        """Large batch should not cause memory issues."""
        with patch.object(client_with_mocks, '_make_request') as mock_request:
            mock_request.return_value = {'success': True}

            # Create 1000 events
            events = EventFactory.create_batch(1000)

            # Should handle without memory errors
            result = client_with_mocks.capture_batch(events)

            assert result['success'] is True
```

### Edge Case Tests

```python
# tests/unit/test_edge_cases.py
class TestEdgeCases:
    """Test edge cases and boundary conditions."""

    def test_empty_result_handling(self, client_with_mocks):
        """Empty results should be handled gracefully."""
        with patch.object(client_with_mocks, 'query') as mock_query:
            mock_query.return_value = []

            result = client_with_mocks.get_events(
                event_name='NonExistentEvent'
            )

            assert result == []

    def test_special_character_encoding(self, client_with_mocks):
        """Special characters should be properly encoded."""
        with patch.object(client_with_mocks, '_make_request') as mock_request:
            mock_request.return_value = {'success': True}

            result = client_with_mocks.capture_event(
                event='Event with unicode: 你好',
                distinct_id='user@example.com',
                properties={'emoji': '🚀', 'symbol': '€'}
            )

            # Verify encoding was handled
            assert result['success'] is True

    def test_null_vs_empty_properties(self, client_with_mocks):
        """Null and empty properties should be distinguished."""
        with patch.object(client_with_mocks, '_make_request') as mock_request:
            mock_request.return_value = {'success': True}

            # Empty properties
            client_with_mocks.capture_event(
                event='Test',
                distinct_id='user_1',
                properties={}
            )

            # None properties (should default to {})
            client_with_mocks.capture_event(
                event='Test',
                distinct_id='user_1',
                properties=None
            )

            assert mock_request.call_count == 2

    def test_timezone_handling(self, client_with_mocks):
        """Timestamps with timezones should be handled."""
        from datetime import datetime
        from dateutil import parser

        with patch.object(client_with_mocks, '_make_request') as mock_request:
            mock_request.return_value = {'success': True}

            # UTC timestamp
            result = client_with_mocks.capture_event(
                event='Test',
                distinct_id='user_1',
                timestamp='2024-01-01T12:00:00Z'
            )

            assert result['success'] is True
```

---

## Running the Tests

### Run all tests with coverage
```bash
pytest tests/ -v --cov=posthog_driver --cov-report=html
```

### Run specific test file
```bash
pytest tests/unit/test_http_layer.py -v
```

### Run specific test class
```bash
pytest tests/unit/test_query.py::TestQueryErrorHandling -v
```

### Run tests matching pattern
```bash
pytest -k "test_query" -v
```

### Run with coverage threshold
```bash
pytest tests/ --cov=posthog_driver --cov-fail-under=80
```

### Run performance tests only
```bash
pytest tests/performance -v --benchmark
```

---

## Best Practices for Test Implementation

1. **Use fixtures for reusable setup**
   - Avoid duplication across tests
   - Keep fixtures focused and composable

2. **Use parametrize for related tests**
   ```python
   @pytest.mark.parametrize("status_code,exception", [
       (401, AuthenticationError),
       (403, AuthenticationError),
       (404, ObjectNotFoundError),
       (429, RateLimitError),
   ])
   def test_http_errors(self, client_with_mocks, status_code, exception):
       # Single test tests multiple scenarios
   ```

3. **Mock at appropriate levels**
   - Mock requests.Session at integration layer
   - Mock _make_request() for higher-level tests
   - Use real Session for critical path tests (if safe)

4. **Include docstrings**
   ```python
   def test_query_timeout(self, client_with_mocks):
       """Query timeout should raise PostHogError within configured timeout.

       This tests the SLA: queries should timeout after 30 seconds
       and raise an appropriate error that can be caught and retried.
       """
   ```

5. **Assert specific error messages**
   ```python
   with pytest.raises(RateLimitError) as exc_info:
       client.query(...)

   assert "2400/hour" in str(exc_info.value)
   ```

6. **Test both happy path and error path**
   - Every method should have success test
   - Every method should have error tests
   - Both should verify correct HTTP calls

7. **Use realistic test data**
   - Use factories to generate test data
   - Make timestamps realistic
   - Use real event names and property structures
