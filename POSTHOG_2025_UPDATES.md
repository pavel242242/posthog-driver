# PostHog 2025 Updates & Latest Features

**What's new in PostHog and how it impacts the driver**

---

## New Product Features (2025)

### 1. Max AI - Automated Insights

**What it is:** AI-powered insights and code generation within PostHog

**Capabilities:**
- Automated insight discovery
- Query generation from natural language
- Code suggestions for implementation

**Impact on Driver:**
- Our driver enables similar capability (Claude generates HogQL queries)
- Can complement Max AI by providing external AI agent access
- Opportunity: Benchmark our Claude integration vs. Max AI

### 2. LLM Analytics

**What it is:** Analytics specifically for AI-native products

**Tracks:**
- Token usage and costs
- Model performance metrics
- Latency measurements
- Conversation quality
- Prompt effectiveness

**New Entity Type:**
```python
# LLM-specific events
{
    'event': '$ai_completion',
    'properties': {
        'model': 'gpt-4',
        'tokens_used': 1234,
        'latency_ms': 850,
        'cost': 0.0123,
        'success': true,
        'conversation_id': 'conv_abc123'
    }
}
```

**HogQL Queries for LLM Analytics:**
```sql
-- Token usage by model
SELECT
    properties.model,
    sum(properties.tokens_used) as total_tokens,
    sum(properties.cost) as total_cost,
    avg(properties.latency_ms) as avg_latency
FROM events
WHERE event = '$ai_completion'
  AND timestamp >= now() - INTERVAL 7 DAY
GROUP BY properties.model

-- Conversation quality analysis
SELECT
    properties.conversation_id,
    count() as turns,
    max(properties.success) as successful,
    sum(properties.tokens_used) as conversation_tokens
FROM events
WHERE event = '$ai_completion'
GROUP BY properties.conversation_id
HAVING turns > 5  -- Multi-turn conversations only
ORDER BY conversation_tokens DESC
```

**Impact on Driver:**
- Should add LLM analytics examples to templates
- New persona: AI Product Engineers
- Opportunity: Track our own Claude usage via PostHog!

### 3. Data Warehouse Integration

**What it is:** Built-in SQL query interface for external data

**Features:**
- Import data from S3, BigQuery, Snowflake, Postgres
- Join PostHog events with external data
- Run SQL across multiple sources

**Example:**
```sql
-- Join PostHog events with CRM data
SELECT
    e.distinct_id,
    count() as events,
    c.plan_type,
    c.mrr
FROM events e
JOIN warehouse.customers c ON e.distinct_id = c.user_id
WHERE e.timestamp >= now() - INTERVAL 30 DAY
GROUP BY e.distinct_id, c.plan_type, c.mrr
```

**Impact on Driver:**
- Should document warehouse join patterns
- Enable hybrid analytics (product + business data)

### 4. Website Analytics (Lightweight)

**What it is:** Privacy-focused Google Analytics alternative

**Tracks:**
- Pageviews and traffic sources
- Web vitals (Core Web Vitals: LCP, FID, CLS)
- Visitor behavior
- No cookies, GDPR-compliant

**Use Case:** Public website analytics separate from product analytics

**Impact on Driver:**
- Different event patterns (website vs. product)
- Could support marketing analytics use cases

---

## PostHog Product Suite (Complete)

**10+ Products (as of 2025):**

| # | Product | Description | Driver Support |
|---|---------|-------------|----------------|
| 1 | Product Analytics | Events, trends, funnels | ✅ Full |
| 2 | Session Replay | User session recordings | ✅ API access |
| 3 | Feature Flags | Gradual rollouts | ✅ Full |
| 4 | Experiments | A/B testing | ✅ Full |
| 5 | Surveys | In-app feedback | ✅ Full |
| 6 | **LLM Analytics** | AI product tracking | 🆕 Add templates |
| 7 | **Data Warehouse** | External data joins | 🆕 Document patterns |
| 8 | **Website Analytics** | Public site tracking | 🆕 Add examples |
| 9 | **Max AI** | AI insights | ⚠️ Complementary |
| 10 | Event Pipelines | Data routing | ⚠️ Admin feature |

**Company Update:**
- $70M Series D (June 2025)
- $920M valuation (led by Stripe)
- Expanded from 1 → 10+ products

---

## Common User Questions & HogQL Patterns

### From PostHog Community

**Most Common Questions:**

