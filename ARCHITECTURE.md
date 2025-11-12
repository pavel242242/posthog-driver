# PostHog Driver Architecture - Visual Guide

## System Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                     Claude AI Agent                             │
│  "Find users at risk of churning"                               │
└────────────────────┬────────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────────┐
│                  PostHog Driver (This Package)                  │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │  Driver Contract                                         │   │
│  │  • list_objects() → [events, insights, persons, ...]    │   │
│  │  • get_fields('events') → {event, timestamp, ...}       │   │
│  │  • query(hogql) → Execute analytics queries             │   │
│  └──────────────────────────────────────────────────────────┘   │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │  PostHog Operations                                      │   │
│  │  • capture_event() - Track user actions                 │   │
│  │  • get_cohorts() - User segmentation                    │   │
│  │  • export_events() - Data export                        │   │
│  │  • evaluate_flag() - Feature flags                      │   │
│  └──────────────────────────────────────────────────────────┘   │
└────────────────────┬────────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────────┐
│                    E2B Sandbox (Optional)                       │
│  Isolated Ubuntu VM in Cloud                                    │
│  • Driver uploaded to /home/user/posthog_driver/               │
│  • Dependencies installed (requests, python-dotenv)             │
│  • Scripts execute securely                                     │
│  • 14 pre-built templates available                             │
└────────────────────┬────────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────────┐
│                  PostHog API (US/EU Cloud)                      │
│  ┌──────────────────────┬──────────────────────┐               │
│  │  Analytics Endpoints │  Event Capture       │               │
│  │  /api/query/         │  /i/v0/e/           │               │
│  │  /api/insights/      │  /batch/            │               │
│  │  /api/cohorts/       │                      │               │
│  │  /api/experiments/   │                      │               │
│  └──────────────────────┴──────────────────────┘               │
└─────────────────────────────────────────────────────────────────┘
```

## Data Flow

### 1. Query Analytics (Data Out)

```
Agent Question: "Who are our power users?"
         │
         ▼
┌─────────────────────────────────────┐
│  Driver constructs HogQL query:    │
│                                     │
│  SELECT distinct_id, count()       │
│  FROM events                        │
│  WHERE timestamp >= now() - 7d     │
│  GROUP BY distinct_id              │
│  HAVING count() > 100              │
└────────────┬────────────────────────┘
             │
             ▼
┌─────────────────────────────────────┐
│  POST /api/projects/123/query/     │
│  Authorization: Bearer phx_xxx      │
│  Body: {query: {...}}              │
└────────────┬────────────────────────┘
             │
             ▼
┌─────────────────────────────────────┐
│  PostHog processes query            │
│  • Queries ClickHouse database      │
│  • Executes HogQL                   │
│  • Returns results                  │
└────────────┬────────────────────────┘
             │
             ▼
┌─────────────────────────────────────┐
│  Driver returns to agent:           │
│  [                                  │
│    {distinct_id: "user_123",        │
│     count: 342},                    │
│    {distinct_id: "user_456",        │
│     count: 289},                    │
│    ...                              │
│  ]                                  │
└────────────┬────────────────────────┘
             │
             ▼
Agent Response: "Found 23 power users with 100+ actions in last 7 days"
```

### 2. Track Events (Data In)

```
App Event: User clicks "Export" button
         │
         ▼
┌─────────────────────────────────────┐
│  Driver captures event:             │
│                                     │
│  client.capture_event(              │
│    event="Button Click",           │
│    distinct_id="user_123",         │
│    properties={                     │
│      "button": "export",           │
│      "page": "/dashboard"          │
│    }                                │
│  )                                  │
└────────────┬────────────────────────┘
             │
             ▼
┌─────────────────────────────────────┐
│  POST https://us.i.posthog.com     │
│       /i/v0/e/                     │
│  {                                  │
│    "api_key": "phc_xxx",           │
│    "event": "Button Click",        │
│    "distinct_id": "user_123",      │
│    "properties": {...}             │
│  }                                  │
└────────────┬────────────────────────┘
             │
             ▼
┌─────────────────────────────────────┐
│  PostHog ingests event              │
│  • Stores in ClickHouse             │
│  • Available for queries instantly  │
│  • Updates dashboards/insights      │
└─────────────────────────────────────┘
```

### 3. E2B Sandbox Execution

```
Agent needs to analyze churn risk
         │
         ▼
┌─────────────────────────────────────┐
│  AgentExecutor creates E2B sandbox  │
│  • Spin up Ubuntu VM                │
│  • Upload driver files              │
│  • Install dependencies             │
└────────────┬────────────────────────┘
             │
             ▼
