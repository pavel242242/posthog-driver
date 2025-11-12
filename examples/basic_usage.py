"""
PostHog Driver - Basic Usage Examples

Demonstrates core driver contract and basic PostHog operations.
"""

import sys
sys.path.insert(0, '..')

from posthog_driver import PostHogClient
import json


def driver_contract_demo():
    """Demonstrate the standard driver contract methods."""
    print("=" * 70)
    print("DRIVER CONTRACT DEMONSTRATION")
    print("=" * 70)

    client = PostHogClient()

    # 1. list_objects() - Discover available entity types
    print("\n1. list_objects() - Discover Available Entities")
    print("-" * 70)
    objects = client.list_objects()
    print(f"Available PostHog entities: {', '.join(objects)}")

    # 2. get_fields() - Get schema for each entity
    print("\n2. get_fields() - Get Entity Schema")
    print("-" * 70)
    for obj_type in ['events', 'insights', 'persons']:
        print(f"\n{obj_type.upper()} Schema:")
        fields = client.get_fields(obj_type)
        for field_name, field_def in fields.items():
            print(f"  {field_name}: {field_def['type']} - {field_def['description']}")

    # 3. query() - Execute HogQL queries
    print("\n3. query() - Execute HogQL Queries")
    print("-" * 70)

    # Simple query - get recent events
    hogql = "SELECT event, timestamp, distinct_id FROM events LIMIT 5"
    print(f"Query: {hogql}")

    try:
        results = client.query(hogql)
        print(f"\nResults ({len(results)} rows):")
        print(json.dumps(results, indent=2))
    except Exception as e:
        print(f"Query error: {e}")


def event_tracking_demo():
    """Demonstrate event tracking capabilities."""
    print("\n" + "=" * 70)
    print("EVENT TRACKING DEMONSTRATION")
    print("=" * 70)

    client = PostHogClient()

    # Capture single event
    print("\n1. Capture Single Event")
    print("-" * 70)

    try:
        result = client.capture_event(
            event="Demo Event",
            distinct_id="demo_user_123",
            properties={
                "source": "basic_usage_example",
                "environment": "development"
            }
        )
        print("Event captured successfully:")
        print(json.dumps(result, indent=2))
    except Exception as e:
        print(f"Event capture error: {e}")

    # Capture batch events
    print("\n2. Capture Batch Events")
    print("-" * 70)

    try:
        batch_events = [
            {
                "event": "Page View",
                "distinct_id": "demo_user_123",
                "properties": {"page": "/home"}
            },
            {
                "event": "Button Click",
                "distinct_id": "demo_user_123",
                "properties": {"button": "signup"}
            },
            {
                "event": "Form Submit",
                "distinct_id": "demo_user_123",
                "properties": {"form": "contact"}
            }
        ]

        result = client.capture_batch(batch_events)
        print(f"Batch of {len(batch_events)} events captured successfully:")
        print(json.dumps(result, indent=2))
    except Exception as e:
        print(f"Batch capture error: {e}")


def analytics_demo():
    """Demonstrate analytics and insights retrieval."""
    print("\n" + "=" * 70)
    print("ANALYTICS & INSIGHTS DEMONSTRATION")
    print("=" * 70)

    client = PostHogClient()

    # Get insights
    print("\n1. List Insights")
    print("-" * 70)

    try:
        insights = client.get_insights(limit=5)
        print(f"Found {len(insights)} insights:")
        for insight in insights:
            print(f"\n  - {insight['name']}")
            print(f"    Type: {insight.get('filters', {}).get('insight', 'N/A')}")
            print(f"    ID: {insight['id']}")
    except Exception as e:
        print(f"Insights error: {e}")

    # Query events
    print("\n2. Query Recent Events")
    print("-" * 70)

    try:
        from datetime import datetime, timedelta
        after_date = (datetime.now() - timedelta(days=7)).strftime('%Y-%m-%d')

        events = client.get_events(
            after=after_date,
            limit=10
        )
        print(f"Found {len(events)} events in last 7 days")
        if events:
            print("\nSample event:")
            print(json.dumps(events[0], indent=2))
    except Exception as e:
        print(f"Event query error: {e}")


