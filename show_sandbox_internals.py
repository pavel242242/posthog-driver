#!/usr/bin/env python3
"""
Show what happens inside the E2B sandbox
"""

print("""
╔══════════════════════════════════════════════════════════════════════════╗
║                 INSIDE THE E2B SANDBOX (Step-by-Step)                    ║
╚══════════════════════════════════════════════════════════════════════════╝

═══════════════════════════════════════════════════════════════════════════
STEP 1: Sandbox Creation
═══════════════════════════════════════════════════════════════════════════

Your code:
  sandbox = Sandbox(api_key=E2B_API_KEY)

E2B creates:
  • Fresh Ubuntu 22.04 VM in the cloud
  • Isolated from your local machine
  • No access to your files
  • Temporary (destroyed after use)
  • CPU: 2 cores, RAM: 4GB

Location: E2B Cloud (secure data center)

═══════════════════════════════════════════════════════════════════════════
STEP 2: File Upload (PostHog Driver)
═══════════════════════════════════════════════════════════════════════════

Your code:
  sandbox.files.write('/home/user/posthog_driver/__init__.py', content)
  sandbox.files.write('/home/user/posthog_driver/client.py', content)
  sandbox.files.write('/home/user/posthog_driver/exceptions.py', content)

Inside sandbox:
  /home/user/
  └── posthog_driver/
      ├── __init__.py       (exports PostHogClient)
      ├── client.py         (core driver: query(), get_events(), etc.)
      └── exceptions.py     (error handling)

File sizes:
  • __init__.py: ~0.5KB
  • client.py: ~25KB (main driver logic)
  • exceptions.py: ~2KB

═══════════════════════════════════════════════════════════════════════════
STEP 3: Install Dependencies
═══════════════════════════════════════════════════════════════════════════

Your code:
  sandbox.commands.run('pip install requests python-dotenv')

Inside sandbox:
  $ pip install requests python-dotenv
  Collecting requests...
  Installing collected packages: requests, python-dotenv
  Successfully installed requests-2.31.0 python-dotenv-1.0.0

Installed packages:
  • requests → HTTP library for PostHog API calls
  • python-dotenv → Environment variable handling

═══════════════════════════════════════════════════════════════════════════
STEP 4: Write Query Script
═══════════════════════════════════════════════════════════════════════════

Your code:
  script = '''
  from posthog_driver import PostHogClient
  client = PostHogClient(api_key='...', project_id='...')
  results = client.query("SELECT event, count()...")
  print(results)
  '''
  sandbox.files.write('/home/user/query_script.py', script)

Inside sandbox:
  /home/user/
  ├── posthog_driver/
  │   ├── __init__.py
  │   ├── client.py
  │   └── exceptions.py
  └── query_script.py  ← New script file

═══════════════════════════════════════════════════════════════════════════
STEP 5: Execute Python Script
═══════════════════════════════════════════════════════════════════════════

Your code:
  sandbox.commands.run('cd /home/user && python3 query_script.py')

Inside sandbox terminal:
  user@e2b-sandbox:~$ cd /home/user
  user@e2b-sandbox:/home/user$ python3 query_script.py

Python execution:
  ┌────────────────────────────────────────────────────────────┐
  │ query_script.py                                            │
  ├────────────────────────────────────────────────────────────┤
  │                                                            │
  │ import sys                                                 │
  │ sys.path.insert(0, '/home/user')                          │
  │                                                            │
  │ from posthog_driver import PostHogClient  ← Loads driver  │
  │                                                            │
  │ client = PostHogClient(                                    │
  │     api_key='phx_13WiXxD1fwBRds8YE...',                   │
  │     project_id='245832'                                    │
  │ )                                                          │
  │                                                            │
  │ # Execute HogQL query                                      │
  │ results = client.query("""                                 │
  │     SELECT event, count() as total                         │
  │     FROM events                                            │
  │     WHERE timestamp >= now() - INTERVAL 7 DAY              │
  │     GROUP BY event                                         │
  │     ORDER BY total DESC                                    │
  │     LIMIT 5                                                │
  │ """)                                                       │
  │                                                            │
  │ # Print results                                            │
  │ for row in results:                                        │
  │     print(f"{row[0]}: {row[1]} events")                   │
  │                                                            │
  └────────────────────────────────────────────────────────────┘

═══════════════════════════════════════════════════════════════════════════
STEP 6: PostHog Driver Makes API Call
═══════════════════════════════════════════════════════════════════════════

Inside posthog_driver/client.py:

  def query(self, hogql_query: str):
      endpoint = f'/api/projects/{self.project_id}/query/'

      # Prepare request
      payload = {
          'query': {
              'kind': 'HogQLQuery',
              'query': hogql_query
          }
      }

      # Make HTTPS request
      response = requests.post(
          url=f'https://us.posthog.com{endpoint}',
          headers={
              'Authorization': f'Bearer {self.api_key}',
              'Content-Type': 'application/json'
          },
          json=payload
      )

      return response.json()['results']

Network traffic (from sandbox):
  ┌─────────────────┐         HTTPS          ┌─────────────────┐
  │  E2B Sandbox    │ ───────────────────▶   │  PostHog API    │
  │  (Ubuntu VM)    │                         │  us.posthog.com │
  │                 │ ◀───────────────────    │                 │
  └─────────────────┘      JSON Results       └─────────────────┘

Request:
  POST https://us.posthog.com/api/projects/245832/query/
  Authorization: Bearer phx_13WiXxD1fwBRds8YE...
  {
    "query": {
      "kind": "HogQLQuery",
      "query": "SELECT event, count() as total FROM events..."
    }
  }

Response:
  {
    "results": [
      ["$pageview", 206],
      ["$groupidentify", 200],
      ["user_logged_in", 53],
      ["subscription_purchased", 20],
      ["subscription_intent", 20]
    ]
  }

═══════════════════════════════════════════════════════════════════════════
STEP 7: Print Results (stdout)
═══════════════════════════════════════════════════════════════════════════

Python script continues:
  for i, row in enumerate(results, 1):
      print(f"{i}. {row[0]}: {row[1]} events")

Terminal output (stdout):
  1. $pageview: 206 events
  2. $groupidentify: 200 events
  3. user_logged_in: 53 events
  4. subscription_purchased: 20 events
  5. subscription_intent: 20 events

═══════════════════════════════════════════════════════════════════════════
STEP 8: Capture Output
═══════════════════════════════════════════════════════════════════════════

Your code:
  result = sandbox.commands.run('cd /home/user && python3 query_script.py')
  output = result.stdout

What you receive:
  result.stdout = '''1. $pageview: 206 events
2. $groupidentify: 200 events
3. user_logged_in: 53 events
4. subscription_purchased: 20 events
5. subscription_intent: 20 events'''

  result.exit_code = 0  (success)
  result.stderr = ''     (no errors)

═══════════════════════════════════════════════════════════════════════════
STEP 9: Return to Claude
═══════════════════════════════════════════════════════════════════════════

Your code:
  return result.stdout

Claude receives:
  {
    "type": "tool_result",
    "tool_use_id": "toolu_abc123",
    "content": "1. $pageview: 206 events\\n2. $groupidentify: 200 events..."
  }

Claude processes and formats for user:
  "Based on the PostHog analytics data from the last week,
   here are the top events:

   1. **$pageview** - 206 events (most common)
   2. **$groupidentify** - 200 events
   ..."

═══════════════════════════════════════════════════════════════════════════
STEP 10: Sandbox Cleanup
═══════════════════════════════════════════════════════════════════════════

Your code:
  sandbox.kill()

E2B:
  • Terminates the Ubuntu VM
  • Deletes all files
  • Frees resources
  • No traces left

Total lifecycle: ~10-15 seconds

═══════════════════════════════════════════════════════════════════════════
SECURITY & ISOLATION
═══════════════════════════════════════════════════════════════════════════

What the sandbox CAN do:
  ✅ Run Python code
  ✅ Install packages (pip)
  ✅ Make HTTP requests to PostHog API
  ✅ Read/write files in /home/user
  ✅ Execute shell commands

What the sandbox CANNOT do:
  ❌ Access your local files
  ❌ Access your environment variables (except what you pass)
  ❌ Persist data after termination
  ❌ Access other sandboxes
  ❌ Escape to host system
  ❌ Mine crypto or abuse resources (monitored & limited)

═══════════════════════════════════════════════════════════════════════════
SANDBOX FILE SYSTEM (Final State)
═══════════════════════════════════════════════════════════════════════════

/
├── home/
│   └── user/
│       ├── posthog_driver/
│       │   ├── __init__.py
│       │   ├── client.py
│       │   └── exceptions.py
│       ├── query_script.py
│       └── complex_query.py  (if complex example ran)
├── usr/
│   └── local/
│       └── lib/
│           └── python3.10/
│               └── site-packages/
│                   ├── requests/
│                   └── dotenv/
└── tmp/  (temporary files)

Total disk usage: ~50-100 MB

═══════════════════════════════════════════════════════════════════════════
PERFORMANCE METRICS
═══════════════════════════════════════════════════════════════════════════

Timing breakdown (typical):
  • Sandbox creation:        ~2 seconds
  • File uploads (3 files):  ~0.5 seconds
  • Pip install:             ~2 seconds
  • Script execution:        ~1-2 seconds
  • PostHog API response:    ~0.5-1 seconds
  • Capture output:          ~0.1 seconds
  • Sandbox cleanup:         ~1 second
  ─────────────────────────────────────
  Total:                     ~7-9 seconds

Cost per query:
  • E2B sandbox time: ~$0.00015 (0.15 cents)
  • Claude API call:  ~$0.003 (0.3 cents)
  • PostHog API:      Free (within limits)
  ─────────────────────────────────────
  Total:              ~$0.003 per query

═══════════════════════════════════════════════════════════════════════════
SUMMARY
═══════════════════════════════════════════════════════════════════════════

The E2B sandbox is a:
  🔒 Secure, isolated Ubuntu VM
  ☁️  Running in E2B cloud
  🐍 Executing Python code
  📊 Querying PostHog API
  🔄 Returning results to Claude
  💥 Self-destructing when done

Think of it as a temporary, disposable computer that:
  • Exists only for your query
  • Can't touch your local machine
  • Runs untrusted code safely
  • Cleans up automatically

═══════════════════════════════════════════════════════════════════════════
""")
