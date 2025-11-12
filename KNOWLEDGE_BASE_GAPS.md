# PostHog Knowledge Base - Gap Analysis

**Critical evaluation of POSTHOG_KNOWLEDGE_BASE.md completeness**

---

## Executive Summary

**Current State:** Knowledge base covers **core analytics workflow** (events, HogQL, basic entities)

**Coverage Score:**
- **User Intent Mapping**: 30% - Has personas but lacks intent → query translation
- **PostHog API Coverage**: 40% - Covers 8 main endpoints, missing ~15 others
- **Overall Completeness**: 35% - Good foundation, significant gaps for production

---

## Gap 1: User Intent Mapping (Critical)

### What We Have ✅

```
User Personas:
  - Product Engineers (typical questions listed)
  - Technical PMs (typical questions listed)
  - Data Analysts
  - Growth Marketers
  - Customer Success

Real Examples:
  - "Where do users drop off?" → Funnel query
  - "What drives conversion?" → Activity comparison query
```

### What's Missing ❌

#### 1.1 Intent Classification System

**Need:** Decision tree for query type selection

```
User Question Type → Query Strategy

"How many...?"          → Aggregation query (count, sum)
"Who...?"               → User segmentation (WHERE distinct_id IN...)
"Why...?"               → Correlation analysis (multiple queries + comparison)
"When...?"              → Time-series query (GROUP BY toDate(timestamp))
"Where do users...?"    → Funnel or path analysis
"What drives...?"       → Cohort comparison
"Which feature...?"     → Feature adoption query
```

**Example Missing:**
```markdown
### Intent: "Why are sales dropping?"

Step 1: Clarify the question
  - Time period? (last week vs. last month)
  - Metric definition? (revenue, transaction count, unique buyers)
  - Expected baseline? (compare to what?)

Step 2: Choose analysis type
  → Time-series trend (daily sales over period)
  → Cohort comparison (week-over-week)
  → Funnel analysis (where in purchase flow)

Step 3: Generate queries
Query 1: Overall trend
  SELECT toDate(timestamp) as date, count() as sales
  FROM events WHERE event = 'purchase' AND timestamp >= now() - INTERVAL 30 DAY
  GROUP BY date ORDER BY date

Query 2: Funnel to identify drop-off
  [Conversion funnel query]

Query 3: User segments
  [Compare converting vs. non-converting behavior]
```

#### 1.2 Question → Template Mapping

**Need:** Library of common questions mapped to HogQL templates

```markdown
### Question: "What are our most popular features?"

**Template:** Feature Usage Ranking
**HogQL:**
```sql
SELECT
    properties.feature_name as feature,
    count(DISTINCT distinct_id) as unique_users,
    count() as total_uses,
    round(total_uses / unique_users, 2) as uses_per_user
FROM events
WHERE
    event = 'feature_used'
    AND timestamp >= now() - INTERVAL {{time_period}}
GROUP BY feature
ORDER BY unique_users DESC
LIMIT 20
```

**Parameters:**
- {{time_period}}: 7 DAY, 30 DAY, 90 DAY
- Optional filter: properties.feature_category = {{category}}

**Interpretation:**
- unique_users: Breadth of adoption
- uses_per_user: Depth of engagement
- Look for: High adoption + high engagement = core feature
```

**Missing Templates:**
- User activation ("What gets users to their aha moment?")
- Retention analysis ("Who comes back?")
- Churn prediction ("Who's at risk?")
- Revenue analytics ("What drives LTV?")
- Feature correlation ("What features predict conversion?")
- User journey analysis ("What paths lead to success?")
- A/B test analysis ("Did experiment X work?")
- Time-to-value ("How long until first value?")

#### 1.3 Ambiguity Resolution

**Need:** Guide for handling vague questions

```markdown
### Handling Ambiguous Questions

**Example: "Show me user engagement"**

❌ **Bad Response:** Run generic query and hope it's relevant

✅ **Good Response:** Clarify intent first

**Clarification Questions:**
1. What time period? (today, this week, this month, all time)
2. How do you define engagement? (DAU, events per user, session duration, feature usage)
3. Which users? (all users, new users, paying users, specific cohort)
4. What's the goal? (track trend, compare segments, identify issues, report to exec)

**Based on answers, choose:**
- Trend chart: Daily engagement over time
- Cohort analysis: Engagement by user type
- Distribution: Histogram of engagement levels
- Correlation: Engagement vs. conversion
```

