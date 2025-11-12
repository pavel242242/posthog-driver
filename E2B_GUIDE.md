# Running Claude Agent SDK with PostHog Driver in E2B

This guide shows you how to run the PostHog driver in E2B sandboxes and access it from your Claude agent.

## Overview

```
Your Machine                    E2B Cloud
─────────────                   ──────────────────────────────────

Claude Agent  ─────────────>   E2B Sandbox (Ubuntu VM)
(Python)                       ├── Python 3.x
                               ├── /home/user/posthog_driver/
                               │   ├── __init__.py
                               │   ├── client.py
                               │   └── exceptions.py
                               └── Your analysis scripts

                               ↓
                               PostHog API (us.posthog.com)
```

## Prerequisites

1. **E2B Account & API Key**
   - Sign up at https://e2b.dev
   - Get your API key from dashboard

2. **PostHog Credentials**
   - Personal API Key (phx_...)
   - Project ID

3. **Python Environment**
   ```bash
   pip install e2b anthropic
   ```

## Method 1: Direct E2B Execution (Simplest)

This method directly executes PostHog queries in E2B without Claude agent integration.

### Step 1: Create E2B Script

```python
# run_in_e2b.py
from e2b import Sandbox
import os

# Your credentials
E2B_API_KEY = os.getenv('E2B_API_KEY')
POSTHOG_API_KEY = os.getenv('POSTHOG_PERSONAL_API_KEY')
POSTHOG_PROJECT_ID = os.getenv('POSTHOG_PROJECT_ID')

def run_posthog_analysis():
    """Run PostHog analysis in E2B sandbox."""

    print("🚀 Creating E2B sandbox...")
    sandbox = Sandbox.create(api_key=E2B_API_KEY)

    try:
        # Upload PostHog driver files
        print("📦 Uploading driver files...")

        driver_files = {
            '__init__.py': 'posthog_driver/__init__.py',
            'client.py': 'posthog_driver/client.py',
            'exceptions.py': 'posthog_driver/exceptions.py'
        }

        for remote_name, local_path in driver_files.items():
            with open(local_path, 'r') as f:
                content = f.read()
                sandbox.files.write(
                    f'/home/user/posthog_driver/{remote_name}',
                    content
                )

        # Install dependencies
        print("📥 Installing dependencies...")
        result = sandbox.commands.run('pip install requests python-dotenv')
        if result.exit_code != 0:
            print(f"⚠️  Install warning: {result.stderr}")

        # Run analysis script
        print("🔍 Running analysis...")

        analysis_script = f"""
import sys
import json
sys.path.insert(0, '/home/user')

from posthog_driver import PostHogClient

# Initialize client
client = PostHogClient(
    api_key='{POSTHOG_API_KEY}',
    project_id='{POSTHOG_PROJECT_ID}'
)

# Query top events
query = '''
SELECT
    event,
    count() as occurrences,
    count(DISTINCT distinct_id) as unique_users
FROM events
WHERE timestamp >= now() - INTERVAL 7 DAY
GROUP BY event
ORDER BY occurrences DESC
LIMIT 10
'''

results = client.query(query)

# Print results
print("\\n=== Top Events (Last 7 Days) ===")
for i, event in enumerate(results, 1):
    event_name = event[0] if isinstance(event, (list, tuple)) else event.get('event')
    occurrences = event[1] if isinstance(event, (list, tuple)) else event.get('occurrences')
    users = event[2] if isinstance(event, (list, tuple)) else event.get('unique_users')
    print(f"{{i}}. {{event_name}}: {{occurrences:,}} events, {{users:,}} users")
"""

        result = sandbox.run_code(
            code=analysis_script,
            envs={
                'PYTHONPATH': '/home/user'
            }
        )

        if result.error:
            print(f"❌ Error: {result.error}")
        else:
            print(f"✅ Output:\n{result.logs.stdout}")

    finally:
        print("🧹 Cleaning up sandbox...")
        sandbox.kill()

if __name__ == '__main__':
    run_posthog_analysis()
```

### Step 2: Set Environment Variables

```bash
export E2B_API_KEY="your_e2b_key"
export POSTHOG_PERSONAL_API_KEY="phx_YOUR_KEY_HERE"
export POSTHOG_PROJECT_ID="245832"
```

### Step 3: Run It

```bash
python run_in_e2b.py
```

**Output:**
```
🚀 Creating E2B sandbox...
📦 Uploading driver files...
📥 Installing dependencies...
🔍 Running analysis...
✅ Output:

=== Top Events (Last 7 Days) ===
1. $pageview: 1,521 events, 243 users
2. user_logged_in: 507 events, 87 users
3. subscription_purchased: 89 events, 80 users
...
🧹 Cleaning up sandbox...
```

