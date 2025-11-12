# Claude Agent SDK Integration Guide

This guide shows **exactly** how the PostHog driver integrates with Claude Agent SDK.

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│                      Your Application                        │
│                                                              │
│  ┌────────────────┐         ┌─────────────────────┐        │
│  │  Claude Agent  │────────▶│  PostHog Tool Def   │        │
│  │     (API)      │         │  (query_posthog)    │        │
│  └────────┬───────┘         └──────────┬──────────┘        │
│           │                            │                     │
│           │ Tool use request          │ Executes in E2B    │
│           ▼                            ▼                     │
│  ┌────────────────────────────────────────────┐            │
│  │         E2B Sandbox (Isolated VM)          │            │
│  │                                             │            │
│  │  ┌──────────────────────────────────┐     │            │
│  │  │    PostHog Driver                │     │            │
│  │  │  - client.py                     │     │            │
│  │  │  - query(hogql)                  │     │            │
│  │  │  - list_objects()                │     │            │
│  │  │  - get_fields()                  │     │            │
│  │  └──────────┬───────────────────────┘     │            │
│  │             │                               │            │
│  │             ▼                               │            │
│  │  ┌──────────────────────────────────┐     │            │
│  │  │      PostHog API                 │     │            │
│  │  │  api.posthog.com/api/projects/   │     │            │
│  │  └──────────────────────────────────┘     │            │
│  └────────────────────────────────────────────┘            │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

## Key Integration Points

### 1. Tool Definition

Claude needs to know the tool exists and what it does:

```python
from anthropic import Anthropic

POSTHOG_TOOL = {
    "name": "query_posthog",
    "description": "Query PostHog analytics to answer questions about user behavior",
    "input_schema": {
        "type": "object",
        "properties": {
            "question": {
                "type": "string",
                "description": "The analytics question (e.g., 'What are the top events?')"
            },
            "time_period": {
                "type": "string",
                "enum": ["7_days", "30_days", "90_days"]
            }
        },
        "required": ["question"]
    }
}
```

### 2. Claude API Call with Tool

Pass the tool definition when calling Claude:

```python
anthropic = Anthropic(api_key=ANTHROPIC_API_KEY)

response = anthropic.messages.create(
    model="claude-3-5-sonnet-20241022",
    max_tokens=4096,
    tools=[POSTHOG_TOOL],  # ← Register the tool
    messages=[
        {"role": "user", "content": "What are the top events?"}
    ]
)
```

### 3. Tool Execution Handler

When Claude calls the tool, execute it in E2B:

```python
from e2b import Sandbox

def execute_posthog_tool(sandbox, tool_input):
    """Called when Claude invokes query_posthog tool."""

    question = tool_input["question"]
    time_period = tool_input.get("time_period", "30_days")

    # Convert question to HogQL query
    hogql = question_to_hogql(question, time_period)

    # Execute in E2B sandbox
    script = f'''
import sys
sys.path.insert(0, '/home/user')
from posthog_driver import PostHogClient

client = PostHogClient(
    api_key="{POSTHOG_API_KEY}",
    project_id="{POSTHOG_PROJECT_ID}"
)

results = client.query("""{hogql}""")
print(results)
'''

    result = sandbox.run_code(code=script)
    return result.logs.stdout
```

### 4. Tool Use Loop

Handle Claude's tool use requests:

```python
while response.stop_reason == "tool_use":
    # Extract tool use block
    tool_use = next(block for block in response.content if block.type == "tool_use")

    # Execute the tool
    tool_result = execute_posthog_tool(sandbox, tool_use.input)

    # Send result back to Claude
    messages.append({"role": "assistant", "content": response.content})
    messages.append({
        "role": "user",
        "content": [{
            "type": "tool_result",
            "tool_use_id": tool_use.id,
            "content": tool_result
        }]
    })

    # Get Claude's final response
    response = anthropic.messages.create(
        model="claude-3-5-sonnet-20241022",
        max_tokens=4096,
        tools=[POSTHOG_TOOL],
        messages=messages
    )
```

## Complete Example

See `claude_agent_with_posthog.py` for a full working example:

```bash
# Set your API keys
export ANTHROPIC_API_KEY="sk-ant-..."
export E2B_API_KEY="e2b_..."

# Run the agent
python3 claude_agent_with_posthog.py
```

### What It Does

1. **User asks:** "What are the top events?"

2. **Claude decides:** "I'll use the query_posthog tool"
   ```json
   {
     "name": "query_posthog",
     "input": {
       "question": "What are the top events?",
       "time_period": "30_days"
     }
   }
   ```

3. **Your code:**
   - Converts question to HogQL
   - Uploads PostHog driver to E2B sandbox
   - Executes query in isolated environment
   - Returns results

4. **Claude receives:** Query results and formats answer

5. **User sees:** "Here are the top 5 events in the last 30 days:
   1. $pageview (1,521 events, 243 users)
   2. user_logged_in (507 events, 87 users)
   ..."

## Why E2B?

The PostHog driver runs in E2B sandboxes for:

- **Security:** Isolated from your main application
- **Safety:** Can't access local files or environment
- **Reproducibility:** Same environment every time
- **No dependencies:** No need to install PostHog driver locally
- **Easy cleanup:** Sandbox destroyed after use

## Message Flow

