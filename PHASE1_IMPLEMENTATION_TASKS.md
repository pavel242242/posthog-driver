# Phase 1: Critical Path Implementation Tasks

## Overview
Phase 1 gets the project from Beta (35/100) to Pre-Production (65/100) quality. This is the minimum viable set of features needed for safe production deployment.

**Timeline:** 1-2 weeks with 1-2 developers
**Effort:** 15-20 hours
**Tests:** All existing tests must still pass

---

## Task Breakdown

### Task 1: Add Structured Logging (2-3 hours)

#### 1.1 Create logging_config.py
**File:** `posthog_driver/logging_config.py`
**Acceptance Criteria:**
- [ ] JSON-formatted log output
- [ ] Structured logging with timestamp, level, logger, message
- [ ] API key masking (never full key in logs)
- [ ] Correlation ID support
- [ ] Exception stack traces

**Code Outline:**
```python
import logging
import json
from datetime import datetime

class StructuredFormatter(logging.Formatter):
    def format(self, record):
        # Create JSON log entry
        # Mask API keys
        # Add correlation ID if present
        # Include exception info
        return json.dumps(log_obj)

def configure_logging(level=logging.INFO):
    # Setup logger with structured formatter
    # Return configured logger
    return logger

def mask_api_key(key):
    # Return "xxx...xx" format for logging
    return f"{key[:6]}...{key[-2:]}"
```

#### 1.2 Update client.py with logging
**File:** `posthog_driver/client.py`
**Changes:**
- Add `import logging` at top
- Add `logger = logging.getLogger(__name__)` after imports
- Add logging to `_make_request()` method:
  - DEBUG: Start of request (method, endpoint)
  - INFO: Success (status, latency)
  - WARNING: Retries and timeouts
  - ERROR: Final failures (with masked context)
- Add logging to all public methods
- Log connection/authentication errors

**Code Example:**
```python
def _make_request(self, endpoint, method='GET', **kwargs):
    base_url = self.capture_url if kwargs.pop('use_capture_url', False) else self.api_url
    url = f"{base_url}{endpoint}"

    for attempt in range(self.max_retries):
        start_time = time.time()
        try:
            logger.debug(f"{method} {endpoint}", extra={'attempt': attempt + 1})
            response = self.session.request(method, url, timeout=self.timeout, **kwargs)
            latency_ms = (time.time() - start_time) * 1000
            logger.info(f"{method} {endpoint}", extra={
                'status_code': response.status_code,
                'latency_ms': latency_ms
            })
            # ... rest of method
```

#### 1.3 Add logging tests
**File:** `tests/test_logging.py`
**Tests:**
- [ ] Verify logger configured correctly
- [ ] Check JSON format of logs
- [ ] Verify API key masking
- [ ] Verify correlation ID included
- [ ] Verify exception logging works

**Test Example:**
```python
def test_api_key_masking():
    key = "phx_1234567890"
    masked = mask_api_key(key)
    assert "1234567890" not in masked
    assert "phx_" in masked

def test_logging_format():
    # Call API method and capture logs
    # Verify JSON format
    # Verify required fields present
```

---

### Task 2: Implement Exponential Backoff (3-4 hours)

#### 2.1 Create retry.py
**File:** `posthog_driver/retry.py`
**Acceptance Criteria:**
- [ ] Exponential backoff function (1s, 2s, 4s, 8s, 16s, 32s)
- [ ] Jitter (10% random variation)
- [ ] Max wait time cap (32s default)
- [ ] Should_retry() function to distinguish retryable errors
- [ ] Unit tests for backoff calculations

