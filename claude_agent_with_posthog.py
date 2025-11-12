#!/usr/bin/env python3
"""
Claude Agent SDK + PostHog Driver Integration

This script demonstrates how to integrate the PostHog driver with Claude Agent SDK,
allowing Claude to answer natural language questions about your PostHog analytics data.

The integration runs in E2B sandboxes for security and isolation.
"""

import os
import json
from anthropic import Anthropic
from e2b import Sandbox

# ============================================================================
# CONFIGURATION
# ============================================================================

ANTHROPIC_API_KEY = os.getenv('ANTHROPIC_API_KEY')
E2B_API_KEY = os.getenv('E2B_API_KEY')
POSTHOG_API_KEY = os.getenv('POSTHOG_API_KEY')
POSTHOG_PROJECT_ID = os.getenv('POSTHOG_PROJECT_ID')

# ============================================================================
# TOOL DEFINITION - This is what Claude sees
# ============================================================================

POSTHOG_TOOL = {
    "name": "query_posthog",
    "description": """Query PostHog analytics data to answer questions about user behavior,
    product usage, and conversion metrics. This tool can:

    - Find top events and their frequencies
    - Analyze user funnels and drop-off points
    - Identify conversion drivers and patterns
    - Segment users by activity level
    - Track feature usage and adoption
    - Analyze time-based patterns

    The tool accepts natural language questions and automatically translates them
    into HogQL queries to retrieve the relevant data.""",
    "input_schema": {
        "type": "object",
        "properties": {
            "question": {
                "type": "string",
                "description": "The analytics question to answer (e.g., 'What are the top events in the last 7 days?', 'Where do users drop off?', 'What drives conversion?')"
            },
            "time_period": {
                "type": "string",
                "enum": ["7_days", "30_days", "90_days"],
                "description": "Time period for the analysis",
                "default": "30_days"
            }
        },
        "required": ["question"]
    }
}

# ============================================================================
# QUERY MAPPER - Converts natural language to HogQL
# ============================================================================

QUERY_TEMPLATES = {
    "top_events": """
        SELECT
            event,
            count() as total_events,
            count(DISTINCT distinct_id) as unique_users
        FROM events
        WHERE timestamp >= now() - INTERVAL {days} DAY
        GROUP BY event
        ORDER BY total_events DESC
        LIMIT 10
    """,

    "user_funnel": """
        SELECT
            event,
            count(DISTINCT distinct_id) as users
        FROM events
        WHERE timestamp >= now() - INTERVAL {days} DAY
        GROUP BY event
        ORDER BY users DESC
    """,

    "conversion_analysis": """
        SELECT
            event,
            count() as occurrences,
            count(DISTINCT distinct_id) as unique_users,
            count() / count(DISTINCT distinct_id) as avg_per_user
        FROM events
        WHERE timestamp >= now() - INTERVAL {days} DAY
            AND event IN ('subscription_purchased', 'movie_buy_complete', 'movie_rent_complete', 'upgrade_completed')
        GROUP BY event
        ORDER BY unique_users DESC
    """,

    "activity_distribution": """
        SELECT
            CASE
                WHEN event_count < 5 THEN 'Low activity (1-4 events)'
                WHEN event_count < 20 THEN 'Medium activity (5-19 events)'
                ELSE 'High activity (20+ events)'
            END as activity_level,
            count() as user_count
        FROM (
            SELECT distinct_id, count() as event_count
            FROM events
            WHERE timestamp >= now() - INTERVAL {days} DAY
            GROUP BY distinct_id
        )
        GROUP BY activity_level
        ORDER BY user_count DESC
    """,

    "time_patterns": """
        SELECT
            toDayOfWeek(timestamp) as day_of_week,
            toHour(timestamp) as hour,
            count() as events
        FROM events
        WHERE timestamp >= now() - INTERVAL {days} DAY
        GROUP BY day_of_week, hour
        ORDER BY events DESC
        LIMIT 20
    """
}

def question_to_query(question: str, time_period: str = "30_days") -> str:
    """Convert natural language question to HogQL query."""

    days_map = {"7_days": 7, "30_days": 30, "90_days": 90}
    days = days_map.get(time_period, 30)

    question_lower = question.lower()

    # Pattern matching
    if any(word in question_lower for word in ["top events", "most common", "popular events"]):
        return QUERY_TEMPLATES["top_events"].format(days=days)

    elif any(word in question_lower for word in ["drop off", "funnel", "user journey"]):
        return QUERY_TEMPLATES["user_funnel"].format(days=days)

    elif any(word in question_lower for word in ["conversion", "purchase", "buy", "subscribe"]):
        return QUERY_TEMPLATES["conversion_analysis"].format(days=days)

    elif any(word in question_lower for word in ["activity", "engagement", "active users"]):
        return QUERY_TEMPLATES["activity_distribution"].format(days=days)

    elif any(word in question_lower for word in ["time", "when", "hour", "day"]):
        return QUERY_TEMPLATES["time_patterns"].format(days=days)

    else:
        # Default to top events
        return QUERY_TEMPLATES["top_events"].format(days=days)

# ============================================================================
# E2B EXECUTOR - Runs queries in isolated sandbox
# ============================================================================

