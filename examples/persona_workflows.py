"""
PostHog Driver - Persona-Based Workflow Examples

Real-world examples demonstrating how different team personas use
PostHog for analytics, based on typical questions and pain points.

Personas covered:
- Product Engineers
- Technical Product Managers
- Data Analysts
- Growth Marketers
- Customer Success
"""

import sys
sys.path.insert(0, '..')

from posthog_driver import PostHogClient
import json
from datetime import datetime, timedelta


def setup_client():
    """Setup PostHog client (uses environment variables)."""
    return PostHogClient()


# =================================================================
# PRODUCT ENGINEER WORKFLOWS
# =================================================================

def feature_impact_analysis():
    """
    Product Engineer: "Did our new feature actually improve engagement?"

    Workflow:
    1. Deploy new feature
    2. Track feature usage events
    3. Create trend analysis
    4. Compare to baseline metrics
    """
    client = setup_client()

    # Get usage of new feature over last 7 days
    hogql = """
    SELECT
        toDate(timestamp) as date,
        count(DISTINCT distinct_id) as active_users,
        count() as feature_uses
    FROM events
    WHERE
        event = 'New Feature Used'
        AND timestamp >= now() - INTERVAL 7 DAY
    GROUP BY date
    ORDER BY date
    """

    results = client.query(hogql)

    print("=== Feature Impact Analysis ===")
    print(json.dumps(results, indent=2))

    # Also check overall engagement
    engagement_query = """
    SELECT
        count(DISTINCT distinct_id) as total_users,
        countIf(distinct_id, event = 'New Feature Used') as feature_users
    FROM events
    WHERE timestamp >= now() - INTERVAL 7 DAY
    """

    engagement = client.query(engagement_query)
    print("\n=== Engagement Metrics ===")
    print(json.dumps(engagement, indent=2))


def bug_investigation_with_error_tracking():
    """
    Product Engineer / QA: "What errors are affecting users most?"

    Workflow:
    1. Track error events in application
    2. Query error frequency and impact
    3. Identify affected users for follow-up
    """
    client = setup_client()

    # Find most common errors in last 24 hours
    hogql = """
    SELECT
        properties.error_type as error_type,
        properties.error_message as message,
        count() as occurrences,
        count(DISTINCT distinct_id) as affected_users,
        max(timestamp) as last_occurrence
    FROM events
    WHERE
        event = 'Error Occurred'
        AND timestamp >= now() - INTERVAL 24 HOUR
    GROUP BY error_type, message
    ORDER BY occurrences DESC
    LIMIT 20
    """

    errors = client.query(hogql)

    print("=== Critical Errors (Last 24h) ===")
    for error in errors:
        print(f"Type: {error['error_type']}")
        print(f"Message: {error['message']}")
        print(f"Occurrences: {error['occurrences']}")
        print(f"Affected Users: {error['affected_users']}")
        print(f"Last Seen: {error['last_occurrence']}")
        print("-" * 50)


# =================================================================
# TECHNICAL PRODUCT MANAGER WORKFLOWS
# =================================================================