**Code Outline:**
```python
import random
import time
import logging

def exponential_backoff(attempt, base=1, max_wait=32):
    """Calculate exponential backoff with jitter."""
    wait_time = min(base ** attempt, max_wait)
    jitter = random.uniform(0, wait_time * 0.1)
    return wait_time + jitter

def should_retry(exception, status_code=None):
    """Determine if error is retryable."""
    import requests

    # Network errors are retryable
    if isinstance(exception, (requests.ConnectionError, requests.Timeout)):
        return True

    # 5xx errors are retryable
    if status_code and 500 <= status_code < 600:
        return True

    # 429 (rate limit) is retryable
    if status_code == 429:
        return True

    # 4xx client errors are NOT retryable
    if status_code and 400 <= status_code < 500:
        return False

    return False
```

#### 2.2 Update client.py retry logic
**File:** `posthog_driver/client.py`
**Changes:**
- Replace simple for loop with exponential backoff
- Import exponential_backoff and should_retry from retry.py
- Add jitter to prevent thundering herd
- Add logging for retries
- Handle timeout properly

**Code Replacement:**
```python
from .retry import exponential_backoff, should_retry
import time

def _make_request(self, endpoint, method='GET', **kwargs):
    # ... existing code ...

    for attempt in range(self.max_retries):
        try:
            response = self.session.request(method, url, timeout=self.timeout, **kwargs)

            # Check if status code is retryable
            if response.status_code >= 400:
                if not should_retry(None, response.status_code):
                    response.raise_for_status()  # Fail fast for 4xx

            return response.json()  # Success!

        except (requests.ConnectionError, requests.Timeout) as e:
            if attempt < self.max_retries - 1 and should_retry(e):
                wait_time = exponential_backoff(attempt)
                logger.warning(
                    f"Request failed, retrying in {wait_time:.2f}s",
                    extra={'attempt': attempt + 1, 'error': str(e)}
                )
                time.sleep(wait_time)
            else:
                logger.error(f"Request failed after {attempt + 1} attempts", exc_info=True)
                raise
```

#### 2.3 Add retry tests
**File:** `tests/test_retry.py`
**Tests:**
- [ ] exponential_backoff produces correct sequence
- [ ] Jitter within expected range
- [ ] Max wait cap works
- [ ] should_retry identifies correct errors
- [ ] 5xx returns retryable
- [ ] 429 returns retryable
- [ ] 4xx (non-429) returns non-retryable

**Test Example:**
```python
def test_exponential_backoff_sequence():
    assert abs(exponential_backoff(0) - 1) < 0.2  # ~1s ±jitter
    assert abs(exponential_backoff(1) - 2) < 0.3  # ~2s ±jitter
    assert abs(exponential_backoff(2) - 4) < 0.5  # ~4s ±jitter

def test_max_backoff_cap():
    wait = exponential_backoff(10)  # Very large
    assert wait <= 32  # Capped

def test_should_retry_5xx():
    assert should_retry(None, 500) == True
    assert should_retry(None, 503) == True

def test_should_not_retry_4xx():
    assert should_retry(None, 400) == False
    assert should_retry(None, 401) == False
    assert should_retry(None, 404) == False
```

---

### Task 3: Add Circuit Breaker (5-6 hours)

#### 3.1 Create circuit_breaker.py
**File:** `posthog_driver/circuit_breaker.py`
**Acceptance Criteria:**
- [ ] Three states: CLOSED, OPEN, HALF_OPEN
- [ ] Failure threshold configurable
- [ ] Recovery timeout configurable
- [ ] Fast-fail when OPEN
- [ ] Auto-recovery attempt when timeout passes
- [ ] Detailed logging of state transitions