#### 1.4 Multi-Query Workflows

**Need:** Guidance on when one query isn't enough

```markdown
### Complex Intent: "Why did conversion drop?"

**This requires 4+ queries:**

1. **Trend Confirmation**
   - Verify conversion actually dropped
   - Identify when the drop started
   - Query: Daily conversion rate over 30 days

2. **Funnel Analysis**
   - Find which step broke
   - Compare before vs. after drop
   - Query: Conversion funnel for both periods

3. **Segment Comparison**
   - Which user segments affected?
   - New vs. returning? Channels? Devices?
   - Query: Conversion by segment before/after

4. **Behavior Changes**
   - Did user behavior change?
   - Are users taking different paths?
   - Query: Path analysis for both periods

5. **External Factors**
   - Check annotations (deployments, campaigns)
   - Look for correlated events
   - Query: Timeline of product changes
```

---

## Gap 2: PostHog API Coverage (Important)

### What We Have ✅

**8 Endpoints Documented:**
1. Query API (POST /api/projects/{id}/query/) - **Well covered**
2. Events API (GET/POST /api/projects/{id}/events/)
3. Persons API (GET/POST /api/projects/{id}/persons/)
4. Insights API (GET/POST /api/projects/{id}/insights/)
5. Cohorts API (GET /api/projects/{id}/cohorts/)
6. Feature Flags API (GET /api/projects/{id}/feature_flags/)
7. Sessions API (GET /api/projects/{id}/sessions/)
8. Annotations API (GET /api/projects/{id}/annotations/)
9. Experiments API (GET /api/projects/{id}/experiments/)

### What's Missing ❌

#### 2.1 Data Management APIs

```markdown
### Missing: Data Management

**Exports:**
- GET /api/projects/{id}/exports/
- POST /api/projects/{id}/exports/ - Create export job
- GET /api/projects/{id}/exports/{export_id}/ - Check status

**Event Deletion:**
- DELETE /api/projects/{id}/events/{event_id}/

**Bulk Operations:**
- POST /api/projects/{id}/batch/ - Batch event ingestion

**Use case:** Data analysts need to export data for warehouse integration
```

#### 2.2 Actions API

```markdown
### Missing: Actions (Saved Event Definitions)

**Endpoints:**
- GET /api/projects/{id}/actions/
- POST /api/projects/{id}/actions/
- PATCH /api/projects/{id}/actions/{action_id}/
- DELETE /api/projects/{id}/actions/{action_id}/

**What are Actions?**
Actions are saved definitions of events, allowing:
- Combine multiple events (signup_clicked OR signup_completed)
- Add filters (pageview WHERE url contains '/pricing')
- Autocapture naming (clicks on button with class 'cta-button')

**Use case:** Product managers define business events once, use everywhere
```

#### 2.3 Dashboards API

```markdown
### Missing: Dashboards

**Endpoints:**
- GET /api/projects/{id}/dashboards/
- POST /api/projects/{id}/dashboards/
- GET /api/projects/{id}/dashboards/{dashboard_id}/
- PATCH /api/projects/{id}/dashboards/{dashboard_id}/
- DELETE /api/projects/{id}/dashboards/{dashboard_id}/

**Schema:**
{
  "id": 123,
  "name": "Executive Dashboard",
  "description": "Weekly metrics for leadership",
  "pinned": true,
  "items": [
    {"insight_id": 456, "layout": {"x": 0, "y": 0, "w": 6, "h": 4}},
    {"insight_id": 789, "layout": {"x": 6, "y": 0, "w": 6, "h": 4}}
  ],
  "tags": ["executive", "weekly"]
}

**Use case:** Programmatically create/update dashboards for customers
```

#### 2.4 Session Recordings API

```markdown
### Missing: Session Recordings

**Endpoints:**
- GET /api/projects/{id}/session_recordings/
- GET /api/projects/{id}/session_recordings/{recording_id}/
- GET /api/projects/{id}/session_recordings/{recording_id}/snapshots/

**What is Session Recording?**
PostHog captures user sessions (mouse movements, clicks, scrolls) for replay

**Use case:** Customer success wants to see how user X interacted with feature Y
```

#### 2.5 Organization & Project Management

