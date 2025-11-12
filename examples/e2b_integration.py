"""
PostHog Driver - E2B Sandbox Integration Example

Demonstrates how to use the PostHog driver within E2B sandboxes
for isolated, cloud-based execution.
"""

import os
from agent_executor import PostHogAgentExecutor
from script_templates import TEMPLATES
import json


def example_basic_execution():
    """
    Example 1: Basic script execution in E2B sandbox.
    """
    print("=" * 70)
    print("EXAMPLE 1: Basic Script Execution")
    print("=" * 70)

    with PostHogAgentExecutor(
        e2b_api_key=os.getenv('E2B_API_KEY'),
        posthog_api_key=os.getenv('POSTHOG_PERSONAL_API_KEY'),
        posthog_project_id=os.getenv('POSTHOG_PROJECT_ID')
    ) as executor:

        script = """
import sys
import json
sys.path.insert(0, '/home/user')

from posthog_driver import PostHogClient

# Initialize client
client = PostHogClient()

# Test connection
healthy = client.health_check()

# Get available entities
objects = client.list_objects()

# Output result
print(json.dumps({
    'success': True,
    'connection_healthy': healthy,
    'available_objects': objects
}, indent=2))
"""

        result = executor.execute_script(
            script=script,
            description="Test PostHog driver in E2B sandbox"
        )

        print(f"\nSuccess: {result['success']}")
        print(f"Output:\n{result['output']}")

        if result['error']:
            print(f"Error: {result['error']}")


def example_template_execution():
    """
    Example 2: Using pre-built script templates.
    """
    print("\n" + "=" * 70)
    print("EXAMPLE 2: Template-Based Execution")
    print("=" * 70)

    with PostHogAgentExecutor(
        e2b_api_key=os.getenv('E2B_API_KEY'),
        posthog_api_key=os.getenv('POSTHOG_PERSONAL_API_KEY'),
        posthog_project_id=os.getenv('POSTHOG_PROJECT_ID')
    ) as executor:

        # Execute "get recent events" template
        result = executor.execute_template(
            template_name='get_recent_events',
            template_vars={
                'event_name': 'User Signup',
                'after_date': '2024-01-01',
                'limit': '10'
            },
            templates=TEMPLATES
        )

        print(f"\nTemplate: get_recent_events")
        print(f"Success: {result['success']}")
        print(f"Output:\n{result['output']}")


def example_power_user_analysis():
    """
    Example 3: Identify power users using template.
    """
    print("\n" + "=" * 70)
    print("EXAMPLE 3: Power User Identification")
    print("=" * 70)

    with PostHogAgentExecutor(
        e2b_api_key=os.getenv('E2B_API_KEY'),
        posthog_api_key=os.getenv('POSTHOG_PERSONAL_API_KEY'),
        posthog_project_id=os.getenv('POSTHOG_PROJECT_ID')
    ) as executor:

        result = executor.execute_template(
            template_name='identify_power_users',
            template_vars={
                'key_event': 'Feature Used',
                'min_occurrences': '10',
                'days': '30'
            },
            templates=TEMPLATES
        )

        print(f"\nSuccess: {result['success']}")

        if result['success']:
            # Parse JSON output
            try:
                data = json.loads(result['output'])
                print(f"\nPower Users Found: {data['power_users_count']}")
                print(f"Criteria: {json.dumps(data['criteria'], indent=2)}")

                if data['power_users']:
                    print("\nTop Power Users:")
                    for user in data['power_users'][:5]:
                        print(f"  - {user.get('email', user['distinct_id'])}: "
                              f"{user['action_count']} actions")
            except json.JSONDecodeError:
                print(f"Raw output:\n{result['output']}")
        else:
            print(f"Error: {result['error']}")


def example_batch_execution():
    """
    Example 4: Execute multiple scripts in sequence.
    """
    print("\n" + "=" * 70)
    print("EXAMPLE 4: Batch Script Execution")
    print("=" * 70)

    with PostHogAgentExecutor(
        e2b_api_key=os.getenv('E2B_API_KEY'),
        posthog_api_key=os.getenv('POSTHOG_PERSONAL_API_KEY'),
        posthog_project_id=os.getenv('POSTHOG_PROJECT_ID')
    ) as executor:

        scripts = [
            {
                'code': TEMPLATES['get_insights'].replace(
                    '{insight_type}', 'TRENDS'
                ).replace('{limit}', '5'),
                'description': 'Get trend insights'
            },
            {
                'code': TEMPLATES['get_insights'].replace(
                    '{insight_type}', 'FUNNELS'
                ).replace('{limit}', '5'),
                'description': 'Get funnel insights'
            }
        ]

        results = executor.batch_execute(scripts)

        for i, result in enumerate(results, 1):
            print(f"\nScript {i}: {result['description']}")
            print(f"Success: {result['success']}")

            if result['success']:
                try:
                    data = json.loads(result['output'])
                    print(f"Found {data['count']} insights")
                except:
                    print(f"Output:\n{result['output'][:200]}...")
            else:
                print(f"Error: {result['error']}")