**Code Outline:**
```python
from enum import Enum
from time import time as current_time
import logging

class CircuitState(Enum):
    CLOSED = "closed"           # Normal operation
    OPEN = "open"               # Failing, reject requests
    HALF_OPEN = "half_open"    # Testing if recovered

class CircuitBreaker:
    def __init__(self, failure_threshold=5, recovery_timeout=60, name="api"):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.name = name
        self.failure_count = 0
        self.last_failure_time = None
        self.state = CircuitState.CLOSED

    def record_success(self):
        """Record successful request."""
        if self.failure_count > 0:
            logger.info(f"Circuit breaker '{self.name}' recovered")
        self.failure_count = 0
        self.state = CircuitState.CLOSED

    def record_failure(self):
        """Record failed request."""
        self.failure_count += 1
        self.last_failure_time = current_time()
        if self.failure_count >= self.failure_threshold:
            self.state = CircuitState.OPEN
            logger.error(f"Circuit breaker '{self.name}' OPEN")

    def is_open(self):
        """Check if circuit is OPEN."""
        if self.state == CircuitState.OPEN:
            if current_time() - self.last_failure_time > self.recovery_timeout:
                self.state = CircuitState.HALF_OPEN
                logger.info(f"Circuit breaker '{self.name}' attempting recovery")
                return False
            return True
        return False

    def can_execute(self):
        """Check if request can be executed."""
        return not self.is_open()
```

#### 3.2 Add CircuitBreakerOpen exception
**File:** `posthog_driver/exceptions.py`
**Changes:**
- Add new exception class after RateLimitError

```python
class CircuitBreakerOpen(PostHogError):
    """Raised when circuit breaker is open and rejecting requests."""
    pass
```

#### 3.3 Update client.py with circuit breaker
**File:** `posthog_driver/client.py`
**Changes:**
- Import CircuitBreaker from circuit_breaker.py
- Create circuit breaker instances in __init__
- Check circuit breaker state before requests
- Record success/failure

**Code Example:**
```python
from .circuit_breaker import CircuitBreaker

class PostHogClient:
    def __init__(self, ...):
        # ... existing init code ...
        self.circuit_breaker = CircuitBreaker(name="posthog_api")

    def _make_request(self, endpoint, ...):
        # Check circuit breaker
        if not self.circuit_breaker.can_execute():
            raise CircuitBreakerOpen(
                f"Circuit breaker is OPEN. API degraded, retry later."
            )

        try:
            response = self.session.request(...)
            self.circuit_breaker.record_success()
            return response.json()
        except Exception as e:
            self.circuit_breaker.record_failure()
            raise
```

#### 3.4 Add circuit breaker tests
**File:** `tests/test_circuit_breaker.py`
**Tests:**
- [ ] Initial state is CLOSED
- [ ] Transitions to OPEN after threshold failures
- [ ] is_open() returns True when OPEN
- [ ] Transitions to HALF_OPEN after timeout
- [ ] can_execute() returns False when OPEN
- [ ] record_success() resets to CLOSED
- [ ] Logging on state transitions

**Test Example:**
```python
def test_circuit_breaker_opens_on_threshold():
    cb = CircuitBreaker(failure_threshold=3, name="test")
    assert cb.state == CircuitState.CLOSED

    cb.record_failure()
    cb.record_failure()
    assert cb.state == CircuitState.CLOSED  # Not yet

    cb.record_failure()
    assert cb.state == CircuitState.OPEN  # Now open
    assert not cb.can_execute()

def test_circuit_breaker_auto_recovery():
    cb = CircuitBreaker(failure_threshold=1, recovery_timeout=0.1, name="test")
    cb.record_failure()
    assert cb.state == CircuitState.OPEN

    time.sleep(0.2)  # Wait for timeout
    assert cb.is_open() == False  # Auto-transitioned to HALF_OPEN
    assert cb.state == CircuitState.HALF_OPEN
```

---

### Task 4: Create setup.py (3-4 hours)

#### 4.1 Create setup.py
**File:** `setup.py` (at project root)
**Acceptance Criteria:**
- [ ] Package metadata complete
- [ ] Dependencies listed correctly
- [ ] Dev dependencies optional
- [ ] Entry points defined (if any)
- [ ] Long description from README
- [ ] PyPI classifiers correct

