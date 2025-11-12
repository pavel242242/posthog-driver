# PostHog Driver for Claude Agent SDK

A Python client library for integrating PostHog analytics with AI agents running in E2B sandboxes. This driver enables AI agents to perform analytics tracking, data export/ETL, and information lookup from PostHog's Product OS.

## Features

- **Driver Contract Implementation**: Standard 3-method interface (`list_objects`, `get_fields`, `query`) for dynamic discovery
- **Analytics Tracking**: Real-time event capture and batch ingestion
- **Data Export/ETL**: Bulk event export for data warehouse sync
- **HogQL Queries**: SQL-like analytics queries with full PostHog data access
- **Cohort Management**: User segmentation and behavioral cohorts
- **Feature Flags & Experiments**: A/B test evaluation and flag management
- **Persona-Aware**: Built-in understanding of typical PostHog user workflows
- **E2B Sandbox Ready**: Designed for isolated cloud execution environments

## Table of Contents

- [Installation](#installation)
- [Quick Start](#quick-start)
- [Claude Agent SDK Integration](#claude-agent-sdk-integration) ⭐ **New**
- [Configuration](#configuration)
- [Driver Contract](#driver-contract)
- [Core Operations](#core-operations)
- [E2B Sandbox Integration](#e2b-sandbox-integration)
- [Persona-Based Workflows](#persona-based-workflows)
- [API Reference](#api-reference)
- [Examples](#examples)
- [Troubleshooting](#troubleshooting)

## Installation

### Local Development

```bash
cd posthog-driver
pip install -r requirements.txt
```

### E2B Sandbox

The driver is designed to be uploaded to E2B sandboxes:

```python
from e2b import Sandbox

sandbox = Sandbox.create(api_key=e2b_api_key)

# Upload driver files
sandbox.files.write('/home/user/posthog_driver/__init__.py', content)
sandbox.files.write('/home/user/posthog_driver/client.py', content)
sandbox.files.write('/home/user/posthog_driver/exceptions.py', content)

# Install dependencies
sandbox.commands.run('pip install requests python-dotenv')
```

## Quick Start

### Basic Usage

```python
from posthog_driver import PostHogClient

# Initialize client
client = PostHogClient(
    api_key='phx_your_personal_api_key',
    project_id='12345',
    project_api_key='phc_your_project_api_key'  # For event capture
)

# Query recent events
events = client.get_events(
    event_name="User Signup",
    after="2024-01-01",
    limit=100
)

# Run HogQL query
results = client.query("""
    SELECT event, count() as count
    FROM events
    WHERE timestamp >= '2024-01-01'
    GROUP BY event
    ORDER BY count DESC
    LIMIT 10
""")

# Export data for ETL
exported_events = client.export_events(
    start_date="2024-01-01",
    end_date="2024-01-31"
)
```

### With E2B Sandbox

```python
from agent_executor import PostHogAgentExecutor

# Use context manager for automatic cleanup
with PostHogAgentExecutor(
    e2b_api_key='your_e2b_key',
    posthog_api_key='phx_your_key',
    posthog_project_id='12345'
) as executor:
    # Execute script in sandbox
    result = executor.execute_script("""
import sys
sys.path.insert(0, '/home/user')

from posthog_driver import PostHogClient

client = PostHogClient()
events = client.get_events(limit=10)
print(f"Found {len(events)} events")
    """)

    print(result['output'])
```

## Claude Agent SDK Integration

This driver integrates seamlessly with Claude Agent SDK, allowing Claude to query PostHog analytics conversationally.

### How It Works

```
User: "What are the top events?"
  ↓
Claude: [Uses query_posthog tool]
  ↓
Your code: Executes in E2B sandbox
  ↓
PostHog: Returns data
  ↓
Claude: "Here are the top 5 events: $pageview (1,521), user_logged_in (507)..."
```

### Minimal Example

```python
from anthropic import Anthropic
from e2b import Sandbox

# 1. Define tool for Claude
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

# 2. Call Claude with tool
anthropic = Anthropic(api_key=ANTHROPIC_API_KEY)
response = anthropic.messages.create(
    model="claude-3-5-sonnet-20241022",
    tools=[TOOL],
    messages=[{"role": "user", "content": "What are the top events?"}]
)

# 3. When Claude calls the tool, execute in E2B
if response.stop_reason == "tool_use":
    sandbox = Sandbox.create(api_key=E2B_API_KEY)
    # Upload driver, run query, return results
```

### Complete Examples

Three levels of integration:

1. **Minimal** - `minimal_claude_example.py` - Just the basics (~100 lines)
2. **Complete** - `claude_agent_with_posthog.py` - Full conversation loop (~350 lines)
3. **Production** - `agent_executor.py` + `script_templates.py` - Reusable components

Run a complete example:

```bash
# Set API keys
export ANTHROPIC_API_KEY="sk-ant-..."
export E2B_API_KEY="e2b_..."
export POSTHOG_API_KEY="phx_..."
export POSTHOG_PROJECT_ID="12345"

# Run
python3 claude_agent_with_posthog.py
```

### What You'll See

```
💬 User: What are the top events?

🔍 Claude asked: 'What are the top events?'
🔧 Generated HogQL query
☁️  Executing in E2B sandbox...
✅ Retrieved 10 results

🤖 Claude: Based on the query results, here are the top 5 events
in the last 30 days:

1. $pageview - 1,521 events from 243 unique users
2. user_logged_in - 507 events from 87 users
3. subscription_purchased - 89 events from 80 users
4. movie_buy_complete - 75 events from 52 users
5. movie_rent_complete - 68 events from 45 users
```

### Key Integration Points

**1. Tool Definition** - Tell Claude about the PostHog tool:
```python
POSTHOG_TOOL = {
    "name": "query_posthog",
    "description": "Query PostHog analytics...",
    "input_schema": {...}
}
```

**2. Tool Execution** - Run queries in E2B when Claude requests:
```python
def execute_posthog_tool(sandbox, tool_input):
    # Upload driver to sandbox
    # Convert question to HogQL
    # Run query
    # Return results
```

**3. Message Loop** - Handle tool use responses:
```python
while response.stop_reason == "tool_use":
    tool_result = execute_posthog_tool(...)
    # Send result back to Claude
    response = anthropic.messages.create(...)
```

See **[CLAUDE_INTEGRATION.md](CLAUDE_INTEGRATION.md)** for complete documentation.

### Why This Architecture?

✅ **Natural Language** - Users ask questions in plain English, not SQL
✅ **Secure** - Queries run in isolated E2B sandboxes
✅ **Flexible** - Claude decides when to query PostHog
✅ **Composable** - Chain multiple tools together
✅ **Production-Ready** - Handles errors, rate limits, timeouts

## Configuration

### Environment Variables

Create a `.env` file (see `.env.example`):

```bash
# Required
POSTHOG_PERSONAL_API_KEY=phx_your_personal_api_key_here
POSTHOG_PROJECT_ID=12345

# Required for event capture and feature flag evaluation
POSTHOG_PROJECT_API_KEY=phc_your_project_api_key_here

# Optional (defaults to US cloud)
POSTHOG_API_URL=https://us.posthog.com

# For E2B execution
E2B_API_KEY=your_e2b_api_key_here
```

### Getting PostHog API Keys

1. **Personal API Key** (for analytics/queries):
   - Go to PostHog → Account Settings → Personal API Keys
   - Click "Create Personal API Key"
   - Set appropriate scopes (recommended: project:read, insight:read, cohort:read)

2. **Project API Key** (for event capture):
   - Go to Project Settings → General Settings
   - Find "Project API Key" section

3. **Project ID**:
   - Found in Project Settings or in the URL: `app.posthog.com/project/[PROJECT_ID]`

### Regional Configuration

**US Cloud** (default):
```python
client = PostHogClient(api_url='https://us.posthog.com', ...)
```

**EU Cloud**:
```python
client = PostHogClient(api_url='https://eu.posthog.com', ...)
```

**Self-Hosted**:
```python
client = PostHogClient(api_url='https://your-instance.com', ...)
```

## Driver Contract

The PostHog driver implements the standard 3-method driver contract:

### 1. list_objects()

Discover available PostHog entity types:

```python
objects = client.list_objects()
# Returns: ['events', 'insights', 'persons', 'cohorts', 'feature_flags',
#           'sessions', 'annotations', 'experiments']
```

### 2. get_fields(object_name)

Get schema/field definitions for an entity:

```python
event_schema = client.get_fields('events')
# Returns: {
#     'event': {'type': 'string', 'description': 'Event name'},
#     'timestamp': {'type': 'datetime', 'description': 'When event occurred'},
#     'distinct_id': {'type': 'string', 'description': 'User identifier'},
#     ...
# }
```

### 3. query(hogql_query)

Execute HogQL queries (PostHog's SQL-like language):

```python
results = client.query("""
    SELECT * FROM events
    WHERE event = 'User Signup'
    AND timestamp >= '2024-01-01'
    LIMIT 100
""")
```

## Core Operations

### Event Tracking

#### Single Event Capture

```python
client.capture_event(
    event="Feature Used",
    distinct_id="user_123",
    properties={
        "feature_name": "dark_mode",
        "enabled": True
    }
)
```

#### Batch Event Capture

```python
client.capture_batch([
    {
        "event": "Page View",
        "distinct_id": "user_123",
        "properties": {"page": "/home"}
    },
    {
        "event": "Button Click",
        "distinct_id": "user_123",
        "properties": {"button": "signup"}
    }
])
```

### Analytics & Insights

#### List Insights

```python
# Get all insights
insights = client.get_insights()

# Filter by type
funnels = client.get_insights(insight_type='FUNNELS')
trends = client.get_insights(insight_type='TRENDS')
```

#### Query Events

```python
events = client.get_events(
    event_name="Purchase Completed",
    after="2024-01-01",
    before="2024-01-31",
    limit=1000
)
```

### Data Export (ETL)

```python
# Export events for data warehouse sync
events = client.export_events(
    start_date="2024-01-01",
    end_date="2024-01-31",
    event_names=["User Signup", "Purchase Completed"]
)

# Export to S3, BigQuery, etc.
upload_to_warehouse(events)
```

### Cohort Management

```python
# List all cohorts
cohorts = client.get_cohorts()

# Create new cohort
client.create_cohort(
    name="Power Users",
    description="Users with 100+ events in last 30 days",
    filters={
        "properties": {
            "type": "behavioral",
            "event_count_operator": "gte",
            "event_count_value": 100
        }
    }
)

# Get persons in cohort
persons = client.get_persons(cohort_id=123)
```

### Feature Flags & Experiments

```python
# List all feature flags
flags = client.get_feature_flags()

# Evaluate flag for user
result = client.evaluate_flag(
    key="new-dashboard",
    distinct_id="user_123",
    person_properties={"plan": "pro"}
)

# Get A/B test results
experiments = client.get_experiments()
```

## E2B Sandbox Integration

### AgentExecutor

The `PostHogAgentExecutor` manages E2B sandbox lifecycle:

```python
from agent_executor import PostHogAgentExecutor

executor = PostHogAgentExecutor(
    e2b_api_key='your_e2b_key',
    posthog_api_key='phx_xxx',
    posthog_project_id='12345',
    posthog_api_url='https://us.posthog.com'
)

with executor:
    # Execute script
    result = executor.execute_script(
        script=my_python_code,
        description="Query power users"
    )

    # Or use templates
    result = executor.execute_template(
        template_name='identify_power_users',
        template_vars={
            'key_event': 'Feature Used',
            'min_occurrences': '10',
            'days': '7'
        },
        templates=TEMPLATES
    )
```

### Script Templates

Pre-built templates for common operations:

```python
from script_templates import TEMPLATES, get_template

# Available templates:
# - capture_event, capture_batch
# - get_recent_events, hogql_query, get_insights
# - export_events, export_cohort
# - identify_power_users, identify_churn_risk
# - analyze_funnel, get_experiments
# - evaluate_flags, track_errors

template = get_template('identify_power_users')
```

## Persona-Based Workflows

The driver includes examples for typical PostHog user personas:

### Product Engineers

**"Did our new feature improve engagement?"**

```python
from examples.persona_workflows import feature_impact_analysis

feature_impact_analysis()
```

**"What errors are affecting users?"**

```python
from examples.persona_workflows import bug_investigation_with_error_tracking

bug_investigation_with_error_tracking()
```

### Technical Product Managers

**"Where are users dropping off in our funnel?"**

```python
from examples.persona_workflows import user_journey_funnel_analysis

user_journey_funnel_analysis()
```

**"How do paid users behave vs free users?"**

```python
from examples.persona_workflows import cohort_comparison_analysis

cohort_comparison_analysis()
```

### Data Analysts

**"Complex behavioral pattern analysis"**

```python
from examples.persona_workflows import complex_hogql_analysis

complex_hogql_analysis()
```

**"Export data for warehouse sync"**

```python
from examples.persona_workflows import data_warehouse_export

data_warehouse_export()
```

### Growth Marketers

**"Which marketing channels drive best users?"**

```python
from examples.persona_workflows import marketing_channel_performance

marketing_channel_performance()
```

### Customer Success

**"What has this user been doing?"**

```python
from examples.persona_workflows import individual_user_journey

individual_user_journey()
```

**"Who are our power users?"**

```python
from examples.persona_workflows import power_user_identification

power_user_identification()
```

## API Reference

### PostHogClient

#### Initialization

```python
client = PostHogClient(
    api_url: Optional[str] = None,           # Default: https://us.posthog.com
    api_key: Optional[str] = None,           # Personal API key (required)
    project_id: Optional[str] = None,        # Project ID (required)
    project_api_key: Optional[str] = None,   # For event capture
    timeout: int = 30,                       # Request timeout (seconds)
    max_retries: int = 3                     # Max retry attempts
)
```

#### Core Methods

- `list_objects() -> List[str]` - List available entity types
- `get_fields(object_name: str) -> Dict` - Get entity schema
- `query(hogql_query: str) -> List[Dict]` - Execute HogQL query

#### Event Methods

- `capture_event(event, distinct_id, properties, timestamp)` - Capture single event
- `capture_batch(events)` - Capture multiple events

#### Analytics Methods

- `get_insights(insight_type, limit, offset)` - List insights
- `create_insight(name, insight_type, filters)` - Create insight
- `get_events(event_name, after, before, distinct_id, limit)` - Query events
- `export_events(start_date, end_date, event_names, properties_filter)` - Export events

#### Cohort Methods

- `get_cohorts(search)` - List cohorts
- `create_cohort(name, description, filters)` - Create cohort
- `get_persons(search, cohort_id, properties, limit)` - Query persons

#### Feature Flag Methods

- `get_feature_flags()` - List feature flags
- `evaluate_flag(key, distinct_id, person_properties)` - Evaluate flag
- `get_experiments()` - List experiments

#### Utility Methods

- `get_project_info()` - Get project details
- `health_check()` - Test API connection

### Exception Classes

- `PostHogError` - Base exception
- `AuthenticationError` - Invalid credentials
- `ObjectNotFoundError` - Resource not found
- `QueryError` - Query execution failed
- `ConnectionError` - Network issues
- `RateLimitError` - Rate limit exceeded
- `ValidationError` - Input validation failed

## Examples

### Example 1: Power User Identification

```python
from posthog_driver import PostHogClient

client = PostHogClient()

# Find users with high engagement
hogql = """
SELECT
    distinct_id,
    person.properties.email as email,
    count() as event_count
FROM events
WHERE timestamp >= now() - INTERVAL 30 DAY
GROUP BY distinct_id, email
HAVING event_count >= 100
ORDER BY event_count DESC
LIMIT 50
"""

power_users = client.query(hogql)
print(f"Found {len(power_users)} power users")
```

### Example 2: Funnel Drop-off Analysis

```python
from posthog_driver import PostHogClient

client = PostHogClient()

funnel_steps = ['Signup Started', 'Email Verified', 'Profile Completed']

for step in funnel_steps:
    hogql = f"""
    SELECT count(DISTINCT distinct_id) as count
    FROM events
    WHERE event = '{step}'
    AND timestamp >= '2024-01-01'
    """

    result = client.query(hogql)
    print(f"{step}: {result[0]['count']} users")
```

### Example 3: Marketing Channel Performance

```python
from posthog_driver import PostHogClient

client = PostHogClient()

hogql = """
SELECT
    properties.utm_source as source,
    count(DISTINCT distinct_id) as signups,
    countIf(distinct_id, event = 'Purchase') as conversions
FROM events
WHERE event = 'User Signup'
AND timestamp >= now() - INTERVAL 30 DAY
GROUP BY source
ORDER BY signups DESC
"""

channels = client.query(hogql)
for channel in channels:
    conv_rate = (channel['conversions'] / channel['signups']) * 100
    print(f"{channel['source']}: {channel['signups']} signups, {conv_rate:.1f}% conversion")
```

## Rate Limits

PostHog enforces the following rate limits:

- **Analytics endpoints** (insights, persons, cohorts): 240/minute, 1200/hour
- **Query endpoint** (HogQL): 2400/hour
- **Event capture**: No limits

**Best Practices**:
- Use batch event capture for high-volume ingestion
- For large exports, use PostHog's native batch export feature (to S3, BigQuery, etc.)
- Implement client-side rate limiting for analytics queries
- Cache insight results when appropriate

## Troubleshooting

### Authentication Errors

```
AuthenticationError: Authentication failed
```

**Solution**: Check your Personal API key and ensure it has correct scopes.

### Rate Limit Errors

```
RateLimitError: Rate limit exceeded
```

**Solution**: Reduce query frequency or use batch exports for large data transfers.

### Connection Errors

```
ConnectionError: Failed to connect to PostHog API
```

**Solution**:
- Check `POSTHOG_API_URL` is correct for your region (US/EU)
- Verify network connectivity
- For self-hosted, ensure instance is accessible

### Query Errors

```
QueryError: Query execution failed
```

**Solution**:
- Validate HogQL syntax
- Check that referenced properties exist
- Ensure date filters are in ISO 8601 format

### E2B Sandbox Issues

**Driver files not found**:
```python
# Ensure proper path setup
sys.path.insert(0, '/home/user')
```

**Dependencies not installed**:
```python
# Install in sandbox before execution
sandbox.commands.run('pip install requests python-dotenv')
```

## Contributing

Contributions are welcome! Please:

1. Fork the repository
2. Create a feature branch
3. Add tests for new functionality
4. Submit a pull request

## License

MIT License - see LICENSE file for details.

## Support

- **Documentation**: See `examples/` directory for usage examples
- **Issues**: Report bugs or request features via GitHub Issues
- **PostHog Docs**: https://posthog.com/docs

## Acknowledgments

Built for the Claude Agent SDK following the driver pattern from [ng_component](https://github.com/padak/ng_component).

Based on PostHog's comprehensive Product OS and data infrastructure capabilities.