## Method 2: Claude Agent SDK Integration

This integrates the PostHog driver as a tool for Claude agents.

### Step 1: Create Agent Tool Definition

```python
# posthog_tools.py
from anthropic import Anthropic
from e2b import Sandbox
import json

def create_posthog_tool():
    """Define PostHog analysis tool for Claude."""
    return {
        "name": "analyze_posthog",
        "description": "Query and analyze PostHog analytics data. Can answer questions about user behavior, events, conversions, and drop-off points.",
        "input_schema": {
            "type": "object",
            "properties": {
                "question": {
                    "type": "string",
                    "description": "The analytics question to answer (e.g., 'What are the top events?' or 'Where do users drop off?')"
                },
                "time_period": {
                    "type": "string",
                    "enum": ["7_days", "30_days", "90_days"],
                    "description": "Time period to analyze",
                    "default": "30_days"
                }
            },
            "required": ["question"]
        }
    }

def execute_posthog_tool(question, time_period="30_days", credentials=None):
    """Execute PostHog analysis in E2B sandbox."""

    # Map time periods to intervals
    intervals = {
        "7_days": "7 DAY",
        "30_days": "30 DAY",
        "90_days": "90 DAY"
    }
    interval = intervals.get(time_period, "30 DAY")

    # Create sandbox
    sandbox = Sandbox.create(api_key=credentials['e2b_api_key'])

    try:
        # Upload driver (simplified - in production, cache this)
        upload_driver(sandbox)

        # Install dependencies
        sandbox.commands.run('pip install requests python-dotenv')

        # Determine query based on question
        if "top events" in question.lower():
            query = f"""
SELECT event, count() as count, count(DISTINCT distinct_id) as users
FROM events
WHERE timestamp >= now() - INTERVAL {interval}
GROUP BY event
ORDER BY count DESC
LIMIT 10
"""
        elif "drop off" in question.lower() or "drop-off" in question.lower():
            query = f"""
SELECT event, count(DISTINCT distinct_id) as users
FROM events
WHERE timestamp >= now() - INTERVAL {interval}
GROUP BY event
ORDER BY users DESC
LIMIT 20
"""
        else:
            # Generic query
            query = f"""
SELECT event, count() as count
FROM events
WHERE timestamp >= now() - INTERVAL {interval}
GROUP BY event
LIMIT 20
"""

        # Execute query
        script = f"""
import sys
import json
sys.path.insert(0, '/home/user')
from posthog_driver import PostHogClient

client = PostHogClient(
    api_key='{credentials['posthog_api_key']}',
    project_id='{credentials['posthog_project_id']}'
)

results = client.query('''{query}''')
print(json.dumps(results, default=str))
"""

        result = sandbox.run_code(code=script, envs={'PYTHONPATH': '/home/user'})

        if result.error:
            return {"error": str(result.error)}

        return {"results": result.logs.stdout, "query": query}

    finally:
        sandbox.kill()

def upload_driver(sandbox):
    """Upload PostHog driver files to sandbox."""
    driver_files = {
        '__init__.py': 'posthog_driver/__init__.py',
        'client.py': 'posthog_driver/client.py',
        'exceptions.py': 'posthog_driver/exceptions.py'
    }

    for remote_name, local_path in driver_files.items():
        with open(local_path, 'r') as f:
            sandbox.files.write(
                f'/home/user/posthog_driver/{remote_name}',
                f.read()
            )
```

### Step 2: Create Claude Agent with Tool