**Code:**
```python
from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setup(
    name='posthog-driver',
    version='1.0.0',
    description='PostHog analytics driver for Claude Agent SDK',
    long_description=long_description,
    long_description_content_type="text/markdown",
    author='PostHog Community',
    author_email='support@posthog.com',
    url='https://github.com/posthog/posthog-driver',
    license='MIT',
    packages=find_packages(),
    python_requires='>=3.8',
    install_requires=[
        'requests>=2.31.0',
        'python-dotenv>=1.0.0',
        'e2b>=0.15.0',
    ],
    extras_require={
        'dev': [
            'pytest>=7.0',
            'pytest-cov>=4.0',
            'black>=23.0',
            'flake8>=6.0',
            'mypy>=1.0',
        ]
    },
    classifiers=[
        'Development Status :: 4 - Beta',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: MIT License',
        'Operating System :: OS Independent',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.8',
        'Programming Language :: Python :: 3.9',
        'Programming Language :: Python :: 3.10',
        'Programming Language :: Python :: 3.11',
        'Programming Language :: Python :: 3.12',
        'Topic :: Software Development :: Libraries',
    ],
    keywords='posthog analytics claude agent',
)
```

#### 4.2 Test setup.py works
**Commands to verify:**
```bash
# Test installation in clean environment
python -m pip install -e .

# Test import works
python -c "from posthog_driver import PostHogClient; print('OK')"

# Test version is accessible
python -c "import posthog_driver; print(posthog_driver.__version__)"

# Test package can be built
python setup.py sdist bdist_wheel
```

#### 4.3 Update __init__.py for version
**File:** `posthog_driver/__init__.py`
**Add:**
```python
__version__ = '1.0.0'
```

---

### Task 5: Create Dockerfile (2-3 hours)

#### 5.1 Create Dockerfile
**File:** `Dockerfile` (at project root)
**Acceptance Criteria:**
- [ ] Based on python:3.11-slim
- [ ] Multi-stage build for size
- [ ] Dependencies installed
- [ ] Non-root user
- [ ] Health check included
- [ ] Reasonable default CMD

**Code:**
```dockerfile
# Build stage
FROM python:3.11-slim as builder

WORKDIR /build
COPY requirements.txt .
RUN pip install --user --no-cache-dir -r requirements.txt

# Final stage
FROM python:3.11-slim

WORKDIR /app

# Copy packages from builder
COPY --from=builder /root/.local /root/.local
ENV PATH=/root/.local/bin:$PATH

# Copy source code
COPY posthog_driver/ ./posthog_driver/
COPY setup.py .
COPY README.md .

# Install package
RUN pip install --no-cache-dir -e .

# Create non-root user
RUN useradd -m -u 1000 appuser && chown -R appuser:appuser /app
USER appuser

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "from posthog_driver import PostHogClient; exit(0 if PostHogClient().health_check() else 1)"

CMD ["python", "-c", "print('PostHog Driver Ready')"]
```

#### 5.2 Create .dockerignore
**File:** `.dockerignore` (at project root)
**Content:**
```
__pycache__
*.pyc
*.pyo
*.egg-info
build/
dist/
.pytest_cache/
.coverage
htmlcov/
.env
.env.local
.git
.gitignore
.github/
*.md
!README.md
.vscode/
.idea/
*.swp
*.swo
```

#### 5.3 Test Dockerfile works
**Commands:**
```bash
# Build image
docker build -t posthog-driver:1.0.0 .

# Run container
docker run --rm posthog-driver:1.0.0

# Test health check
docker run --rm -e POSTHOG_PERSONAL_API_KEY="test" -e POSTHOG_PROJECT_ID="123" \
  posthog-driver:1.0.0 healthcheck
```

---

### Task 6: Write Deployment Guide (2-3 hours)

#### 6.1 Create DEPLOYMENT.md
**File:** `DEPLOYMENT.md` (at project root)
**Sections:**
- [ ] Prerequisites (Python, Docker, etc.)
- [ ] Installation via pip
- [ ] Installation via Docker
- [ ] Configuration (env vars, .env file)
- [ ] Testing installation
- [ ] Production deployment steps
- [ ] Monitoring setup
- [ ] Troubleshooting

