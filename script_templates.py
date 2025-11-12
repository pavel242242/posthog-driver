"""
PostHog Script Templates for Common Operations

Pre-built script templates for typical analytics, ETL, and data lookup tasks.
These templates can be executed in E2B sandboxes with variable substitution.
"""

# ==================== EVENT TRACKING ====================

CAPTURE_EVENT = """
import sys
import json
sys.path.insert(0, '/home/user')

from posthog_driver import PostHogClient

# Initialize client
client = PostHogClient(
    api_key='<api_key_placeholder>',
    project_id='<project_id_placeholder>',
    project_api_key='<project_api_key_placeholder>'
)

# Capture event
result = client.capture_event(
    event='{event_name}',
    distinct_id='{distinct_id}',
    properties={properties}
)

print(json.dumps({{'success': True, 'result': result}}))
"""

CAPTURE_BATCH_EVENTS = """
import sys
import json
sys.path.insert(0, '/home/user')

from posthog_driver import PostHogClient

client = PostHogClient(
    api_key='<api_key_placeholder>',
    project_id='<project_id_placeholder>',
    project_api_key='<project_api_key_placeholder>'
)

# Batch event capture
events = {events_list}

result = client.capture_batch(events)

print(json.dumps({{'success': True, 'events_count': len(events), 'result': result}}))
"""

# ==================== ANALYTICS QUERIES ====================

GET_RECENT_EVENTS = """
import sys
import json
sys.path.insert(0, '/home/user')

from posthog_driver import PostHogClient

client = PostHogClient(
    api_key='<api_key_placeholder>',
    project_id='<project_id_placeholder>'
)

# Query recent events
events = client.get_events(
    event_name='{event_name}' if '{event_name}' else None,
    after='{after_date}',
    limit={limit}
)

print(json.dumps({{
    'success': True,
    'count': len(events),
    'events': events
}}, indent=2))
"""

HOGQL_QUERY = """
import sys
import json
sys.path.insert(0, '/home/user')

from posthog_driver import PostHogClient

client = PostHogClient(
    api_key='<api_key_placeholder>',
    project_id='<project_id_placeholder>'
)

# Execute HogQL query
query = '''{hogql_query}'''

results = client.query(query)

print(json.dumps({{
    'success': True,
    'rows': len(results),
    'results': results
}}, indent=2))
"""

GET_INSIGHTS = """
import sys
import json
sys.path.insert(0, '/home/user')

from posthog_driver import PostHogClient

client = PostHogClient(
    api_key='<api_key_placeholder>',
    project_id='<project_id_placeholder>'
)

# List insights
insights = client.get_insights(
    insight_type='{insight_type}' if '{insight_type}' else None,
    limit={limit}
)

# Format for display
formatted_insights = [
    {{
        'id': i['id'],
        'name': i['name'],
        'type': i.get('filters', {{}}).get('insight', 'UNKNOWN'),
        'created_at': i.get('created_at')
    }}
    for i in insights
]

print(json.dumps({{
    'success': True,
    'count': len(insights),
    'insights': formatted_insights
}}, indent=2))
"""

# ==================== DATA EXPORT / ETL ====================

EXPORT_EVENTS_ETL = """
import sys
import json
sys.path.insert(0, '/home/user')

from posthog_driver import PostHogClient

client = PostHogClient(
    api_key='<api_key_placeholder>',
    project_id='<project_id_placeholder>'
)

# Export events for date range
events = client.export_events(
    start_date='{start_date}',
    end_date='{end_date}',
    event_names={event_names} if {event_names} else None
)

print(json.dumps({{
    'success': True,
    'exported_count': len(events),
    'date_range': {{
        'start': '{start_date}',
        'end': '{end_date}'
    }},
    'sample': events[:5] if len(events) > 5 else events
}}, indent=2))
"""

EXPORT_COHORT_DATA = """
import sys
import json
sys.path.insert(0, '/home/user')

from posthog_driver import PostHogClient

client = PostHogClient(
    api_key='<api_key_placeholder>',
    project_id='<project_id_placeholder>'
)

# Get cohort details
cohort_id = {cohort_id}
persons = client.get_persons(cohort_id=cohort_id)

print(json.dumps({{
    'success': True,
    'cohort_id': cohort_id,
    'persons_count': len(persons),
    'persons': persons
}}, indent=2))
"""