```python
# claude_agent_with_posthog.py
from anthropic import Anthropic
import os
import json
from posthog_tools import create_posthog_tool, execute_posthog_tool

def run_claude_agent():
    """Run Claude agent with PostHog analysis capability."""

    client = Anthropic(api_key=os.getenv('ANTHROPIC_API_KEY'))

    # Credentials for E2B and PostHog
    credentials = {
        'e2b_api_key': os.getenv('E2B_API_KEY'),
        'posthog_api_key': os.getenv('POSTHOG_PERSONAL_API_KEY'),
        'posthog_project_id': os.getenv('POSTHOG_PROJECT_ID')
    }

    # Define tools
    tools = [create_posthog_tool()]

    # Conversation loop
    print("🤖 Claude Agent with PostHog Analysis")
    print("=" * 60)
    print("Ask questions about your PostHog data!")
    print("Examples:")
    print("  - What are the top events in the last 7 days?")
    print("  - Where do users drop off?")
    print("  - Analyze user behavior")
    print("=" * 60 + "\n")

    messages = []

    while True:
        # Get user input
        user_input = input("You: ").strip()
        if not user_input or user_input.lower() in ['exit', 'quit']:
            break

        messages.append({
            "role": "user",
            "content": user_input
        })

        # Call Claude
        response = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=4096,
            tools=tools,
            messages=messages
        )

        # Process response
        while response.stop_reason == "tool_use":
            # Extract tool use
            tool_use = next(
                (block for block in response.content if block.type == "tool_use"),
                None
            )

            if tool_use and tool_use.name == "analyze_posthog":
                print(f"\n🔍 Analyzing PostHog data...")

                # Execute tool
                tool_result = execute_posthog_tool(
                    question=tool_use.input['question'],
                    time_period=tool_use.input.get('time_period', '30_days'),
                    credentials=credentials
                )

                # Add tool result to messages
                messages.append({
                    "role": "assistant",
                    "content": response.content
                })

                messages.append({
                    "role": "user",
                    "content": [{
                        "type": "tool_result",
                        "tool_use_id": tool_use.id,
                        "content": json.dumps(tool_result)
                    }]
                })

                # Get next response
                response = client.messages.create(
                    model="claude-sonnet-4-20250514",
                    max_tokens=4096,
                    tools=tools,
                    messages=messages
                )

        # Display final response
        assistant_message = next(
            (block.text for block in response.content if hasattr(block, 'text')),
            "No response"
        )

        print(f"\nClaude: {assistant_message}\n")

        messages.append({
            "role": "assistant",
            "content": response.content
        })

if __name__ == '__main__':
    run_claude_agent()
```

### Step 3: Run the Agent

```bash
export ANTHROPIC_API_KEY="your_anthropic_key"
export E2B_API_KEY="your_e2b_key"
export POSTHOG_PERSONAL_API_KEY="phx_YOUR_KEY_HERE"
export POSTHOG_PROJECT_ID="245832"

python claude_agent_with_posthog.py
```

**Example Interaction:**

```
🤖 Claude Agent with PostHog Analysis
============================================================
Ask questions about your PostHog data!
Examples:
  - What are the top events in the last 7 days?
  - Where do users drop off?
  - Analyze user behavior
============================================================

You: What are the most common events?

🔍 Analyzing PostHog data...

Claude: Based on the PostHog data, here are the most common events in your
application (last 30 days):

1. $pageview - 1,521 occurrences (243 unique users)
   Most users are browsing pages

2. user_logged_in - 507 occurrences (87 users)
   About 36% of page viewers log in

3. subscription_purchased - 89 occurrences (80 users)
   Strong conversion to paid subscriptions

The data shows a significant drop-off between page views and logins (64% drop).
Would you like me to analyze this funnel in more detail?

You: Yes, analyze the drop-off

🔍 Analyzing PostHog data...

Claude: I've analyzed the user journey and found the critical drop-off point:

📊 Key Finding: 64.2% drop-off from pageview → login

From the data:
- 243 users view pages
- Only 87 users (35.8%) proceed to log in
- 156 users are lost at this step

However, once users log in, conversion is excellent:
- 80 of 87 logged-in users purchase subscriptions (92%)
- Movie purchases show 100% completion rates

Recommendations:
1. Simplify the login process
2. Add social login options (Google, Apple)
3. Consider allowing browsing before requiring login
4. A/B test different login prompts

Would you like me to analyze what drives successful conversions?
```

## Method 3: Using the AgentExecutor (Pre-built)

The simplest method using our pre-built executor.

### Code

```python
# quick_e2b_analysis.py
from agent_executor import PostHogAgentExecutor
from script_templates import TEMPLATES
import os
import json

def main():
    """Quick PostHog analysis using AgentExecutor."""

    with PostHogAgentExecutor(
        e2b_api_key=os.getenv('E2B_API_KEY'),
        posthog_api_key=os.getenv('POSTHOG_PERSONAL_API_KEY'),
        posthog_project_id=os.getenv('POSTHOG_PROJECT_ID')
    ) as executor:

        # Run power user analysis
        print("🔍 Identifying power users...")
        result = executor.execute_template(
            template_name='identify_power_users',
            template_vars={
                'key_event': 'subscription_purchased',
                'min_occurrences': '1',
                'days': '30'
            },
            templates=TEMPLATES
        )

        if result['success']:
            data = json.loads(result['output'])
            print(f"\n✅ Found {data['power_users_count']} power users")
            print("\nTop users:")
            for user in data['power_users'][:5]:
                print(f"  - {user.get('email', user['distinct_id'])}: {user['action_count']} actions")
        else:
            print(f"❌ Error: {result['error']}")

if __name__ == '__main__':
    main()
```