#### 1. "How do I query event properties in HogQL?"

**Answer:**
```sql
-- Event properties: properties.field_name
SELECT
    properties.$browser,
    properties.custom_field,
    count() as events
FROM events
WHERE timestamp >= now() - INTERVAL 7 DAY
GROUP BY properties.$browser, properties.custom_field

-- Person properties: person.properties.field_name
SELECT
    person.properties.$email,
    person.properties.plan_type,
    count() as events
FROM events
GROUP BY person.properties.$email, person.properties.plan_type
```

#### 2. "How do I join event data with person data?"

**Answer:** HogQL auto-joins when you reference `person.*`:
```sql
SELECT
    distinct_id,
    event,
    person.properties.$email,  -- Auto-joined!
    person.created_at
FROM events
WHERE person.properties.plan = 'enterprise'
```

#### 3. "How do I do advanced breakdowns?"

**Answer:** Use CASE statements:
```sql
SELECT
    CASE
        WHEN properties.$screen_width < 768 THEN 'mobile'
        WHEN properties.$screen_width < 1024 THEN 'tablet'
        ELSE 'desktop'
    END as device_category,
    count() as events
FROM events
GROUP BY device_category
```

#### 4. "Why is my query slow?"

**Common Issues:**
- ❌ No time filter (scans entire dataset)
- ❌ Filtering on unindexed property
- ❌ No LIMIT clause
- ❌ Too wide date range (>90 days)

**Solutions:**
```sql
-- ✅ Fast query
SELECT event, count()
FROM events
WHERE
    timestamp >= now() - INTERVAL 7 DAY  -- Time filter
    AND event IN ('signup', 'purchase')  -- Indexed column
GROUP BY event
ORDER BY count() DESC
LIMIT 100  -- Explicit limit
```

#### 5. "How do I calculate conversion rates?"

**Answer:** Use subqueries for funnel math:
```sql
SELECT
    step,
    users,
    round(100.0 * users / (SELECT count(DISTINCT distinct_id) FROM events WHERE event = 'pageview'), 2) as conversion_pct
FROM (
    SELECT 'pageview' as step, count(DISTINCT distinct_id) as users
    FROM events WHERE event = 'pageview'

    UNION ALL

    SELECT 'signup', count(DISTINCT distinct_id)
    FROM events WHERE event = 'signup'

    UNION ALL

    SELECT 'purchase', count(DISTINCT distinct_id)
    FROM events WHERE event = 'purchase'
)
```

#### 6. "How do I track user journeys?"

**Answer:** Use window functions:
```sql
SELECT
    distinct_id,
    event,
    timestamp,
    row_number() OVER (PARTITION BY distinct_id ORDER BY timestamp) as step_number,
    lag(event, 1) OVER (PARTITION BY distinct_id ORDER BY timestamp) as previous_event
FROM events
WHERE timestamp >= now() - INTERVAL 1 DAY
ORDER BY distinct_id, timestamp
```

#### 7. "How do I aggregate by time periods?"

**Answer:** Use time functions:
```sql
-- Hourly
SELECT
    toStartOfHour(timestamp) as hour,
    count() as events
FROM events
WHERE timestamp >= now() - INTERVAL 24 HOUR
GROUP BY hour
ORDER BY hour

-- Daily
SELECT
    toDate(timestamp) as date,
    count(DISTINCT distinct_id) as dau
FROM events
WHERE timestamp >= now() - INTERVAL 30 DAY
GROUP BY date
ORDER BY date

-- Weekly
SELECT
    toStartOfWeek(timestamp) as week,
    count() as events
FROM events
GROUP BY week
ORDER BY week
```

#### 8. "How do I find power users?"

**Answer:** Activity-based segmentation:
```sql
SELECT
    distinct_id,
    person.properties.$email,
    count() as total_events,
    count(DISTINCT toDate(timestamp)) as active_days,
    round(total_events / active_days, 2) as events_per_day
FROM events
WHERE timestamp >= now() - INTERVAL 30 DAY
GROUP BY distinct_id, person.properties.$email
HAVING total_events >= 100  -- Definition of power user
ORDER BY total_events DESC
```

#### 9. "How do I do cohort retention analysis?"

**Answer:** Time-based cohort comparison:
```sql
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
    END) as week_1_retention,
    round(100.0 * week_1_retention / cohort_size, 2) as week_1_retention_pct
FROM cohorts c
LEFT JOIN events e ON c.distinct_id = e.distinct_id
GROUP BY c.cohort_week
ORDER BY c.cohort_week DESC
```

