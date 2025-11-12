# PostHog Driver for Claude Agent SDK (E2B Sandbox) - Implementation Plan

## Overview
Building a PostHog driver that integrates with the Claude Agent SDK and runs in E2B sandboxes. The driver enables AI agents to perform analytics tracking, data export/ETL, and information lookup from PostHog.

## Architecture Context

### Driver Pattern (ng_component SDK)
Drivers implement a 3-method contract for dynamic discovery:
- `list_objects()` - Discover available entities
- `get_fields(object_name)` - Get schema for entity type
- `query(query_string)` - Execute queries in native language

### E2B Sandbox Execution
- All code runs inside isolated E2B VM sandboxes
- Driver files uploaded to `/home/user/posthog_driver/`
- API credentials passed via environment variables
- Network access available for external API calls

### PostHog API
- **Authentication**: Personal API Key + Project ID
- **Base URL**: `https://us.posthog.com` or `https://eu.posthog.com`
- **Query Language**: HogQL (SQL-like)
- **Rate Limits**: 240/min, 1200/hour (analytics), 2400/hour (queries)

## Implementation Phases

### Phase 1: Driver Core Implementation ✓
1. Create `posthog_driver/` package structure
   - `client.py` - Main PostHogClient class
   - `exceptions.py` - Custom exceptions
   - `__init__.py` - Package exports

2. Implement Driver Contract Methods:
   - `list_objects()` → ['events', 'insights', 'persons', 'cohorts', 'feature_flags', 'sessions']
   - `get_fields(object_name)` → Schema for each PostHog entity
   - `query(hogql_query)` → Execute HogQL queries

3. Add PostHog-Specific Methods:
   - `get_insights(insight_type, limit)` - Analytics insights
   - `get_events(filters)` - Event queries
   - `export_events(start_date, end_date)` - Bulk export
   - `get_cohorts()` - User cohorts
   - `get_persons(filters)` - Person profiles

### Phase 2: E2B Sandbox Integration
1. Create `AgentExecutor` class:
   - Initialize E2B sandbox
   - Upload driver files
   - Install dependencies
   - Manage environment variables

2. Build script templates:
   - Query recent events
   - Export data for ETL
   - Get insights and analytics
   - Lookup cohorts/persons

### Phase 3: PostHog Persona Knowledge
Embed understanding of typical PostHog users:

**Product Engineers**
- Needs: Feature impact analysis, bug investigation
- Workflows: Deploy → Track events → View trends → Watch replays → Iterate
- Pain points: Context switching, slow analytics tools

**Technical PMs**
- Needs: Data-driven decisions, A/B test analysis
- Workflows: Create funnels → Identify drop-offs → Review replays → Optimize
- Pain points: Balance between speed and depth

**Data Analysts**
- Needs: Complex SQL queries, data warehouse integration
- Workflows: Write HogQL → Export data → Cross-platform analysis
- Pain points: Platform limitations, data coordination

### Phase 4: Authentication & Error Handling
1. Authentication:
   - Personal API Key for private endpoints
   - US/EU region support
   - Environment variable fallbacks

2. Error handling:
   - Rate limit detection
   - Network timeout handling
   - Clear error messages

### Phase 5: Documentation & Examples
1. README with:
   - Quick start guide
   - E2B setup instructions
   - Environment configuration
   - Persona-based workflows

2. Example scripts:
   - `basic_usage.py` - Driver contract demo
   - `analytics_tracking.py` - Insights and trends
   - `etl_export.py` - Bulk data export
   - `persona_workflows.py` - User scenarios

## Key Technical Details

### Dependencies
```
requests>=2.31.0
python-dotenv>=1.0.0
```

### Environment Variables
```
POSTHOG_API_URL=https://us.posthog.com
POSTHOG_PERSONAL_API_KEY=your_personal_api_key
POSTHOG_PROJECT_ID=your_project_id
```

### PostHog Entity Mapping
- **events** - User actions tracked in applications
- **insights** - Pre-configured analytics (trends, funnels, retention)
- **persons** - User profiles with properties
- **cohorts** - User segments/groups
- **feature_flags** - Feature toggle configurations
- **sessions** - User session data with replays

### Common Use Cases
1. **Analytics Tracking**: Query trends, funnels, retention metrics
2. **Data Export/ETL**: Bulk event export for warehousing
3. **Info Lookup**: Get event definitions, user cohorts, insights

## Deliverables

1. **Core Driver Package**
   - `posthog_driver/client.py`
   - `posthog_driver/exceptions.py`
   - `posthog_driver/__init__.py`

2. **E2B Integration**
   - `agent_executor.py`
   - `script_templates.py`

3. **Examples**
   - `examples/basic_usage.py`
   - `examples/analytics_tracking.py`
   - `examples/etl_export.py`
   - `examples/persona_workflows.py`

4. **Documentation**
   - `README.md`
   - `.env.example`
   - `requirements.txt`

5. **Testing**
   - `tests/test_client.py`
   - `tests/test_e2b.py`

## Success Criteria

- ✓ Implements full driver contract (list_objects, get_fields, query)
- ✓ Supports analytics tracking, ETL export, and info lookup
- ✓ Runs successfully in E2B sandbox environment
- ✓ Handles authentication and errors gracefully
- ✓ Includes persona-based workflow examples
- ✓ Comprehensive documentation for setup and usage