**Outline:**
```markdown
# Deployment Guide

## Installation

### Via pip
```bash
pip install posthog-driver
```

### Via Docker
```bash
docker build -t posthog-driver:1.0.0 .
docker run -e POSTHOG_PERSONAL_API_KEY=... posthog-driver:1.0.0
```

## Configuration

### Environment Variables
```
POSTHOG_PERSONAL_API_KEY=phx_xxx
POSTHOG_PROJECT_ID=123
POSTHOG_API_URL=https://us.posthog.com
```

## Production Deployment

### Kubernetes
- Create ConfigMap for non-secrets
- Create Secret for API keys
- Create Deployment with pod
- Create Service for access
- Configure liveness/readiness probes

### Docker Compose
```yaml
version: '3'
services:
  posthog-driver:
    build: .
    environment:
      POSTHOG_PERSONAL_API_KEY: ${POSTHOG_API_KEY}
      POSTHOG_PROJECT_ID: ${POSTHOG_PROJECT_ID}
```

## Monitoring

See MONITORING.md for setup.
```

---

### Task 7: Create Monitoring Guide (2-3 hours)

#### 7.1 Create MONITORING.md
**File:** `MONITORING.md` (at project root)
**Sections:**
- [ ] Logging setup
- [ ] Structured log format
- [ ] Viewing logs
- [ ] Common log patterns
- [ ] Health checks
- [ ] Metrics to track
- [ ] Alerting rules

**Key Content:**
```markdown
# Monitoring Guide

## Structured Logging

All logs are JSON formatted with:
- timestamp: ISO 8601
- level: DEBUG, INFO, WARNING, ERROR
- logger: module name
- message: log message
- status_code: HTTP status (if applicable)
- latency_ms: request latency
- error: error message
- exception: stack trace (if applicable)

## Viewing Logs

### Local
```bash
python -c "import logging; logging.basicConfig(level=logging.INFO); ..."
```

### Docker
```bash
docker logs -f <container_id>
```

### Log Aggregation (ELK/Datadog/CloudWatch)
Configure JSON parsing for structured logs.

## Key Metrics

- Request latency (p50, p95, p99)
- Error rate by type
- Retry rate
- Circuit breaker state
- Rate limit hits

## Alerting

Alert on:
- Error rate > 1%
- Circuit breaker OPEN
- Health check failures
- Latency p95 > 500ms
```

---

### Task 8: Update Tests (2-3 hours)

#### 8.1 Verify existing tests pass
**Commands:**
```bash
# Run all tests
python -m pytest tests/ -v

# Check test coverage
python -m pytest tests/ --cov=posthog_driver --cov-report=html

# All 40 tests must pass
```

#### 8.2 Add tests for new code
**New test files:**
- `tests/test_logging.py` (logging tests)
- `tests/test_retry.py` (exponential backoff tests)
- `tests/test_circuit_breaker.py` (circuit breaker tests)

**Test summary:**
- [ ] ~10 tests for logging
- [ ] ~10 tests for retry logic
- [ ] ~10 tests for circuit breaker
- [ ] Total: ~30 new tests (bringing total to 70+)

---

### Task 9: Integration Testing (2-3 hours)

#### 9.1 Create integration test file
**File:** `tests/test_integration.py`
**Tests:**
- [ ] End-to-end query with logging
- [ ] Retry logic with mock failures
- [ ] Circuit breaker with cascading errors
- [ ] Error handling and exceptions
- [ ] Rate limiting (if implemented)

**Test Example:**
```python
def test_query_with_retry_and_logging(caplog):
    client = PostHogClient(api_key="test", project_id="123")

    # Mock responses to test retry
    with patch('requests.Session.request') as mock_request:
        # First call fails, second succeeds
        mock_request.side_effect = [
            ConnectionError("Network error"),
            MagicMock(status_code=200, json=lambda: {'results': []})
        ]

        result = client.query("SELECT 1")

        # Verify retry happened
        assert mock_request.call_count == 2

        # Verify logging occurred
        assert "Retry" in caplog.text or "retry" in caplog.text
```

