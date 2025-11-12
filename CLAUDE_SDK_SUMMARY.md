# Claude Agent SDK Integration - Complete Summary

## What You Asked For

> "how could this use claude agent sdk?"

Here's the complete answer with working code examples.

## The Answer: 3 Integration Methods

### Method 1: Minimal Integration (Start Here)

**File:** `minimal_claude_example.py`

This 100-line script shows the core pattern:

```bash
python3 minimal_claude_example.py
```

**What it does:**
1. Defines a tool Claude can use
2. Claude decides to use the tool
3. Tool executes PostHog query in E2B sandbox
4. Claude receives results and formats answer

**When to use:** Learning, prototyping, simple use cases

---

### Method 2: Complete Conversation Agent

**File:** `claude_agent_with_posthog.py`

This 350-line script shows a full conversational agent:

```bash
python3 claude_agent_with_posthog.py
```

**What it does:**
- Runs multiple questions in sequence
- Converts natural language to HogQL automatically
- Handles tool use loop properly
- Shows formatted results

**Sample conversation:**
```
User: "What are the top events?"
→ Claude uses query_posthog tool
→ Executes HogQL query in E2B
→ "Here are the top 5 events..."

User: "Where do users drop off?"
→ Claude uses query_posthog tool again
→ Analyzes funnel data
→ "64% drop off at login..."
```

**When to use:** Building conversational analytics interface

---

### Method 3: Production Components

**Files:**
- `agent_executor.py` - Reusable E2B sandbox manager
- `script_templates.py` - 14 pre-built query templates

```python
from agent_executor import PostHogAgentExecutor
from script_templates import TEMPLATES

with PostHogAgentExecutor(...) as executor:
    result = executor.execute_template(
        template_name='identify_power_users',
        template_vars={'key_event': 'purchase', 'days': '30'}
    )
```

**When to use:** Production apps, multiple queries, reusable components

---

## Quick Start

### 1. Set API Keys

```bash
export ANTHROPIC_API_KEY="sk-ant-..."
export E2B_API_KEY="e2b_..."
export POSTHOG_API_KEY="phx_..."
export POSTHOG_PROJECT_ID="12345"
```

### 2. Run Example

```bash
# Simplest
python3 minimal_claude_example.py

# Full featured
python3 claude_agent_with_posthog.py

# Quick demo (no Claude, just E2B)
python3 quick_start_e2b.py
```

---

## How The Integration Works

### Architecture

```
┌─────────────────────────────────────────────────────────┐
│  Your Application                                        │
│                                                          │
│  ┌──────────────┐                                       │
│  │   Claude     │  "What are the top events?"          │
│  │   Agent      │────────────┐                          │
│  │   (Anthropic │            │                          │
│  │   API)       │            ▼                          │
│  └──────────────┘   ┌────────────────────┐             │
│                      │  query_posthog     │             │
│                      │  tool definition   │             │
│                      └─────────┬──────────┘             │
│                                │                         │
│                                ▼                         │
│                      ┌────────────────────┐             │
│                      │  Tool Executor     │             │
│                      │  (Your Code)       │             │
│                      └─────────┬──────────┘             │
│                                │                         │
│                                ▼                         │
│  ┌─────────────────────────────────────────────┐       │
│  │  E2B Sandbox (Isolated Cloud VM)            │       │
│  │                                              │       │
│  │  ┌─────────────────────────────────┐        │       │
│  │  │  PostHog Driver                 │        │       │
│  │  │  • client.py                    │        │       │
│  │  │  • query(hogql)                 │        │       │
│  │  │  • get_events()                 │        │       │
│  │  └────────────┬────────────────────┘        │       │
│  │               │                              │       │
│  │               ▼                              │       │
│  │  ┌─────────────────────────────────┐        │       │
│  │  │  PostHog API                    │        │       │
│  │  │  api.posthog.com                │        │       │
│  │  └─────────────────────────────────┘        │       │
│  └─────────────────────────────────────────────┘       │
│                                                          │
└─────────────────────────────────────────────────────────┘
```

### Message Flow

```
1. User asks question
   ↓
2. Claude receives question + tool definition
   ↓
3. Claude decides: "I should use query_posthog tool"
   ↓
4. Claude returns tool_use response with parameters
   ↓
5. Your code receives tool_use
   ↓
6. Your code:
   - Creates E2B sandbox
   - Uploads PostHog driver
   - Executes query
   - Returns results
   ↓
7. You send tool_result back to Claude
   ↓
8. Claude receives results and formats answer
   ↓
9. User sees final answer
```

### Code Flow

```python
# Step 1: Define tool
TOOL = {
    "name": "query_posthog",
    "description": "Query PostHog analytics",
    "input_schema": {...}
}

# Step 2: Call Claude with tool
response = anthropic.messages.create(
    tools=[TOOL],
    messages=[{"role": "user", "content": "What are the top events?"}]
)

# Step 3: Check if Claude wants to use tool
if response.stop_reason == "tool_use":
    tool_use = next(b for b in response.content if b.type == "tool_use")

    # Step 4: Execute tool in E2B
    sandbox = Sandbox.create()
    result = execute_in_sandbox(sandbox, tool_use.input)

    # Step 5: Send result back to Claude
    messages.append({"role": "assistant", "content": response.content})
    messages.append({
        "role": "user",
        "content": [{
            "type": "tool_result",
            "tool_use_id": tool_use.id,
            "content": result
        }]
    })

    # Step 6: Get Claude's final answer
    final_response = anthropic.messages.create(
        tools=[TOOL],
        messages=messages
    )
```

