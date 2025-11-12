#!/usr/bin/env python3
"""
Complex Question Example: Claude + PostHog Advanced Analytics
"""

import os
from anthropic import Anthropic
from e2b import Sandbox

# Tool definition
TOOL = {
    "name": "query_posthog",
    "description": "Query PostHog analytics data to analyze user behavior, conversion funnels, and product metrics",
    "input_schema": {
        "type": "object",
        "properties": {
            "question": {"type": "string", "description": "Complex analytics question"}
        },
        "required": ["question"]
    }
}

def execute_tool(sandbox, question):
    """Execute PostHog query in E2B sandbox."""

    script = f'''
import sys
sys.path.insert(0, '/home/user')
from posthog_driver import PostHogClient

client = PostHogClient(
    api_key="{os.getenv('POSTHOG_API_KEY')}",
    project_id="{os.getenv('POSTHOG_PROJECT_ID')}"
)

print("=== ANALYZING YOUR PRODUCT DATA ===\\n")

# Query 1: User Journey - Drop-off Analysis
print("📊 CONVERSION FUNNEL:")
print("-" * 60)

funnel_steps = [
    ('Viewed pages', '$pageview'),
    ('Logged in', 'user_logged_in'),
    ('Started subscription', 'subscription_intent'),
    ('Completed purchase', 'subscription_purchased'),
]

prev_users = None
for step_name, event_name in funnel_steps:
    query = f"""
    SELECT count(DISTINCT distinct_id) as users
    FROM events
    WHERE event = '{{event_name}}'
        AND timestamp >= now() - INTERVAL 30 DAY
    """

    try:
        result = client.query(query)
        users = result[0][0] if result and len(result) > 0 else 0

        if prev_users is not None:
            drop_off = prev_users - users
            drop_off_pct = (drop_off / prev_users * 100) if prev_users > 0 else 0
            conversion_pct = (users / prev_users * 100) if prev_users > 0 else 0
            print(f"{{step_name:<25}} {{users:>6}} users  ({{conversion_pct:>5.1f}}% converted, {{drop_off:>4}} dropped)")
        else:
            print(f"{{step_name:<25}} {{users:>6}} users")

        prev_users = users
    except Exception as e:
        print(f"{{step_name:<25}} Error: {{e}}")

# Query 2: User Activity vs Conversion
print("\\n📈 USER ACTIVITY vs CONVERSION:")
print("-" * 60)

# Get converters
converter_query = """
SELECT DISTINCT distinct_id
FROM events
WHERE event IN ('subscription_purchased', 'movie_buy_complete', 'movie_rent_complete')
    AND timestamp >= now() - INTERVAL 30 DAY
"""

converters = client.query(converter_query)
converter_ids = [str(row[0]) for row in converters] if converters else []

print(f"Converters: {{len(converter_ids)}} users")

# Get activity levels for converters vs non-converters
if len(converter_ids) > 0:
    converter_ids_str = "', '".join(converter_ids[:50])  # Limit for query size

    # Converter activity
    converter_activity_query = f"""
    SELECT count() / count(DISTINCT distinct_id) as avg_events_per_user
    FROM events
    WHERE distinct_id IN ('{{converter_ids_str}}')
        AND timestamp >= now() - INTERVAL 30 DAY
    """

    try:
        result = client.query(converter_activity_query)
        converter_avg = float(result[0][0]) if result else 0
        print(f"Converters avg activity: {{converter_avg:.1f}} events/user")
    except:
        converter_avg = 0

    # Non-converter activity
    non_converter_query = f"""
    SELECT count() / count(DISTINCT distinct_id) as avg_events_per_user
    FROM events
    WHERE distinct_id NOT IN ('{{converter_ids_str}}')
        AND timestamp >= now() - INTERVAL 30 DAY
    """

    try:
        result = client.query(non_converter_query)
        non_converter_avg = float(result[0][0]) if result else 0
        print(f"Non-converters avg activity: {{non_converter_avg:.1f}} events/user")

        if non_converter_avg > 0:
            multiplier = converter_avg / non_converter_avg
            print(f"\\n💡 Converters are {{multiplier:.1f}}x more active!")
    except:
        pass

# Query 3: Time-based patterns
print("\\n⏰ CONVERSION TIMING PATTERNS:")
print("-" * 60)

time_query = """
SELECT
    toDayOfWeek(timestamp) as day_of_week,
    toHour(timestamp) as hour,
    count() as conversions
FROM events
WHERE event IN ('subscription_purchased', 'movie_buy_complete', 'movie_rent_complete')
    AND timestamp >= now() - INTERVAL 30 DAY
GROUP BY day_of_week, hour
ORDER BY conversions DESC
LIMIT 5
"""

try:
    results = client.query(time_query)
    days = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']

    print("Best conversion times:")
    for row in results:
        day_num = int(row[0]) - 1  # Adjust for 0-indexing
        day_name = days[day_num] if 0 <= day_num < 7 else 'Unknown'
        hour = int(row[1])
        count = int(row[2])
        print(f"  {{day_name}} at {{hour:02d}}:00 - {{count}} conversions")
except Exception as e:
    print(f"  Error: {{e}}")

# Query 4: Feature adoption
print("\\n🎯 FEATURE ADOPTION:")
print("-" * 60)

feature_query = """
SELECT
    event,
    count(DISTINCT distinct_id) as unique_users,
    count() as total_events,
    count() / count(DISTINCT distinct_id) as avg_per_user
FROM events
WHERE timestamp >= now() - INTERVAL 30 DAY
    AND event NOT LIKE '$%'  -- Exclude system events
GROUP BY event
ORDER BY unique_users DESC
"""

try:
    results = client.query(feature_query)
    print(f"{'Feature':<30} {'Users':>8} {'Total':>8} {'Avg/User':>10}")
    print("-" * 60)
    for row in results[:10]:
        feature = str(row[0])[:28]
        users = int(row[1])
        total = int(row[2])
        avg = float(row[3])
        print(f"{{feature:<30}} {{users:>8}} {{total:>8}} {{avg:>10.1f}}")
except Exception as e:
    print(f"Error: {{e}}")

print("\\n" + "=" * 60)
'''

    # Write and execute script
    sandbox.files.write('/home/user/complex_query.py', script)
    result = sandbox.commands.run('cd /home/user && python3 complex_query.py')
    return result.stdout or result.stderr

