# Claude + PostHog + E2B Architecture

Visual guide to how all the pieces fit together.

## Complete System Architecture

```
┌───────────────────────────────────────────────────────────────────────┐
│                           USER APPLICATION                             │
│                                                                        │
│  ┌──────────────────────────────────────────────────────────────┐   │
│  │                     FRONTEND / CLI                            │   │
│  │  User asks: "What are the top events?"                       │   │
│  └─────────────────────────┬────────────────────────────────────┘   │
│                            │                                          │
│                            ▼                                          │
│  ┌──────────────────────────────────────────────────────────────┐   │
│  │               CLAUDE AGENT (Anthropic API)                    │   │
│  │                                                               │   │
│  │  1. Receives user question                                   │   │
│  │  2. Sees available tools: [query_posthog]                    │   │
│  │  3. Decides to use query_posthog tool                        │   │
│  │  4. Returns tool_use request:                                │   │
│  │     {                                                         │   │
│  │       "name": "query_posthog",                               │   │
│  │       "input": {                                             │   │
│  │         "question": "What are the top events?",              │   │
│  │         "time_period": "30_days"                             │   │
│  │       }                                                       │   │
│  │     }                                                         │   │
│  └─────────────────────────┬────────────────────────────────────┘   │
│                            │                                          │
│                            ▼                                          │
│  ┌──────────────────────────────────────────────────────────────┐   │
│  │              TOOL EXECUTOR (Your Code)                        │   │
│  │                                                               │   │
│  │  def execute_posthog_tool(sandbox, tool_input):              │   │
│  │      question = tool_input["question"]                       │   │
│  │      time_period = tool_input["time_period"]                 │   │
│  │                                                               │   │
│  │      # 1. Convert question to HogQL                          │   │
│  │      hogql = question_to_hogql(question, time_period)        │   │
│  │                                                               │   │
│  │      # 2. Execute in E2B                                     │   │
│  │      result = execute_in_sandbox(sandbox, hogql)             │   │
│  │                                                               │   │
│  │      # 3. Return formatted results                           │   │
│  │      return format_results(result)                           │   │
│  └─────────────────────────┬────────────────────────────────────┘   │
│                            │                                          │
│                            ▼                                          │
│  ┌──────────────────────────────────────────────────────────────┐   │
│  │              E2B SANDBOX MANAGER                              │   │
│  │                                                               │   │
│  │  sandbox = Sandbox.create(api_key=E2B_API_KEY)               │   │
│  │                                                               │   │
│  │  # Upload driver files                                       │   │
│  │  sandbox.files.write('posthog_driver/__init__.py', ...)      │   │
│  │  sandbox.files.write('posthog_driver/client.py', ...)        │   │
│  │  sandbox.files.write('posthog_driver/exceptions.py', ...)    │   │
│  │                                                               │   │
│  │  # Install dependencies                                      │   │
│  │  sandbox.commands.run('pip install requests')                │   │
│  │                                                               │   │
│  │  # Run query script                                          │   │
│  │  result = sandbox.run_code(code=script)                      │   │
│  └─────────────────────────┬────────────────────────────────────┘   │
│                            │                                          │
└────────────────────────────┼──────────────────────────────────────────┘
                             │
                             ▼
┌────────────────────────────────────────────────────────────────────────┐
│                        E2B CLOUD SANDBOX                               │
│                  (Isolated Ubuntu VM in Cloud)                         │
│                                                                        │
│  ┌──────────────────────────────────────────────────────────────┐   │
│  │  /home/user/                                                  │   │
│  │  ├── posthog_driver/                                          │   │
│  │  │   ├── __init__.py                                          │   │
│  │  │   ├── client.py                                            │   │
│  │  │   └── exceptions.py                                        │   │
│  │  └── query_script.py                                          │   │
│  └──────────────────────────────────────────────────────────────┘   │
│                                                                        │
│  ┌──────────────────────────────────────────────────────────────┐   │
│  │              SCRIPT EXECUTION                                 │   │
│  │                                                               │   │
│  │  from posthog_driver import PostHogClient                    │   │
│  │                                                               │   │
│  │  client = PostHogClient(                                     │   │
│  │      api_key='phx_...',                                      │   │
│  │      project_id='12345'                                      │   │
│  │  )                                                            │   │
│  │                                                               │   │
│  │  results = client.query("""                                  │   │
│  │      SELECT event, count() as total                          │   │
│  │      FROM events                                             │   │
│  │      WHERE timestamp >= now() - INTERVAL 30 DAY              │   │
│  │      GROUP BY event                                          │   │
│  │      ORDER BY total DESC                                     │   │
│  │      LIMIT 10                                                │   │
│  │  """)                                                         │   │
│  │                                                               │   │
│  │  print(json.dumps(results))                                  │   │
│  └─────────────────────────┬────────────────────────────────────┘   │
│                            │                                          │
│                            ▼                                          │
│  ┌──────────────────────────────────────────────────────────────┐   │
│  │           POSTHOG DRIVER (client.py)                          │   │
│  │                                                               │   │
│  │  class PostHogClient:                                        │   │
│  │      def query(self, hogql_query: str):                      │   │
│  │          endpoint = f'/api/projects/{project_id}/query/'     │   │
│  │          response = requests.post(                           │   │
│  │              url=f'{self.api_url}{endpoint}',                │   │
│  │              headers={'Authorization': f'Bearer {api_key}'}, │   │
│  │              json={'query': {                                │   │
│  │                  'kind': 'HogQLQuery',                       │   │
│  │                  'query': hogql_query                        │   │
│  │              }}                                               │   │
│  │          )                                                    │   │
│  │          return response.json()['results']                   │   │
│  └─────────────────────────┬────────────────────────────────────┘   │
│                            │                                          │
└────────────────────────────┼──────────────────────────────────────────┘
                             │
                             │ HTTPS Request
                             │
                             ▼
┌────────────────────────────────────────────────────────────────────────┐
│                         POSTHOG API                                    │
│                    api.posthog.com (or EU)                             │
│                                                                        │
│  POST /api/projects/245832/query/                                     │
│  Authorization: Bearer phx_...                                         │
│  {                                                                     │
│    "query": {                                                          │
│      "kind": "HogQLQuery",                                             │
│      "query": "SELECT event, count()..."                               │
│    }                                                                   │
│  }                                                                     │
│                                                                        │
│  Response:                                                             │
│  {                                                                     │
│    "results": [                                                        │
│      ["$pageview", 1521],                                              │
│      ["user_logged_in", 507],                                          │
│      ["subscription_purchased", 89],                                   │
│      ...                                                               │
│    ]                                                                   │
│  }                                                                     │
└────────────────────────────────────────────────────────────────────────┘
```