---

## Key Files Reference

### Documentation
- **CLAUDE_INTEGRATION.md** - Complete integration guide
- **GET_STARTED.md** - 3-step quick start
- **E2B_GUIDE.md** - E2B sandbox details
- **README.md** - Full documentation

### Runnable Examples
- **minimal_claude_example.py** - 100-line minimal example
- **claude_agent_with_posthog.py** - 350-line complete agent
- **quick_start_e2b.py** - E2B demo (no Claude needed)

### Core Components
- **posthog_driver/client.py** - Driver implementation
- **agent_executor.py** - E2B sandbox manager
- **script_templates.py** - Pre-built query templates

### Testing & Demo
- **show_demo.py** - Interactive demo of all features
- **live_analysis.py** - Real data analysis example
- **tests/** - 40 passing tests

---

## Example Output

When you run `claude_agent_with_posthog.py`:

```
════════════════════════════════════════════════════════════
  Claude Agent SDK + PostHog Driver Integration
════════════════════════════════════════════════════════════

🤖 Initializing Claude Agent...
☁️  Creating E2B sandbox...
📦 Uploading PostHog driver...
📥 Installing dependencies...
✅ Setup complete!

════════════════════════════════════════════════════════════
💬 User: What are the top 5 most common events in the last 30 days?
════════════════════════════════════════════════════════════

🔍 Claude asked: 'What are the top 5 most common events in the last 30 days?'
⏱️  Time period: 30_days
🔧 Generated HogQL query
☁️  Executing in E2B sandbox...
✅ Retrieved 10 results

🤖 Claude: Based on the query results, here are the top 5 most
common events in the last 30 days:

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

────────────────────────────────────────────────────────────

════════════════════════════════════════════════════════════
💬 User: Where do users drop off in the funnel?
════════════════════════════════════════════════════════════

🔍 Claude asked: 'Where do users drop off in the funnel?'
⏱️  Time period: 30_days
🔧 Generated HogQL query
☁️  Executing in E2B sandbox...
✅ Retrieved 10 results

🤖 Claude: Looking at the user funnel, there's a significant
drop-off point:

The main drop-off occurs between page views and login:
- $pageview: 243 users
- user_logged_in: 87 users
- Drop-off rate: 64.2%

This means that out of every 100 visitors who view pages, only
36 actually log in. This is your primary conversion barrier.

However, once users log in, conversion is excellent:
- Logged in: 87 users
- Subscription purchased: 80 users
- Conversion: 92%

Recommendation: Focus on improving the page view → login
conversion. Consider:
- Simplifying login flow
- Adding social login options
- Offering value before requiring login
- A/B testing different login prompts

────────────────────────────────────────────────────────────
```

---

## Advantages

### For Users
- ✅ Ask questions in plain English
- ✅ No need to learn HogQL/SQL
- ✅ Conversational analytics
- ✅ Claude explains results in context

### For Developers
- ✅ Secure execution (E2B sandboxes)
- ✅ No local dependencies
- ✅ Easy to integrate
- ✅ Reusable components

### For Operations
- ✅ Isolated execution
- ✅ Automatic cleanup
- ✅ Rate limit handling
- ✅ Error recovery

---

## Next Steps

1. **Try minimal example:**
   ```bash
   python3 minimal_claude_example.py
   ```

2. **Try full agent:**
   ```bash
   python3 claude_agent_with_posthog.py
   ```

3. **Read detailed guide:**
   ```bash
   cat CLAUDE_INTEGRATION.md
   ```

4. **Customize for your needs:**
   - Add more tools
   - Customize query templates
   - Build web UI
   - Deploy to production

---

## Common Questions

### Q: Do I need Claude to use this driver?
**A:** No! The driver works standalone. Claude integration is optional.

```python
# Use without Claude
from posthog_driver import PostHogClient
client = PostHogClient(...)
results = client.query("SELECT * FROM events")
```

### Q: Can I run this without E2B?
**A:** Yes, but E2B provides security and isolation.

```python
# Use locally (not recommended for production)
from posthog_driver import PostHogClient
client = PostHogClient(...)
```

### Q: What if I want to add more tools?
**A:** Define additional tools and handlers:

```python
TOOLS = [
    POSTHOG_TOOL,
    EXPORT_COHORT_TOOL,
    CREATE_INSIGHT_TOOL,
]
```

### Q: Can Claude chain multiple queries?
**A:** Yes! Claude can use the tool multiple times:

```
User: "Find power users and export them"
→ Claude: Uses query_posthog to find power users
→ Claude: Uses export_cohort to export list
→ Done!
```

---

## Support

- **Issues:** Check `troubleshooting` section in README.md
- **Examples:** See `examples/` directory
- **Tests:** Run `python -m pytest tests/`
- **Docs:** Read CLAUDE_INTEGRATION.md for details

---

## Summary

You now have **3 ways** to integrate PostHog with Claude Agent SDK:

1. **Minimal** (`minimal_claude_example.py`) - Learn the pattern
2. **Complete** (`claude_agent_with_posthog.py`) - Build conversational interface
3. **Production** (`agent_executor.py` + templates) - Scale to production

All running securely in E2B sandboxes with automatic cleanup.

**Start here:** `python3 minimal_claude_example.py`