def main():
    print("\n" + "=" * 70)
    print("  Claude + PostHog: Complex Analytics Question")
    print("=" * 70 + "\n")

    # Initialize
    anthropic = Anthropic(api_key=os.getenv('ANTHROPIC_API_KEY'))
    sandbox = Sandbox(api_key=os.getenv('E2B_API_KEY'))

    try:
        # Upload PostHog driver
        print("📦 Setting up sandbox...")
        for filename in ['__init__.py', 'client.py', 'exceptions.py']:
            with open(f'posthog_driver/{filename}', 'r') as f:
                sandbox.files.write(f'/home/user/posthog_driver/{filename}', f.read())

        sandbox.commands.run('pip install requests python-dotenv -q')
        print("✅ Ready!\n")

        # Ask Claude a complex question
        question = """Analyze my product's conversion funnel and user behavior:

1. Where do users drop off in the conversion journey?
2. What's the relationship between user activity and conversion?
3. When do most conversions happen?
4. Which features are most adopted?

Provide actionable insights and recommendations."""

        print(f"💬 Complex Question:\n{question}\n")
        print("─" * 70 + "\n")

        messages = [{"role": "user", "content": question}]

        # Call Claude with tool
        print("🤖 Claude is analyzing your data...\n")
        response = anthropic.messages.create(
            model="claude-sonnet-4-5-20250929",
            max_tokens=2048,
            tools=[TOOL],
            messages=messages
        )

        # Handle tool use loop
        while response.stop_reason == "tool_use":
            # Get all tool uses in this response
            tool_uses = [b for b in response.content if b.type == "tool_use"]

            print(f"🔍 Claude is using {len(tool_uses)} tool call(s)\n")

            # Execute each tool and collect results
            tool_results = []
            for tool_use in tool_uses:
                print(f"Executing: {tool_use.name}\n")
                result = execute_tool(sandbox, tool_use.input.get("question", ""))
                print(f"{result}\n")
                print("─" * 70 + "\n")

                tool_results.append({
                    "type": "tool_result",
                    "tool_use_id": tool_use.id,
                    "content": result
                })

            # Send results back to Claude
            messages.append({"role": "assistant", "content": response.content})
            messages.append({"role": "user", "content": tool_results})

            # Get Claude's next response
            print("🤖 Claude's Analysis:\n")
            response = anthropic.messages.create(
                model="claude-sonnet-4-5-20250929",
                max_tokens=2048,
                tools=[TOOL],
                messages=messages
            )

        # Print final text response
        answer = next((b.text for b in response.content if hasattr(b, "text")), "")
        print(answer)
        print()

    finally:
        sandbox.kill()
        print("\n✅ Analysis complete!\n")

if __name__ == '__main__':
    main()
