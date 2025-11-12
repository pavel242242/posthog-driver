#!/usr/bin/env python3
"""
Claude Generates HogQL Example

This shows Claude dynamically creating HogQL queries based on your questions.
Claude analyzes your question, writes the HogQL, creates a Python script,
and documents the findings.
"""

import os
from anthropic import Anthropic
from e2b import Sandbox

# Tool that lets Claude generate HogQL
TOOL = {
    "name": "run_posthog_analysis",
    "description": """Execute PostHog analytics queries using HogQL.

    HogQL is PostHog's SQL-like query language for product analytics.

    IMPORTANT: A PostHogClient instance named 'client' is already available.
    Do NOT import or initialize PostHogClient - it's provided for you.

    HogQL Examples:
    - SELECT event, count() FROM events WHERE timestamp >= now() - INTERVAL 7 DAY
    - SELECT distinct_id FROM events WHERE event = 'signup' GROUP BY distinct_id
    - SELECT properties.$browser FROM events WHERE event = '$pageview'

    Available in HogQL:
    - Tables: events, persons, sessions, groups
    - Time: now(), INTERVAL N DAY/HOUR/MINUTE
    - Aggregations: count(), count(DISTINCT), avg(), sum(), min(), max()
    - Functions: toDate(), toHour(), toDayOfWeek(), arrayJoin()

    Your Python script should:
    1. Use the provided 'client' variable (already initialized)
    2. Execute HogQL queries with: results = client.query("YOUR HOGQL")
    3. Process and format results
    4. Print insights with good formatting

    Example:
    ```python
    # Query active users (client is already available!)
    query = '''
    SELECT distinct_id, count() as events
    FROM events
    WHERE timestamp >= now() - INTERVAL 7 DAY
    GROUP BY distinct_id
    '''

    results = client.query(query)
    print(f"Found {len(results)} active users")
    for row in results:
        print(f"User {row[0]}: {row[1]} events")
    ```
    """,
    "input_schema": {
        "type": "object",
        "properties": {
            "python_script": {
                "type": "string",
                "description": "Complete Python script with PostHogClient queries and analysis"
            },
            "description": {
                "type": "string",
                "description": "Brief description of what this analysis does"
            }
        },
        "required": ["python_script", "description"]
    }
}

def execute_tool(sandbox, python_script, description):
    """Execute Claude's generated Python script in E2B."""

    print(f"📊 Analysis: {description}\n")

    # Fix any incorrect imports Claude might have generated
    python_script = python_script.replace('from posthog import', 'from posthog_driver import')
    python_script = python_script.replace('import posthog', 'import posthog_driver as posthog')

    # Remove any client initialization Claude added (we do it ourselves)
    lines = python_script.split('\n')
    filtered_lines = []
    skip_next = False
    for line in lines:
        if 'PostHogClient()' in line or 'PostHogClient(' in line:
            continue  # Skip Claude's client initialization
        if 'client = ' in line and 'PostHog' in line:
            continue
        filtered_lines.append(line)

    python_script = '\n'.join(filtered_lines)

    # Write Claude's script to sandbox with proper setup
    full_script = f'''
import sys
sys.path.insert(0, '/home/user')
from posthog_driver import PostHogClient

# Initialize client (we provide this)
client = PostHogClient(
    api_key="{os.getenv('POSTHOG_API_KEY')}",
    project_id="{os.getenv('POSTHOG_PROJECT_ID')}"
)

{python_script}
'''

    sandbox.files.write('/home/user/analysis.py', full_script)

    # Execute it
    result = sandbox.commands.run('cd /home/user && python3 analysis.py')

    return result.stdout or result.stderr

def main():
    print("\n" + "=" * 70)
    print("  Claude Generates HogQL Queries Dynamically")
    print("=" * 70 + "\n")

    # Initialize
    anthropic = Anthropic(api_key=os.getenv('ANTHROPIC_API_KEY'))
    sandbox = Sandbox(api_key=os.getenv('E2B_API_KEY'))

    try:
        # Setup sandbox
        print("📦 Setting up sandbox...")
        for filename in ['__init__.py', 'client.py', 'exceptions.py']:
            with open(f'posthog_driver/{filename}', 'r') as f:
                sandbox.files.write(f'/home/user/posthog_driver/{filename}', f.read())
        sandbox.commands.run('pip install requests python-dotenv -q')
        print("✅ Ready!\n")

        # Ask Claude to analyze with custom questions
        question = """I want to understand user engagement patterns. Please:

1. Find users who have been active in the last 7 days
2. Categorize them by activity level (1-5 events = low, 6-15 = medium, 16+ = high)
3. For each category, show the most common events
4. Identify which events correlate with higher engagement

Write HogQL queries to answer these questions and provide insights."""

        print(f"💬 Question:\n{question}\n")
        print("─" * 70 + "\n")

        messages = [{"role": "user", "content": question}]

        # Call Claude
        print("🤖 Claude is generating HogQL queries...\n")
        response = anthropic.messages.create(
            model="claude-sonnet-4-5-20250929",
            max_tokens=4096,
            tools=[TOOL],
            messages=messages
        )

        # Handle tool use
        while response.stop_reason == "tool_use":
            tool_uses = [b for b in response.content if b.type == "tool_use"]

            print(f"🔍 Claude created {len(tool_uses)} analysis script(s)\n")

            tool_results = []
            for tool_use in tool_uses:
                description = tool_use.input.get("description", "Analysis")
                python_script = tool_use.input.get("python_script", "")

                # Show what Claude generated
                print("─" * 70)
                print("CLAUDE'S GENERATED SCRIPT:")
                print("─" * 70)
                print(python_script[:500] + "..." if len(python_script) > 500 else python_script)
                print("─" * 70)
                print()

                # Execute it
                result = execute_tool(sandbox, python_script, description)
                print(f"📈 Results:\n{result}\n")
                print("─" * 70 + "\n")

                tool_results.append({
                    "type": "tool_result",
                    "tool_use_id": tool_use.id,
                    "content": result
                })

            # Send results back to Claude
            messages.append({"role": "assistant", "content": response.content})
            messages.append({"role": "user", "content": tool_results})

            # Get Claude's analysis
            print("🤖 Claude's Final Analysis:\n")
            response = anthropic.messages.create(
                model="claude-sonnet-4-5-20250929",
                max_tokens=4096,
                tools=[TOOL],
                messages=messages
            )

        # Print final answer
        answer = next((b.text for b in response.content if hasattr(b, "text")), "")
        print(answer)
        print()

    finally:
        sandbox.kill()
        print("\n✅ Analysis complete!\n")

if __name__ == '__main__':
    main()