---

## Verification Checklist

After completing all tasks, verify:

### Code Quality
- [ ] All 40+ unit tests passing
- [ ] New tests added for logging, retry, circuit breaker
- [ ] No TODO comments in code
- [ ] Code follows existing style
- [ ] No hardcoded API keys or secrets
- [ ] Type hints added to new functions
- [ ] Docstrings updated

### Functionality
- [ ] Logging outputs structured JSON
- [ ] Exponential backoff follows sequence (1, 2, 4, 8, 16, 32)
- [ ] Circuit breaker transitions through states correctly
- [ ] setup.py installs package correctly
- [ ] Dockerfile builds and runs
- [ ] Import works: `from posthog_driver import PostHogClient`

### Security
- [ ] No API keys in code or logs
- [ ] API keys masked in output (phx_xxx...xx)
- [ ] No secrets in git history
- [ ] .gitignore updated if needed

### Documentation
- [ ] DEPLOYMENT.md created
- [ ] MONITORING.md created
- [ ] README.md updated (if needed)
- [ ] Code comments added to complex logic
- [ ] Function docstrings complete

### Deployment
- [ ] setup.py works correctly
- [ ] Dockerfile builds image
- [ ] Image runs successfully
- [ ] Health check works
- [ ] Installation via pip works

---

## Timeline Estimate

| Task | Hours | Days | Who |
|------|-------|------|-----|
| 1. Logging | 2-3 | 0.5 | Dev1 |
| 2. Exponential Backoff | 3-4 | 1 | Dev2 |
| 3. Circuit Breaker | 5-6 | 1.5 | Dev1+Dev2 |
| 4. setup.py | 3-4 | 0.5 | Dev2 |
| 5. Dockerfile | 2-3 | 0.5 | Dev2 |
| 6. Deployment Guide | 2-3 | 0.5 | Dev1 |
| 7. Monitoring Guide | 2-3 | 0.5 | Dev1 |
| 8. Update Tests | 2-3 | 0.5 | Dev1 |
| 9. Integration Tests | 2-3 | 1 | Dev1 |
| **TOTAL** | **24-32h** | **6-7d** | **1-2 devs** |

With parallel work: **3-4 days with 2 developers**

---

## Success Criteria

Phase 1 is complete when:

**Must Have (Blocking)**
- [ ] All 40+ unit tests passing
- [ ] Structured logging implemented and working
- [ ] Exponential backoff with jitter implemented
- [ ] Circuit breaker pattern implemented
- [ ] setup.py works for installation
- [ ] Dockerfile builds and runs
- [ ] No API keys in logs or code
- [ ] Documentation written (DEPLOYMENT.md, MONITORING.md)

**Should Have**
- [ ] Integration tests created
- [ ] Health check improved
- [ ] Example deployment configs provided
- [ ] Team trained on changes

**Nice to Have**
- [ ] Type hints added
- [ ] Code coverage > 80%
- [ ] Performance benchmarks run

---

## Risk Mitigation

### Risk: Breaking existing functionality
**Mitigation:** Run all 40 tests after each change. Feature branches with CI/CD.

### Risk: Performance impact
**Mitigation:** Add logging overhead test. Measure latency before/after.

### Risk: API key exposure
**Mitigation:** Code review for all logging. Grep for "phx_", "phc_" in logs.

### Risk: Circuit breaker too aggressive
**Mitigation:** Start with high threshold (5 failures) and long timeout (60s). Adjust based on production metrics.

---

## Next Steps After Phase 1

Once Phase 1 complete:

1. **Deploy to staging** - Test all changes with real API
2. **Run load tests** - Verify performance impact
3. **Team training** - Teach team about new features
4. **Plan Phase 2** - Rate limiting, better health checks, security
5. **Production rollout** - Blue-green deployment with monitoring

---

**Phase 1 Status:** Ready to Start
**Estimated Completion:** 3-4 days
**Next Review:** When all tests passing + deployment verified