# ==================== COHORT & PERSONA ANALYSIS ====================

IDENTIFY_POWER_USERS = """
import sys
import json
sys.path.insert(0, '/home/user')

from posthog_driver import PostHogClient

client = PostHogClient(
    api_key='<api_key_placeholder>',
    project_id='<project_id_placeholder>'
)

# Find power users using HogQL
# Users who performed key action {min_occurrences} or more times in last {days} days
hogql = '''
SELECT
    distinct_id,
    count() as action_count,
    person.properties.email as email
FROM events
WHERE
    event = '{key_event}'
    AND timestamp >= now() - INTERVAL {days} DAY
GROUP BY distinct_id, email
HAVING action_count >= {min_occurrences}
ORDER BY action_count DESC
LIMIT 100
'''

power_users = client.query(hogql)

print(json.dumps({{
    'success': True,
    'power_users_count': len(power_users),
    'criteria': {{
        'event': '{key_event}',
        'min_occurrences': {min_occurrences},
        'time_period_days': {days}
    }},
    'power_users': power_users
}}, indent=2))
"""

IDENTIFY_CHURN_RISK = """
import sys
import json
sys.path.insert(0, '/home/user')

from posthog_driver import PostHogClient

client = PostHogClient(
    api_key='<api_key_placeholder>',
    project_id='<project_id_placeholder>'
)

# Find users at risk of churning
# Users who were active in previous period but not in recent period
hogql = '''
SELECT DISTINCT
    distinct_id,
    person.properties.email as email,
    max(timestamp) as last_seen
FROM events
WHERE
    timestamp >= now() - INTERVAL {lookback_days} DAY
    AND timestamp < now() - INTERVAL {inactive_days} DAY
    AND distinct_id NOT IN (
        SELECT DISTINCT distinct_id
        FROM events
        WHERE timestamp >= now() - INTERVAL {inactive_days} DAY
    )
GROUP BY distinct_id, email
ORDER BY last_seen DESC
LIMIT 200
'''

churn_risk_users = client.query(hogql)

print(json.dumps({{
    'success': True,
    'churn_risk_count': len(churn_risk_users),
    'criteria': {{
        'inactive_for_days': {inactive_days},
        'previously_active_days': {lookback_days}
    }},
    'users': churn_risk_users
}}, indent=2))
"""

# ==================== FUNNEL & CONVERSION ANALYSIS ====================

ANALYZE_FUNNEL_DROPOFF = """
import sys
import json
sys.path.insert(0, '/home/user')

from posthog_driver import PostHogClient

client = PostHogClient(
    api_key='<api_key_placeholder>',
    project_id='<project_id_placeholder>'
)

# Analyze funnel drop-off points
# Simple sequential funnel analysis with HogQL
funnel_steps = {funnel_steps}  # e.g., ['Signup Started', 'Email Verified', 'Profile Completed']

# Get count for each step
results = {{}}
for step in funnel_steps:
    hogql = f'''
    SELECT count(DISTINCT distinct_id) as count
    FROM events
    WHERE event = '{{step}}'
    AND timestamp >= '{{start_date}}'
    AND timestamp <= '{{end_date}}'
    '''

    step_result = client.query(hogql)
    results[step] = step_result[0]['count'] if step_result else 0

# Calculate drop-off rates
funnel_data = []
prev_count = None
for step in funnel_steps:
    count = results[step]
    dropoff_rate = None
    if prev_count is not None and prev_count > 0:
        dropoff_rate = ((prev_count - count) / prev_count) * 100

    funnel_data.append({{
        'step': step,
        'users': count,
        'dropoff_rate': round(dropoff_rate, 2) if dropoff_rate else None
    }})
    prev_count = count

print(json.dumps({{
    'success': True,
    'funnel_steps': len(funnel_steps),
    'funnel_analysis': funnel_data
}}, indent=2))
"""