#### 10. "How do I track feature adoption?"

**Answer:** Feature usage by user segment:
```sql
SELECT
    person.properties.plan_type as plan,
    count(DISTINCT CASE
        WHEN event = 'feature_used' AND properties.feature_name = 'new_dashboard'
        THEN distinct_id
    END) as users_adopted,
    count(DISTINCT distinct_id) as total_users,
    round(100.0 * users_adopted / total_users, 2) as adoption_rate
FROM events
WHERE timestamp >= now() - INTERVAL 30 DAY
GROUP BY plan
ORDER BY adoption_rate DESC
```

---

## Product Engineer Workflows

### How Product Engineers Use PostHog

**Core Workflow:**
```
1. Build feature
2. Ship with feature flag (gradual rollout)
3. Monitor with product analytics
4. Watch session replays
5. Survey users
6. Iterate based on data
```

### Common Use Cases

#### 1. Feature Validation

**Question:** "Is the new feature being used?"

**PostHog Workflow:**
1. Add feature flag to control access
2. Track `feature_used` events
3. Create insight: adoption rate over time
4. Watch session replays of feature usage
5. Survey users who tried it

**HogQL Query:**
```sql
-- Feature adoption by day
SELECT
    toDate(timestamp) as date,
    count(DISTINCT distinct_id) as users,
    count() as uses
FROM events
WHERE
    event = 'feature_used'
    AND properties.feature_name = 'new_dashboard'
    AND timestamp >= now() - INTERVAL 30 DAY
GROUP BY date
ORDER BY date
```

#### 2. Bug Investigation

**Question:** "Why did user X see an error?"

**PostHog Workflow:**
1. Search for user by email/ID
2. View their timeline of events
3. Find error event
4. Watch session replay
5. See exact steps leading to error

**HogQL Query:**
```sql
-- User's error timeline
SELECT
    timestamp,
    event,
    properties.$current_url,
    properties.error_message
FROM events
WHERE
    person.properties.$email = 'user@example.com'
    AND event IN ('$pageview', '$exception', 'error_occurred')
    AND timestamp >= now() - INTERVAL 7 DAY
ORDER BY timestamp
```

#### 3. Rollout Monitoring

**Question:** "Is the new version causing issues?"

**PostHog Workflow:**
1. Deploy with 5% rollout
2. Monitor error rate by variant
3. Compare metrics (control vs. test)
4. Gradually increase if stable

**HogQL Query:**
```sql
-- Error rate by variant
SELECT
    properties.feature_flag_variant as variant,
    count(DISTINCT distinct_id) as users,
    countIf(event = '$exception') as errors,
    round(1000.0 * errors / users, 2) as errors_per_1000_users
FROM events
WHERE timestamp >= now() - INTERVAL 1 DAY
GROUP BY variant
```

#### 4. Conversion Optimization

**Question:** "What makes users convert?"

**PostHog Workflow:**
1. Define conversion event (e.g., `subscription_purchased`)
2. Compare converter vs. non-converter behavior
3. Identify differentiating actions
4. Test hypotheses with experiments

**HogQL Query:**
```sql
-- Actions that predict conversion
WITH converters AS (
    SELECT DISTINCT distinct_id
    FROM events
    WHERE event = 'subscription_purchased'
)
SELECT
    event,
    count(DISTINCT CASE WHEN c.distinct_id IS NOT NULL THEN e.distinct_id END) as converter_count,
    count(DISTINCT CASE WHEN c.distinct_id IS NULL THEN e.distinct_id END) as non_converter_count,
    round(
        converter_count::float / (SELECT count(*) FROM converters),
        3
    ) as converter_rate,
    round(
        non_converter_count::float / (SELECT count(DISTINCT distinct_id) FROM events WHERE distinct_id NOT IN (SELECT distinct_id FROM converters)),
        3
    ) as non_converter_rate,
    round(converter_rate / non_converter_rate, 2) as lift
FROM events e
LEFT JOIN converters c ON e.distinct_id = c.distinct_id
WHERE e.event != 'subscription_purchased'
GROUP BY event
HAVING converter_count >= 5  -- Minimum sample size
ORDER BY lift DESC
LIMIT 20
```

#### 5. Performance Monitoring