## Accessing E2B Sandboxes

### Option 1: From Your Local Machine

```python
from e2b import Sandbox

# Create sandbox
sandbox = Sandbox.create(api_key="your_e2b_key")

# Run command
result = sandbox.commands.run("python --version")
print(result.stdout)  # Python 3.x.x

# Write file
sandbox.files.write("/home/user/test.py", "print('Hello from E2B!')")

# Run script
result = sandbox.run_code("print('Hello from E2B!')")
print(result.logs.stdout)

# Cleanup
sandbox.kill()
```

### Option 2: From Cloud/Server

Same code works anywhere! E2B is cloud-based, so you can run it from:
- Your laptop
- AWS Lambda
- Google Cloud Functions
- Docker containers
- CI/CD pipelines

### Option 3: Long-running Agent

```python
# Keep sandbox alive for multiple queries
sandbox = Sandbox.create(api_key="your_e2b_key")

# Upload driver once
upload_driver(sandbox)

try:
    # Run multiple analyses
    for question in questions:
        result = sandbox.run_code(f"""
        # Analysis code using pre-uploaded driver
        from posthog_driver import PostHogClient
        client = PostHogClient(...)
        # ...
        """)
        print(result.logs.stdout)
finally:
    sandbox.kill()  # Cleanup when done
```

## Production Deployment

### 1. Environment Variables

```bash
# .env
E2B_API_KEY=e2b_xxxxx
POSTHOG_PERSONAL_API_KEY=phx_xxxxx
POSTHOG_PROJECT_ID=245832
ANTHROPIC_API_KEY=sk-ant-xxxxx
```

### 2. Docker Container

```dockerfile
FROM python:3.11-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install -r requirements.txt

# Copy driver and agent code
COPY posthog_driver/ ./posthog_driver/
COPY agent_executor.py .
COPY script_templates.py .
COPY claude_agent_with_posthog.py .

# Run agent
CMD ["python", "claude_agent_with_posthog.py"]
```

### 3. AWS Lambda

```python
# lambda_handler.py
import json
from agent_executor import PostHogAgentExecutor
from script_templates import TEMPLATES
import os

def lambda_handler(event, context):
    """AWS Lambda handler for PostHog analysis."""

    question = event.get('question', '')
    template = event.get('template', 'get_recent_events')

    with PostHogAgentExecutor(
        e2b_api_key=os.environ['E2B_API_KEY'],
        posthog_api_key=os.environ['POSTHOG_API_KEY'],
        posthog_project_id=os.environ['POSTHOG_PROJECT_ID']
    ) as executor:

        result = executor.execute_template(
            template_name=template,
            template_vars=event.get('vars', {}),
            templates=TEMPLATES
        )

        return {
            'statusCode': 200,
            'body': json.dumps(result)
        }
```

## Troubleshooting

### Issue: "Module not found"

```python
# Make sure path is set correctly
sys.path.insert(0, '/home/user')
```

### Issue: "Connection timeout"

```python
# Increase timeout
client = PostHogClient(timeout=60)
```

### Issue: "Sandbox creation failed"

```python
# Check E2B API key
print(os.getenv('E2B_API_KEY'))  # Should start with 'e2b_'
```

### Issue: "Query returns empty"

```python
# Check time range
query = "SELECT * FROM events WHERE timestamp >= now() - INTERVAL 90 DAY"
```

## Cost Optimization

E2B pricing is based on sandbox uptime. Optimize costs:

1. **Reuse sandboxes** for multiple queries
2. **Kill immediately** when done
3. **Use templates** to avoid redundant setup
4. **Batch queries** when possible

```python
# Good: Reuse sandbox
sandbox = Sandbox.create()
upload_driver(sandbox)  # Once
for query in queries:
    sandbox.run_code(...)  # Multiple times
sandbox.kill()  # Cleanup

# Bad: Create new sandbox each time
for query in queries:
    sandbox = Sandbox.create()  # Expensive!
    upload_driver(sandbox)
    sandbox.run_code(...)
    sandbox.kill()
```

## Summary

**Three ways to access:**

1. **Direct E2B** - Simple script execution
2. **Claude Agent** - Full conversational AI with PostHog access
3. **AgentExecutor** - Pre-built template system

**All methods:**
- ✅ Run securely in isolated cloud VMs
- ✅ Access your PostHog data
- ✅ Auto-cleanup when done
- ✅ Work from anywhere

**Next steps:**
1. Get E2B API key: https://e2b.dev
2. Choose your method above
3. Run the example code
4. Start analyzing!