# ==================== FEATURE FLAG & EXPERIMENTATION ====================

GET_EXPERIMENT_RESULTS = """
import sys
import json
sys.path.insert(0, '/home/user')

from posthog_driver import PostHogClient

client = PostHogClient(
    api_key='<api_key_placeholder>',
    project_id='<project_id_placeholder>'
)

# Get experiment results
experiments = client.get_experiments()

# Format results
formatted_experiments = [
    {{
        'id': exp['id'],
        'name': exp['name'],
        'feature_flag': exp.get('feature_flag_key'),
        'start_date': exp.get('start_date'),
        'end_date': exp.get('end_date'),
        'results': exp.get('results', {{}})
    }}
    for exp in experiments
]

print(json.dumps({{
    'success': True,
    'experiments_count': len(experiments),
    'experiments': formatted_experiments
}}, indent=2))
"""

EVALUATE_FEATURE_FLAGS = """
import sys
import json
sys.path.insert(0, '/home/user')

from posthog_driver import PostHogClient

client = PostHogClient(
    api_key='<api_key_placeholder>',
    project_id='<project_id_placeholder>',
    project_api_key='<project_api_key_placeholder>'
)

# Get all feature flags
flags = client.get_feature_flags()

# Evaluate flag for specific user
flag_evaluation = client.evaluate_flag(
    key='{flag_key}',
    distinct_id='{distinct_id}'
)

print(json.dumps({{
    'success': True,
    'total_flags': len(flags),
    'evaluation': flag_evaluation,
    'user': '{distinct_id}'
}}, indent=2))
"""

# ==================== ERROR TRACKING & MONITORING ====================

TRACK_ERROR_EVENTS = """
import sys
import json
sys.path.insert(0, '/home/user')

from posthog_driver import PostHogClient

client = PostHogClient(
    api_key='<api_key_placeholder>',
    project_id='<project_id_placeholder>'
)

# Query error events
hogql = '''
SELECT
    event,
    properties.error_type as error_type,
    properties.error_message as error_message,
    count() as occurrences,
    count(DISTINCT distinct_id) as affected_users
FROM events
WHERE
    event LIKE '%error%' OR event LIKE '%failed%'
    AND timestamp >= '{start_date}'
    AND timestamp <= '{end_date}'
GROUP BY event, error_type, error_message
ORDER BY occurrences DESC
LIMIT 50
'''

errors = client.query(hogql)

print(json.dumps({{
    'success': True,
    'error_types_count': len(errors),
    'errors': errors
}}, indent=2))
"""

# ==================== TEMPLATE REGISTRY ====================

TEMPLATES = {
    # Event tracking
    'capture_event': CAPTURE_EVENT,
    'capture_batch': CAPTURE_BATCH_EVENTS,

    # Analytics queries
    'get_recent_events': GET_RECENT_EVENTS,
    'hogql_query': HOGQL_QUERY,
    'get_insights': GET_INSIGHTS,

    # Data export
    'export_events': EXPORT_EVENTS_ETL,
    'export_cohort': EXPORT_COHORT_DATA,

    # Persona analysis
    'identify_power_users': IDENTIFY_POWER_USERS,
    'identify_churn_risk': IDENTIFY_CHURN_RISK,

    # Funnel analysis
    'analyze_funnel': ANALYZE_FUNNEL_DROPOFF,

    # Experiments
    'get_experiments': GET_EXPERIMENT_RESULTS,
    'evaluate_flags': EVALUATE_FEATURE_FLAGS,

    # Error tracking
    'track_errors': TRACK_ERROR_EVENTS
}


def get_template(name: str) -> str:
    """
    Get a script template by name.

    Args:
        name: Template name from TEMPLATES registry

    Returns:
        Template string

    Raises:
        KeyError: Unknown template name
    """
    if name not in TEMPLATES:
        available = ', '.join(TEMPLATES.keys())
        raise KeyError(
            f"Unknown template '{name}'. Available templates: {available}"
        )
    return TEMPLATES[name]


def list_templates() -> list:
    """List all available template names."""
    return list(TEMPLATES.keys())