def execute_posthog_query_in_e2b(sandbox, query: str) -> dict:
    """Execute a PostHog query inside an E2B sandbox."""

    script = f'''
import sys
sys.path.insert(0, '/home/user')
from posthog_driver import PostHogClient
import json

try:
    client = PostHogClient(
        api_key="{POSTHOG_API_KEY}",
        project_id="{POSTHOG_PROJECT_ID}"
    )

    results = client.query("""{query}""")

    # Convert results to JSON-serializable format
    output = []
    for row in results:
        if isinstance(row, dict):
            output.append(row)
        else:
            # Convert list/tuple to dict with generic keys
            output.append({{"col_" + str(i): val for i, val in enumerate(row)}})

    print(json.dumps({{"success": True, "results": output}}))

except Exception as e:
    print(json.dumps({{"success": False, "error": str(e)}}))
'''

    result = sandbox.run_code(code=script, envs={'PYTHONPATH': '/home/user'})

    if result.error:
        return {"success": False, "error": result.error}

    try:
        return json.loads(result.logs.stdout)
    except:
        return {"success": False, "error": "Failed to parse results", "raw": result.logs.stdout}

# ============================================================================
# TOOL EXECUTOR - Called when Claude invokes the tool
# ============================================================================

def execute_posthog_tool(sandbox, tool_input: dict) -> str:
    """Execute the PostHog tool - called when Claude uses the tool."""

    question = tool_input.get("question", "")
    time_period = tool_input.get("time_period", "30_days")

    print(f"\n🔍 Claude asked: '{question}'")
    print(f"⏱️  Time period: {time_period}")

    # Convert question to query
    hogql_query = question_to_query(question, time_period)
    print(f"🔧 Generated HogQL query")

    # Execute in E2B
    print("☁️  Executing in E2B sandbox...")
    result = execute_posthog_query_in_e2b(sandbox, hogql_query)

    if not result.get("success"):
        return f"Error querying PostHog: {result.get('error', 'Unknown error')}"

    # Format results for Claude
    results = result.get("results", [])
    print(f"✅ Retrieved {len(results)} results\n")

    # Return formatted results
    output = f"Query Results ({len(results)} rows):\n\n"

    if results:
        # Show first 10 results
        for i, row in enumerate(results[:10], 1):
            output += f"{i}. "
            if isinstance(row, dict):
                output += ", ".join(f"{k}: {v}" for k, v in row.items())
            else:
                output += str(row)
            output += "\n"

        if len(results) > 10:
            output += f"\n... and {len(results) - 10} more results"
    else:
        output += "No results found"

    output += f"\n\nQuery executed: {hogql_query[:200]}..."

    return output

# ============================================================================
# CLAUDE AGENT LOOP
# ============================================================================

def run_claude_agent():
    """Run the Claude agent with PostHog tool integration."""

    print("\n" + "=" * 80)
    print("  Claude Agent SDK + PostHog Driver Integration")
    print("=" * 80)

    # Validate API keys
    if ANTHROPIC_API_KEY == 'YOUR_ANTHROPIC_KEY_HERE':
        print("\n❌ Error: ANTHROPIC_API_KEY not set!")
        print("Set it via: export ANTHROPIC_API_KEY='sk-ant-...'")
        return

    if E2B_API_KEY == 'YOUR_E2B_KEY_HERE':
        print("\n❌ Error: E2B_API_KEY not set!")
        print("Set it via: export E2B_API_KEY='e2b_...'")
        return

    # Initialize Claude client
    print("\n🤖 Initializing Claude Agent...")
    anthropic = Anthropic(api_key=ANTHROPIC_API_KEY)

    # Create E2B sandbox
    print("☁️  Creating E2B sandbox...")
    sandbox = Sandbox(api_key=E2B_API_KEY)

    try:
        # Upload PostHog driver to sandbox
        print("📦 Uploading PostHog driver...")
        driver_files = {
            '__init__.py': 'posthog_driver/__init__.py',
            'client.py': 'posthog_driver/client.py',
            'exceptions.py': 'posthog_driver/exceptions.py'
        }

        for remote_name, local_path in driver_files.items():
            with open(local_path, 'r') as f:
                sandbox.files.write(f'/home/user/posthog_driver/{remote_name}', f.read())

        # Install dependencies
        print("📥 Installing dependencies...")
        sandbox.commands.run('pip install requests python-dotenv')

        print("✅ Setup complete!\n")

        # Example conversations
        conversations = [
            "What are the top 5 most common events in the last 30 days?",
            "Where do users drop off in the funnel?",
            "What drives conversion?",
            "Show me the activity distribution of users"
        ]

        for question in conversations:
            print("\n" + "=" * 80)
            print(f"💬 User: {question}")
            print("=" * 80)

            # Create message with tool
            messages = [
                {
                    "role": "user",
                    "content": question
                }
            ]

            # Call Claude
            response = anthropic.messages.create(
                model="claude-3-5-sonnet-20240620",
                max_tokens=4096,
                tools=[POSTHOG_TOOL],
                messages=messages
            )

            # Process response
            while response.stop_reason == "tool_use":
                # Extract tool use
                tool_use = next(block for block in response.content if block.type == "tool_use")

                # Execute tool
                tool_result = execute_posthog_tool(sandbox, tool_use.input)

                # Add assistant response and tool result to messages
                messages.append({
                    "role": "assistant",
                    "content": response.content
                })

                messages.append({
                    "role": "user",
                    "content": [
                        {
                            "type": "tool_result",
                            "tool_use_id": tool_use.id,
                            "content": tool_result
                        }
                    ]
                })

                # Get final response
                response = anthropic.messages.create(
                    model="claude-3-5-sonnet-20240620",
                    max_tokens=4096,
                    tools=[POSTHOG_TOOL],
                    messages=messages
                )

            # Print Claude's final answer
            final_text = next(
                (block.text for block in response.content if hasattr(block, "text")),
                "No response"
            )
            print(f"\n🤖 Claude: {final_text}")
            print("\n" + "-" * 80)

    finally:
        print("\n🧹 Cleaning up sandbox...")
        sandbox.kill()
        print("✅ Done!\n")

# ============================================================================
# MAIN
# ============================================================================

if __name__ == '__main__':
    run_claude_agent()
