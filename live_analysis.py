#!/usr/bin/env python3
"""
Live PostHog Analysis
Answers real business questions using actual PostHog data
"""

import sys
import json
from posthog_driver import PostHogClient
from datetime import datetime, timedelta


def print_header(text):
    """Print formatted header."""
    print("\n" + "=" * 80)
    print(f"  {text}")
    print("=" * 80)


def print_subheader(text):
    """Print formatted subheader."""
    print(f"\n▶ {text}")
    print("-" * 80)


def analyze_dropoff(client):
    """
    Question: "Where do users drop off?"

    Strategy:
    1. First, discover what events exist
    2. Identify key user journey events
    3. Calculate conversion between steps
    4. Find biggest drop-off points
    """
    print_header("QUESTION 1: Where do users drop off?")

    print("\n🔍 Step 1: Discovering available events...")

    # Query to find most common events (these form the user journey)
    query = """
    SELECT
        event,
        count() as occurrences,
        count(DISTINCT distinct_id) as unique_users
    FROM events
    WHERE timestamp >= now() - INTERVAL 30 DAY
    GROUP BY event
    ORDER BY occurrences DESC
    LIMIT 20
    """

    try:
        results = client.query(query)

        if not results:
            print("\n⚠️  No events found in the last 30 days")
            return

        print(f"\n✓ Found {len(results)} most common events (last 30 days):")
        print("\n{:<40} {:>15} {:>15}".format("Event", "Total Events", "Unique Users"))
        print("-" * 80)

        for i, event in enumerate(results[:10], 1):
            # Handle both dict and list results
            if isinstance(event, dict):
                event_name = event.get('event', 'Unknown')
                occurrences = event.get('occurrences', 0)
                users = event.get('unique_users', 0)
            else:
                # If it's a list, try to parse it
                event_name = str(event[0]) if len(event) > 0 else 'Unknown'
                occurrences = int(event[1]) if len(event) > 1 else 0
                users = int(event[2]) if len(event) > 2 else 0
            print(f"{i:2}. {event_name:<37} {occurrences:>12,} {users:>15,}")

        # Identify potential funnel steps based on event names
        print("\n🔍 Step 2: Analyzing user journey patterns...")

        # Common journey patterns to look for
        journey_keywords = [
            'signup', 'sign up', 'register', 'create account',
            'login', 'sign in',
            'onboard', 'welcome', 'tutorial',
            'view', 'page', 'visit',
            'click', 'button',
            'complete', 'finish', 'submit',
            'purchase', 'checkout', 'payment', 'buy'
        ]

        journey_events = []
        for event_data in results:
            if isinstance(event_data, dict):
                event_name = event_data.get('event', '').lower()
            else:
                event_name = str(event_data[0]).lower() if len(event_data) > 0 else ''

            for keyword in journey_keywords:
                if keyword in event_name:
                    journey_events.append(event_data)
                    break

        if journey_events:
            print(f"\n✓ Identified {len(journey_events)} potential journey events:")
            for event in journey_events[:5]:
                if isinstance(event, dict):
                    print(f"   • {event.get('event')}")
                else:
                    print(f"   • {event[0] if len(event) > 0 else 'Unknown'}")

        # Calculate drop-off rates between sequential events
        print("\n🔍 Step 3: Calculating drop-off rates...")

        if len(results) >= 2:
            print("\nSequential event conversion:")
            print("\n{:<35} → {:<35} {:>10}".format("From Event", "To Event", "Retention"))
            print("-" * 80)

            # Compare first few events to see drop-off
            for i in range(min(3, len(results) - 1)):
                from_event = results[i]
                to_event = results[i + 1]

                # Handle both dict and list
                if isinstance(from_event, dict):
                    from_users = from_event.get('unique_users', 1)
                    from_name = from_event.get('event', '')[:33]
                else:
                    from_users = int(from_event[2]) if len(from_event) > 2 else 1
                    from_name = str(from_event[0])[:33] if len(from_event) > 0 else ''

                if isinstance(to_event, dict):
                    to_users = to_event.get('unique_users', 0)
                    to_name = to_event.get('event', '')[:33]
                else:
                    to_users = int(to_event[2]) if len(to_event) > 2 else 0
                    to_name = str(to_event[0])[:33] if len(to_event) > 0 else ''

                retention = (to_users / from_users * 100) if from_users > 0 else 0
                drop_off = 100 - retention

                print(f"{from_name:<35} → {to_name:<35} {retention:>9.1f}%")
                if drop_off > 50:
                    print(f"   ⚠️  HIGH DROP-OFF: {drop_off:.1f}% of users don't continue")

        # Look for specific funnel patterns
        print("\n🔍 Step 4: Checking for funnel patterns...")

        # Try to find signup → activation pattern
        signup_query = """
        SELECT
            count(DISTINCT distinct_id) as signup_users
        FROM events
        WHERE event ILIKE '%signup%' OR event ILIKE '%register%'
            AND timestamp >= now() - INTERVAL 30 DAY
        """

        activation_query = """
        SELECT
            count(DISTINCT distinct_id) as active_users
        FROM events
        WHERE timestamp >= now() - INTERVAL 30 DAY
        GROUP BY distinct_id
        HAVING count() >= 5
        """

        try:
            signup_result = client.query(signup_query)
            activation_result = client.query(activation_query)

            if signup_result and len(activation_result) > 0:
                signups = signup_result[0].get('signup_users', 0) if signup_result else 0
                activated = len(activation_result)

                if signups > 0:
                    activation_rate = (activated / signups * 100)
                    print(f"\n📊 Signup to Activation:")
                    print(f"   Signups: {signups:,} users")
                    print(f"   Activated (5+ events): {activated:,} users")
                    print(f"   Activation rate: {activation_rate:.1f}%")

                    if activation_rate < 50:
                        print(f"\n   ⚠️  Only {activation_rate:.1f}% of signups become active")
                        print(f"   💡 Recommendation: Improve onboarding flow")
        except Exception as e:
            print(f"\n   (Could not calculate activation: {e})")

        # Summary
        print("\n" + "=" * 80)
        print("📋 KEY FINDINGS - Where Users Drop Off:")
        print("=" * 80)

        if len(results) >= 2:
            biggest_drop = None
            biggest_drop_pct = 0

            for i in range(min(5, len(results) - 1)):
                if isinstance(results[i], dict):
                    from_users = results[i].get('unique_users', 1)
                    from_event_name = results[i].get('event')
                else:
                    from_users = int(results[i][2]) if len(results[i]) > 2 else 1
                    from_event_name = str(results[i][0]) if len(results[i]) > 0 else ''

                if isinstance(results[i+1], dict):
                    to_users = results[i + 1].get('unique_users', 0)
                    to_event_name = results[i + 1].get('event')
                else:
                    to_users = int(results[i+1][2]) if len(results[i+1]) > 2 else 0
                    to_event_name = str(results[i+1][0]) if len(results[i+1]) > 0 else ''

                drop_pct = ((from_users - to_users) / from_users * 100) if from_users > 0 else 0

                if drop_pct > biggest_drop_pct:
                    biggest_drop_pct = drop_pct
                    biggest_drop = (from_event_name, to_event_name)

            if biggest_drop:
                print(f"\n1. Biggest drop-off: {biggest_drop_pct:.1f}%")
                print(f"   Between '{biggest_drop[0]}' → '{biggest_drop[1]}'")

            print(f"\n2. Top events by user count:")
            for i, event in enumerate(results[:3], 1):
                if isinstance(event, dict):
                    print(f"   {i}. {event.get('event')}: {event.get('unique_users', 0):,} users")
                else:
                    event_name = str(event[0]) if len(event) > 0 else 'Unknown'
                    users = int(event[2]) if len(event) > 2 else 0
                    print(f"   {i}. {event_name}: {users:,} users")

            if journey_events:
                print(f"\n3. Identified {len(journey_events)} journey-related events")
                print("   Focus on optimizing transitions between these steps")

    except Exception as e:
        print(f"\n❌ Error querying data: {e}")
        print(f"   Make sure your API key has query permissions")