┌─────────────────────────────────────┐
│  Execute template:                  │
│  'identify_churn_risk'              │
│  Variables:                         │
│    inactive_days: 7                 │
│    lookback_days: 30                │
└────────────┬────────────────────────┘
             │
             ▼
┌─────────────────────────────────────┐
│  Sandbox runs Python script:        │
│  import posthog_driver              │
│  client = PostHogClient()           │
│  results = client.query(...)        │
│  print(json.dumps(results))         │
└────────────┬────────────────────────┘
             │
             ▼
┌─────────────────────────────────────┐
│  Output returned to agent:          │
│  {                                  │
│    "churn_risk_count": 23,         │
│    "users": [...]                  │
│  }                                  │
└────────────┬────────────────────────┘
             │
             ▼
┌─────────────────────────────────────┐
│  Sandbox cleaned up                 │
│  • VM destroyed                     │
│  • Resources freed                  │
└─────────────────────────────────────┘
```

## Component Breakdown

### PostHogClient Class

```python
PostHogClient
├── Initialization
│   ├── api_url (US/EU/self-hosted)
│   ├── api_key (Personal API key)
│   ├── project_id
│   ├── project_api_key (for event capture)
│   └── HTTP session with auth headers
│
├── Driver Contract Methods
│   ├── list_objects() → 8 entity types
│   ├── get_fields(name) → Schema for entity
│   └── query(hogql) → Execute queries
│
├── Event Tracking
│   ├── capture_event(event, distinct_id, properties)
│   └── capture_batch([events])
│
├── Analytics
│   ├── get_insights(type, limit)
│   ├── get_events(filters)
│   └── export_events(start_date, end_date)
│
├── Segmentation
│   ├── get_cohorts()
│   ├── create_cohort(name, filters)
│   └── get_persons(cohort_id)
│
├── Experimentation
│   ├── get_feature_flags()
│   ├── evaluate_flag(key, distinct_id)
│   └── get_experiments()
│
└── Utilities
    ├── health_check()
    ├── get_project_info()
    └── Context manager support
```

### AgentExecutor Class

```python
PostHogAgentExecutor
├── __init__(e2b_key, posthog_key, project_id)
│   └── Store credentials
│
├── __enter__()
│   ├── Create E2B sandbox
│   ├── Upload driver files
│   │   ├── /home/user/posthog_driver/__init__.py
│   │   ├── /home/user/posthog_driver/client.py
│   │   └── /home/user/posthog_driver/exceptions.py
│   └── Install dependencies (pip install requests)
│
├── execute_script(code, description)
│   ├── Replace API key placeholders
│   ├── Set environment variables
│   ├── Run code in sandbox
│   └── Return {success, output, error}
│
├── execute_template(name, vars, templates)
│   ├── Get template from registry
│   ├── Substitute variables
│   └── Execute via execute_script()
│
└── __exit__()
    └── Kill sandbox (cleanup)
```

## Workflow Examples

### Example 1: Feature Impact Analysis

```
User: "Did the new dashboard increase engagement?"
  │
  ▼
Agent: Uses driver to query event trends
  │
  ▼
client.query("""
    SELECT
        toDate(timestamp) as date,
        count(DISTINCT distinct_id) as users,
        count() as actions
    FROM events
    WHERE event = 'Dashboard View'
      AND properties.version = 'new'
      AND timestamp >= now() - INTERVAL 14 DAY
    GROUP BY date
    ORDER BY date
""")
  │
  ▼
Results: Daily user counts and action counts
  │
  ▼
Agent: "New dashboard has 23% more daily active users
        and 41% more actions/user compared to old version"
```

### Example 2: Churn Prediction

```
User: "Who might churn soon?"
  │
  ▼
Agent: Uses 'identify_churn_risk' template in E2B
  │
  ▼
E2B Sandbox:
  • Upload driver
  • Install deps
  • Run query:
    - Find users active 2-4 weeks ago
    - But NOT active in last 7 days
  • Return list
  │
  ▼
Results: 23 users at risk
  │
  ▼
Agent: "Found 23 users showing churn signals.
        Would you like me to:
        1. Export list for email campaign
        2. Analyze their last actions
        3. Create retention cohort"
```

### Example 3: A/B Test Analysis

```
User: "Did the green button outperform the blue one?"
  │
  ▼
Agent: Queries experiment results
  │
  ▼
client.get_experiments()
  │
  ▼
Results:
  Control (blue): 23% conversion (1000 users)
  Variant (green): 28% conversion (1050 users)
  Probability: 98% improvement
  Significant: Yes
  │
  ▼
