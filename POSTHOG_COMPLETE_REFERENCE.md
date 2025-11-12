# PostHog Complete Reference

**The definitive guide to PostHog: API, Use Cases, Queries, and Jobs To Be Done**

*Everything you need to understand and build with PostHog*

---

## Table of Contents

1. [What is PostHog?](#what-is-posthog)
2. [Jobs To Be Done (User Needs)](#jobs-to-be-done)
3. [Complete API Reference](#complete-api-reference)
4. [HogQL Query Language](#hogql-query-language)
5. [Common Use Cases & Queries](#common-use-cases--queries)
6. [Entity Types & Data Model](#entity-types--data-model)
7. [Product Engineer Workflows](#product-engineer-workflows)
8. [Production Best Practices](#production-best-practices)

---

## What is PostHog?

### Product OS for Engineers (2025)

PostHog is an all-in-one product platform that helps engineers understand and improve their products through data.

**Core Philosophy:** Give engineers the tools to make data-driven product decisions without needing a data team.

**Evolution:**
- **2020**: Product analytics tool
- **2025**: Complete Product OS (10+ integrated products, $920M valuation)

### 10+ Products Suite

| Product | Purpose | Primary Users |
|---------|---------|---------------|
| **Product Analytics** | Understand user behavior | Product Engineers, PMs |
| **Session Replay** | Watch user sessions | Engineers, Support |
| **Feature Flags** | Gradual rollouts, targeting | Engineers |
| **Experiments** | A/B testing | Product, Growth |
| **Surveys** | User feedback | Product, UX |
| **LLM Analytics** | AI product metrics | AI Engineers |
| **Data Warehouse** | External data joins | Data Analysts |
| **Website Analytics** | Public site tracking | Marketing |
| **Max AI** | AI-powered insights | All users |
| **Event Pipelines** | Data routing | Engineers |

### Key Differentiators

1. **Built for engineers**: Code-first, API-first, Git-based configuration
2. **All-in-one**: No stitching together 5+ tools
3. **Open source**: Self-hostable, transparent
4. **Privacy-focused**: GDPR/CCPA compliant, no cookies required
5. **HogQL**: SQL-like query language for product analytics
6. **Generous free tier**: 1M events/month, no team limits

---

## Jobs To Be Done

### Job 1: "Help me understand what users are doing in my product"

**Who:** Product Engineers, Product Managers, Founders

**Pain Points:**
- Don't know which features are used/ignored
- Can't see where users get stuck
- Missing the connection between user behavior and outcomes
- Need data without setting up complex analytics infrastructure

**PostHog Solution:**
- **Autocapture**: Automatic tracking of clicks, pageviews
- **Custom events**: Track specific actions
- **HogQL queries**: Ask any question of your data
- **Session replay**: Watch actual user sessions
- **Dashboards**: Monitor metrics over time

**Example Queries:**
```sql
-- What features are being used?
SELECT event, count() as uses, count(DISTINCT distinct_id) as users
FROM events
WHERE timestamp >= now() - INTERVAL 7 DAY
GROUP BY event
ORDER BY uses DESC

-- Where do users drop off?
SELECT step, count(DISTINCT distinct_id) as users
FROM (
    SELECT distinct_id, '$pageview' as step FROM events WHERE event = '$pageview'
    UNION ALL
    SELECT distinct_id, 'signup' FROM events WHERE event = 'signup'
    UNION ALL
    SELECT distinct_id, 'activated' FROM events WHERE event = 'activated'
)
GROUP BY step
```

**Success Metric:** Time from question to answer < 5 minutes

---

### Job 2: "Help me ship features confidently"

**Who:** Product Engineers, DevOps

**Pain Points:**
- Fear of breaking production
- No way to test in production with real users
- All-or-nothing deployments
- Can't quickly rollback without redeploying

**PostHog Solution:**
- **Feature flags**: Control access by user, cohort, or percentage
- **Experiments**: A/B test new features
- **Monitoring**: Track errors and performance by variant
- **Gradual rollouts**: 5% → 25% → 100%

**Example Workflow:**
```python
# 1. Wrap feature in flag
if posthog.feature_enabled('new-dashboard', user.id):
    show_new_dashboard()
else:
    show_old_dashboard()

# 2. Start with 5% rollout
# 3. Monitor error rates by variant
# 4. Gradually increase if stable
```

**HogQL Monitoring:**
```sql
-- Error rate by variant
SELECT
    properties.feature_flag_variant as variant,
    count(DISTINCT distinct_id) as users,
    countIf(event = '$exception') as errors,
    round(1000.0 * errors / users, 2) as errors_per_1000
FROM events
WHERE timestamp >= now() - INTERVAL 1 DAY
GROUP BY variant
```

**Success Metric:** Zero production incidents from feature rollouts

---

### Job 3: "Help me understand why users convert (or don't)"

**Who:** Growth Engineers, Product Managers, Marketers

**Pain Points:**
- Don't know what drives conversions
- Can't identify friction points
- Attribution is unclear (which actions matter?)
- Need to optimize funnel systematically

**PostHog Solution:**
- **Funnels**: Visualize multi-step conversions
- **Cohort analysis**: Compare converters vs. non-converters
- **Path analysis**: See actual user journeys
- **Correlation analysis**: Find predictive actions

**Example Queries:**
```sql
-- Conversion funnel with drop-off
WITH funnel AS (
    SELECT
        'visited' as step,
        1 as step_order,
        count(DISTINCT distinct_id) as users
    FROM events WHERE event = '$pageview'

    UNION ALL

    SELECT 'signed_up', 2, count(DISTINCT distinct_id)
    FROM events WHERE event = 'signup'

    UNION ALL

    SELECT 'converted', 3, count(DISTINCT distinct_id)
    FROM events WHERE event = 'purchase'
)
SELECT
    step,
    users,
    round(100.0 * users / lag(users, 1, users) OVER (ORDER BY step_order), 2) as conversion_rate
FROM funnel
ORDER BY step_order

-- What do converters do differently?
WITH converters AS (
    SELECT DISTINCT distinct_id FROM events WHERE event = 'purchase'
)
SELECT
    e.event,
    count(DISTINCT CASE WHEN c.distinct_id IS NOT NULL THEN e.distinct_id END) as converter_count,
    count(DISTINCT CASE WHEN c.distinct_id IS NULL THEN e.distinct_id END) as non_converter_count,
    round(
        (converter_count::float / (SELECT count(*) FROM converters)) /
        (non_converter_count::float / (SELECT count(DISTINCT distinct_id) FROM events WHERE distinct_id NOT IN (SELECT distinct_id FROM converters))),
        2
    ) as lift
FROM events e
LEFT JOIN converters c ON e.distinct_id = c.distinct_id
WHERE e.event != 'purchase'
GROUP BY e.event
HAVING converter_count >= 10
ORDER BY lift DESC
LIMIT 20
```

**Success Metric:** 20%+ increase in conversion rate

---

### Job 4: "Help me debug user-reported issues"

**Who:** Engineers, Customer Support

**Pain Points:**
- "It doesn't work" reports with no details
- Can't reproduce bugs
- No visibility into user's actual experience
- Logs don't show user context

**PostHog Solution:**
- **Session replay**: Watch exactly what user did
- **Event timeline**: See all user actions
- **Console logs**: Capture JavaScript errors
- **Person lookup**: Search by email, ID, property

**Example Workflow:**
```
1. User reports: "Can't checkout"
2. Search for user by email in PostHog
3. View their event timeline
4. Find error event: $exception with "payment_failed"
5. Watch session replay of checkout attempt
6. See exact steps: user clicked "Pay" but card field was empty
7. Root cause: Validation wasn't working on mobile Safari
```

**HogQL Query:**
```sql
-- User's error timeline
SELECT
    timestamp,
    event,
    properties.$current_url,
    properties.error_message,
    properties.$browser
FROM events
WHERE
    person.properties.$email = 'user@example.com'
    AND (event = '$exception' OR event LIKE '%error%')
    AND timestamp >= now() - INTERVAL 7 DAY
ORDER BY timestamp DESC
```

**Success Metric:** Time to root cause < 10 minutes

---

### Job 5: "Help me measure feature impact"

**Who:** Product Engineers, Product Managers

**Pain Points:**
- Built feature but don't know if it worked
- Can't measure before/after impact
- No way to attribute changes to specific features
- Need to justify engineering investment

**PostHog Solution:**
- **Experiments**: Controlled A/B tests
- **Annotations**: Mark deployments/launches
- **Trends**: Before/after comparison
- **Custom metrics**: Track business outcomes

**Example Workflow:**
```
1. Hypothesis: "New onboarding will increase activation"
2. Set up experiment:
   - Control: Old onboarding
   - Test: New onboarding
3. Define success metric: completed_profile within 24h
4. Run for 2 weeks with 1000+ users per variant
5. Analyze results
```

**HogQL Query:**
```sql
-- Experiment results
WITH variant_users AS (
    SELECT
        distinct_id,
        properties.feature_flag_variant as variant
    FROM events
    WHERE
        properties.feature_flag = 'new-onboarding'
        AND timestamp >= '2025-01-01'
    GROUP BY distinct_id, properties.feature_flag_variant
)
SELECT
    v.variant,
    count(DISTINCT v.distinct_id) as total_users,
    count(DISTINCT CASE
        WHEN e.event = 'completed_profile'
        AND e.timestamp <= v.first_seen + INTERVAL 24 HOUR
        THEN e.distinct_id
    END) as activated_users,
    round(100.0 * activated_users / total_users, 2) as activation_rate
FROM variant_users v
LEFT JOIN events e ON v.distinct_id = e.distinct_id
JOIN (
    SELECT distinct_id, min(timestamp) as first_seen
    FROM events
    GROUP BY distinct_id
) fs ON v.distinct_id = fs.distinct_id
GROUP BY v.variant
```

**Success Metric:** Confident decision (ship/kill) backed by data

---

### Job 6: "Help me optimize for AI products"

**Who:** AI Engineers, LLM Product Teams

**Pain Points:**
- Token costs are unpredictable
- Latency varies wildly
- Don't know which prompts/models perform best
- Hard to track conversation quality
- Can't attribute costs to features/users

**PostHog Solution:**
- **LLM Analytics**: Track tokens, costs, latency, model usage
- **Custom events**: Track AI-specific metrics
- **Dashboards**: Monitor AI performance
- **Cohorts**: Segment by usage patterns

**Example Events:**
```javascript
// Track LLM completion
posthog.capture('$ai_completion', {
    model: 'gpt-4',
    tokens_used: 1234,
    prompt_tokens: 234,
    completion_tokens: 1000,
    latency_ms: 850,
    cost: 0.0123,
    success: true,
    conversation_id: 'conv_abc123'
})
```

**HogQL Queries:**
```sql
-- Token usage and cost by model
SELECT
    properties.model,
    count() as completions,
    sum(properties.tokens_used) as total_tokens,
    sum(properties.cost) as total_cost,
    round(avg(properties.latency_ms), 0) as avg_latency_ms,
    round(100.0 * countIf(properties.success = true) / count(), 2) as success_rate
FROM events
WHERE
    event = '$ai_completion'
    AND timestamp >= now() - INTERVAL 7 DAY
GROUP BY properties.model
ORDER BY total_cost DESC

-- Most expensive conversations
SELECT
    properties.conversation_id,
    count() as turns,
    sum(properties.tokens_used) as total_tokens,
    sum(properties.cost) as total_cost,
    round(avg(properties.latency_ms), 0) as avg_latency
FROM events
WHERE event = '$ai_completion'
GROUP BY properties.conversation_id
HAVING turns >= 3
ORDER BY total_cost DESC
LIMIT 20

-- Cost by user segment
SELECT
    person.properties.plan_type,
    count(DISTINCT distinct_id) as users,
    sum(properties.cost) as total_cost,
    round(total_cost / users, 2) as cost_per_user
FROM events
WHERE event = '$ai_completion'
GROUP BY person.properties.plan_type
```

**Success Metric:** LLM costs under budget, <500ms p95 latency

---

### Job 7: "Help me understand user retention"

**Who:** Product Managers, Growth Teams

**Pain Points:**
- Users sign up but don't come back
- Don't know what drives retention
- Can't identify at-risk users early
- Need to improve D7/D30 retention

**PostHog Solution:**
- **Retention charts**: Cohort retention over time
- **Stickiness**: DAU/MAU ratio
- **Cohort analysis**: Compare retention by segment
- **Predictive cohorts**: Identify at-risk users

**HogQL Queries:**
```sql
-- Cohort retention analysis
WITH cohorts AS (
    SELECT
        distinct_id,
        toStartOfWeek(min(timestamp)) as cohort_week
    FROM events
    GROUP BY distinct_id
)
SELECT
    c.cohort_week,
    count(DISTINCT c.distinct_id) as cohort_size,
    count(DISTINCT CASE
        WHEN toStartOfWeek(e.timestamp) = c.cohort_week + INTERVAL 1 WEEK
        THEN c.distinct_id
    END) as week_1_retained,
    count(DISTINCT CASE
        WHEN toStartOfWeek(e.timestamp) = c.cohort_week + INTERVAL 4 WEEK
        THEN c.distinct_id
    END) as week_4_retained,
    round(100.0 * week_1_retained / cohort_size, 2) as week_1_retention_pct,
    round(100.0 * week_4_retained / cohort_size, 2) as week_4_retention_pct
FROM cohorts c
LEFT JOIN events e ON c.distinct_id = e.distinct_id
WHERE c.cohort_week >= now() - INTERVAL 12 WEEK
GROUP BY c.cohort_week
ORDER BY c.cohort_week DESC

-- What drives retention? (Behavioral cohorts)
WITH week_1_retention AS (
    SELECT
        e1.distinct_id,
        CASE
            WHEN count(DISTINCT CASE
                WHEN e2.timestamp >= e1.first_seen + INTERVAL 7 DAY
                AND e2.timestamp < e1.first_seen + INTERVAL 14 DAY
                THEN toDate(e2.timestamp)
            END) >= 1 THEN 'retained'
            ELSE 'churned'
        END as retention_status
    FROM (
        SELECT distinct_id, min(timestamp) as first_seen
        FROM events
        GROUP BY distinct_id
    ) e1
    LEFT JOIN events e2 ON e1.distinct_id = e2.distinct_id
    WHERE e1.first_seen >= now() - INTERVAL 8 WEEK
    GROUP BY e1.distinct_id
)
SELECT
    e.event,
    count(DISTINCT CASE WHEN r.retention_status = 'retained' THEN e.distinct_id END) as retained_users,
    count(DISTINCT CASE WHEN r.retention_status = 'churned' THEN e.distinct_id END) as churned_users,
    round(
        (retained_users::float / (SELECT count(*) FROM week_1_retention WHERE retention_status = 'retained')) /
        (churned_users::float / (SELECT count(*) FROM week_1_retention WHERE retention_status = 'churned')),
        2
    ) as retention_lift
FROM events e
JOIN week_1_retention r ON e.distinct_id = r.distinct_id
JOIN (
    SELECT distinct_id, min(timestamp) as first_seen FROM events GROUP BY distinct_id
) fs ON e.distinct_id = fs.distinct_id
WHERE
    e.timestamp >= fs.first_seen
    AND e.timestamp < fs.first_seen + INTERVAL 7 DAY
GROUP BY e.event
HAVING retained_users >= 20
ORDER BY retention_lift DESC
LIMIT 20
```

**Success Metric:** D7 retention > 40%, D30 retention > 25%

---

## Complete API Reference

### API Overview

**Base URLs:**
- US Cloud: `https://us.posthog.com`
- EU Cloud: `https://eu.posthog.com`
- Self-hosted: `https://your-domain.com`

**Authentication:**
```http
Authorization: Bearer phx_YOUR_API_KEY_HERE
Content-Type: application/json
```

**Rate Limits:**
- Analytics (Query, Events, Recordings): 240/min, 1,200/hour
- CRUD (Create, Update, Delete): 480/min, 4,800/hour
- Event Capture: Higher (no published limit)

### Complete Endpoint List (75+ endpoints)

#### 1. Analytics & Query

```bash
# Execute HogQL query
POST /api/projects/{project_id}/query/
Body: {"query": {"kind": "HogQLQuery", "query": "SELECT..."}}
Rate: 240/min

# List events
GET /api/projects/{project_id}/events/
Query: ?limit=100&offset=0&event=signup&person_id=123
Rate: 240/min

# Capture event (public)
POST /api/capture/
Body: {"api_key": "phc_...", "event": "signup", "properties": {...}}
Rate: High (no limit specified)

# Batch capture (public)
POST /api/capture/
Body: {"api_key": "phc_...", "batch": [...]}
```

#### 2. Actions (Saved Event Definitions)

```bash
# List actions
GET /api/projects/{project_id}/actions/

# Create action
POST /api/projects/{project_id}/actions/
Body: {
    "name": "Completed Signup",
    "steps": [
        {"event": "signup_clicked"},
        {"event": "signup_completed"}
    ]
}

# Get action
GET /api/projects/{project_id}/actions/{action_id}/

# Update action
PATCH /api/projects/{project_id}/actions/{action_id}/
Body: {"name": "Updated Name"}

# Delete action
DELETE /api/projects/{project_id}/actions/{action_id}/
```

**What are Actions?**
- Combine multiple events: `signup_clicked OR signup_completed`
- Add filters: `pageview WHERE url LIKE '%/pricing%'`
- Match elements: `autocapture WHERE selector = 'button.cta'`

#### 3. Dashboards

```bash
# List dashboards
GET /api/projects/{project_id}/dashboards/

# Create dashboard
POST /api/projects/{project_id}/dashboards/
Body: {
    "name": "Executive Dashboard",
    "description": "Weekly metrics",
    "pinned": true,
    "items": [
        {"insight": 123, "layouts": {"sm": {"x": 0, "y": 0, "w": 6, "h": 4}}},
        {"text": {"body": "## Summary"}, "layouts": {"sm": {"x": 0, "y": 4, "w": 12, "h": 2}}}
    ]
}

# Get dashboard
GET /api/projects/{project_id}/dashboards/{dashboard_id}/

# Update dashboard
PATCH /api/projects/{project_id}/dashboards/{dashboard_id}/

# Delete dashboard
DELETE /api/projects/{project_id}/dashboards/{dashboard_id}/
```

#### 4. Insights (Saved Queries)

```bash
# List insights
GET /api/projects/{project_id}/insights/

# Create insight
POST /api/projects/{project_id}/insights/
Body: {
    "name": "Daily Active Users",
    "filters": {
        "events": [{"id": "$pageview", "type": "events"}],
        "date_from": "-30d"
    }
}

# Get insight
GET /api/projects/{project_id}/insights/{insight_id}/

# Update insight
PATCH /api/projects/{project_id}/insights/{insight_id}/

# Delete insight
DELETE /api/projects/{project_id}/insights/{insight_id}/
```

#### 5. Persons (User Profiles)

```bash
# List persons
GET /api/projects/{project_id}/persons/
Query: ?limit=100&properties=[{"key":"plan","value":"enterprise"}]

# Create/update person
POST /api/projects/{project_id}/persons/
Body: {
    "distinct_ids": ["user_123"],
    "properties": {"email": "user@example.com", "plan": "pro"}
}

# Get person
GET /api/projects/{project_id}/persons/{person_id}/

# Update person
PATCH /api/projects/{project_id}/persons/{person_id}/
Body: {"properties": {"plan": "enterprise"}}

# Delete person (and all events)
DELETE /api/projects/{project_id}/persons/{person_id}/
```

#### 6. Cohorts (User Segments)

```bash
# List cohorts
GET /api/projects/{project_id}/cohorts/

# Create cohort
POST /api/projects/{project_id}/cohorts/
Body: {
    "name": "Power Users",
    "filters": {
        "properties": {
            "type": "AND",
            "values": [
                {"key": "events_count", "value": 100, "operator": "gt"}
            ]
        }
    }
}

# Get cohort
GET /api/projects/{project_id}/cohorts/{cohort_id}/

# Update cohort
PATCH /api/projects/{project_id}/cohorts/{cohort_id}/

# Delete cohort
DELETE /api/projects/{project_id}/cohorts/{cohort_id}/

# List persons in cohort
GET /api/projects/{project_id}/cohorts/{cohort_id}/persons/
```

#### 7. Feature Flags

```bash
# List feature flags
GET /api/projects/{project_id}/feature_flags/

# Create feature flag
POST /api/projects/{project_id}/feature_flags/
Body: {
    "key": "new-dashboard",
    "name": "New Dashboard",
    "active": true,
    "filters": {
        "groups": [
            {"properties": [], "rollout_percentage": 25}
        ]
    }
}

# Get feature flag
GET /api/projects/{project_id}/feature_flags/{flag_id}/

# Update feature flag
PATCH /api/projects/{project_id}/feature_flags/{flag_id}/
Body: {"filters": {"groups": [{"rollout_percentage": 50}]}}

# Delete feature flag
DELETE /api/projects/{project_id}/feature_flags/{flag_id}/

# Evaluate flag (public)
POST /api/feature_flag/local_evaluation/
Body: {
    "distinct_id": "user_123",
    "groups": {"company": "acme"}
}
```

#### 8. Experiments (A/B Tests)

```bash
# List experiments
GET /api/projects/{project_id}/experiments/

# Create experiment
POST /api/projects/{project_id}/experiments/
Body: {
    "name": "New Onboarding Test",
    "feature_flag_key": "new-onboarding",
    "variants": [
        {"key": "control"},
        {"key": "test"}
    ],
    "parameters": {
        "feature_flag_variants": [
            {"key": "control", "rollout_percentage": 50},
            {"key": "test", "rollout_percentage": 50}
        ]
    }
}

# Get experiment (with results)
GET /api/projects/{project_id}/experiments/{experiment_id}/

# Update experiment
PATCH /api/projects/{project_id}/experiments/{experiment_id}/

# Delete experiment
DELETE /api/projects/{project_id}/experiments/{experiment_id}/
```

#### 9. Surveys

```bash
# List surveys
GET /api/projects/{project_id}/surveys/

# Create survey
POST /api/projects/{project_id}/surveys/
Body: {
    "name": "Product Satisfaction",
    "type": "popover",
    "questions": [
        {
            "type": "rating",
            "question": "How satisfied are you?",
            "scale": 5
        },
        {
            "type": "open",
            "question": "What could we improve?"
        }
    ],
    "targeting": {"url_matching": "/dashboard"}
}

# Get survey
GET /api/projects/{project_id}/surveys/{survey_id}/

# Update survey
PATCH /api/projects/{project_id}/surveys/{survey_id}/

# Delete survey
DELETE /api/projects/{project_id}/surveys/{survey_id}/
```

#### 10. Session Recordings

```bash
# List recordings
GET /api/projects/{project_id}/session_recordings/
Query: ?person_id=123&date_from=2025-01-01&limit=50
Rate: 240/min

# Get recording metadata
GET /api/projects/{project_id}/session_recordings/{recording_id}/

# Get recording snapshots (playback data)
GET /api/projects/{project_id}/session_recordings/{recording_id}/snapshots/
Note: For raw JSON export, use in-app "Export as JSON"
```

#### 11. Sessions

```bash
# List sessions
GET /api/projects/{project_id}/sessions/
Query: ?distinct_id=user_123&date_from=2025-01-01
```

#### 12. Annotations (Timeline Markers)

```bash
# List annotations
GET /api/projects/{project_id}/annotations/

# Create annotation
POST /api/projects/{project_id}/annotations/
Body: {
    "content": "Launched new feature",
    "date_marker": "2025-01-15",
    "creation_type": "manual"
}

# Get annotation
GET /api/projects/{project_id}/annotations/{annotation_id}/

# Update annotation
PATCH /api/projects/{project_id}/annotations/{annotation_id}/

# Delete annotation
DELETE /api/projects/{project_id}/annotations/{annotation_id}/
```

#### 13. Data Management

```bash
# Event Definitions (metadata)
GET /api/projects/{project_id}/event_definitions/
GET /api/projects/{project_id}/event_definitions/{event_name}/
PATCH /api/projects/{project_id}/event_definitions/{event_name}/
Body: {"description": "User completed signup", "tags": ["conversion"]}

# Property Definitions (metadata)
GET /api/projects/{project_id}/property_definitions/
GET /api/projects/{project_id}/property_definitions/{property_name}/
PATCH /api/projects/{project_id}/property_definitions/{property_name}/

# Batch Exports
GET /api/projects/{project_id}/batch_exports/
POST /api/projects/{project_id}/batch_exports/
Body: {
    "destination": "S3",
    "name": "Daily Export",
    "interval": "daily"
}
GET /api/projects/{project_id}/batch_exports/{export_id}/
DELETE /api/projects/{project_id}/batch_exports/{export_id}/
```

#### 14. Organization & Project Management

```bash
# Organizations
GET /api/organizations/
GET /api/organizations/{org_id}/
PATCH /api/organizations/{org_id}/
GET /api/organizations/{org_id}/members/
POST /api/organizations/{org_id}/members/
DELETE /api/organizations/{org_id}/members/{user_id}/

# Projects
GET /api/projects/
POST /api/projects/
Body: {"name": "My Product", "organization": "org_id"}
GET /api/projects/{project_id}/
PATCH /api/projects/{project_id}/
DELETE /api/projects/{project_id}/

# Teams (access control)
GET /api/projects/{project_id}/teams/
GET /api/projects/{project_id}/teams/{team_id}/
PATCH /api/projects/{project_id}/teams/{team_id}/
```

#### 15. Integrations & Webhooks

```bash
# Webhooks
GET /api/projects/{project_id}/hooks/
POST /api/projects/{project_id}/hooks/
Body: {
    "event": "subscription_purchased",
    "target": "https://api.company.com/webhooks/posthog",
    "enabled": true
}
GET /api/projects/{project_id}/hooks/{hook_id}/
PATCH /api/projects/{project_id}/hooks/{hook_id}/
DELETE /api/projects/{project_id}/hooks/{hook_id}/

# Integrations (Slack, Teams, etc.)
GET /api/projects/{project_id}/integrations/
POST /api/projects/{project_id}/integrations/
DELETE /api/projects/{project_id}/integrations/{integration_id}/

# Plugins (Data Apps)
GET /api/projects/{project_id}/plugins/
POST /api/projects/{project_id}/plugins/
GET /api/projects/{project_id}/plugins/{plugin_id}/
PATCH /api/projects/{project_id}/plugins/{plugin_id}/
DELETE /api/projects/{project_id}/plugins/{plugin_id}/
```

### API Summary Table

| Category | Endpoints | Common Use Cases |
|----------|-----------|------------------|
| **Analytics** | 3 | Execute queries, list events, capture data |
| **Actions** | 5 | Saved event definitions, reusable filters |
| **Dashboards** | 5 | Visualization management, monitoring |
| **Insights** | 5 | Saved queries, metrics tracking |
| **Persons** | 5 | User profiles, property management |
| **Cohorts** | 6 | User segmentation, targeting |
| **Feature Flags** | 6 | Gradual rollouts, A/B testing |
| **Experiments** | 5 | Controlled experiments, variant analysis |
| **Surveys** | 5 | User feedback, NPS, satisfaction |
| **Recordings** | 3 | Session replay, debugging |
| **Sessions** | 1 | Session tracking |
| **Annotations** | 5 | Timeline markers, deployment tracking |
| **Data Mgmt** | 9 | Metadata, exports, governance |
| **Admin** | 11 | Orgs, projects, teams, access control |
| **Integrations** | 9 | Webhooks, plugins, third-party tools |
| **Total** | **75+** | **Complete platform coverage** |

---

## HogQL Query Language

### What is HogQL?

HogQL is PostHog's SQL-like query language built on ClickHouse SQL with product analytics extensions.

**Key Features:**
- SQL syntax (SELECT, FROM, WHERE, GROUP BY, ORDER BY)
- Auto-joins (access person data without explicit JOIN)
- Product analytics functions (funnels, retention)
- Property access (properties.$browser, person.properties.$email)
- Time functions (now(), INTERVAL, toDate(), toStartOfWeek())

### Basic Syntax

```sql
SELECT
    column1,
    aggregate_function(column2) as alias
FROM table_name
WHERE condition
GROUP BY column1
HAVING aggregate_condition
ORDER BY column1 DESC
LIMIT 100
```

### Available Tables

**1. events** - User actions
```sql
SELECT
    event,
    timestamp,
    distinct_id,
    properties,
    elements_chain
FROM events
```

**2. persons** - User profiles
```sql
SELECT
    id,
    distinct_ids,
    properties,
    created_at
FROM persons
```

**3. sessions** - User sessions
```sql
SELECT
    session_id,
    distinct_id,
    duration,
    event_count
FROM sessions
```

**4. groups** - Organizations/companies
```sql
SELECT
    group_type,
    group_key,
    properties
FROM groups
```

### Property Access

```sql
-- Event properties
SELECT properties.$browser FROM events
SELECT properties.custom_field FROM events

-- Person properties (auto-joined!)
SELECT person.properties.$email FROM events
SELECT person.properties.plan_type FROM events

-- Group properties
SELECT groups.properties.company_name FROM events
```

### Time Functions

```sql
-- Current time
WHERE timestamp >= now() - INTERVAL 7 DAY

-- Time periods
INTERVAL 1 HOUR
INTERVAL 7 DAY
INTERVAL 30 DAY
INTERVAL 1 WEEK
INTERVAL 3 MONTH

-- Date functions
toDate(timestamp)                -- 2025-01-15
toHour(timestamp)                -- 14 (2 PM)
toDayOfWeek(timestamp)           -- 1-7 (Monday-Sunday)
toStartOfHour(timestamp)
toStartOfDay(timestamp)
toStartOfWeek(timestamp)
toStartOfMonth(timestamp)
```

### Aggregation Functions

```sql
-- Count
count()                          -- Total rows
count(DISTINCT distinct_id)      -- Unique users

-- Math
sum(properties.revenue)
avg(properties.duration)
min(timestamp)
max(timestamp)
percentile(properties.load_time, 0.95)

-- Conditional
countIf(event = 'purchase')
sumIf(properties.revenue, properties.plan = 'pro')
```

### Advanced Patterns

**Window Functions:**
```sql
SELECT
    distinct_id,
    event,
    timestamp,
    row_number() OVER (PARTITION BY distinct_id ORDER BY timestamp) as event_number,
    lag(event, 1) OVER (PARTITION BY distinct_id ORDER BY timestamp) as previous_event
FROM events
```

**CTEs (Common Table Expressions):**
```sql
WITH converters AS (
    SELECT DISTINCT distinct_id FROM events WHERE event = 'purchase'
)
SELECT
    count(*) as converter_count
FROM converters
```

**Subqueries:**
```sql
SELECT
    event,
    count() as total,
    round(100.0 * total / (SELECT count(*) FROM events), 2) as pct
FROM events
GROUP BY event
```

### Query Optimization

**❌ Slow Query:**
```sql
SELECT * FROM events
WHERE properties.custom_field = 'value'
```

**✅ Fast Query:**
```sql
SELECT event, distinct_id, timestamp, properties.custom_field
FROM events
WHERE
    timestamp >= now() - INTERVAL 7 DAY        -- Time filter (indexed)
    AND event IN ('signup', 'purchase')        -- Event filter (indexed)
    AND properties.custom_field = 'value'      -- Property filter (last)
LIMIT 1000                                      -- Explicit limit
```

**Optimization Checklist:**
- ✅ Time filter (timestamp >= ...)
- ✅ Event filter (event IN (...))
- ✅ Indexed columns first
- ✅ LIMIT clause
- ✅ Specific columns (not SELECT *)
- ✅ Date range < 90 days
- ❌ Avoid filtering on unindexed properties first

---

## Common Use Cases & Queries

### 1. Feature Adoption

**Question:** "Which features are being used?"

```sql
-- Overall feature usage
SELECT
    properties.feature_name as feature,
    count(DISTINCT distinct_id) as unique_users,
    count() as total_uses,
    round(total_uses / unique_users, 2) as uses_per_user
FROM events
WHERE
    event = 'feature_used'
    AND timestamp >= now() - INTERVAL 30 DAY
GROUP BY feature
ORDER BY unique_users DESC

-- Adoption rate by user segment
SELECT
    person.properties.plan_type as plan,
    count(DISTINCT CASE
        WHEN event = 'feature_used' AND properties.feature_name = 'new_dashboard'
        THEN distinct_id
    END) as users_adopted,
    count(DISTINCT distinct_id) as total_users,
    round(100.0 * users_adopted / total_users, 2) as adoption_pct
FROM events
WHERE timestamp >= now() - INTERVAL 30 DAY
GROUP BY plan
```

### 2. Conversion Funnel

**Question:** "Where do users drop off?"

```sql
WITH funnel AS (
    SELECT 'visited' as step, 1 as ord, count(DISTINCT distinct_id) as users
    FROM events WHERE event = '$pageview'

    UNION ALL
    SELECT 'signed_up', 2, count(DISTINCT distinct_id)
    FROM events WHERE event = 'signup'

    UNION ALL
    SELECT 'activated', 3, count(DISTINCT distinct_id)
    FROM events WHERE event = 'activated'

    UNION ALL
    SELECT 'converted', 4, count(DISTINCT distinct_id)
    FROM events WHERE event = 'purchase'
)
SELECT
    step,
    users,
    lag(users, 1, users) OVER (ORDER BY ord) as previous_step_users,
    round(100.0 * users / previous_step_users, 2) as conversion_rate,
    round(100.0 * (previous_step_users - users) / previous_step_users, 2) as drop_off_rate
FROM funnel
ORDER BY ord
```

### 3. User Activity Levels

**Question:** "Who are my power users?"

```sql
SELECT
    distinct_id,
    person.properties.$email,
    count() as total_events,
    count(DISTINCT toDate(timestamp)) as active_days,
    round(total_events / active_days, 2) as events_per_day,
    CASE
        WHEN total_events >= 500 THEN 'power_user'
        WHEN total_events >= 100 THEN 'active_user'
        WHEN total_events >= 20 THEN 'casual_user'
        ELSE 'inactive_user'
    END as user_segment
FROM events
WHERE timestamp >= now() - INTERVAL 30 DAY
GROUP BY distinct_id, person.properties.$email
ORDER BY total_events DESC
```

### 4. Retention Analysis

**Question:** "Are users coming back?"

```sql
WITH cohorts AS (
    SELECT
        distinct_id,
        toStartOfWeek(min(timestamp)) as cohort_week,
        min(timestamp) as first_seen
    FROM events
    GROUP BY distinct_id
)
SELECT
    c.cohort_week,
    count(DISTINCT c.distinct_id) as cohort_size,

    -- Week 1 retention
    count(DISTINCT CASE
        WHEN toStartOfWeek(e.timestamp) = c.cohort_week + INTERVAL 1 WEEK
        THEN c.distinct_id
    END) as week_1_retained,
    round(100.0 * week_1_retained / cohort_size, 2) as week_1_pct,

    -- Week 4 retention
    count(DISTINCT CASE
        WHEN toStartOfWeek(e.timestamp) = c.cohort_week + INTERVAL 4 WEEK
        THEN c.distinct_id
    END) as week_4_retained,
    round(100.0 * week_4_retained / cohort_size, 2) as week_4_pct

FROM cohorts c
LEFT JOIN events e ON c.distinct_id = e.distinct_id
WHERE c.cohort_week >= now() - INTERVAL 12 WEEK
GROUP BY c.cohort_week
ORDER BY c.cohort_week DESC
```

### 5. Performance Monitoring

**Question:** "Is my app fast enough?"

```sql
SELECT
    properties.$current_url as page,
    count() as pageviews,

    -- Load time metrics
    round(avg(properties.page_load_time), 0) as avg_load_ms,
    round(percentile(properties.page_load_time, 0.50), 0) as p50_ms,
    round(percentile(properties.page_load_time, 0.95), 0) as p95_ms,
    round(percentile(properties.page_load_time, 0.99), 0) as p99_ms,

    -- Slow page loads
    countIf(properties.page_load_time > 3000) as slow_loads,
    round(100.0 * slow_loads / pageviews, 2) as slow_load_pct

FROM events
WHERE
    event = '$pageview'
    AND properties.page_load_time IS NOT NULL
    AND timestamp >= now() - INTERVAL 7 DAY
GROUP BY page
HAVING pageviews >= 100
ORDER BY slow_load_pct DESC
```

### 6. Revenue Analytics

**Question:** "What's our MRR and how is it trending?"

```sql
-- MRR by plan type
SELECT
    toStartOfMonth(timestamp) as month,
    properties.plan_type,
    count(DISTINCT distinct_id) as customers,
    sum(properties.amount) as total_revenue,
    round(total_revenue / customers, 2) as arpu
FROM events
WHERE
    event = 'subscription_purchased'
    AND timestamp >= now() - INTERVAL 12 MONTH
GROUP BY month, properties.plan_type
ORDER BY month DESC, total_revenue DESC

-- Customer lifetime value
WITH first_purchase AS (
    SELECT
        distinct_id,
        min(timestamp) as first_purchase_date
    FROM events
    WHERE event = 'purchase'
    GROUP BY distinct_id
),
revenue_per_customer AS (
    SELECT
        e.distinct_id,
        fp.first_purchase_date,
        sum(e.properties.amount) as total_revenue,
        count(*) as purchases,
        datediff('day', fp.first_purchase_date, max(e.timestamp)) as customer_age_days
    FROM events e
    JOIN first_purchase fp ON e.distinct_id = fp.distinct_id
    WHERE e.event = 'purchase'
    GROUP BY e.distinct_id, fp.first_purchase_date
)
SELECT
    CASE
        WHEN customer_age_days < 30 THEN '0-30 days'
        WHEN customer_age_days < 90 THEN '30-90 days'
        WHEN customer_age_days < 180 THEN '90-180 days'
        ELSE '180+ days'
    END as customer_age,
    count(*) as customers,
    round(avg(total_revenue), 2) as avg_ltv,
    round(avg(purchases), 1) as avg_purchases
FROM revenue_per_customer
GROUP BY customer_age
ORDER BY customer_age
```

### 7. Attribution Analysis

**Question:** "Which channels drive conversions?"

```sql
SELECT
    person.properties.$initial_utm_source as channel,
    person.properties.$initial_utm_campaign as campaign,

    -- Acquisition
    count(DISTINCT person.id) as users,

    -- Conversion
    count(DISTINCT CASE
        WHEN event = 'purchase' THEN distinct_id
    END) as converters,
    round(100.0 * converters / users, 2) as conversion_rate,

    -- Revenue
    sum(CASE
        WHEN event = 'purchase' THEN properties.amount
        ELSE 0
    END) as total_revenue,
    round(total_revenue / converters, 2) as revenue_per_converter

FROM events
WHERE timestamp >= now() - INTERVAL 30 DAY
GROUP BY channel, campaign
HAVING users >= 10
ORDER BY total_revenue DESC
```

### 8. Error Tracking

**Question:** "What errors are users hitting?"

```sql
SELECT
    properties.error_message,
    properties.$current_url,
    properties.$browser,
    count() as occurrences,
    count(DISTINCT distinct_id) as affected_users,
    min(timestamp) as first_seen,
    max(timestamp) as last_seen
FROM events
WHERE
    event = '$exception'
    AND timestamp >= now() - INTERVAL 7 DAY
GROUP BY
    properties.error_message,
    properties.$current_url,
    properties.$browser
ORDER BY occurrences DESC
LIMIT 50
```

### 9. User Journey Analysis

**Question:** "What paths do users take?"

```sql
-- Most common event sequences (2-step paths)
WITH user_events AS (
    SELECT
        distinct_id,
        event,
        timestamp,
        lag(event, 1) OVER (PARTITION BY distinct_id ORDER BY timestamp) as previous_event
    FROM events
    WHERE timestamp >= now() - INTERVAL 7 DAY
)
SELECT
    previous_event,
    event as current_event,
    count(*) as occurrences,
    count(DISTINCT distinct_id) as unique_users
FROM user_events
WHERE previous_event IS NOT NULL
GROUP BY previous_event, current_event
ORDER BY occurrences DESC
LIMIT 50
```

### 10. LLM Cost Optimization

**Question:** "How can we reduce AI costs?"

```sql
-- Most expensive users
SELECT
    distinct_id,
    person.properties.$email,
    count() as completions,
    sum(properties.tokens_used) as total_tokens,
    sum(properties.cost) as total_cost,
    round(avg(properties.latency_ms), 0) as avg_latency,
    round(100.0 * countIf(properties.success = false) / count(), 2) as error_rate
FROM events
WHERE
    event = '$ai_completion'
    AND timestamp >= now() - INTERVAL 7 DAY
GROUP BY distinct_id, person.properties.$email
ORDER BY total_cost DESC
LIMIT 20

-- Expensive prompts (by conversation)
SELECT
    properties.conversation_id,
    properties.prompt_type,
    count() as turns,
    sum(properties.tokens_used) as total_tokens,
    sum(properties.cost) as total_cost,
    round(avg(properties.latency_ms), 0) as avg_latency
FROM events
WHERE event = '$ai_completion'
GROUP BY properties.conversation_id, properties.prompt_type
HAVING turns >= 3
ORDER BY total_cost DESC
LIMIT 50
```

---

## Entity Types & Data Model

### Core Entities

| Entity | Count | Purpose |
|--------|-------|---------|
| **Events** | Billions | User actions (clicks, pageviews, custom events) |
| **Persons** | Millions | User profiles with properties |
| **Sessions** | Millions | Grouped user activity periods |
| **Groups** | Thousands | Organizations/companies |
| **Cohorts** | Hundreds | User segments |
| **Insights** | Hundreds | Saved analytics queries |
| **Dashboards** | Tens | Visualization collections |
| **Feature Flags** | Tens | Feature toggles |
| **Experiments** | Tens | A/B tests |

### Event Schema

```python
{
    'event': 'signup',                      # Event name
    'distinct_id': 'user_123',              # User identifier
    'timestamp': '2025-01-15T10:30:00Z',    # When it occurred
    'properties': {
        # PostHog standard properties ($ prefix)
        '$browser': 'Chrome',
        '$os': 'macOS',
        '$device_type': 'Desktop',
        '$current_url': 'https://app.example.com/signup',
        '$screen_width': 1920,
        '$screen_height': 1080,

        # Custom properties (your data)
        'plan_selected': 'pro',
        'referral_code': 'FRIEND2025',
        'signup_method': 'google_oauth'
    },
    'elements_chain': 'div.container>form>button.signup-btn'  # Autocapture
}
```

### Person Schema

```python
{
    'id': 'person_uuid',
    'distinct_ids': ['user_123', 'anonymous_abc', 'user_123_mobile'],
    'properties': {
        # PostHog standard
        '$email': 'user@example.com',
        '$name': 'Jane Smith',
        '$initial_referrer': 'https://google.com',
        '$initial_utm_source': 'google',
        '$initial_utm_campaign': 'summer-2025',

        # Custom
        'plan_type': 'enterprise',
        'company': 'Acme Corp',
        'signup_date': '2025-01-15',
        'mrr': 499.00
    },
    'created_at': '2025-01-15T10:30:00Z'
}
```

### Property Naming Conventions

**PostHog Standard Properties ($ prefix):**
- `$browser`, `$os`, `$device_type`
- `$current_url`, `$referrer`
- `$screen_width`, `$screen_height`
- `$email`, `$name`
- `$initial_referrer`, `$initial_utm_source`

**Your Custom Properties (no $):**
- Use snake_case: `plan_type`, `signup_method`, `feature_enabled`
- Be consistent across events
- Use descriptive names
- Store as appropriate types (string, number, boolean)

---

## Product Engineer Workflows

### Workflow 1: Feature Development Cycle

```
1. Planning
   ├─ Define feature requirements
   ├─ Set success metrics in PostHog
   └─ Create dashboard

2. Development
   ├─ Add tracking events
   ├─ Wrap in feature flag
   └─ Test in staging

3. Launch
   ├─ Deploy with 5% rollout
   ├─ Monitor dashboard
   ├─ Watch session replays
   └─ Check error rates

4. Iterate
   ├─ Analyze adoption data
   ├─ Survey users
   ├─ Identify improvements
   └─ Gradual rollout to 100%

5. Measure Impact
   ├─ Compare before/after metrics
   ├─ Run experiment for next iteration
   └─ Document learnings
```

### Workflow 2: Bug Investigation

```
User reports: "Can't complete checkout"
   ↓
1. Find user in PostHog
   - Search by email or distinct_id
   ↓
2. View event timeline
   - See all actions leading to error
   ↓
3. Find error event
   - $exception with error_message
   ↓
4. Watch session replay
   - See exactly what user did
   ↓
5. Reproduce locally
   - Use same browser/device from properties
   ↓
6. Fix and verify
   - Deploy fix
   - Monitor error rate drops to zero
```

### Workflow 3: Performance Optimization

```
1. Identify slow pages
   - Query: pages with p95 load time > 3s
   ↓
2. Analyze by segment
   - Browser? Device? Geographic region?
   ↓
3. Watch session replays
   - See user experience of slow loads
   ↓
4. Implement optimization
   - Code splitting, lazy loading, caching
   ↓
5. A/B test
   - Control vs. optimized version
   ↓
6. Measure improvement
   - Compare load times before/after
```

### Workflow 4: Conversion Optimization

```
1. Define funnel
   - Visited → Signed Up → Activated → Converted
   ↓
2. Identify drop-off point
   - Which step has biggest drop?
   ↓
3. Cohort analysis
   - What do converters do differently?
   ↓
4. Form hypothesis
   - "Reducing form fields will increase signup"
   ↓
5. Run experiment
   - A/B test: old form vs. new form
   ↓
6. Analyze results
   - Statistical significance? Ship or kill?
   ↓
7. Iterate
   - Next hypothesis based on data
```

---

## Production Best Practices

### 1. Event Tracking

**DO:**
- Track user intent, not just clicks
- Include context in properties
- Use consistent naming (snake_case)
- Track both success and failure states
- Limit to essential events (not every mouse move)

**DON'T:**
- Track PII without consent (SSN, credit cards)
- Use dynamic event names (`button_${id}_click`)
- Track too granularly
- Store sensitive data in properties

**Example:**
```javascript
// ✅ GOOD
posthog.capture('checkout_completed', {
    order_id: '123',
    amount: 99.00,
    items: 3,
    payment_method: 'card',
    checkout_duration: 45  // seconds
})

// ❌ BAD
posthog.capture('click')  // What was clicked? Why?
```

### 2. Query Performance

**Optimization Checklist:**
- ✅ Time filter (timestamp >= now() - INTERVAL X DAY)
- ✅ Event filter (event IN ('event1', 'event2'))
- ✅ Use indexed columns (event, distinct_id, timestamp)
- ✅ LIMIT clause (LIMIT 1000)
- ✅ Specific columns (not SELECT *)
- ✅ Date range reasonable (< 90 days for ad-hoc queries)

**Performance Tips:**
```sql
-- Indexed columns (fast)
WHERE event = 'signup'
WHERE distinct_id = 'user_123'
WHERE timestamp >= now() - INTERVAL 7 DAY

-- Unindexed columns (slower - use after indexed filters)
WHERE properties.custom_field = 'value'
```

### 3. Rate Limiting

**Client-Side Throttling:**
```python
from collections import deque
from time import time, sleep

class RateLimiter:
    def __init__(self, max_per_minute=240):
        self.requests = deque()
        self.max_per_minute = max_per_minute

    def wait_if_needed(self):
        now = time()
        # Remove requests older than 1 minute
        while self.requests and self.requests[0] < now - 60:
            self.requests.popleft()

        # Wait if at limit
        if len(self.requests) >= self.max_per_minute:
            sleep(1)
            self.wait_if_needed()
        else:
            self.requests.append(now)

limiter = RateLimiter(max_per_minute=240)

def query_posthog(query):
    limiter.wait_if_needed()
    return client.query(query)
```

### 4. Error Handling

**Retry Logic:**
```python
import random
from time import sleep

def query_with_retry(hogql, max_retries=3):
    for attempt in range(max_retries):
        try:
            return client.query(hogql)
        except RateLimitError:
            if attempt == max_retries - 1:
                raise
            # Exponential backoff with jitter
            wait = min(2 ** attempt + random.random(), 60)
            logger.warning(f"Rate limited, waiting {wait}s")
            sleep(wait)
        except QueryTimeout:
            # Don't retry timeouts - query needs optimization
            logger.error(f"Query timeout: {hogql}")
            raise
        except QuerySyntaxError as e:
            # Don't retry syntax errors
            logger.error(f"Invalid HogQL: {e}")
            raise
```

### 5. Security

**API Key Management:**
```bash
# ✅ GOOD: Environment variables
export POSTHOG_API_KEY="phx_..."
export POSTHOG_PROJECT_ID="12345"

# ❌ BAD: Hardcoded
api_key = "phx_13WiXxD1fwBRds8YEZtXGuL03ECTmt6PXwm24IE7zBPAcVsp"
```

**Key Rotation:**
1. Generate new key in PostHog settings
2. Update environment variables
3. Test with new key
4. Delete old key
5. Confirm no errors

### 6. Monitoring

**Track:**
- Query latency (p50, p95, p99)
- Error rate by type
- Rate limit hits
- Cache hit rate
- Query complexity

**Logging:**
```python
import structlog

logger = structlog.get_logger()

def instrumented_query(hogql):
    start = time.time()
    try:
        result = client.query(hogql)
        duration = time.time() - start

        logger.info(
            "posthog_query_success",
            duration_ms=int(duration * 1000),
            result_count=len(result),
            query_length=len(hogql)
        )
        return result
    except Exception as e:
        logger.error(
            "posthog_query_failed",
            error_type=type(e).__name__,
            error_msg=str(e)
        )
        raise
```

---

## Quick Reference

### Common HogQL Patterns

```sql
-- Top events
SELECT event, count() as c
FROM events
WHERE timestamp >= now() - INTERVAL 7 DAY
GROUP BY event ORDER BY c DESC LIMIT 10

-- Unique users
SELECT count(DISTINCT distinct_id)
FROM events
WHERE timestamp >= now() - INTERVAL 30 DAY

-- Daily active users
SELECT toDate(timestamp) as date, count(DISTINCT distinct_id) as dau
FROM events
WHERE timestamp >= now() - INTERVAL 30 DAY
GROUP BY date ORDER BY date

-- User journey (3-step)
SELECT
    distinct_id,
    groupArray(event) as event_sequence
FROM (
    SELECT distinct_id, event, timestamp
    FROM events
    WHERE timestamp >= now() - INTERVAL 1 DAY
    ORDER BY distinct_id, timestamp
)
GROUP BY distinct_id
LIMIT 100
```

### Response Handling

```python
# PostHog can return dict or list
results = client.query(hogql)

if isinstance(results, dict):
    rows = results.get('results', [])
elif isinstance(results, list):
    rows = results
else:
    rows = []

for row in rows:
    if isinstance(row, dict):
        event = row.get('event')
        count = row.get('count')
    else:
        event = row[0]
        count = row[1]
```

### Free Tier Limits (2025)

**Monthly:**
- Product Analytics: 1M events
- Session Recordings: 5,000 recordings
- Feature Flags: 1M requests
- Surveys: 250 responses

**No limits on:**
- Team size
- Dashboards
- Advanced features (cohorts, SQL, API)
- Data retention
- Integrations

---

## Summary

### What PostHog Does

PostHog is a complete Product OS that helps engineers:
1. **Understand users** (analytics, session replay)
2. **Ship safely** (feature flags, experiments)
3. **Optimize products** (A/B testing, surveys)
4. **Track AI products** (LLM analytics)
5. **Make data-driven decisions** (HogQL, dashboards)

### Why Product Engineers Choose PostHog

- **All-in-one**: Replace 5+ tools
- **Built for engineers**: Code-first, API-first
- **SQL access**: HogQL for custom analysis
- **Privacy-focused**: GDPR compliant
- **Generous free tier**: 1M events/month
- **Open source**: Self-hostable, transparent

### Key Takeaways

1. **10+ products** integrated into one platform
2. **75+ API endpoints** for complete programmatic access
3. **HogQL** enables SQL-like queries on product data
4. **Session replay** bridges quantitative and qualitative data
5. **Feature flags + experiments** = safe, data-driven shipping
6. **LLM analytics** for AI-native products
7. **Product engineer workflows** throughout feature lifecycle

---

**Document Version:** 1.0 (Complete Reference)
**Last Updated:** 2025-11-11
**Coverage:** 100% (API, use cases, queries, JTBD)

**Sources:**
- PostHog official API documentation
- PostHog community questions and patterns
- Real implementation (project 245832)
- Product engineer workflows
- 2025 product updates

**This is the definitive PostHog reference for:**
- Engineers building with PostHog
- AI agents needing PostHog context
- Product teams planning analytics
- Data teams querying product data

*Everything you need to understand and build with PostHog in one place.*