def analyze_conversion_drivers(client):
    """
    Question: "What drives conversion?"

    Strategy:
    1. Define what "conversion" means (purchases, completions, etc.)
    2. Look at user properties and behaviors that correlate
    3. Analyze by traffic source, user attributes, timing
    """
    print_header("QUESTION 2: What drives conversion?")

    print("\n🔍 Step 1: Identifying conversion events...")

    # Look for conversion-related events
    conversion_query = """
    SELECT
        event,
        count() as occurrences,
        count(DISTINCT distinct_id) as converters
    FROM events
    WHERE (
        event ILIKE '%purchase%' OR
        event ILIKE '%checkout%' OR
        event ILIKE '%complete%' OR
        event ILIKE '%success%' OR
        event ILIKE '%paid%' OR
        event ILIKE '%conversion%' OR
        event ILIKE '%subscribe%'
    )
    AND timestamp >= now() - INTERVAL 30 DAY
    GROUP BY event
    ORDER BY occurrences DESC
    LIMIT 10
    """

    try:
        conversion_events = client.query(conversion_query)

        if not conversion_events:
            print("\n⚠️  No obvious conversion events found")
            print("   Looking for events with: purchase, checkout, complete, subscribe, etc.")
        else:
            print(f"\n✓ Found {len(conversion_events)} conversion-related events:")
            for i, event in enumerate(conversion_events, 1):
                if isinstance(event, dict):
                    event_name = event.get('event', 'Unknown')
                    converters = event.get('converters', 0)
                else:
                    event_name = str(event[0]) if len(event) > 0 else 'Unknown'
                    converters = int(event[2]) if len(event) > 2 else 0
                print(f"   {i}. {event_name}: {converters:,} users converted")

        # Analyze conversion by traffic source
        print("\n🔍 Step 2: Analyzing conversion by traffic source...")

        source_query = """
        SELECT
            properties.$initial_utm_source as source,
            count(DISTINCT distinct_id) as users,
            countIf(event ILIKE '%purchase%' OR event ILIKE '%complete%' OR event ILIKE '%subscribe%') as conversions
        FROM events
        WHERE timestamp >= now() - INTERVAL 30 DAY
            AND properties.$initial_utm_source IS NOT NULL
        GROUP BY source
        ORDER BY users DESC
        LIMIT 10
        """

        try:
            source_results = client.query(source_query)

            if source_results and len(source_results) > 0:
                print("\n✓ Conversion by traffic source:")
                print("\n{:<25} {:>12} {:>12} {:>15}".format("Source", "Total Users", "Conversions", "Conv. Rate"))
                print("-" * 80)

                best_source = None
                best_rate = 0

                for source_data in source_results:
                    if isinstance(source_data, dict):
                        source = source_data.get('source', 'Unknown')[:23]
                        users = source_data.get('users', 0)
                        conversions = source_data.get('conversions', 0)
                    else:
                        source = str(source_data[0])[:23] if len(source_data) > 0 else 'Unknown'
                        users = int(source_data[1]) if len(source_data) > 1 else 0
                        conversions = int(source_data[2]) if len(source_data) > 2 else 0

                    rate = (conversions / users * 100) if users > 0 else 0

                    print(f"{source:<25} {users:>12,} {conversions:>12,} {rate:>14.1f}%")

                    if rate > best_rate and users > 10:
                        best_rate = rate
                        best_source = source

                if best_source:
                    print(f"\n   🎯 Best converting source: {best_source} ({best_rate:.1f}%)")
            else:
                print("\n   ℹ️  No UTM source data found")
        except Exception as e:
            print(f"\n   (Could not analyze by source: {e})")

        # Analyze by user behavior patterns
        print("\n🔍 Step 3: Analyzing user behavior patterns...")

        behavior_query = """
        SELECT
            count() as total_events,
            countIf(event ILIKE '%purchase%' OR event ILIKE '%complete%' OR event ILIKE '%subscribe%') as has_conversion
        FROM events
        WHERE timestamp >= now() - INTERVAL 30 DAY
        GROUP BY distinct_id
        ORDER BY total_events DESC
        LIMIT 100
        """

        try:
            behavior_results = client.query(behavior_query)

            if behavior_results:
                converters = []
                non_converters = []

                for b in behavior_results:
                    if isinstance(b, dict):
                        has_conv = b.get('has_conversion', 0)
                    else:
                        has_conv = int(b[1]) if len(b) > 1 else 0

                    if has_conv > 0:
                        converters.append(b)
                    else:
                        non_converters.append(b)

                if converters and non_converters:
                    def get_total_events(item):
                        if isinstance(item, dict):
                            return item.get('total_events', 0)
                        return int(item[0]) if len(item) > 0 else 0

                    avg_events_converters = sum(get_total_events(b) for b in converters) / len(converters)
                    avg_events_non = sum(get_total_events(b) for b in non_converters) / len(non_converters)

                    print(f"\n✓ Activity patterns:")
                    print(f"   Converters average: {avg_events_converters:.1f} events")
                    print(f"   Non-converters average: {avg_events_non:.1f} events")

                    if avg_events_converters > avg_events_non * 1.5:
                        print(f"\n   💡 Converters are {avg_events_converters/avg_events_non:.1f}x more active")
                        print("   💡 Recommendation: Drive engagement to increase conversions")
        except Exception as e:
            print(f"\n   (Could not analyze behavior: {e})")

        # Look at time-based patterns
        print("\n🔍 Step 4: Checking timing patterns...")

        timing_query = """
        SELECT
            toDayOfWeek(timestamp) as day_of_week,
            toHour(timestamp) as hour_of_day,
            count() as events,
            countIf(event ILIKE '%purchase%' OR event ILIKE '%complete%' OR event ILIKE '%subscribe%') as conversions
        FROM events
        WHERE timestamp >= now() - INTERVAL 30 DAY
        GROUP BY day_of_week, hour_of_day
        HAVING conversions > 0
        ORDER BY conversions DESC
        LIMIT 5
        """

        try:
            timing_results = client.query(timing_query)

            if timing_results:
                print(f"\n✓ Peak conversion times:")

                days = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']

                for time_data in timing_results[:3]:
                    if isinstance(time_data, dict):
                        day = time_data.get('day_of_week', 0)
                        hour = time_data.get('hour_of_day', 0)
                        conversions = time_data.get('conversions', 0)
                    else:
                        day = int(time_data[0]) if len(time_data) > 0 else 0
                        hour = int(time_data[1]) if len(time_data) > 1 else 0
                        conversions = int(time_data[3]) if len(time_data) > 3 else 0

                    day_name = days[day - 1] if 1 <= day <= 7 else 'Unknown'
                    print(f"   • {day_name} at {hour:02d}:00 - {conversions:,} conversions")
        except Exception as e:
            print(f"\n   (Could not analyze timing: {e})")

        # Summary
        print("\n" + "=" * 80)
        print("📋 KEY FINDINGS - What Drives Conversion:")
        print("=" * 80)

        findings = []

        if conversion_events:
            def get_converters(e):
                if isinstance(e, dict):
                    return e.get('converters', 0)
                return int(e[2]) if len(e) > 2 else 0

            total_converters = sum(get_converters(e) for e in conversion_events)
            findings.append(f"Found {len(conversion_events)} conversion events with {total_converters:,} total converters")

        if source_results and len(source_results) > 0:
            def get_rate(x):
                if isinstance(x, dict):
                    users = x.get('users', 1)
                    convs = x.get('conversions', 0)
                else:
                    users = int(x[1]) if len(x) > 1 else 1
                    convs = int(x[2]) if len(x) > 2 else 0
                return (convs / users) if users > 10 else 0

            best = max(source_results, key=get_rate)
            if best:
                if isinstance(best, dict):
                    best_users = best.get('users', 0)
                    best_convs = best.get('conversions', 0)
                    best_source = best.get('source')
                else:
                    best_users = int(best[1]) if len(best) > 1 else 0
                    best_convs = int(best[2]) if len(best) > 2 else 0
                    best_source = str(best[0]) if len(best) > 0 else 'Unknown'

                if best_users > 10:
                    rate = (best_convs / best_users * 100)
                    findings.append(f"Best traffic source: {best_source} ({rate:.1f}% conversion)")

        if findings:
            for i, finding in enumerate(findings, 1):
                print(f"\n{i}. {finding}")
        else:
            print("\nNo conversion patterns identified yet.")
            print("This could mean:")
            print("  • Not enough data collected")
            print("  • Conversion events aren't tracked")
            print("  • Need to define what 'conversion' means for your product")

    except Exception as e:
        print(f"\n❌ Error querying data: {e}")
        print(f"   Details: {type(e).__name__}")