```
┌─────────┐                                    ┌─────────┐
│  User   │                                    │ Claude  │
└────┬────┘                                    └────┬────┘
     │                                              │
     │ "What are the top events?"                  │
     ├────────────────────────────────────────────▶│
     │                                              │
     │                              Tool use needed │
     │                         {name: query_posthog}│
     │◀─────────────────────────────────────────────┤
     │                                              │
┌────▼─────────────────────┐                      │
│  Execute in E2B Sandbox  │                      │
│  1. Upload driver        │                      │
│  2. Run query            │                      │
│  3. Get results          │                      │
└────┬─────────────────────┘                      │
     │                                              │
     │ Tool result: [query results]                │
     ├────────────────────────────────────────────▶│
     │                                              │
     │                      Formatted answer        │
     │                  "Top 5 events are..."       │
     │◀─────────────────────────────────────────────┤
     │                                              │
```

## Key Code Files

1. **claude_agent_with_posthog.py** - Complete working example
2. **agent_executor.py** - PostHogAgentExecutor helper class
3. **script_templates.py** - Pre-built query templates
4. **posthog_driver/client.py** - Core driver implementation

## Advantages of This Architecture

### 1. **Natural Language Interface**
Users can ask questions in plain English instead of writing HogQL:
- ✅ "Where do users drop off?"
- ✅ "What drives conversion?"
- ❌ "SELECT event, count(DISTINCT distinct_id)..."

### 2. **Secure Execution**
Queries run in isolated E2B sandboxes:
- Can't access your local files
- Can't modify your system
- Automatic cleanup after execution

### 3. **Flexible Integration**
Three ways to integrate:

#### Option A: Direct (Most Control)
```python
# You handle everything
sandbox = Sandbox.create()
# Upload driver, run queries, handle results
```

#### Option B: AgentExecutor (Easier)
```python
from agent_executor import PostHogAgentExecutor

with PostHogAgentExecutor(...) as executor:
    result = executor.execute_template('identify_power_users', {...})
```

#### Option C: Claude Tools (Most User-Friendly)
```python
# Let Claude decide when to query PostHog
anthropic.messages.create(
    tools=[POSTHOG_TOOL],
    messages=[{"role": "user", "content": "Analyze my product"}]
)
```

## Extending the Integration

### Add More Tools

```python
POSTHOG_TOOLS = [
    {
        "name": "query_posthog",
        "description": "Query analytics data",
        # ...
    },
    {
        "name": "export_cohort",
        "description": "Export a user cohort to CSV",
        "input_schema": {
            "type": "object",
            "properties": {
                "cohort_name": {"type": "string"},
                "format": {"type": "string", "enum": ["csv", "json"]}
            }
        }
    },
    {
        "name": "create_insight",
        "description": "Create a saved insight in PostHog",
        # ...
    }
]
```

### Add Context from Other Sources

```python
def execute_posthog_tool(sandbox, tool_input, context):
    """Enhanced tool with additional context."""

    # Get user's company info
    company = context.get("company")

    # Customize query based on context
    if company == "enterprise":
        time_period = "90_days"  # More data for enterprise
    else:
        time_period = "30_days"

    # Execute query...
```

### Chain Multiple Tools

```python
# Claude can chain tools together:
# 1. query_posthog → Get power users
# 2. export_cohort → Export them
# 3. send_email → Send marketing campaign
```

## Testing

Test the integration:

```bash
# Run unit tests
python -m pytest tests/test_driver.py

# Test Claude integration
python claude_agent_with_posthog.py

# Test specific query
python -c "
from agent_executor import PostHogAgentExecutor
with PostHogAgentExecutor(...) as executor:
    result = executor.execute_script('''
        from posthog_driver import PostHogClient
        client = PostHogClient(...)
        print(client.query('SELECT count() FROM events'))
    ''')
    print(result)
"
```

## Troubleshooting

### "Tool not executed"
- Check tool name matches exactly
- Verify tool is in `tools` parameter
- Check Claude API response for errors

### "Sandbox failed"
- Verify E2B_API_KEY is correct
- Check E2B credits: https://e2b.dev/dashboard
- Ensure driver files exist in local directory

### "Query error"
- Verify POSTHOG_API_KEY has query permissions
- Check project ID is correct
- Try query directly in PostHog UI first

### "Rate limit"
- PostHog limits: 240 requests/min (analytics), 2400/hour (queries)
- Add delays between queries
- Cache results when possible

## Production Checklist

- [ ] Store API keys securely (not in code)
- [ ] Add error handling for tool execution
- [ ] Implement rate limiting
- [ ] Add logging for debugging
- [ ] Cache common queries
- [ ] Set timeout for E2B sandboxes
- [ ] Monitor E2B usage and costs
- [ ] Add authentication for user access
- [ ] Validate tool inputs
- [ ] Handle PostHog API changes

## Next Steps

1. **Run the example:** `python3 claude_agent_with_posthog.py`
2. **Customize queries:** Edit `QUERY_TEMPLATES` in the script
3. **Add more tools:** Define additional tool functions
4. **Build UI:** Create a chat interface for users
5. **Deploy:** Host on cloud with proper auth

## Resources

- **Claude Tool Use Docs:** https://docs.anthropic.com/claude/docs/tool-use
- **E2B Documentation:** https://e2b.dev/docs
- **PostHog API Reference:** https://posthog.com/docs/api
- **Example Code:** See `claude_agent_with_posthog.py`
