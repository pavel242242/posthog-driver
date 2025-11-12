#!/usr/bin/env python3
"""
MINIMAL EXAMPLE: Claude Agent SDK + PostHog Driver

This is the simplest possible integration showing the core pattern.
Just 3 steps:
1. Define tool for Claude
2. Call Claude with tool
3. Execute tool in E2B when Claude requests it
"""

import os
from anthropic import Anthropic
from e2b import Sandbox

# ============================================================================
# STEP 1: Define the tool
# ============================================================================

TOOL = {
    "name": "query_posthog",
    "description": "Query PostHog analytics data",
    "input_schema": {
        "type": "object",
        "properties": {
            "question": {"type": "string", "description": "Analytics question to answer"}
        },
        "required": ["question"]
    }
}

# ============================================================================
# STEP 2: Tool executor
# ============================================================================

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

# Simple query
query = """
SELECT event, count() as total
FROM events
WHERE timestamp >= now() - INTERVAL 7 DAY
GROUP BY event
ORDER BY total DESC
LIMIT 5
"""

results = client.query(query)
for i, row in enumerate(results, 1):
    if isinstance(row, dict):
        print(f"{{i}}. {{row.get('event')}}: {{row.get('total')}} events")
    else:
        print(f"{{i}}. {{row[0]}}: {{row[1]}} events")
'''

    # Write script to file
    sandbox.files.write('/home/user/query_script.py', script)

    # Execute script
    result = sandbox.commands.run('cd /home/user && python3 query_script.py')
    return result.stdout or result.stderr

# ============================================================================
# STEP 3: Run Claude with tool
# ============================================================================

def main():
    print("\nMinimal Claude + PostHog Integration\n" + "=" * 50)

    # Initialize
    anthropic = Anthropic(api_key=os.getenv('ANTHROPIC_API_KEY'))
    sandbox = Sandbox(api_key=os.getenv('E2B_API_KEY'))

    try:
        # Upload PostHog driver
        print("📦 Setting up sandbox...")
        for filename in ['__init__.py', 'client.py', 'exceptions.py']:
            with open(f'posthog_driver/{filename}', 'r') as f:
                sandbox.files.write(f'/home/user/posthog_driver/{filename}', f.read())

        sandbox.commands.run('pip install requests python-dotenv')
        print("✅ Ready!\n")

        # Ask Claude a question
        question = "What are the top events in the last week?"
        print(f"💬 User: {question}\n")

        messages = [{"role": "user", "content": question}]

        # Call Claude with tool
        response = anthropic.messages.create(
            model="claude-sonnet-4-5-20250929",
            max_tokens=1024,
            tools=[TOOL],
            messages=messages
        )

        # If Claude wants to use the tool
        if response.stop_reason == "tool_use":
            tool_use = next(b for b in response.content if b.type == "tool_use")

            print(f"🤖 Claude: I'll use the {tool_use.name} tool\n")

            # Execute tool
            tool_result = execute_tool(sandbox, tool_use.input["question"])
            print(f"📊 Results:\n{tool_result}\n")

            # Send results back to Claude
            messages.append({"role": "assistant", "content": response.content})
            messages.append({
                "role": "user",
                "content": [{
                    "type": "tool_result",
                    "tool_use_id": tool_use.id,
                    "content": tool_result
                }]
            })

            # Get Claude's final answer
            final_response = anthropic.messages.create(
                model="claude-sonnet-4-5-20250929",
                max_tokens=1024,
                tools=[TOOL],
                messages=messages
            )

            # Print answer
            answer = next((b.text for b in final_response.content if hasattr(b, "text")), "")
            print(f"🤖 Claude: {answer}\n")

        else:
            # Claude answered directly
            text = next((b.text for b in response.content if hasattr(b, "text")), "")
            print(f"🤖 Claude: {text}\n")

    finally:
        sandbox.kill()
        print("✅ Done!")

# ============================================================================
# Run it
# ============================================================================

if __name__ == '__main__':
    # Check for required env vars
    required = ['ANTHROPIC_API_KEY', 'E2B_API_KEY', 'POSTHOG_API_KEY', 'POSTHOG_PROJECT_ID']
    missing = [var for var in required if not os.getenv(var)]

    if missing:
        print(f"\n❌ Missing environment variables: {', '.join(missing)}\n")
        print("Set them like this:")
        for var in missing:
            print(f"  export {var}='your_value_here'")
        print()
    else:
        main()
