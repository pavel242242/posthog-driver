# AI Developer Guide: Building Production-Ready Python Drivers

**Lessons Learned from Building PostHog Driver for Claude Agent SDK**

This guide captures hard-won lessons from building a production-ready Python driver that integrates with Claude Agent SDK and E2B sandboxes. Use this as a checklist when building similar projects.

---

## Table of Contents

1. [Project Architecture](#project-architecture)
2. [Security First](#security-first)
3. [Development Foundations](#development-foundations)
4. [Production Readiness](#production-readiness)
5. [Claude SDK Integration](#claude-sdk-integration)
6. [Testing Strategy](#testing-strategy)
7. [Documentation](#documentation)
8. [Common Pitfalls](#common-pitfalls)
9. [Deployment Checklist](#deployment-checklist)

---

## Project Architecture

### The Driver Contract Pattern

**What We Built:** A driver that implements a standard 3-method interface for dynamic data discovery.

```python
class PostHogClient:
    def list_objects(self) -> List[str]:
        """Return available entity types (events, persons, cohorts, etc.)"""

    def get_fields(self, object_name: str) -> Dict[str, Any]:
        """Return schema for a specific entity type"""

    def query(self, hogql_query: str) -> List[Dict[str, Any]]:
        """Execute queries against the data source"""
```

**Why This Pattern:**
- Dynamic discovery of available data
- Self-documenting API
- Claude can explore capabilities without hardcoded knowledge
- Standard interface across different data sources

**Lesson:** Start with the contract interface before implementing methods. This forces you to think about the API surface first.

---

## Security First

### Critical Security Lessons

**🔴 MISTAKE WE MADE:** Hardcoded API keys in example files for "convenience"

**Impact:**
- Keys exposed in 3 Python files
- Keys in git commit history
- Keys in documentation examples
- Required full git history rewrite
- Key rotation needed

**What We Should Have Done:**

```python
# ❌ NEVER DO THIS
POSTHOG_API_KEY = 'phx_EXAMPLE_KEY_NEVER_HARDCODE_REAL_KEYS_HERE'

# ✅ ALWAYS DO THIS
POSTHOG_API_KEY = os.getenv('POSTHOG_API_KEY')

# Add validation
if not POSTHOG_API_KEY:
    raise ValueError("POSTHOG_API_KEY environment variable is required")
```

**Security Checklist:**

- [ ] **No hardcoded secrets** anywhere (code, docs, examples, tests)
- [ ] **Environment variables only** for all credentials
- [ ] **Validate required env vars** at startup
- [ ] **Pre-commit hooks** to catch secrets (use `detect-secrets`)
- [ ] **Git history clean** (never commit secrets, rewrite if exposed)
- [ ] **.env.example** with placeholders only
- [ ] **.gitignore** includes `.env`, `.env.local`

### SQL Injection Prevention

**🔴 VULNERABILITY WE HAD:**

```python
# ❌ DANGEROUS - SQL Injection vulnerability
where_parts.append(f"event = '{event_name}'")
where_parts.append(f"distinct_id = '{distinct_id}'")
```

**Attack Example:**
```python
event_name = "signup' OR '1'='1"
# Results in: event = 'signup' OR '1'='1'  (returns ALL events!)
```

**✅ FIX: Query Builder with Escaping**

```python
class HogQLBuilder:
    def _escape_string(self, value: str) -> str:
        """Escape single quotes and validate input"""
        if not isinstance(value, str):
            raise ValueError("Expected string")
        # Escape single quotes (SQL standard)
        return value.replace("'", "''")

    def where_event(self, event_name: str):
        safe_name = self._escape_string(event_name)
        self.parts.append(f"event = '{safe_name}'")
        return self
```

**Lesson:** Never use f-strings for SQL/HogQL query construction. Always escape or use parameterized queries.

---

## Development Foundations

### 1. Logging Infrastructure (Day 1 Priority)

**🔴 MISTAKE:** We built the entire project without logging, making debugging impossible.

**What We Should Have Done:**

```python
# posthog_driver/logger.py
import logging
import os

def get_logger(name: str) -> logging.Logger:
    logger = logging.getLogger(name)
    level = os.getenv('LOG_LEVEL', 'INFO')
    logger.setLevel(getattr(logging, level))

    handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    ))
    logger.addHandler(handler)
    return logger

# Usage in every module
logger = get_logger(__name__)

def query(self, hogql_query: str):
    logger.info("Executing HogQL query", extra={
        "query_length": len(hogql_query),
        "project_id": self.project_id
    })
    try:
        result = self._make_request(...)
        logger.debug(f"Query succeeded: {len(result)} rows")
        return result
    except Exception as e:
        logger.error("Query failed", exc_info=True, extra={
            "query": hogql_query[:100]  # Log first 100 chars only
        })
        raise
```

**Logging Best Practices:**
- Add logging on Day 1, not as an afterthought
- Log at appropriate levels: DEBUG (verbose), INFO (operations), WARNING (retries), ERROR (failures)
- Include context in logs (project_id, user_id, query_id)
- Never log sensitive data (API keys, passwords, PII)
- Use structured logging (JSON format) for production

### 2. Type Hints Everywhere

```python
from typing import List, Dict, Any, Optional

def query(
    self,
    hogql_query: str,
    limit: Optional[int] = None
) -> List[Dict[str, Any]]:
    """Execute HogQL query.

    Args:
        hogql_query: The HogQL query string
        limit: Optional row limit

    Returns:
        List of result rows as dictionaries

    Raises:
        QueryError: If query execution fails
    """
```

**Enable mypy:**
```bash
pip install mypy
mypy posthog_driver/
```

### 3. Package Structure (setup.py from Day 1)

**🔴 MISTAKE:** We built without setup.py, making it impossible to install via pip.

**✅ FIX: Create setup.py immediately**

```python
# setup.py
from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setup(
    name="posthog-driver",
    version="1.0.0",
    author="Your Name",
    description="PostHog API client for Claude Agent SDK",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/yourusername/posthog-driver",
    packages=find_packages(),
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
    ],
    python_requires=">=3.8",
    install_requires=[
        "requests>=2.31.0,<3.0.0",
        "python-dotenv>=1.0.0,<2.0.0",
    ],
    extras_require={
        "dev": [
            "pytest>=7.0.0",
            "mypy>=1.0.0",
            "black>=23.0.0",
            "flake8>=6.0.0",
        ],
        "e2b": [
            "e2b>=0.15.0,<1.0.0",
        ],
    },
)
```

**Install locally:**
```bash
pip install -e .                    # Development install
pip install -e ".[dev]"              # With dev dependencies
pip install -e ".[dev,e2b]"          # With all extras
```

---

## Production Readiness

### 1. Exponential Backoff (Not Linear Retry)

**🔴 MISTAKE:** We implemented linear retry, which hammers APIs during outages.

```python
# ❌ LINEAR RETRY (bad during outages)
for attempt in range(max_retries):
    try:
        return self._make_request(...)
    except Exception:
        time.sleep(1)  # Always wait 1 second
```

**✅ EXPONENTIAL BACKOFF WITH JITTER:**

```python
import time
import random
from requests.exceptions import RequestException, Timeout

def _make_request_with_backoff(self, *args, **kwargs):
    max_retries = self.max_retries

    for attempt in range(max_retries):
        try:
            return self._make_request(*args, **kwargs)

        except (RequestException, Timeout) as e:
            if attempt < max_retries - 1:
                # Exponential backoff: 1s, 2s, 4s, 8s...
                wait_time = (2 ** attempt) + random.uniform(0, 1)
                logger.warning(
                    f"Retry {attempt+1}/{max_retries} after {wait_time:.2f}s",
                    extra={"error": str(e)}
                )
                time.sleep(wait_time)
            else:
                logger.error(f"Max retries exceeded", exc_info=True)
                raise
```

**Why Exponential Backoff:**
- Prevents thundering herd during outages
- Gives APIs time to recover
- Adds jitter to prevent synchronized retries

### 2. Rate Limiting (Client-Side)

**🔴 MISSING:** No rate limiting, will violate API limits in production.

**✅ IMPLEMENT CLIENT-SIDE RATE LIMITER:**

```python
from collections import deque
from time import time
from threading import Lock

class RateLimiter:
    def __init__(self, max_requests: int, time_window: int):
        """
        Args:
            max_requests: Max requests allowed
            time_window: Time window in seconds
        """
        self.max_requests = max_requests
        self.time_window = time_window
        self.requests = deque()
        self.lock = Lock()

    def acquire(self) -> bool:
        """Try to acquire a request slot."""
        with self.lock:
            now = time()

            # Remove expired timestamps
            while self.requests and self.requests[0] < now - self.time_window:
                self.requests.popleft()

            if len(self.requests) < self.max_requests:
                self.requests.append(now)
                return True

            return False

    def wait_and_acquire(self, timeout: Optional[float] = None):
        """Wait until a slot is available."""
        start = time()
        while True:
            if self.acquire():
                return

            if timeout and (time() - start) > timeout:
                raise TimeoutError("Rate limit wait timeout")

            time.sleep(0.1)

# Usage
class PostHogClient:
    def __init__(self, api_key: str, project_id: str):
        # PostHog limits: 240 requests/min, 1200 requests/hour
        self.rate_limiter = RateLimiter(max_requests=240, time_window=60)

    def _make_request(self, *args, **kwargs):
        self.rate_limiter.wait_and_acquire(timeout=30)
        return requests.request(*args, **kwargs)
```

### 3. Circuit Breaker Pattern

**Why:** Prevents cascading failures when downstream service is down.

```python
from enum import Enum
from datetime import datetime, timedelta

class CircuitState(Enum):
    CLOSED = "closed"      # Normal operation
    OPEN = "open"          # Failing, reject requests
    HALF_OPEN = "half_open"  # Testing recovery

class CircuitBreaker:
    def __init__(
        self,
        failure_threshold: int = 5,
        timeout: int = 60,
        success_threshold: int = 2
    ):
        self.failure_threshold = failure_threshold
        self.timeout = timeout
        self.success_threshold = success_threshold

        self.state = CircuitState.CLOSED
        self.failures = 0
        self.successes = 0
        self.opened_at = None

    def call(self, func, *args, **kwargs):
        if self.state == CircuitState.OPEN:
            if datetime.now() - self.opened_at > timedelta(seconds=self.timeout):
                self.state = CircuitState.HALF_OPEN
                self.successes = 0
            else:
                raise CircuitBreakerError("Circuit breaker is OPEN")

        try:
            result = func(*args, **kwargs)
            self._on_success()
            return result
        except Exception as e:
            self._on_failure()
            raise

    def _on_success(self):
        if self.state == CircuitState.HALF_OPEN:
            self.successes += 1
            if self.successes >= self.success_threshold:
                self.state = CircuitState.CLOSED
                self.failures = 0

        self.failures = 0

    def _on_failure(self):
        self.failures += 1
        if self.failures >= self.failure_threshold:
            self.state = CircuitState.OPEN
            self.opened_at = datetime.now()

# Usage
class PostHogClient:
    def __init__(self, api_key: str, project_id: str):
        self.circuit_breaker = CircuitBreaker(failure_threshold=5, timeout=60)

    def query(self, hogql_query: str):
        return self.circuit_breaker.call(self._query_impl, hogql_query)
```

### 4. Configuration Management

```python
from dataclasses import dataclass
from typing import Optional

@dataclass
class PostHogConfig:
    """Centralized configuration."""
    api_key: str
    project_id: str
    api_url: str = "https://us.posthog.com"
    project_api_key: Optional[str] = None
    timeout: int = 30
    max_retries: int = 3
    log_level: str = "INFO"
    rate_limit_per_minute: int = 240
    rate_limit_per_hour: int = 1200

    @classmethod
    def from_env(cls) -> 'PostHogConfig':
        """Load config from environment variables."""
        api_key = os.getenv('POSTHOG_API_KEY')
        if not api_key:
            raise ValueError("POSTHOG_API_KEY is required")

        project_id = os.getenv('POSTHOG_PROJECT_ID')
        if not project_id:
            raise ValueError("POSTHOG_PROJECT_ID is required")

        return cls(
            api_key=api_key,
            project_id=project_id,
            api_url=os.getenv('POSTHOG_API_URL', cls.api_url),
            timeout=int(os.getenv('POSTHOG_TIMEOUT', cls.timeout)),
            max_retries=int(os.getenv('POSTHOG_MAX_RETRIES', cls.max_retries)),
            log_level=os.getenv('LOG_LEVEL', cls.log_level),
        )

# Usage
config = PostHogConfig.from_env()
client = PostHogClient(config)
```

---

## Claude SDK Integration

### 1. Tool Definition Best Practices

```python
TOOL = {
    "name": "query_posthog",
    "description": """Query PostHog analytics data using natural language.

    This tool can:
    - Find top events and their frequencies
    - Analyze user funnels and drop-off points
    - Identify conversion drivers and patterns
    - Segment users by activity level
    - Track feature usage and adoption

    Examples:
    - "What are the top 5 events in the last 7 days?"
    - "Where do users drop off in the signup funnel?"
    - "Which features are most used by power users?"

    The tool accepts natural language questions and automatically
    translates them into HogQL queries.

    Note: Results are limited to 1000 rows by default.
    """,
    "input_schema": {
        "type": "object",
        "properties": {
            "question": {
                "type": "string",
                "description": "Natural language analytics question"
            },
            "time_period": {
                "type": "string",
                "enum": ["1d", "7d", "30d", "90d", "all"],
                "description": "Time period for analysis",
                "default": "7d"
            }
        },
        "required": ["question"]
    }
}
```

**Key Elements:**
- Clear, comprehensive description with examples
- Explain capabilities and limitations
- Use enums for constrained parameters
- Provide sensible defaults
- Document return format

### 2. System Prompts for Domain Context

**🔴 MISTAKE:** We didn't use system prompts, relying only on tool descriptions.

**✅ ADD DOMAIN-SPECIFIC SYSTEM PROMPT:**

```python
SYSTEM_PROMPT = """You are an expert product analytics assistant helping users
understand their PostHog data through natural language conversations.

Your capabilities:
- Query PostHog analytics data using the query_posthog tool
- Interpret event data, user behavior, and conversion metrics
- Provide actionable insights and recommendations
- Suggest follow-up analyses

When answering questions:
1. Analyze what data the user is seeking
2. Use the query_posthog tool with clear, specific questions
3. Interpret results in business context
4. Provide actionable insights, not just raw numbers
5. Suggest follow-up analyses when relevant

Output format:
- Lead with the direct answer
- Provide data-driven evidence
- Highlight key insights (trends, anomalies, correlations)
- Give actionable recommendations
- Suggest related analyses

Remember:
- You're analyzing product analytics, not general business data
- Focus on user behavior, conversion, retention, and engagement
- Be precise with numbers and time periods
- Explain technical terms (cohorts, funnels, etc.) when needed
"""

response = anthropic.messages.create(
    model="claude-sonnet-4-5-20250929",
    max_tokens=4096,
    system=SYSTEM_PROMPT,  # ← Add this
    tools=[TOOL],
    messages=messages
)
```

### 3. Error Handling with Retries

```python
from anthropic import Anthropic, RateLimitError, APIError
import time

def call_claude_with_retry(
    client: Anthropic,
    messages: List[Dict],
    tools: List[Dict],
    max_retries: int = 3
):
    for attempt in range(max_retries):
        try:
            return client.messages.create(
                model="claude-sonnet-4-5-20250929",
                max_tokens=4096,
                system=SYSTEM_PROMPT,
                tools=tools,
                messages=messages
            )
        except RateLimitError as e:
            if attempt < max_retries - 1:
                wait_time = (2 ** attempt) + random.uniform(0, 1)
                logger.warning(f"Claude rate limited, waiting {wait_time:.2f}s")
                time.sleep(wait_time)
            else:
                raise
        except APIError as e:
            logger.error(f"Claude API error: {e}", exc_info=True)
            raise
```

### 4. Streaming Responses

```python
def stream_claude_response(
    client: Anthropic,
    messages: List[Dict],
    tools: List[Dict]
):
    with client.messages.stream(
        model="claude-sonnet-4-5-20250929",
        max_tokens=4096,
        system=SYSTEM_PROMPT,
        tools=tools,
        messages=messages
    ) as stream:
        for text in stream.text_stream:
            print(text, end="", flush=True)

        # Handle tool calls
        final_message = stream.get_final_message()
        if final_message.stop_reason == "tool_use":
            # Process tool calls...
            pass
```

---

## Testing Strategy

### 1. Test Coverage Goals

**🔴 REALITY:** We achieved only 46% coverage.

**✅ TARGET: 95%+ coverage**

**Test Pyramid:**
```
                 E2E (5%)
            Integration (15%)
         Unit Tests (80%)
```

### 2. Essential Test Categories

```python
import pytest
from unittest.mock import Mock, patch

# 1. Driver Contract Tests
def test_list_objects():
    client = PostHogClient(api_key="test", project_id="123")
    objects = client.list_objects()
    assert "events" in objects
    assert "persons" in objects

# 2. Error Handling Tests
def test_query_with_rate_limit_error():
    client = PostHogClient(api_key="test", project_id="123")
    with patch.object(client, '_make_request') as mock_request:
        mock_request.side_effect = RateLimitError("Rate limited")

        with pytest.raises(RateLimitError):
            client.query("SELECT * FROM events")

# 3. Retry Logic Tests
def test_exponential_backoff():
    client = PostHogClient(api_key="test", project_id="123")

    call_times = []
    def mock_request(*args, **kwargs):
        call_times.append(time.time())
        if len(call_times) < 3:
            raise Timeout()
        return {"results": []}

    with patch.object(client, '_make_request', side_effect=mock_request):
        client.query("SELECT * FROM events")

    # Verify exponential backoff
    assert len(call_times) == 3
    assert call_times[1] - call_times[0] >= 1  # ~1s wait
    assert call_times[2] - call_times[1] >= 2  # ~2s wait

# 4. SQL Injection Tests
def test_query_escapes_sql_injection():
    builder = HogQLBuilder()
    builder.where_event("signup' OR '1'='1")
    query = builder.build()

    # Should escape single quotes
    assert "signup'' OR ''1''=''1" in query
    # Should NOT contain unescaped injection
    assert " OR '1'='1" not in query

# 5. Edge Case Tests
def test_query_with_empty_results():
    client = PostHogClient(api_key="test", project_id="123")
    with patch.object(client, '_make_request', return_value={"results": []}):
        results = client.query("SELECT * FROM events WHERE false")
        assert results == []

# 6. Integration Tests (with real API)
@pytest.mark.integration
def test_real_posthog_query():
    """Test against actual PostHog API (requires real credentials)"""
    client = PostHogClient.from_env()
    results = client.query("SELECT event, count() FROM events LIMIT 5")
    assert len(results) > 0
    assert "event" in results[0]
```

### 3. Test Fixtures

```python
# conftest.py
import pytest

@pytest.fixture
def mock_posthog_client():
    """Mock PostHog client for testing"""
    with patch('posthog_driver.PostHogClient._make_request') as mock:
        mock.return_value = {
            "results": [
                ["$pageview", 100],
                ["signup", 50]
            ]
        }
        client = PostHogClient(api_key="test", project_id="123")
        yield client

@pytest.fixture
def sample_events():
    """Sample event data for testing"""
    return [
        {"event": "$pageview", "timestamp": "2025-01-01T00:00:00Z"},
        {"event": "signup", "timestamp": "2025-01-01T00:01:00Z"},
    ]
```

---

## Documentation

### Essential Documents (Create on Day 1)

1. **LICENSE** (5 minutes)
```markdown
MIT License

Copyright (c) 2025 Your Name

Permission is hereby granted, free of charge, to any person obtaining a copy...
```

2. **CONTRIBUTING.md** (30 minutes)
```markdown
# Contributing

## Development Setup
1. Clone the repository
2. Create virtual environment: `python -m venv venv`
3. Install dev dependencies: `pip install -e ".[dev]"`
4. Run tests: `pytest`

## Code Standards
- Black for formatting: `black .`
- Flake8 for linting: `flake8`
- Mypy for type checking: `mypy posthog_driver/`
- 95%+ test coverage

## Pull Request Process
1. Create feature branch: `git checkout -b feature/your-feature`
2. Make changes with tests
3. Run full test suite
4. Submit PR with description
```

3. **SECURITY.md** (15 minutes)
```markdown
# Security Policy

## Reporting a Vulnerability

**DO NOT** open public issues for security vulnerabilities.

Email: security@yourproject.com

Include:
- Description of vulnerability
- Steps to reproduce
- Potential impact
- Suggested fix (if any)

We'll respond within 48 hours.
```

4. **CHANGELOG.md** (keep updated)
```markdown
# Changelog

## [1.0.0] - 2025-01-15

### Added
- Initial driver contract implementation
- E2B sandbox integration
- Claude Agent SDK integration
- 40 passing tests

### Security
- Fixed hardcoded API keys vulnerability
- Added SQL injection prevention
```

---

## Common Pitfalls

### 1. Starting Without Logging
**Mistake:** "We'll add logging later"
**Reality:** Debugging production issues becomes impossible
**Fix:** Add logging infrastructure on Day 1

### 2. Hardcoded Secrets for "Convenience"
**Mistake:** "Just for examples/testing"
**Reality:** Keys get committed, exposed, require history rewrite
**Fix:** Never hardcode secrets, even in examples

### 3. Linear Retry Logic
**Mistake:** Simple `for` loop with fixed sleep
**Reality:** Hammers APIs during outages, makes problems worse
**Fix:** Exponential backoff with jitter from the start

### 4. No SQL Injection Protection
**Mistake:** Using f-strings for query construction
**Reality:** Security vulnerability, data breach risk
**Fix:** Query builder with escaping or parameterized queries

### 5. Missing Production Infrastructure
**Mistake:** "We'll add rate limiting when we need it"
**Reality:** Violates API limits on day 1 of production
**Fix:** Build rate limiting, circuit breakers, monitoring from start

### 6. Insufficient Test Coverage
**Mistake:** "Happy path tests are enough"
**Reality:** Error cases cause production failures
**Fix:** Test error paths, edge cases, retry logic

### 7. No setup.py
**Mistake:** "Users can just copy the files"
**Reality:** Dependency hell, version conflicts
**Fix:** Create setup.py on Day 1

### 8. Missing Type Hints
**Mistake:** "Python is dynamically typed"
**Reality:** Refactoring becomes scary, bugs slip through
**Fix:** Type hints everywhere, enable mypy

---

## Deployment Checklist

### Pre-Production Checklist

**Security:**
- [ ] No hardcoded secrets anywhere
- [ ] Environment variable validation
- [ ] Pre-commit hooks for secret detection
- [ ] Git history clean
- [ ] SQL injection prevention
- [ ] Input validation on all user inputs

**Infrastructure:**
- [ ] Logging infrastructure complete
- [ ] Exponential backoff implemented
- [ ] Rate limiting active
- [ ] Circuit breaker implemented
- [ ] Health check endpoint
- [ ] Monitoring and alerting configured

**Code Quality:**
- [ ] setup.py created
- [ ] Type hints everywhere
- [ ] 95%+ test coverage
- [ ] All tests passing
- [ ] Linting (flake8) passing
- [ ] Type checking (mypy) passing
- [ ] Documentation complete

**Documentation:**
- [ ] LICENSE file
- [ ] CONTRIBUTING.md
- [ ] SECURITY.md
- [ ] CHANGELOG.md
- [ ] README.md with examples
- [ ] API documentation
- [ ] Architecture documentation

**Deployment:**
- [ ] Dockerfile created
- [ ] CI/CD pipeline configured
- [ ] Staging environment tested
- [ ] Load testing completed
- [ ] Rollback plan documented
- [ ] Runbook for common issues

---

## Key Metrics to Track

### Development Metrics
- Test coverage: Target 95%+
- Type hint coverage: Target 100%
- Documentation coverage: All public methods

### Production Metrics
- Request latency (p50, p95, p99)
- Error rate (target <0.1%)
- Rate limit hits (should be 0)
- Circuit breaker opens (monitor trends)
- Retry attempts (monitor for API issues)

### Business Metrics
- API calls per user
- Cost per query
- Active users
- Feature adoption

---

## Final Wisdom

### What We Learned the Hard Way

1. **Security is not optional** - One mistake (hardcoded keys) required rewriting entire git history
2. **Logging is infrastructure** - Not adding it from day 1 made debugging impossible
3. **Error paths matter more than happy paths** - 46% test coverage isn't enough
4. **Production readiness takes time** - We estimated 2 weeks, reality was 3-4 weeks
5. **Documentation is code** - Missing LICENSE blocked adoption, missing CONTRIBUTING blocked contributions

### The Golden Rule

> "Build production infrastructure from Day 1, not as an afterthought"

This includes:
- Logging
- Rate limiting
- Retry logic with exponential backoff
- Circuit breakers
- Monitoring
- Deployment artifacts

### Time Investment

| Phase | Estimated | Actual | Lesson |
|-------|-----------|--------|--------|
| Core driver | 1 week | 1 week | ✅ On track |
| Claude integration | 3 days | 4 days | Close |
| Documentation | 2 days | 3 days | More than expected |
| Security fixes | N/A | 1 day | 🔴 Unplanned |
| Production readiness | "Later" | 2-3 weeks | 🔴 Huge gap |

**Total: Estimated 2 weeks, Actual 4-5 weeks**

**Lesson:** Budget 2x time for production readiness, security, and polish.

---

## Quick Start Template

When starting a new Python driver project, use this template:

```bash
# 1. Create project structure
mkdir my-driver
cd my-driver
git init

# 2. Create essential files FIRST
touch LICENSE                    # MIT, Apache, etc.
touch README.md                  # Basic description
touch CONTRIBUTING.md            # Dev setup
touch SECURITY.md               # Security policy
touch CHANGELOG.md              # Start at v0.1.0
touch .gitignore                # Python, .env, etc.
touch setup.py                  # Package config
touch requirements.txt          # Dependencies
touch requirements-dev.txt      # Dev dependencies
touch .env.example              # Config template

# 3. Create package structure
mkdir my_driver
touch my_driver/__init__.py
touch my_driver/client.py
touch my_driver/exceptions.py
touch my_driver/logger.py
touch my_driver/config.py

# 4. Create tests
mkdir tests
touch tests/__init__.py
touch tests/test_client.py
touch tests/conftest.py

# 5. Set up pre-commit hooks
pip install pre-commit detect-secrets
cat > .pre-commit-config.yaml <<EOF
repos:
  - repo: https://github.com/Yelp/detect-secrets
    rev: v1.4.0
    hooks:
      - id: detect-secrets
EOF
pre-commit install

# 6. Start coding!
```

---

## Resources

### Tools We Used
- **Anthropic Claude SDK** - AI agent framework
- **E2B** - Secure code execution sandboxes
- **PostHog** - Product analytics platform
- **pytest** - Testing framework
- **mypy** - Type checking
- **black** - Code formatting
- **detect-secrets** - Secret detection

### Further Reading
- [The Twelve-Factor App](https://12factor.net/) - Production app principles
- [Python Packaging Guide](https://packaging.python.org/)
- [Semantic Versioning](https://semver.org/)
- [Keep a Changelog](https://keepachangelog.com/)

---

**Last Updated:** 2025-11-11
**Project:** PostHog Driver for Claude Agent SDK
**Status:** Production-Ready (after security fixes)

---

*This guide was created after building a complete PostHog driver from scratch, including all mistakes, fixes, and lessons learned. Use it to avoid our pitfalls and build production-ready code from day 1.*