```markdown
### Missing: Admin APIs

**Organization:**
- GET /api/organizations/
- PATCH /api/organizations/{id}/
- GET /api/organizations/{id}/members/
- POST /api/organizations/{id}/members/ - Invite user

**Projects:**
- GET /api/projects/
- POST /api/projects/ - Create new project
- PATCH /api/projects/{id}/

**Teams:**
- GET /api/projects/{id}/teams/
- PATCH /api/projects/{id}/teams/{team_id}/

**Use case:** SaaS platforms provisioning PostHog for customers
```

#### 2.6 Other Missing Endpoints

```markdown
### Webhooks
- POST /api/projects/{id}/hooks/
- GET /api/projects/{id}/hooks/

### Surveys
- GET /api/projects/{id}/surveys/
- POST /api/projects/{id}/surveys/

### Early Access Features
- GET /api/projects/{id}/early_access_features/

### Integrations
- GET /api/projects/{id}/integrations/
- POST /api/projects/{id}/integrations/

### Batch Exports
- GET /api/projects/{id}/batch_exports/
- POST /api/projects/{id}/batch_exports/
```

### API Coverage Summary

| Category | Documented | Missing | Coverage |
|----------|------------|---------|----------|
| **Analytics** | Query, Events, Persons, Sessions | Actions, Paths | 70% |
| **Insights** | Insights, Annotations | Dashboards, Saved Queries | 40% |
| **Product Features** | Feature Flags, Experiments | Surveys, Early Access | 50% |
| **User Management** | Persons, Cohorts | Teams, Permissions | 60% |
| **Data Management** | Basic Events API | Exports, Imports, Deletion, Batch | 20% |
| **Admin** | Project info only | Org management, Billing | 10% |
| **Recordings** | - | Session Recordings API | 0% |
| **Integrations** | - | Webhooks, Integrations | 0% |
| **Overall** | **9 endpoints** | **~18 endpoints** | **35%** |

---

## Gap 3: Intent → Implementation Examples (Critical)

### What's Missing: End-to-End Workflows

**Need:** Complete examples showing user question → insight

```markdown
### Workflow: "Which acquisition channel has best ROI?"

**Step 1: Define metrics**
- Acquisition: Users with $initial_utm_source property
- ROI: (Revenue - Cost) / Cost
- Need: UTM tracking + revenue events

**Step 2: Data requirements**
✅ Available: Events with properties.$initial_utm_source
❌ Missing: Cost per channel (needs external data)

**Step 3: Queries**

Query 1: Users by channel
```sql
SELECT
    person.properties.$initial_utm_source as channel,
    count(DISTINCT distinct_id) as users
FROM events
WHERE person.properties.$initial_utm_source IS NOT NULL
GROUP BY channel
```

Query 2: Revenue by channel
```sql
SELECT
    person.properties.$initial_utm_source as channel,
    sum(properties.amount) as revenue,
    count(DISTINCT distinct_id) as paying_users,
    revenue / paying_users as arpu
FROM events
WHERE
    event = 'purchase'
    AND person.properties.$initial_utm_source IS NOT NULL
GROUP BY channel
ORDER BY revenue DESC
```

Query 3: Combine with cost data (requires external join)
*Note: PostHog doesn't store marketing cost, need to:*
1. Export channel data from PostHog
2. Join with cost data from ad platforms
3. Calculate ROI = (revenue - cost) / cost

**Step 4: Interpretation**
- High revenue ≠ high ROI (if cost is also high)
- Consider both new user acquisition and LTV
- Look at cohort retention by channel

**Step 5: Follow-up questions**
- "What do high-ROI channel users do differently?"
- "What's the retention rate by channel?"
- "Time-to-conversion by channel?"
```

---

## Gap 4: Advanced HogQL Patterns (Moderate)

### What's Missing: Complex Query Patterns

```markdown
### 1. Cohort Retention Analysis

**Intent:** "Do users who engage early stay longer?"

**Pattern:** Cohort definition + retention calculation

```sql
-- Step 1: Define early engagement cohort
WITH engaged_users AS (
    SELECT DISTINCT distinct_id
    FROM events
    WHERE
        timestamp >= person.properties.$signup_date
        AND timestamp <= person.properties.$signup_date + INTERVAL 7 DAY
    GROUP BY distinct_id
    HAVING count() >= 10  -- 10+ events in first week
)

-- Step 2: Calculate retention
SELECT
    week_number,
    count(DISTINCT CASE WHEN e.distinct_id IN engaged_users THEN e.distinct_id END) as engaged_retained,
    count(DISTINCT CASE WHEN e.distinct_id NOT IN engaged_users THEN e.distinct_id END) as not_engaged_retained