## Message Flow Timeline

```
TIME →

0s    User: "What are the top events?"
      │
      ├──▶ Your App: Creates message for Claude
      │
1s    ├──▶ Claude API: Receives question + tool definitions
      │
      │    Claude thinks:
      │    "I need to query analytics data to answer this.
      │     I'll use the query_posthog tool."
      │
2s    ├──▶ Claude API: Returns tool_use response
      │    {
      │      "type": "tool_use",
      │      "name": "query_posthog",
      │      "input": {"question": "What are the top events?", ...}
      │    }
      │
      ├──▶ Your App: Receives tool_use, calls execute_posthog_tool()
      │
3s    ├──▶ E2B: Creates new sandbox (Ubuntu VM)
      │
4s    ├──▶ E2B: Uploads posthog_driver files
      │
5s    ├──▶ E2B: Runs pip install requests
      │
6s    ├──▶ E2B: Executes query script
      │
7s    ├──▶ PostHog API: Receives HogQL query
      │
      │    PostHog processes query against ClickHouse database
      │
8s    ├──▶ PostHog API: Returns results
      │
9s    ├──▶ E2B: Script prints results
      │
      ├──▶ Your App: Receives results from E2B
      │
      ├──▶ Your App: Formats tool_result
      │
      ├──▶ Your App: Sends tool_result back to Claude
      │
10s   ├──▶ Claude API: Receives results, formats answer
      │
      │    Claude thinks:
      │    "I'll format these results in a clear, informative way
      │     and explain what they mean."
      │
11s   ├──▶ Claude API: Returns final text response
      │
      └──▶ User sees: "Here are the top 5 events:
            1. $pageview - 1,521 events from 243 users
            2. user_logged_in - 507 events from 87 users
            ..."
```

## Component Interaction Diagram