**Question:** "Are users experiencing slow load times?"

**PostHog Workflow:**
1. Track performance events
2. Monitor web vitals
3. Break down by device/browser
4. Correlate with user behavior

**HogQL Query:**
```sql
-- Performance metrics by page
SELECT
    properties.$current_url as page,
    count() as pageviews,
    round(avg(properties.page_load_time), 0) as avg_load_ms,
    round(percentile(properties.page_load_time, 0.95), 0) as p95_load_ms,
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

---

## Driver Enhancement Recommendations

Based on 2025 updates and community patterns:

### 1. Add LLM Analytics Templates

**New script template:** `llm_analytics.py`
```python
def analyze_llm_usage(time_period='7d'):
    """
    Analyze LLM usage patterns

    Returns:
    - Token usage by model
    - Cost analysis
    - Latency metrics
    - Success rates
    """
    query = f'''
    SELECT
        properties.model,
        count() as completions,
        sum(properties.tokens_used) as total_tokens,
        sum(properties.cost) as total_cost,
        avg(properties.latency_ms) as avg_latency,
        round(100.0 * countIf(properties.success = true) / count(), 2) as success_rate
    FROM events
    WHERE
        event = '$ai_completion'
        AND timestamp >= now() - INTERVAL {time_period}
    GROUP BY properties.model
    ORDER BY total_cost DESC
    '''
    return client.query(query)
```

### 2. Add Product Engineer Persona Templates

**Focus:** Feature validation, bug investigation, rollout monitoring

**New templates:**
- `feature_adoption_analysis.py`
- `error_investigation.py`
- `rollout_monitoring.py`
- `conversion_attribution.py`

### 3. Add Common HogQL Patterns

**Documentation section:** "Common Query Patterns"

Include 15+ examples:
- Property access patterns
- Time-based aggregations
- Conversion funnels
- Cohort retention
- User journey analysis
- Performance monitoring

### 4. Update Entity Types

**Add:** LLM-specific event properties schema

```python
'$ai_completion': {
    'properties': {
        'model': 'Model identifier (gpt-4, claude-3, etc.)',
        'tokens_used': 'Total tokens consumed',
        'cost': 'API cost in USD',
        'latency_ms': 'Response time in milliseconds',
        'success': 'Boolean completion success',
        'conversation_id': 'Multi-turn conversation identifier',
        'prompt_tokens': 'Input tokens',
        'completion_tokens': 'Output tokens',
        'error': 'Error message if failed'
    }
}
```

### 5. Enhance Driver Examples

**Add advanced examples:**
- Data warehouse joins
- Window function queries
- Cohort analysis
- Multi-step funnels
- Attribution modeling

---

## Updated Free Tier Limits (2025)

**Monthly Limits:**
- Product Analytics: 1M events
- Session Recordings: 5,000 recordings
- Feature Flags: 1M requests
- Surveys: 250 responses

**No restrictions on:**
- Team size
- Dashboard complexity
- Advanced features (cohorts, SQL, API)
- Data retention
- Integrations

**This impacts driver testing:**
- Can test extensively on free tier
- No need for paid account for development
- 1M events = substantial testing capacity

---

## Summary: What Changed in 2025

| Aspect | Before | 2025 Update |
|--------|--------|-------------|
| **Products** | Product Analytics only | 10+ integrated products |
| **AI Features** | None | Max AI + LLM Analytics |
| **Data Access** | PostHog events only | Data Warehouse (external joins) |
| **Analytics** | Product-focused | Product + Website + LLM |
| **Funding** | Series C | $70M Series D ($920M valuation) |
| **Common Queries** | Basic aggregations | Complex HogQL with joins, windows |
| **Target Users** | Product managers | Product engineers (code + product) |

**Key Insight:** PostHog evolved from "product analytics" to "Product OS for engineers"

**Impact on Driver:**
- Should support all 10+ products (not just analytics)
- Need LLM analytics examples (growing use case)
- Product engineer workflows are primary persona
- HogQL complexity increased (more advanced patterns needed)

---

**Document Version:** 1.0
**Last Updated:** 2025-11-11
**Sources:** PostHog official blog, documentation, web search (2025)

**Next Actions:**
1. Add LLM analytics template to driver
2. Create product engineer workflow examples
3. Document 15+ common HogQL patterns
4. Update persona documentation (emphasize product engineers)
5. Add data warehouse join examples
