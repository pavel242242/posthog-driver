# How to Run the Minimal Example

## What It Is

The **simplest possible** Claude + PostHog integration (163 lines).

Shows the 3-step pattern:
1. Define tool for Claude
2. Call Claude with tool
3. Execute tool in E2B when requested

## Prerequisites

You need 4 API keys:

### 1. Anthropic API Key
- Get from: https://console.anthropic.com
- Format: `sk-ant-...`

### 2. E2B API Key
- Get from: https://e2b.dev/dashboard
- Free tier available
- Format: `e2b_...`

### 3. PostHog API Key (You Already Have)
- Already in your quick_start_e2b.py
- Format: `phx_...`

### 4. PostHog Project ID (You Already Have)
- Already in your quick_start_e2b.py
- Format: `245832`

## Step-by-Step

### 1. Set Environment Variables

```bash
# Claude API (get from https://console.anthropic.com)
export ANTHROPIC_API_KEY="sk-ant-YOUR_KEY_HERE"

# E2B API (get from https://e2b.dev/dashboard)
export E2B_API_KEY="e2b_YOUR_KEY_HERE"

# PostHog (get your API key from PostHog settings)
export POSTHOG_API_KEY="phx_YOUR_KEY_HERE"
export POSTHOG_PROJECT_ID="YOUR_PROJECT_ID"
```

### 2. Install Python Dependencies

```bash
pip install anthropic e2b requests python-dotenv
```

### 3. Run It

```bash
python3 minimal_claude_example.py
```

## What You'll See

```
Minimal Claude + PostHog Integration
==================================================
📦 Setting up sandbox...
✅ Ready!

💬 User: What are the top events in the last week?

🤖 Claude: I'll use the query_posthog tool

📊 Results:
1. $pageview: 1521 events
2. user_logged_in: 507 events
3. subscription_purchased: 89 events
4. movie_buy_complete: 75 events
5. movie_rent_complete: 68 events

🤖 Claude: Here are the top 5 events in the last week:

1. $pageview - 1,521 total events
   This is your most common event, representing page views.

2. user_logged_in - 507 events
   Users are logging in multiple times.

3. subscription_purchased - 89 events
   Strong conversion event.

4. movie_buy_complete - 75 events
   Movie purchases.

5. movie_rent_complete - 68 events
   Movie rentals.

✅ Done!
```

## The Code Structure

```python
# STEP 1: Define tool
TOOL = {
    "name": "query_posthog",
    "description": "Query PostHog analytics data",
    "input_schema": {...}
}

# STEP 2: Tool executor
def execute_tool(sandbox, question):
    # Run PostHog query in E2B sandbox
    script = '''
    from posthog_driver import PostHogClient
    client = PostHogClient(...)
    results = client.query("SELECT ...")
    print(results)
    '''
    result = sandbox.run_code(code=script)
    return result.logs.stdout

# STEP 3: Main loop
def main():
    # Initialize Claude & E2B
    anthropic = Anthropic(api_key=ANTHROPIC_API_KEY)
    sandbox = Sandbox.create(api_key=E2B_API_KEY)

    # Upload PostHog driver
    sandbox.files.write('posthog_driver/__init__.py', ...)

    # Ask Claude
    response = anthropic.messages.create(
        tools=[TOOL],
        messages=[{"role": "user", "content": question}]
    )

    # If Claude uses tool
    if response.stop_reason == "tool_use":
        tool_result = execute_tool(sandbox, ...)

        # Send result back to Claude
        messages.append({"role": "assistant", ...})
        messages.append({"role": "user", "content": tool_result})

        # Get final answer
        final = anthropic.messages.create(...)
```

## Troubleshooting

### "Missing API key"
→ Make sure you've set all 4 environment variables
→ Check with: `echo $ANTHROPIC_API_KEY`

### "Sandbox creation failed"
→ Check E2B API key: https://e2b.dev/dashboard
→ Ensure you have E2B credits

### "Module not found: anthropic"
→ Run: `pip install anthropic e2b`

### "Cannot find posthog_driver files"
→ Make sure you're in the posthog-driver directory
→ Files should be at: `posthog_driver/__init__.py`, etc.

## Don't Have API Keys Yet?

### Option 1: See the Pattern Without Running
```bash
python3 show_3_step_pattern.py
```
This shows the entire pattern visually (no API keys needed).

### Option 2: Run E2B Demo Without Claude
```bash
# Set just E2B key
export E2B_API_KEY="e2b_..."

# Run PostHog in E2B (no Claude)
python3 quick_start_e2b.py
```

### Option 3: Get Free API Keys

**Anthropic Claude:**
1. Go to https://console.anthropic.com
2. Sign up (free credits available)
3. Create API key

**E2B Sandboxes:**
1. Go to https://e2b.dev
2. Sign up (free tier: 100 minutes/month)
3. Dashboard → API Keys

## Next Steps

Once you've run the minimal example:

1. **Understand it:** Read the 163 lines in `minimal_claude_example.py`

2. **See full version:** Run `claude_agent_with_posthog.py` (350 lines)

3. **Read docs:**
   - `CLAUDE_SDK_SUMMARY.md` - Complete explanation
   - `ARCHITECTURE_CLAUDE.md` - Visual diagrams

4. **Customize:**
   - Add more tools
   - Change queries
   - Build your own agent

## Summary

✅ **163 lines** of code
✅ **3 steps**: Define tool → Call Claude → Execute in E2B
✅ **4 API keys** needed
✅ **5 minutes** to run once set up

**File:** `minimal_claude_example.py`
**Demo:** `show_3_step_pattern.py` (no API keys needed)
