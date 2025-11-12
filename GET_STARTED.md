# Get Started with E2B + PostHog Driver

## What You'll Do

Run PostHog analytics in a secure cloud sandbox (E2B) in **3 simple steps**.

## Step 1: Get E2B API Key

1. Go to **https://e2b.dev**
2. Sign up (free tier available)
3. Go to **Dashboard** → **API Keys**
4. Copy your API key (starts with `e2b_`)

## Step 2: Set Your API Key

### Option A: Environment Variable (Recommended)

```bash
export E2B_API_KEY="e2b_your_key_here"
```

### Option B: Edit the Script

Open `quick_start_e2b.py` and replace:
```python
E2B_API_KEY = 'YOUR_E2B_KEY_HERE'
```

With:
```python
E2B_API_KEY = 'e2b_your_actual_key'
```

## Step 3: Run It!

```bash
python3 quick_start_e2b.py
```

**That's it!** The script will:
1. ✅ Create cloud sandbox
2. ✅ Upload PostHog driver
3. ✅ Install dependencies
4. ✅ Run analysis on your PostHog data
5. ✅ Show results
6. ✅ Clean up automatically

## What You'll See

```
╔════════════════════════════════════════════════════════════════════════════╗
║                    PostHog in E2B - Quick Start                            ║
╚════════════════════════════════════════════════════════════════════════════╝

🚀 Step 1: Creating E2B sandbox...
   ✓ Sandbox created!

📦 Step 2: Uploading PostHog driver to sandbox...
   ✓ Driver uploaded!

📥 Step 3: Installing dependencies...
   ✓ Dependencies installed!

🔍 Step 4: Running PostHog analysis...

══════════════════════════════════════════════════════════════════════════════
  PostHog Analysis Running in E2B Sandbox
══════════════════════════════════════════════════════════════════════════════

🔧 Connecting to PostHog...
✓ Connected to: Default project

══════════════════════════════════════════════════════════════════════════════
QUERY 1: Top Events (Last 7 Days)
══════════════════════════════════════════════════════════════════════════════

Event                                    Total Events    Unique Users
──────────────────────────────────────────────────────────────────────────────
 1. $pageview                                    1,521             243
 2. user_logged_in                                 507              87
 3. subscription_purchased                          89              80
 4. movie_buy_complete                              75              52
 5. movie_rent_complete                             68              45

✓ Found 10 events

══════════════════════════════════════════════════════════════════════════════
QUERY 2: User Activity Distribution
══════════════════════════════════════════════════════════════════════════════

Activity Level                               Number of Users
──────────────────────────────────────────────────────────────────────────────
High activity (20+ events)                                        47
Medium activity (5-19 events)                                    112
Low activity (1-4 events)                                         84
──────────────────────────────────────────────────────────────────────────────
                                                                 243

✓ Analyzed 243 users

══════════════════════════════════════════════════════════════════════════════
QUERY 3: Purchase Conversion Funnel
══════════════════════════════════════════════════════════════════════════════

Step                                 Users       Conversion Rate
──────────────────────────────────────────────────────────────────────────────
Viewed pages                           243                    -
Logged in                               87                35.8%
Purchased subscription                  80                92.0%

══════════════════════════════════════════════════════════════════════════════
✅ Analysis Complete!
══════════════════════════════════════════════════════════════════════════════

🧹 Step 5: Cleaning up sandbox...
   ✓ Sandbox destroyed!
```

## What Just Happened?

Your PostHog data was analyzed in a **secure, isolated cloud environment**:

- ✅ **No installation** needed on your machine
- ✅ **Isolated** from your files and system
- ✅ **Automatic cleanup** - no traces left
- ✅ **Secure** - runs in sandboxed Ubuntu VM
- ✅ **Fast** - results in seconds

## Next Steps

### 1. Try Different Queries

Edit the `ANALYSIS_SCRIPT` in `quick_start_e2b.py` to run your own queries:

```python
query = '''
SELECT
    event,
    properties.$current_url as url,
    count() as visits
FROM events
WHERE event = '$pageview'
    AND timestamp >= now() - INTERVAL 7 DAY
GROUP BY event, url
ORDER BY visits DESC
LIMIT 20
'''
```

### 2. Integrate with Claude

See `E2B_GUIDE.md` → "Method 2: Claude Agent SDK Integration"

### 3. Use Pre-built Templates

```python
from agent_executor import PostHogAgentExecutor
from script_templates import TEMPLATES

with PostHogAgentExecutor(
    e2b_api_key='e2b_xxx',
    posthog_api_key='phx_xxx',
    posthog_project_id='12345'
) as executor:
    result = executor.execute_template(
        template_name='identify_power_users',
        template_vars={'key_event': 'purchase', 'min_occurrences': '5', 'days': '30'},
        templates=TEMPLATES
    )
    print(result['output'])
```

### 4. Build a Full Agent

```python
# See claude_agent_with_posthog.py in E2B_GUIDE.md
# Gives Claude the ability to query PostHog conversationally:

You: "What are the top events?"
Claude: [Queries PostHog in E2B] "Here are the top events..."

You: "Where do users drop off?"
Claude: [Analyzes funnel] "64% drop off at login..."
```

## Troubleshooting

### "Failed to create sandbox"

- Check your E2B API key is correct
- Make sure you have E2B credits
- Visit https://e2b.dev/dashboard

### "Cannot find posthog_driver"

- Make sure you're in the `posthog-driver` directory
- Files should be at `posthog_driver/__init__.py`, etc.

### "Query error"

- Check your PostHog API key has query permissions
- Verify project ID is correct
- Try increasing time range (90 days instead of 7)

## Resources

- **E2B Docs:** https://e2b.dev/docs
- **E2B Dashboard:** https://e2b.dev/dashboard
- **PostHog API Docs:** https://posthog.com/docs/api
- **Full Guide:** See `E2B_GUIDE.md` in this directory

## Summary

✅ You just ran analytics in the cloud with **3 commands**:
1. Get E2B key
2. Set environment variable
3. Run `python3 quick_start_e2b.py`

🎉 **That's it!** Your PostHog driver is now running securely in E2B sandboxes.
