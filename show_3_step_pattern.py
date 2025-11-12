#!/usr/bin/env python3
"""
DEMONSTRATION: The 3-Step Pattern
Shows how Claude Agent SDK integrates with PostHog Driver
"""

print("\n" + "=" * 70)
print("  CLAUDE AGENT SDK + POSTHOG DRIVER: 3-STEP PATTERN")
print("=" * 70 + "\n")

# ============================================================================
# STEP 1: Define the Tool
# ============================================================================
print("┌" + "─" * 68 + "┐")
print("│  STEP 1: Define the Tool (What Claude Can Do)                     │")
print("└" + "─" * 68 + "┘\n")

print("This tells Claude: 'You can query PostHog analytics'\n")

print("Tool Definition:")
print("─" * 70)
print("""
TOOL = {
    "name": "query_posthog",
    "description": "Query PostHog analytics data",
    "input_schema": {
        "type": "object",
        "properties": {
            "question": {"type": "string"}
        },
        "required": ["question"]
    }
}
""")
print("─" * 70 + "\n")

# ============================================================================
# STEP 2: Call Claude with Tool
# ============================================================================
print("┌" + "─" * 68 + "┐")
print("│  STEP 2: Call Claude with Tool (Give Claude the Ability)          │")
print("└" + "─" * 68 + "┘\n")

print("💬 User asks: 'What are the top events?'\n")

print("Your code calls Claude API:")
print("─" * 70)
print("""
from anthropic import Anthropic

anthropic = Anthropic(api_key=ANTHROPIC_API_KEY)

response = anthropic.messages.create(
    model='claude-3-5-sonnet-20241022',
    tools=[TOOL],  # ← Claude can now use query_posthog
    messages=[{
        'role': 'user',
        'content': 'What are the top events?'
    }]
)
""")
print("─" * 70 + "\n")

print("🤖 Claude receives:")
print("   • User question: 'What are the top events?'")
print("   • Available tools: [query_posthog]\n")

print("🤖 Claude thinks:")
print("   'I need analytics data to answer this question.")
print("    I have access to query_posthog tool.")
print("    I'll use it!'\n")

print("🤖 Claude responds with tool_use:")
print("─" * 70)
print("""
{
  "stop_reason": "tool_use",
  "content": [
    {
      "type": "tool_use",
      "name": "query_posthog",
      "input": {
        "question": "What are the top events?"
      }
    }
  ]
}
""")
print("─" * 70 + "\n")

# ============================================================================
# STEP 3: Execute Tool
# ============================================================================
print("┌" + "─" * 68 + "┐")
print("│  STEP 3: Execute Tool in E2B (When Claude Requests It)            │")
print("└" + "─" * 68 + "┘\n")

print("Your code receives Claude's tool_use request\n")

print("Check if Claude wants to use a tool:")
print("─" * 70)
print("""
if response.stop_reason == "tool_use":
    # Claude wants to use the tool!
    tool_use = response.content[0]

    # Extract the question
    question = tool_use.input['question']
    # → 'What are the top events?'
""")
print("─" * 70 + "\n")

print("☁️  Execute in E2B sandbox:")
print("─" * 70)
print("""
from e2b import Sandbox

# 1. Create isolated cloud sandbox
sandbox = Sandbox.create(api_key=E2B_API_KEY)

# 2. Upload PostHog driver files
sandbox.files.write('/home/user/posthog_driver/__init__.py', ...)
sandbox.files.write('/home/user/posthog_driver/client.py', ...)

# 3. Execute query script
script = '''
from posthog_driver import PostHogClient

client = PostHogClient(
    api_key='phx_...',
    project_id='12345'
)

results = client.query(\"\"\"
    SELECT event, count() as total
    FROM events
    WHERE timestamp >= now() - INTERVAL 7 DAY
    GROUP BY event
    ORDER BY total DESC
    LIMIT 5
\"\"\")

print(results)
'''

result = sandbox.run_code(code=script)
# → result.logs.stdout contains the query results
""")
print("─" * 70 + "\n")

print("📊 Results flow:")
print("""
  E2B Sandbox executes script
    ↓
  PostHog Driver queries PostHog API
    ↓
  PostHog API returns data
    ↓
  Script prints results
    ↓
  Your code receives output
    ↓
  Format as tool_result
""")
print()

print("Send tool result back to Claude:")
print("─" * 70)
print("""
# Add assistant's tool use to messages
messages.append({
    'role': 'assistant',
    'content': response.content
})

# Add tool result
messages.append({
    'role': 'user',
    'content': [{
        'type': 'tool_result',
        'tool_use_id': tool_use.id,
        'content': result.logs.stdout  # Query results
    }]
})

# Get Claude's final answer
final_response = anthropic.messages.create(
    model='claude-3-5-sonnet-20241022',
    tools=[TOOL],
    messages=messages
)
""")
print("─" * 70 + "\n")

# ============================================================================
# FINAL OUTPUT
# ============================================================================
print("┌" + "─" * 68 + "┐")
print("│  FINAL OUTPUT: What User Sees                                     │")
print("└" + "─" * 68 + "┘\n")

print("🤖 Claude's formatted answer:\n")
print("─" * 70)
print("""
Based on the query results, here are the top 5 events in the
last 7 days:

1. $pageview - 1,521 total events from 243 unique users
   This is your most common event, representing page views across
   your application.

2. user_logged_in - 507 events from 87 unique users
   Users are logging in multiple times, averaging about 5.8 logins
   per user.

3. subscription_purchased - 89 events from 80 unique users
   Strong conversion event with most users purchasing once.

4. movie_buy_complete - 75 events from 52 users
   Movie purchases are averaging 1.4 per user.

5. movie_rent_complete - 68 events from 45 users
   Similar pattern to purchases.
""")
print("─" * 70 + "\n")

# ============================================================================
# SUMMARY
# ============================================================================
print("\n" + "=" * 70)
print("  SUMMARY: The 3-Step Pattern")
print("=" * 70 + "\n")

print("✅ STEP 1: Define Tool")
print("   └─ Tell Claude what it can do via tool definition\n")

print("✅ STEP 2: Call Claude with Tool")
print("   ├─ Pass tool definition to Claude")
print("   └─ Claude decides when to use the tool\n")

print("✅ STEP 3: Execute Tool When Requested")
print("   ├─ Check: if response.stop_reason == 'tool_use'")
print("   ├─ Execute query in E2B sandbox")
print("   ├─ Send results back to Claude")
print("   └─ Claude formats final answer\n")

print("=" * 70 + "\n")

print("🎯 Key Advantages:")
print("   • User asks in plain English")
print("   • Claude decides when to query PostHog")
print("   • Execution is secure (isolated E2B sandbox)")
print("   • Claude formats results intelligently\n")

print("📁 See the real code in:")
print("   • minimal_claude_example.py (100 lines)")
print("   • claude_agent_with_posthog.py (350 lines, full agent)\n")

print("📖 Read more:")
print("   • CLAUDE_SDK_SUMMARY.md (complete explanation)")
print("   • ARCHITECTURE_CLAUDE.md (visual diagrams)\n")