def cohort_demo():
    """Demonstrate cohort operations."""
    print("\n" + "=" * 70)
    print("COHORT MANAGEMENT DEMONSTRATION")
    print("=" * 70)

    client = PostHogClient()

    # List cohorts
    print("\n1. List All Cohorts")
    print("-" * 70)

    try:
        cohorts = client.get_cohorts()
        print(f"Found {len(cohorts)} cohorts:")
        for cohort in cohorts:
            print(f"\n  - {cohort['name']}")
            print(f"    ID: {cohort['id']}")
            print(f"    Count: {cohort.get('count', 'N/A')} users")
            if cohort.get('description'):
                print(f"    Description: {cohort['description']}")
    except Exception as e:
        print(f"Cohort list error: {e}")


def feature_flags_demo():
    """Demonstrate feature flag operations."""
    print("\n" + "=" * 70)
    print("FEATURE FLAGS DEMONSTRATION")
    print("=" * 70)

    client = PostHogClient()

    # List feature flags
    print("\n1. List All Feature Flags")
    print("-" * 70)

    try:
        flags = client.get_feature_flags()
        print(f"Found {len(flags)} feature flags:")
        for flag in flags[:5]:  # Show first 5
            print(f"\n  - {flag['name']}")
            print(f"    Key: {flag['key']}")
            print(f"    Active: {flag.get('active', False)}")
            print(f"    Rollout: {flag.get('rollout_percentage', 0)}%")
    except Exception as e:
        print(f"Feature flags error: {e}")

    # Evaluate a flag
    print("\n2. Evaluate Feature Flag for User")
    print("-" * 70)

    try:
        # Note: This requires a valid flag key and project API key
        if flags:
            flag_key = flags[0]['key']
            evaluation = client.evaluate_flag(
                key=flag_key,
                distinct_id="demo_user_123"
            )
            print(f"Flag '{flag_key}' evaluation:")
            print(json.dumps(evaluation, indent=2))
    except Exception as e:
        print(f"Flag evaluation error: {e}")


def health_check_demo():
    """Demonstrate connection health check."""
    print("\n" + "=" * 70)
    print("HEALTH CHECK DEMONSTRATION")
    print("=" * 70)

    client = PostHogClient()

    print("\nChecking PostHog API connection...")

    if client.health_check():
        print("✓ Connection successful!")

        # Get project info
        project_info = client.get_project_info()
        print(f"\nProject Name: {project_info.get('name')}")
        print(f"Project ID: {project_info.get('id')}")
        print(f"Timezone: {project_info.get('timezone')}")
    else:
        print("✗ Connection failed!")


if __name__ == '__main__':
    print("\n")
    print("╔" + "=" * 68 + "╗")
    print("║" + " " * 15 + "PostHog Driver - Basic Usage Examples" + " " * 15 + "║")
    print("╚" + "=" * 68 + "╝")

    # Run all demos
    try:
        driver_contract_demo()
        event_tracking_demo()
        analytics_demo()
        cohort_demo()
        feature_flags_demo()
        health_check_demo()

        print("\n" + "=" * 70)
        print("All demonstrations completed successfully!")
        print("=" * 70 + "\n")

    except Exception as e:
        print(f"\n\nError running demonstrations: {e}")
        print("\nMake sure you have set the following environment variables:")
        print("  - POSTHOG_PERSONAL_API_KEY")
        print("  - POSTHOG_PROJECT_ID")
        print("  - POSTHOG_PROJECT_API_KEY (for event capture and flag evaluation)")
        print("  - POSTHOG_API_URL (optional, defaults to https://us.posthog.com)")