```
┌─────────────┐         ┌──────────────┐         ┌─────────────┐
│             │         │              │         │             │
│    User     │────────▶│   Claude     │◀───────│  Tool Defs  │
│             │         │   Agent      │         │  (Schema)   │
└─────────────┘         └──────┬───────┘         └─────────────┘
                               │
                               │ tool_use
                               ▼
                        ┌──────────────┐
                        │     Tool     │
                        │   Executor   │
                        └──────┬───────┘
                               │
                ┌──────────────┼──────────────┐
                │              │              │
                ▼              ▼              ▼
         ┌───────────┐  ┌──────────┐  ┌──────────┐
         │  Question │  │   E2B    │  │  Result  │
         │     to    │  │ Sandbox  │  │ Formatter│
         │   HogQL   │  │ Manager  │  │          │
         └───────────┘  └─────┬────┘  └──────────┘
                              │
                ┌─────────────┼─────────────┐
                ▼             ▼             ▼
         ┌──────────┐  ┌──────────┐  ┌──────────┐
         │  Upload  │  │ Install  │  │   Run    │
         │  Driver  │  │   Deps   │  │  Script  │
         └──────────┘  └──────────┘  └─────┬────┘
                                            │
                                            ▼
                                     ┌──────────┐
                                     │ PostHog  │
                                     │  Driver  │
                                     └─────┬────┘
                                           │
                                           ▼
                                     ┌──────────┐
                                     │ PostHog  │
                                     │   API    │
                                     └──────────┘
```

## File Structure & Responsibilities

```
posthog-driver/
│
├── posthog_driver/              # Core driver (runs in E2B)
│   ├── __init__.py              # Package exports
│   ├── client.py                # PostHogClient class
│   │   ├── query()              # Execute HogQL queries
│   │   ├── get_events()         # Fetch events
│   │   ├── get_cohorts()        # Fetch cohorts
│   │   ├── list_objects()       # Driver contract
│   │   ├── get_fields()         # Driver contract
│   │   └── health_check()       # Connection test
│   └── exceptions.py            # Custom exceptions
│
├── agent_executor.py            # E2B sandbox manager
│   └── PostHogAgentExecutor     # Context manager for E2B
│       ├── __enter__()          # Create sandbox, upload driver
│       ├── execute_script()     # Run code in sandbox
│       ├── execute_template()   # Run pre-built template
│       └── __exit__()           # Cleanup sandbox
│
├── script_templates.py          # Pre-built query scripts
│   ├── CAPTURE_EVENT            # Event tracking
│   ├── GET_RECENT_EVENTS        # Fetch events
│   ├── EXPORT_EVENTS            # Data export
│   ├── IDENTIFY_POWER_USERS     # User segmentation
│   ├── ANALYZE_FUNNEL           # Conversion analysis
│   └── ... (14 total)
│
├── minimal_claude_example.py    # 100-line minimal integration
│   ├── TOOL definition          # Claude tool schema
│   ├── execute_tool()           # Tool executor
│   └── main()                   # Message loop
│
├── claude_agent_with_posthog.py # 350-line complete integration
│   ├── POSTHOG_TOOL             # Full tool definition
│   ├── QUERY_TEMPLATES          # Question → HogQL mapping
│   ├── question_to_query()      # NLP to SQL
│   ├── execute_posthog_query_in_e2b()
│   ├── execute_posthog_tool()   # Tool executor
│   └── run_claude_agent()       # Full agent loop
│
├── quick_start_e2b.py           # E2B demo (no Claude)
│   └── Standalone E2B example
│
└── Documentation
    ├── README.md                # Main docs
    ├── CLAUDE_SDK_SUMMARY.md    # This answer!
    ├── CLAUDE_INTEGRATION.md    # Detailed guide
    ├── ARCHITECTURE_CLAUDE.md   # Architecture diagrams
    ├── E2B_GUIDE.md             # E2B details
    └── GET_STARTED.md           # Quick start
```

## Data Flow

### 1. User Question → HogQL Query

```
Input: "What are the top events?"
  ↓
question_to_query():
  - Pattern match: "top events"
  - Select template: "top_events"
  - Substitute variables: {days: 30}
  ↓
Output:
  SELECT event, count() as total
  FROM events
  WHERE timestamp >= now() - INTERVAL 30 DAY
  GROUP BY event
  ORDER BY total DESC
  LIMIT 10
```

### 2. HogQL Query → PostHog API

```
HogQL Query
  ↓
PostHogClient.query():
  - Wrap in HogQLQuery object
  - Add authentication headers
  - POST to /api/projects/{id}/query/
  ↓
PostHog API:
  - Parse HogQL
  - Execute against ClickHouse
  - Return results
  ↓
Results: [["$pageview", 1521], ["user_logged_in", 507], ...]
```

### 3. Results → Claude → User