def user_journey_funnel_analysis():
    """
    Technical PM: "Where are users dropping off in our funnel?"

    Workflow:
    1. Define funnel steps
    2. Calculate conversion rates
    3. Identify drop-off points
    4. Watch session replays (if available)
    """
    client = setup_client()

    # Define funnel steps
    funnel_steps = [
        'Signup Started',
        'Email Verified',
        'Profile Completed',
        'First Action Taken'
    ]

    # Calculate users at each step
    start_date = (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d')
    end_date = datetime.now().strftime('%Y-%m-%d')

    print("=== Signup Funnel Analysis ===")
    print(f"Date Range: {start_date} to {end_date}\n")

    prev_count = None
    for step in funnel_steps:
        hogql = f"""
        SELECT count(DISTINCT distinct_id) as count
        FROM events
        WHERE
            event = '{step}'
            AND timestamp >= '{start_date}'
            AND timestamp <= '{end_date}'
        """

        result = client.query(hogql)
        count = result[0]['count'] if result else 0

        conversion_rate = None
        if prev_count is not None and prev_count > 0:
            conversion_rate = (count / prev_count) * 100
            dropoff_rate = 100 - conversion_rate

        print(f"Step: {step}")
        print(f"  Users: {count}")
        if conversion_rate is not None:
            print(f"  Conversion: {conversion_rate:.1f}%")
            print(f"  Drop-off: {dropoff_rate:.1f}%")
        print()

        prev_count = count


def cohort_comparison_analysis():
    """
    Technical PM: "How do paid users behave differently from free users?"

    Workflow:
    1. Get cohorts (paid vs free users)
    2. Compare key metrics between cohorts
    3. Identify behaviors unique to successful users
    """
    client = setup_client()

    # Get all cohorts
    cohorts = client.get_cohorts()

    print("=== Available Cohorts ===")
    for cohort in cohorts:
        print(f"{cohort['name']}: {cohort.get('count', 'N/A')} users")
    print()

    # Compare activity levels between cohorts
    # (Assuming cohorts exist for 'Paid Users' and 'Free Users')
    comparison_query = """
    SELECT
        if(person.properties.plan_type = 'paid', 'Paid', 'Free') as user_type,
        count(DISTINCT distinct_id) as users,
        count() as total_events,
        count() / count(DISTINCT distinct_id) as avg_events_per_user
    FROM events
    WHERE timestamp >= now() - INTERVAL 30 DAY
    GROUP BY user_type
    """

    comparison = client.query(comparison_query)

    print("=== Cohort Activity Comparison (Last 30 Days) ===")
    print(json.dumps(comparison, indent=2))


def ab_test_evaluation():
    """
    Technical PM / Experiments: "Did our A/B test variant perform better?"

    Workflow:
    1. Get experiment results
    2. Analyze statistical significance
    3. Make rollout decision
    """
    client = setup_client()

    # Get all experiments
    experiments = client.get_experiments()

    print("=== Running Experiments ===")
    for exp in experiments:
        print(f"\nExperiment: {exp['name']}")
        print(f"Feature Flag: {exp.get('feature_flag_key')}")
        print(f"Start Date: {exp.get('start_date')}")

        results = exp.get('results', {})
        if results:
            print("Results:")
            print(json.dumps(results, indent=2))
        else:
            print("No results yet")
        print("-" * 50)


# =================================================================
# DATA ANALYST WORKFLOWS
# =================================================================

def complex_hogql_analysis():
    """
    Data Analyst: "What behavioral patterns correlate with conversion?"

    Workflow:
    1. Write complex HogQL queries
    2. Join events with person properties
    3. Perform statistical analysis
    4. Export for further analysis
    """
    client = setup_client()

    # Complex query joining events and person properties
    hogql = """
    SELECT
        person.properties.initial_referrer as referrer,
        person.properties.plan_type as plan,
        count(DISTINCT distinct_id) as users,
        count() as total_events,
        countIf(event = 'Purchase Completed') as conversions,
        (conversions / users) * 100 as conversion_rate
    FROM events
    WHERE timestamp >= now() - INTERVAL 90 DAY
    GROUP BY referrer, plan
    HAVING users >= 10
    ORDER BY conversion_rate DESC
    LIMIT 50
    """

    results = client.query(hogql)

    print("=== Conversion Analysis by Referrer & Plan ===")
    print(json.dumps(results, indent=2))


def data_warehouse_export():
    """
    Data Analyst: "Export PostHog data for data warehouse sync"

    Workflow:
    1. Export events for date range
    2. Transform and clean data
    3. Load to data warehouse
    4. Join with CRM/payment data
    """
    client = setup_client()

    # Export all events for last week
    start_date = (datetime.now() - timedelta(days=7)).strftime('%Y-%m-%d')
    end_date = datetime.now().strftime('%Y-%m-%d')

    print(f"=== Exporting Events ({start_date} to {end_date}) ===")

    events = client.export_events(
        start_date=start_date,
        end_date=end_date,
        event_names=['User Signup', 'Purchase Completed', 'Feature Used']
    )

    print(f"Exported {len(events)} events")
    print("\nSample (first 3 events):")
    print(json.dumps(events[:3], indent=2))

    # In production, you would write this to S3, BigQuery, etc.
    # For example:
    # upload_to_bigquery(events, table='posthog_events')


# =================================================================
# GROWTH MARKETER WORKFLOWS
# =================================================================

def marketing_channel_performance():
    """
    Growth Marketer: "Which marketing channels drive the best users?"

    Workflow:
    1. Track UTM parameters
    2. Analyze conversion by channel
    3. Compare user quality metrics
    4. Optimize ad spend
    """
    client = setup_client()

    # Analyze signups by marketing channel
    hogql = """
    SELECT
        properties.utm_source as source,
        properties.utm_campaign as campaign,
        count(DISTINCT distinct_id) as signups,
        countIf(distinct_id, event = 'Purchase Completed') as conversions,
        (conversions / signups) * 100 as conversion_rate
    FROM events
    WHERE
        event = 'User Signup'
        AND timestamp >= now() - INTERVAL 30 DAY
        AND properties.utm_source IS NOT NULL
    GROUP BY source, campaign
    ORDER BY signups DESC
    LIMIT 20
    """

    channel_performance = client.query(hogql)

    print("=== Marketing Channel Performance (Last 30 Days) ===")
    for channel in channel_performance:
        print(f"\nSource: {channel['source']}")
        print(f"Campaign: {channel['campaign']}")
        print(f"Signups: {channel['signups']}")
        print(f"Conversions: {channel['conversions']}")
        print(f"Conversion Rate: {channel['conversion_rate']:.2f}%")


# =================================================================
# CUSTOMER SUCCESS WORKFLOWS
# =================================================================

def individual_user_journey():
    """
    Customer Success: "What has this user been doing? Why did they churn?"

    Workflow:
    1. Look up user by email/ID
    2. Get full event history
    3. Review session replays
    4. Identify pain points
    """
    client = setup_client()

    # Look up specific user
    user_email = "user@example.com"

    # Get person details
    persons = client.get_persons(search=user_email)

    if not persons:
        print(f"User not found: {user_email}")
        return

    person = persons[0]
    distinct_id = person['distinct_ids'][0]

    print(f"=== User Journey for {user_email} ===")
    print(f"Person ID: {person['id']}")
    print(f"Distinct ID: {distinct_id}")
    print(f"\nPerson Properties:")
    print(json.dumps(person['properties'], indent=2))

    # Get recent events for this user
    hogql = f"""
    SELECT
        event,
        timestamp,
        properties
    FROM events
    WHERE
        distinct_id = '{distinct_id}'
        AND timestamp >= now() - INTERVAL 30 DAY
    ORDER BY timestamp DESC
    LIMIT 50
    """

    user_events = client.query(hogql)

    print(f"\n=== Recent Events (Last 30 Days) ===")
    for event in user_events[:10]:  # Show first 10
        print(f"{event['timestamp']}: {event['event']}")


def power_user_identification():
    """
    Product / Customer Success: "Who are our power users?"

    Workflow:
    1. Define power user criteria
    2. Create cohort
    3. Analyze their behavior
    4. Engage for testimonials/feedback
    """
    client = setup_client()

    # Find users who use key features frequently
    hogql = """
    SELECT
        distinct_id,
        person.properties.email as email,
        person.properties.plan_type as plan,
        count() as event_count,
        countIf(event = 'Key Feature Used') as key_feature_uses,
        max(timestamp) as last_active
    FROM events
    WHERE
        timestamp >= now() - INTERVAL 30 DAY
    GROUP BY distinct_id, email, plan
    HAVING event_count >= 100 AND key_feature_uses >= 20
    ORDER BY event_count DESC
    LIMIT 50
    """

    power_users = client.query(hogql)

    print("=== Power Users (Last 30 Days) ===")
    print(f"Criteria: 100+ total events, 20+ key feature uses\n")

    for user in power_users[:10]:
        print(f"Email: {user['email']}")
        print(f"Plan: {user['plan']}")
        print(f"Total Events: {user['event_count']}")
        print(f"Key Feature Uses: {user['key_feature_uses']}")
        print(f"Last Active: {user['last_active']}")
        print("-" * 50)


# =================================================================
# MAIN - Run Example Workflows
# =================================================================

if __name__ == '__main__':
    print("PostHog Driver - Persona-Based Workflow Examples\n")
    print("=" * 70)

    # Uncomment the workflow you want to run:

    # Product Engineer
    # feature_impact_analysis()
    # bug_investigation_with_error_tracking()

    # Technical PM
    # user_journey_funnel_analysis()
    # cohort_comparison_analysis()
    # ab_test_evaluation()

    # Data Analyst
    # complex_hogql_analysis()
    # data_warehouse_export()

    # Growth Marketer
    # marketing_channel_performance()

    # Customer Success
    # individual_user_journey()
    # power_user_identification()

    print("\nTo run a workflow, uncomment the desired function in __main__")