Agent: "Green button performs 21.7% better with
        98% confidence. Recommend rolling out to 100%."
```

## File Structure

```
posthog-driver/
│
├── posthog_driver/              # Core package
│   ├── __init__.py             # Exports (PostHogClient, exceptions)
│   ├── client.py               # Main PostHogClient class (700 lines)
│   └── exceptions.py           # 7 exception types
│
├── agent_executor.py           # E2B sandbox integration (175 lines)
├── script_templates.py         # 14 pre-built templates (450 lines)
│
├── examples/                   # Usage examples (1,100 lines)
│   ├── basic_usage.py         # Driver contract demo
│   ├── persona_workflows.py   # 10 persona workflows
│   └── e2b_integration.py     # 6 E2B examples
│
├── tests/                      # Test suite (900 lines)
│   ├── test_driver.py         # 28 unit tests
│   └── test_examples.py       # 12 integration tests
│
├── README.md                   # Complete documentation
├── PLAN.md                     # Implementation plan
├── TEST_RESULTS.md            # Test report
├── ARCHITECTURE.md            # This file
├── requirements.txt           # Dependencies
└── .env.example               # Configuration template
```

## Authentication Flow

```
User provides credentials
         │
         ▼
┌─────────────────────────────────────┐
│  POSTHOG_PERSONAL_API_KEY          │  For analytics queries
│  (phx_xxxxxxxxxxxx)                │  → Insights, cohorts, experiments
│                                     │
│  POSTHOG_PROJECT_API_KEY           │  For event capture
│  (phc_xxxxxxxxxxxx)                │  → /i/v0/e/, /batch/
│                                     │
│  POSTHOG_PROJECT_ID                │  Your project identifier
│  (12345)                            │
│                                     │
│  POSTHOG_API_URL                   │  Regional endpoint
│  (https://us.posthog.com)          │  → US, EU, or self-hosted
└────────────┬────────────────────────┘
             │
             ▼
┌─────────────────────────────────────┐
│  Client creates HTTP session        │
│  Headers:                           │
│    Authorization: Bearer phx_xxx    │
│    Content-Type: application/json   │
└────────────┬────────────────────────┘
             │
             ▼
All API requests authenticated automatically
```

## Rate Limits

```
PostHog API Rate Limits:

┌─────────────────────────────────────┐
│  Analytics Endpoints                │
│  /api/insights/                     │
│  /api/cohorts/                      │
│  /api/persons/                      │
│                                     │
│  Limits: 240/minute, 1200/hour     │
└─────────────────────────────────────┘

┌─────────────────────────────────────┐
│  Query Endpoint                     │
│  /api/query/ (HogQL)               │
│                                     │
│  Limits: 2400/hour                 │
└─────────────────────────────────────┘

┌─────────────────────────────────────┐
│  Event Capture                      │
│  /i/v0/e/                          │
│  /batch/                            │
│                                     │
│  Limits: NONE                       │
│  (Unlimited event ingestion)        │
└─────────────────────────────────────┘

Driver handles:
• Rate limit detection (429 status)
• Automatic retries (configurable)
• Clear error messages
```

## Error Handling

```
API Call
    │
    ▼
Try to execute
    │
    ├─► 401 Unauthorized → AuthenticationError
    │                       "Invalid API key"
    │
    ├─► 403 Forbidden → AuthenticationError
    │                    "Check API key permissions"
    │
    ├─► 404 Not Found → ObjectNotFoundError
    │                    "Resource not found"
    │
    ├─► 429 Too Many → RateLimitError
    │                   "Rate limit exceeded"
    │                   "Use batch exports for large datasets"
    │
    ├─► Network Error → ConnectionError
    │                    "Failed to connect after N retries"
    │
    ├─► Timeout → PostHogError
    │              "Request timeout after 30s"
    │
    └─► Other 4xx/5xx → PostHogError
                         "API error: [details]"
```

## Summary

The PostHog Driver is a **complete integration layer** that:

1. **Abstracts** PostHog's API into a simple driver contract
2. **Enables** AI agents to discover and query data dynamically
3. **Provides** 14 pre-built templates for common operations
4. **Supports** secure execution in E2B cloud sandboxes
5. **Handles** authentication, rate limiting, and errors
6. **Includes** persona-aware workflows for real-world use cases

**Technical Foundation:**
- 3,364 lines of Python
- 40/40 tests passing
- Full documentation
- Production-ready

**Use Cases:**
- AI agents analyze user behavior
- Automated churn prediction
- Dynamic feature rollouts
- Cross-platform data analysis
- Autonomous analytics reporting