FROM events e
WHERE
    toStartOfWeek(timestamp) = toStartOfWeek(person.properties.$signup_date) + INTERVAL week_number WEEK
GROUP BY week_number
ORDER BY week_number
```

### 2. User Journey Paths

**Intent:** "What paths lead to conversion?"

**Pattern:** Sequence aggregation

```sql
SELECT
    arrayJoin(
        arrayMap(
            x -> (x.1, x.2),
            arraySort((a, b) -> a.2 < b.2, groupArray((event, timestamp)))
        )
    ) as event_sequence,
    count(DISTINCT distinct_id) as users,
    sum(CASE WHEN converted = 1 THEN 1 ELSE 0 END) as converters
FROM (
    SELECT
        distinct_id,
        event,
        timestamp,
        max(CASE WHEN event = 'purchase' THEN 1 ELSE 0 END) OVER (PARTITION BY distinct_id) as converted
    FROM events
    WHERE timestamp >= now() - INTERVAL 7 DAY
)
GROUP BY event_sequence
HAVING users >= 10
ORDER BY converters DESC
LIMIT 20
```

### 3. Feature Correlation Matrix

**Intent:** "Which features predict conversion?"

**Pattern:** Cross-tabulation with statistical significance

```sql
-- For each feature, calculate:
-- 1. Adoption rate among converters
-- 2. Adoption rate among non-converters
-- 3. Lift = (converter_rate / non_converter_rate)

SELECT
    feature,
    converter_adoption_rate,
    non_converter_adoption_rate,
    round(converter_adoption_rate / non_converter_adoption_rate, 2) as lift
FROM (
    SELECT
        properties.feature_name as feature,

        -- Converters
        count(DISTINCT CASE
            WHEN distinct_id IN (SELECT distinct_id FROM events WHERE event = 'purchase')
            THEN distinct_id
        END) / (SELECT count(DISTINCT distinct_id) FROM events WHERE event = 'purchase') as converter_adoption_rate,

        -- Non-converters
        count(DISTINCT CASE
            WHEN distinct_id NOT IN (SELECT distinct_id FROM events WHERE event = 'purchase')
            THEN distinct_id
        END) / (SELECT count(DISTINCT distinct_id) FROM events WHERE distinct_id NOT IN (SELECT distinct_id FROM events WHERE event = 'purchase')) as non_converter_adoption_rate

    FROM events
    WHERE event = 'feature_used'
    GROUP BY feature
)
WHERE converter_adoption_rate > 0 AND non_converter_adoption_rate > 0
ORDER BY lift DESC
```

---

## Gap 5: Production Best Practices (Important)

### What's Missing: Operational Guidance

```markdown
### 1. Query Performance Optimization

**Problem:** Query takes 30+ seconds

**Diagnostic checklist:**
- [ ] Query has time filter? (timestamp >= ...)
- [ ] Time range < 90 days?
- [ ] Using indexed columns? (event, distinct_id, timestamp)
- [ ] LIMIT clause present?
- [ ] Avoiding SELECT *?
- [ ] Not filtering on unindexed properties?

**Optimization techniques:**

Before:
```sql
SELECT * FROM events WHERE properties.custom_field = 'value'  -- SLOW
```

After:
```sql
SELECT event, distinct_id, timestamp, properties.custom_field
FROM events
WHERE
    timestamp >= now() - INTERVAL 7 DAY  -- Time filter first
    AND event IN ('event1', 'event2')    -- Index filter second
    AND properties.custom_field = 'value' -- Property filter last
LIMIT 1000
```

### 2. Error Handling Strategies

**Problem:** Query fails in production

**Error types and handling:**

| Error | Cause | Solution |
|-------|-------|----------|
| `timeout` | Query > 60s | Add time filter, reduce range |
| `rate_limit_exceeded` | > 240 req/min | Implement exponential backoff |
| `syntax_error` | Invalid HogQL | Validate before sending |
| `authentication_failed` | Invalid API key | Check key, rotate if needed |
| `project_not_found` | Wrong project ID | Verify project exists |

**Retry logic:**
```python
def query_with_retry(hogql, max_retries=3):
    for attempt in range(max_retries):
        try:
            return client.query(hogql)
        except RateLimitError as e:
            if attempt == max_retries - 1:
                raise
            wait = min(2 ** attempt + random.random(), 60)
            logger.warning(f"Rate limited, waiting {wait}s")
            time.sleep(wait)
        except QueryTimeout as e:
            # Don't retry timeouts - query needs optimization
            logger.error(f"Query timeout: {hogql}")
            raise
        except QuerySyntaxError as e:
            # Don't retry syntax errors
            logger.error(f"Invalid HogQL: {e}")
            raise
```