def example_funnel_analysis():
    """
    Example 5: Analyze conversion funnel.
    """
    print("\n" + "=" * 70)
    print("EXAMPLE 5: Funnel Analysis")
    print("=" * 70)

    with PostHogAgentExecutor(
        e2b_api_key=os.getenv('E2B_API_KEY'),
        posthog_api_key=os.getenv('POSTHOG_PERSONAL_API_KEY'),
        posthog_project_id=os.getenv('POSTHOG_PROJECT_ID')
    ) as executor:

        funnel_template = TEMPLATES['analyze_funnel'].replace(
            '{funnel_steps}', "['Signup Started', 'Email Verified', 'Profile Completed']"
        ).replace('{start_date}', '2024-01-01').replace('{end_date}', '2024-01-31')

        result = executor.execute_script(
            script=funnel_template,
            description="Analyze signup funnel"
        )

        print(f"\nSuccess: {result['success']}")

        if result['success']:
            try:
                data = json.loads(result['output'])
                print(f"\nFunnel Analysis ({data['funnel_steps']} steps):")

                for step in data['funnel_analysis']:
                    print(f"\n  Step: {step['step']}")
                    print(f"  Users: {step['users']}")
                    if step['dropoff_rate'] is not None:
                        print(f"  Drop-off: {step['dropoff_rate']}%")
            except:
                print(f"Output:\n{result['output']}")
        else:
            print(f"Error: {result['error']}")


def example_churn_risk_identification():
    """
    Example 6: Identify users at risk of churning.
    """
    print("\n" + "=" * 70)
    print("EXAMPLE 6: Churn Risk Identification")
    print("=" * 70)

    with PostHogAgentExecutor(
        e2b_api_key=os.getenv('E2B_API_KEY'),
        posthog_api_key=os.getenv('POSTHOG_PERSONAL_API_KEY'),
        posthog_project_id=os.getenv('POSTHOG_PROJECT_ID')
    ) as executor:

        result = executor.execute_template(
            template_name='identify_churn_risk',
            template_vars={
                'inactive_days': '7',   # No activity in last 7 days
                'lookback_days': '30'   # But active in previous 30 days
            },
            templates=TEMPLATES
        )

        print(f"\nSuccess: {result['success']}")

        if result['success']:
            try:
                data = json.loads(result['output'])
                print(f"\nChurn Risk Users: {data['churn_risk_count']}")
                print(f"Criteria: {json.dumps(data['criteria'], indent=2)}")

                if data['users']:
                    print("\nAt-Risk Users:")
                    for user in data['users'][:10]:
                        print(f"  - {user.get('email', user['distinct_id'])}")
                        print(f"    Last seen: {user['last_seen']}")
            except:
                print(f"Output:\n{result['output']}")
        else:
            print(f"Error: {result['error']}")


if __name__ == '__main__':
    print("\n")
    print("╔" + "=" * 68 + "╗")
    print("║" + " " * 12 + "PostHog Driver - E2B Sandbox Integration" + " " * 14 + "║")
    print("╚" + "=" * 68 + "╝")
    print()

    # Check required environment variables
    required_vars = [
        'E2B_API_KEY',
        'POSTHOG_PERSONAL_API_KEY',
        'POSTHOG_PROJECT_ID'
    ]

    missing_vars = [var for var in required_vars if not os.getenv(var)]

    if missing_vars:
        print("ERROR: Missing required environment variables:")
        for var in missing_vars:
            print(f"  - {var}")
        print("\nPlease set these variables in your .env file or environment.")
        exit(1)

    # Run examples
    try:
        print("Running E2B integration examples...\n")

        example_basic_execution()
        example_template_execution()
        example_power_user_analysis()
        example_batch_execution()
        example_funnel_analysis()
        example_churn_risk_identification()

        print("\n" + "=" * 70)
        print("All E2B integration examples completed successfully!")
        print("=" * 70 + "\n")

    except Exception as e:
        print(f"\n\nError running examples: {e}")
        import traceback
        traceback.print_exc()
