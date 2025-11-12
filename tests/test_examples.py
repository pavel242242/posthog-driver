"""
Integration Tests for PostHog Driver Examples

Tests that example code is valid and imports work correctly.
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import unittest
from unittest.mock import patch


class TestExampleImports(unittest.TestCase):
    """Test that all examples can be imported without errors."""

    def test_import_basic_usage(self):
        """Test basic_usage.py imports successfully."""
        # Temporarily add examples to path
        examples_dir = os.path.join(
            os.path.dirname(os.path.dirname(__file__)),
            'examples'
        )
        sys.path.insert(0, examples_dir)

        try:
            # This will execute the module-level code but not __main__
            import basic_usage
            self.assertTrue(hasattr(basic_usage, 'driver_contract_demo'))
            self.assertTrue(hasattr(basic_usage, 'event_tracking_demo'))
            self.assertTrue(hasattr(basic_usage, 'analytics_demo'))
        finally:
            sys.path.remove(examples_dir)

    def test_import_persona_workflows(self):
        """Test persona_workflows.py imports successfully."""
        examples_dir = os.path.join(
            os.path.dirname(os.path.dirname(__file__)),
            'examples'
        )
        sys.path.insert(0, examples_dir)

        try:
            import persona_workflows
            self.assertTrue(hasattr(persona_workflows, 'feature_impact_analysis'))
            self.assertTrue(hasattr(persona_workflows, 'user_journey_funnel_analysis'))
            self.assertTrue(hasattr(persona_workflows, 'power_user_identification'))
        finally:
            sys.path.remove(examples_dir)

    def test_import_e2b_integration(self):
        """Test e2b_integration.py imports successfully."""
        examples_dir = os.path.join(
            os.path.dirname(os.path.dirname(__file__)),
            'examples'
        )
        sys.path.insert(0, examples_dir)

        try:
            import e2b_integration
            self.assertTrue(hasattr(e2b_integration, 'example_basic_execution'))
            self.assertTrue(hasattr(e2b_integration, 'example_template_execution'))
        finally:
            sys.path.remove(examples_dir)


class TestAgentExecutor(unittest.TestCase):
    """Test AgentExecutor initialization."""

    def test_agent_executor_import(self):
        """Test AgentExecutor can be imported."""
        from agent_executor import PostHogAgentExecutor

        self.assertIsNotNone(PostHogAgentExecutor)

    def test_agent_executor_init(self):
        """Test AgentExecutor initialization."""
        from agent_executor import PostHogAgentExecutor

        executor = PostHogAgentExecutor(
            e2b_api_key='test_e2b_key',
            posthog_api_key='test_ph_key',
            posthog_project_id='12345'
        )

        self.assertEqual(executor.posthog_api_key, 'test_ph_key')
        self.assertEqual(executor.posthog_project_id, '12345')
        self.assertEqual(executor.e2b_api_key, 'test_e2b_key')


class TestPackageStructure(unittest.TestCase):
    """Test overall package structure."""

    def test_package_import(self):
        """Test main package imports."""
        import posthog_driver

        self.assertTrue(hasattr(posthog_driver, 'PostHogClient'))
        self.assertTrue(hasattr(posthog_driver, 'PostHogError'))
        self.assertTrue(hasattr(posthog_driver, '__version__'))

    def test_package_version(self):
        """Test package has version."""
        import posthog_driver

        self.assertEqual(posthog_driver.__version__, '1.0.0')

    def test_all_exceptions_exported(self):
        """Test all exception classes are exported."""
        from posthog_driver import (
            PostHogError,
            AuthenticationError,
            ObjectNotFoundError,
            QueryError,
            ConnectionError,
            RateLimitError,
            ValidationError
        )

        # Just verify they can be imported
        self.assertIsNotNone(PostHogError)
        self.assertIsNotNone(AuthenticationError)


class TestDocumentation(unittest.TestCase):
    """Test that documentation files exist."""

    def test_readme_exists(self):
        """Test README.md exists."""
        readme_path = os.path.join(
            os.path.dirname(os.path.dirname(__file__)),
            'README.md'
        )
        self.assertTrue(os.path.exists(readme_path))

    def test_env_example_exists(self):
        """Test .env.example exists."""
        env_path = os.path.join(
            os.path.dirname(os.path.dirname(__file__)),
            '.env.example'
        )
        self.assertTrue(os.path.exists(env_path))

    def test_requirements_exists(self):
        """Test requirements.txt exists."""
        req_path = os.path.join(
            os.path.dirname(os.path.dirname(__file__)),
            'requirements.txt'
        )
        self.assertTrue(os.path.exists(req_path))

    def test_plan_exists(self):
        """Test PLAN.md exists."""
        plan_path = os.path.join(
            os.path.dirname(os.path.dirname(__file__)),
            'PLAN.md'
        )
        self.assertTrue(os.path.exists(plan_path))


if __name__ == '__main__':
    print("\n" + "=" * 70)
    print("PostHog Driver - Integration Tests")
    print("=" * 70 + "\n")

    # Run tests
    unittest.main(verbosity=2)