### 3. Caching Strategy

**Problem:** Repeated identical queries waste API calls

**Caching patterns:**

```python
from functools import lru_cache
import hashlib
import json

class QueryCache:
    def __init__(self, ttl_seconds=300):
        self.cache = {}
        self.ttl = ttl_seconds

    def get(self, hogql):
        key = hashlib.md5(hogql.encode()).hexdigest()
        if key in self.cache:
            result, timestamp = self.cache[key]
            if time.time() - timestamp < self.ttl:
                return result
        return None

    def set(self, hogql, result):
        key = hashlib.md5(hogql.encode()).hexdigest()
        self.cache[key] = (result, time.time())

cache = QueryCache(ttl_seconds=300)  # 5 minute cache

def cached_query(hogql):
    cached = cache.get(hogql)
    if cached:
        return cached

    result = client.query(hogql)
    cache.set(hogql, result)
    return result
```

### 4. Monitoring & Observability

**What to monitor:**

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
            query_hash=hashlib.md5(hogql.encode()).hexdigest()[:8],
            duration_ms=int(duration * 1000),
            result_count=len(result),
            query_length=len(hogql)
        )
        return result

    except Exception as e:
        duration = time.time() - start
        logger.error(
            "posthog_query_failed",
            query_hash=hashlib.md5(hogql.encode()).hexdigest()[:8],
            duration_ms=int(duration * 1000),
            error_type=type(e).__name__,
            error_msg=str(e)
        )
        raise
```

**Metrics to track:**
- Query latency (p50, p95, p99)
- Error rate by type
- Rate limit hits
- Cache hit rate
- Query complexity (length, result size)
```

---

## Recommendations for Knowledge Base Enhancement

### Phase 1: Critical Gaps (1-2 days)

**Add to POSTHOG_KNOWLEDGE_BASE.md:**

1. **New Section: "User Intent → Query Mapping"**
   - Decision tree for query type
   - 20 common questions with templates
   - Ambiguity resolution guide
   - Multi-query workflow examples

2. **Expand "Best Practices":**
   - Query performance optimization
   - Error handling strategies
   - Caching patterns
   - Monitoring & observability

### Phase 2: API Completion (2-3 days)

**Create new document: POSTHOG_API_REFERENCE.md**

1. Document missing 15+ endpoints
2. Full CRUD examples for each
3. Response schemas
4. Error codes
5. Rate limits per endpoint

### Phase 3: Advanced Patterns (1-2 days)

**Add to POSTHOG_KNOWLEDGE_BASE.md:**

1. **New Section: "Advanced HogQL Patterns"**
   - Cohort retention analysis
   - User journey paths
   - Feature correlation
   - Predictive scoring
   - Anomaly detection

### Phase 4: Production Guide (1 day)

**Create: POSTHOG_PRODUCTION_GUIDE.md**

1. Performance optimization
2. Error handling
3. Monitoring
4. Security
5. Cost optimization
6. Scaling strategies

---

## Scoring: Current vs. Ideal

| Dimension | Current | Ideal | Gap |
|-----------|---------|-------|-----|
| **Intent Mapping** | 30% | 100% | Need decision trees, templates, workflows |
| **API Coverage** | 35% | 100% | Need 15+ missing endpoints documented |
| **HogQL Patterns** | 50% | 100% | Need advanced query patterns |
| **Production** | 40% | 100% | Need monitoring, caching, optimization |
| **Examples** | 60% | 100% | Need 20+ end-to-end workflows |
| **Overall** | **43%** | **100%** | **57% gap** |

---

## Next Steps

1. **Immediate (this session):**
   - Add "Intent → Query Mapping" section
   - Add 10 common question templates
   - Document missing API endpoints

2. **Short-term (next iteration):**
   - Create POSTHOG_API_REFERENCE.md
   - Add advanced HogQL patterns
   - Create production guide

3. **Long-term (future):**
   - Build interactive query builder
   - Create ML-based intent classifier
   - Generate query templates from example questions

---

**Assessment:** The knowledge base is a **good foundation** but needs **significant enhancement** for production use, especially in intent mapping and API completeness.

**Priority:** Intent mapping is **critical** - it's the bridge between user questions and driver capabilities.
