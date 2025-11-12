"""
Unit Tests for PostHog Driver

Tests driver contract implementation and core functionality.
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import unittest
from unittest.mock import Mock, patch, MagicMock
from posthog_driver import PostHogClient
from posthog_driver.exceptions import (
    AuthenticationError,
    ObjectNotFoundError,
    QueryError,
    ValidationError
)


class TestDriverContract(unittest.TestCase):
    """Test the standard driver contract methods."""

    def setUp(self):
        """Set up test client with mock credentials."""
        with patch.dict(os.environ, {
            'POSTHOG_PERSONAL_API_KEY': 'test_key',
            'POSTHOG_PROJECT_ID': '12345'
        }):
            self.client = PostHogClient()

    def test_list_objects(self):
        """Test list_objects returns expected entity types."""
        objects = self.client.list_objects()

        self.assertIsInstance(objects, list)
        self.assertGreater(len(objects), 0)

        # Check for expected objects
        expected_objects = [
            'events', 'insights', 'persons', 'cohorts',
            'feature_flags', 'sessions', 'annotations', 'experiments'
        ]

        for obj in expected_objects:
            self.assertIn(obj, objects)

    def test_get_fields_events(self):
        """Test get_fields for events entity."""
        fields = self.client.get_fields('events')

        self.assertIsInstance(fields, dict)

        # Check for required fields
        required_fields = ['event', 'timestamp', 'distinct_id', 'properties']
        for field in required_fields:
            self.assertIn(field, fields)
            self.assertIn('type', fields[field])
            self.assertIn('description', fields[field])

    def test_get_fields_insights(self):
        """Test get_fields for insights entity."""
        fields = self.client.get_fields('insights')

        self.assertIsInstance(fields, dict)
        self.assertIn('id', fields)
        self.assertIn('name', fields)
        self.assertIn('filters', fields)

    def test_get_fields_invalid_object(self):
        """Test get_fields raises error for invalid object."""
        with self.assertRaises(ObjectNotFoundError):
            self.client.get_fields('invalid_object')

    def test_get_fields_all_objects(self):
        """Test get_fields works for all listed objects."""
        objects = self.client.list_objects()

        for obj in objects:
            fields = self.client.get_fields(obj)
            self.assertIsInstance(fields, dict)
            self.assertGreater(len(fields), 0)


class TestClientInitialization(unittest.TestCase):
    """Test client initialization and configuration."""

    def test_init_with_env_vars(self):
        """Test initialization with environment variables."""
        with patch.dict(os.environ, {
            'POSTHOG_PERSONAL_API_KEY': 'test_key',
            'POSTHOG_PROJECT_ID': '12345'
        }):
            client = PostHogClient()

            self.assertEqual(client.api_key, 'test_key')
            self.assertEqual(client.project_id, '12345')
            self.assertEqual(client.api_url, 'https://us.posthog.com')

    def test_init_with_parameters(self):
        """Test initialization with explicit parameters."""
        client = PostHogClient(
            api_key='custom_key',
            project_id='54321',
            api_url='https://eu.posthog.com'
        )

        self.assertEqual(client.api_key, 'custom_key')
        self.assertEqual(client.project_id, '54321')
        self.assertEqual(client.api_url, 'https://eu.posthog.com')

    def test_init_missing_api_key(self):
        """Test initialization fails without API key."""
        with self.assertRaises(AuthenticationError):
            PostHogClient(project_id='12345')

    def test_init_missing_project_id(self):
        """Test initialization fails without project ID."""
        from posthog_driver.exceptions import PostHogError

        with self.assertRaises(PostHogError):
            PostHogClient(api_key='test_key')

    def test_capture_url_generation(self):
        """Test capture URL is correctly generated."""
        client = PostHogClient(
            api_key='test_key',
            project_id='12345',
            api_url='https://us.posthog.com'
        )

        self.assertEqual(client.capture_url, 'https://us.i.posthog.com')

        client_eu = PostHogClient(
            api_key='test_key',
            project_id='12345',
            api_url='https://eu.posthog.com'
        )

        self.assertEqual(client_eu.capture_url, 'https://eu.i.posthog.com')


class TestQueryMethod(unittest.TestCase):
    """Test HogQL query functionality."""

    def setUp(self):
        """Set up test client."""
        with patch.dict(os.environ, {
            'POSTHOG_PERSONAL_API_KEY': 'test_key',
            'POSTHOG_PROJECT_ID': '12345'
        }):
            self.client = PostHogClient()

    def test_query_empty_string(self):
        """Test query with empty string raises validation error."""
        with self.assertRaises(ValidationError):
            self.client.query('')

    def test_query_whitespace_only(self):
        """Test query with whitespace only raises validation error."""
        with self.assertRaises(ValidationError):
            self.client.query('   ')

    @patch('posthog_driver.client.PostHogClient._make_request')
    def test_query_success(self, mock_request):
        """Test successful query execution."""
        mock_request.return_value = {
            'results': [
                {'event': 'User Signup', 'count': 100},
                {'event': 'Button Click', 'count': 50}
            ]
        }

        result = self.client.query("SELECT event, count() FROM events")

        self.assertEqual(len(result), 2)
        self.assertEqual(result[0]['event'], 'User Signup')

        # Verify request was made correctly
        mock_request.assert_called_once()
        call_args = mock_request.call_args
        self.assertEqual(call_args[0][0], '/api/projects/12345/query/')
        self.assertEqual(call_args[1]['method'], 'POST')


class TestEventCapture(unittest.TestCase):
    """Test event capture functionality."""

    def setUp(self):
        """Set up test client."""
        with patch.dict(os.environ, {
            'POSTHOG_PERSONAL_API_KEY': 'test_key',
            'POSTHOG_PROJECT_ID': '12345',
            'POSTHOG_PROJECT_API_KEY': 'test_project_key'
        }):
            self.client = PostHogClient()

    def test_capture_event_requires_project_key(self):
        """Test capture_event requires project API key."""
        client = PostHogClient(
            api_key='test_key',
            project_id='12345'
        )

        with self.assertRaises(AuthenticationError):
            client.capture_event(
                event='Test Event',
                distinct_id='user_123'
            )

    @patch('posthog_driver.client.PostHogClient._make_request')
    def test_capture_event_success(self, mock_request):
        """Test successful event capture."""
        mock_request.return_value = {'success': True}

        result = self.client.capture_event(
            event='Test Event',
            distinct_id='user_123',
            properties={'key': 'value'}
        )

        self.assertTrue(result['success'])

        # Verify correct endpoint was called
        call_args = mock_request.call_args
        self.assertEqual(call_args[0][0], '/i/v0/e/')
        self.assertTrue(call_args[1]['use_capture_url'])

    @patch('posthog_driver.client.PostHogClient._make_request')
    def test_capture_batch_success(self, mock_request):
        """Test successful batch event capture."""
        mock_request.return_value = {'success': True}

        events = [
            {'event': 'Event 1', 'distinct_id': 'user_1'},
            {'event': 'Event 2', 'distinct_id': 'user_2'}
        ]

        result = self.client.capture_batch(events)

        self.assertTrue(result['success'])

        # Verify batch endpoint was called
        call_args = mock_request.call_args
        self.assertEqual(call_args[0][0], '/batch/')

    def test_capture_batch_empty_list(self):
        """Test batch capture with empty list raises error."""
        with self.assertRaises(ValidationError):
            self.client.capture_batch([])


class TestHelperMethods(unittest.TestCase):
    """Test utility and helper methods."""

    def setUp(self):
        """Set up test client."""
        with patch.dict(os.environ, {
            'POSTHOG_PERSONAL_API_KEY': 'test_key',
            'POSTHOG_PROJECT_ID': '12345'
        }):
            self.client = PostHogClient()

    @patch('posthog_driver.client.PostHogClient._make_request')
    def test_health_check_success(self, mock_request):
        """Test health check returns True when connection works."""
        mock_request.return_value = {'id': '12345', 'name': 'Test Project'}

        result = self.client.health_check()

        self.assertTrue(result)

    @patch('posthog_driver.client.PostHogClient._make_request')
    def test_health_check_failure(self, mock_request):
        """Test health check returns False on error."""
        mock_request.side_effect = Exception('Connection failed')

        result = self.client.health_check()

        self.assertFalse(result)

    def test_repr(self):
        """Test string representation."""
        repr_str = repr(self.client)

        self.assertIn('PostHogClient', repr_str)
        self.assertIn('12345', repr_str)

    def test_context_manager(self):
        """Test client works as context manager."""
        with patch.dict(os.environ, {
            'POSTHOG_PERSONAL_API_KEY': 'test_key',
            'POSTHOG_PROJECT_ID': '12345'
        }):
            with PostHogClient() as client:
                self.assertIsNotNone(client)
                self.assertIsNotNone(client.session)


class TestScriptTemplates(unittest.TestCase):
    """Test script templates."""

    def test_template_imports(self):
        """Test script templates can be imported."""
        from script_templates import TEMPLATES, get_template, list_templates

        self.assertIsInstance(TEMPLATES, dict)
        self.assertGreater(len(TEMPLATES), 0)

    def test_list_templates(self):
        """Test listing all templates."""
        from script_templates import list_templates

        templates = list_templates()

        self.assertIsInstance(templates, list)

        # Check for expected templates
        expected = [
            'capture_event', 'get_recent_events', 'export_events',
            'identify_power_users', 'analyze_funnel'
        ]

        for name in expected:
            self.assertIn(name, templates)

    def test_get_template(self):
        """Test getting individual template."""
        from script_templates import get_template

        template = get_template('capture_event')

        self.assertIsInstance(template, str)
        self.assertIn('PostHogClient', template)
        self.assertIn('capture_event', template)

    def test_get_template_invalid(self):
        """Test getting invalid template raises error."""
        from script_templates import get_template

        with self.assertRaises(KeyError):
            get_template('nonexistent_template')

    def test_template_placeholders(self):
        """Test templates contain placeholders."""
        from script_templates import get_template

        template = get_template('get_recent_events')

        # Check for API key placeholders
        self.assertIn('<api_key_placeholder>', template)
        self.assertIn('<project_id_placeholder>', template)


class TestExceptions(unittest.TestCase):
    """Test custom exception classes."""

    def test_exception_hierarchy(self):
        """Test exception inheritance."""
        from posthog_driver.exceptions import (
            PostHogError, AuthenticationError, QueryError
        )

        # All exceptions should inherit from PostHogError
        self.assertTrue(issubclass(AuthenticationError, PostHogError))
        self.assertTrue(issubclass(QueryError, PostHogError))

    def test_exception_messages(self):
        """Test exceptions can carry messages."""
        from posthog_driver.exceptions import AuthenticationError

        error = AuthenticationError("Invalid API key")

        self.assertEqual(str(error), "Invalid API key")


def run_tests():
    """Run all tests and print results."""
    # Create test suite
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()

    # Add all test cases
    suite.addTests(loader.loadTestsFromTestCase(TestDriverContract))
    suite.addTests(loader.loadTestsFromTestCase(TestClientInitialization))
    suite.addTests(loader.loadTestsFromTestCase(TestQueryMethod))
    suite.addTests(loader.loadTestsFromTestCase(TestEventCapture))
    suite.addTests(loader.loadTestsFromTestCase(TestHelperMethods))
    suite.addTests(loader.loadTestsFromTestCase(TestScriptTemplates))
    suite.addTests(loader.loadTestsFromTestCase(TestExceptions))

    # Run tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    return result


if __name__ == '__main__':
    print("\n" + "=" * 70)
    print("PostHog Driver - Unit Tests")
    print("=" * 70 + "\n")

    result = run_tests()

    print("\n" + "=" * 70)
    print(f"Tests run: {result.testsRun}")
    print(f"Successes: {result.testsRun - len(result.failures) - len(result.errors)}")
    print(f"Failures: {len(result.failures)}")
    print(f"Errors: {len(result.errors)}")
    print("=" * 70 + "\n")

    # Exit with appropriate code
    sys.exit(0 if result.wasSuccessful() else 1)