```
Raw Results: [["$pageview", 1521], ...]
  ↓
Format for Claude:
  "Query Results (10 rows):
   1. event: $pageview, total: 1521
   2. event: user_logged_in, total: 507
   ..."
  ↓
Claude formats:
  "Here are the top 5 events in the last 30 days:

   1. $pageview - 1,521 events from 243 unique users
      This is your most common event, representing page views.

   2. user_logged_in - 507 events from 87 users
      Users are logging in multiple times, averaging 5.8 logins per user.
   ..."
  ↓
User sees formatted answer
```

## Security & Isolation

```
┌─────────────────────────────────────────┐
│  Your Application (Trusted)             │
│  - Has your API keys                    │
│  - Controls what queries run            │
│  - Manages E2B sandboxes                │
└──────────────┬──────────────────────────┘
               │
               │ Creates sandbox with API keys
               ▼
┌─────────────────────────────────────────┐
│  E2B Sandbox (Isolated)                 │
│  - Temporary Ubuntu VM                  │
│  - No access to your files              │
│  - No access to your network            │
│  - Only has PostHog API key             │
│  - Destroyed after use                  │
│  - Can't persist data                   │
└──────────────┬──────────────────────────┘
               │
               │ HTTPS only
               ▼
┌─────────────────────────────────────────┐
│  PostHog API (External)                 │
│  - Receives queries                     │
│  - Returns data                         │
└─────────────────────────────────────────┘
```

## Performance Characteristics

```
Operation                    Time    Notes
─────────────────────────────────────────────────────
Create E2B sandbox           ~2s     First call only
Upload driver files          ~1s     3 files, ~50KB total
Install dependencies         ~2s     requests, dotenv
Execute query                ~1s     PostHog API call
Format results               <0.1s   Local processing
Claude API call              ~1-2s   Per message
Total (first query)          ~8-10s  Includes setup
Total (subsequent queries)   ~3-4s   Reuse sandbox
Sandbox cleanup              ~1s     Automatic
─────────────────────────────────────────────────────
```

## Cost Breakdown

```
Service         Cost per Query    Notes
────────────────────────────────────────────────────
Claude API      $0.003           Sonnet 3.5 (1K tokens)
E2B Sandbox     $0.00015         Per second (avg 5s)
PostHog API     Free             Within rate limits
Total           ~$0.003          Per query
────────────────────────────────────────────────────
```

## Scaling Considerations

### Single User
- ✅ Create one sandbox per session
- ✅ Reuse sandbox for multiple queries
- ✅ Destroy when done

### Multiple Users
- ✅ One sandbox per user
- ✅ Implement sandbox pooling
- ✅ Set TTL on sandboxes

### High Volume
- ✅ Cache common queries
- ✅ Batch requests where possible
- ✅ Monitor rate limits
- ✅ Consider PostHog caching

## Error Handling

```
┌─────────────────┐
│  User Question  │
└────────┬────────┘
         │
         ▼
┌─────────────────┐     Error: Claude API
│  Claude API     │────▶ Retry with backoff
└────────┬────────┘     Fallback: Return error msg
         │
         ▼
┌─────────────────┐     Error: Sandbox creation
│  E2B Sandbox    │────▶ Retry once
└────────┬────────┘     Fallback: Use existing sandbox
         │
         ▼
┌─────────────────┐     Error: Upload failed
│  Upload Driver  │────▶ Retry upload
└────────┬────────┘     Fallback: Recreate sandbox
         │
         ▼
┌─────────────────┐     Error: Query syntax
│  Execute Query  │────▶ Return error to Claude
└────────┬────────┘     Claude: Reformulate query
         │
         ▼
┌─────────────────┐     Error: Rate limit
│  PostHog API    │────▶ Wait and retry
└────────┬────────┘     Fallback: Queue for later
         │
         ▼
┌─────────────────┐
│  Return Result  │
└─────────────────┘
```

## Monitoring Points

```
1. Claude API
   - Request latency
   - Token usage
   - Error rate

2. E2B Sandboxes
   - Creation time
   - Active sandbox count
   - Cleanup success rate

3. PostHog API
   - Query latency
   - Rate limit hits
   - Error types

4. End-to-End
   - Total request time
   - Success rate
   - User satisfaction
```

---

This architecture provides:
- ✅ Security through isolation
- ✅ Flexibility through tool definitions
- ✅ Scalability through stateless sandboxes
- ✅ Reliability through error handling
- ✅ Observability through monitoring