def main():
    """Run the live analysis."""
    print("\n" + "╔" + "=" * 78 + "╗")
    print("║" + " " * 20 + "PostHog Driver - LIVE ANALYSIS" + " " * 27 + "║")
    print("║" + " " * 25 + "Real Data, Real Insights" + " " * 29 + "║")
    print("╚" + "=" * 78 + "╝")

    # Initialize client with provided credentials
    print("\n🔧 Connecting to PostHog...")

    try:
        client = PostHogClient(
            api_key='phx_YOUR_KEY_HERE',
            project_id='245832',
            api_url='https://us.posthog.com'
        )

        # Test connection
        print("✓ Testing connection...")
        if client.health_check():
            project_info = client.get_project_info()
            print(f"✓ Connected to project: {project_info.get('name', 'Unknown')}")
        else:
            print("⚠️  Connection test failed, but continuing...")

    except Exception as e:
        print(f"❌ Failed to connect: {e}")
        return

    # Run analyses
    try:
        analyze_dropoff(client)
        analyze_conversion_drivers(client)

        print("\n" + "=" * 80)
        print("✅ Analysis Complete!")
        print("=" * 80)
        print("\n💡 Next steps:")
        print("   1. Review the findings above")
        print("   2. Focus on the biggest drop-off points")
        print("   3. Double down on high-converting traffic sources")
        print("   4. Use insights to optimize your funnel")
        print()

    except Exception as e:
        print(f"\n❌ Error during analysis: {e}")
        import traceback
        traceback.print_exc()


if __name__ == '__main__':
    main()
