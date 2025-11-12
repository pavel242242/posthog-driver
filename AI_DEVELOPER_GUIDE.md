# AI Developer Guide: Building Production-Ready Python Drivers

**A Complete Blueprint from Goal → Architecture → Implementation**

*Lessons learned from building PostHog Driver for Claude Agent SDK*

---

## How to Use This Guide

This guide follows the natural development flow:
1. **Goal** - What are we building and why?
2. **Architecture** - How should it be designed?
3. **Implementation Plan** - Step-by-step execution
4. **Production Checklist** - What must be done before deployment

Use this as a blueprint when building any Python driver that integrates with AI agents.

---

# Part 1: GOAL

## Project Vision

**What:** A Python driver that lets AI agents interact with a data source through natural language.

**Why:**
- Traditional APIs require knowing exact endpoints and parameters
- AI agents need dynamic discovery of capabilities
- Natural language queries are more intuitive than hardcoded templates
- Secure execution in sandboxes prevents local machine access

**Success Criteria:**
- AI can discover what data is available (dynamic)
- AI can query data using natural language
- Queries execute securely (E2B sandboxes)
- Production-ready (logging, monitoring, error handling)
- Well-documented (anyone can use it)

## The Driver Contract Pattern

**Core Insight:** Instead of hardcoded methods, implement a 3-method interface that enables dynamic discovery:

```python
class Driver:
    def list_objects(self) -> List[str]:
        """What entity types are available?"""
        # Returns: ["events", "persons", "cohorts", ...]

    def get_fields(self, object_name: str) -> Dict[str, Any]:
        """What fields does this entity have?"""
        # Returns schema with types, descriptions, constraints

    def query(self, query: str) -> List[Dict[str, Any]]:
        """Execute a query against the data source"""
        # Returns results as list of dictionaries
```

**Why This Pattern:**
- AI can explore without prior knowledge
- Self-documenting (schemas returned dynamically)
- Standard interface across different data sources
- Enables tool use by Claude Agent SDK

## Target Use Cases

1. **Conversational Analytics**
   - "What are the top events this week?"
   - "Where do users drop off in the funnel?"
   - "Which features drive conversion?"

2. **Dynamic Exploration**
   - AI discovers available entities
   - AI learns schema on-the-fly
   - AI constructs appropriate queries

3. **Secure Execution**
   - Queries run in E2B sandboxes
   - No local file system access
   - Automatic cleanup

---

# Part 2: ARCHITECTURE

## System Components

```
┌─────────────────────────────────────────────────────────────┐
│                         User                                 │
└─────────────────┬───────────────────────────────────────────┘
                  │
                  ▼ Natural language question
┌─────────────────────────────────────────────────────────────┐
│                   Claude Agent (Sonnet 4.5)                 │
│  • Understands question                                      │
│  • Decides to use query_posthog tool                        │
│  • Generates HogQL query or uses driver methods             │
└─────────────────┬───────────────────────────────────────────┘
                  │
                  ▼ Tool call with parameters
┌─────────────────────────────────────────────────────────────┐
│                   Python Application                         │
│  • Receives tool call from Claude                           │
│  • Prepares execution environment                           │
└─────────────────┬───────────────────────────────────────────┘
                  │
                  ▼ Create sandbox & upload code
┌─────────────────────────────────────────────────────────────┐
│                   E2B Sandbox (Ubuntu VM)                   │
│  • Isolated cloud environment                               │
│  • PostHog driver uploaded                                  │
│  • Dependencies installed                                   │
│  • Execute query script                                     │
└─────────────────┬───────────────────────────────────────────┘
                  │
                  ▼ HTTPS API request
┌─────────────────────────────────────────────────────────────┐
│                   Data Source API (PostHog)                 │
│  • Receives query                                           │
│  • Returns results                                          │
└─────────────────┬───────────────────────────────────────────┘
                  │
                  ▼ Results bubble back up
                  ▼ Claude formats for user
                  ▼ User sees answer
```

## Directory Structure

```
my-driver/
├── my_driver/                  # Core package
│   ├── __init__.py            # Public API exports
│   ├── client.py              # Main driver implementation
│   ├── exceptions.py          # Custom exceptions
│   ├── logger.py              # Logging setup
│   ├── config.py              # Configuration management
│   └── query_builder.py       # Safe query construction
│
├── tests/                     # Test suite
│   ├── __init__.py
│   ├── conftest.py           # Pytest fixtures
│   ├── test_client.py        # Client tests
│   ├── test_query_builder.py # Query builder tests
│   └── test_integration.py   # Integration tests
│
├── examples/                  # Usage examples
│   ├── basic_usage.py        # Simple examples
│   ├── claude_integration.py # Claude SDK integration
│   └── e2b_sandbox.py        # E2B execution
│
├── docs/                      # Documentation
│   ├── API.md               # API reference
│   └── ARCHITECTURE.md      # Architecture diagrams
│
├── setup.py                  # Package configuration
├── requirements.txt          # Dependencies
├── requirements-dev.txt      # Dev dependencies
├── .gitignore               # Git ignore rules
├── .env.example             # Config template
├── LICENSE                   # License (MIT/Apache)
├── README.md                # Project overview
├── CONTRIBUTING.md          # Contribution guide
├── SECURITY.md              # Security policy
├── CHANGELOG.md             # Version history
└── AI_DEVELOPER_GUIDE.md    # This guide
```

## Core Architecture Decisions

### 1. Configuration Layer

```python
@dataclass
class DriverConfig:
    """Centralized configuration"""
    api_key: str                    # From environment
    project_id: str                 # From environment
    api_url: str = "https://api.example.com"
    timeout: int = 30
    max_retries: int = 3
    rate_limit_per_minute: int = 240
    log_level: str = "INFO"

    @classmethod
    def from_env(cls) -> 'DriverConfig':
        """Load from environment variables with validation"""
        api_key = os.getenv('API_KEY')
        if not api_key:
            raise ValueError("API_KEY is required")
        # ... validate all required fields
        return cls(api_key=api_key, ...)
```

### 2. Logging Layer

```python
# Initialize on module load
logger = get_logger(__name__)

# Use throughout
logger.info("Operation starting", extra={"context": "value"})
logger.error("Operation failed", exc_info=True)
```

### 3. Error Handling Layer

```python
class DriverError(Exception):
    """Base exception"""

class AuthenticationError(DriverError):
    """API key invalid"""

class RateLimitError(DriverError):
    """Rate limit exceeded"""

class QueryError(DriverError):
    """Query execution failed"""
```

### 4. Resilience Layer

```python
class Client:
    def __init__(self, config: DriverConfig):
        self.config = config
        self.rate_limiter = RateLimiter(
            max_requests=config.rate_limit_per_minute,
            time_window=60
        )
        self.circuit_breaker = CircuitBreaker(
            failure_threshold=5,
            timeout=60
        )

    def query(self, query_str: str):
        # Rate limiting
        self.rate_limiter.wait_and_acquire()

        # Circuit breaker
        return self.circuit_breaker.call(
            self._query_with_retry,
            query_str
        )

    def _query_with_retry(self, query_str: str):
        # Exponential backoff retry
        for attempt in range(self.config.max_retries):
            try:
                return self._execute_query(query_str)
            except (Timeout, ConnectionError) as e:
                if attempt < self.config.max_retries - 1:
                    wait = (2 ** attempt) + random.uniform(0, 1)
                    time.sleep(wait)
                else:
                    raise
```

---

# Part 3: IMPLEMENTATION PLAN

## Phase 1: Foundation (Day 1)

**Goal:** Set up project structure with all production infrastructure from the start.

### Step 1.1: Initialize Project (30 minutes)

```bash
# Create directory
mkdir my-driver && cd my-driver

# Initialize git
git init

# Create essential files FIRST (before any code)
touch LICENSE                     # MIT or Apache 2.0
touch .gitignore                 # Python, .env, IDE files
touch README.md                  # Project description
touch CONTRIBUTING.md            # Development guide
touch SECURITY.md                # Security policy
touch CHANGELOG.md               # Start at v0.1.0
touch .env.example               # Config template (NO real keys)

# Create package structure
mkdir my_driver tests examples docs
touch my_driver/{__init__.py,client.py,exceptions.py,logger.py,config.py}
touch tests/{__init__.py,conftest.py,test_client.py}

# Create setup.py
cat > setup.py << 'EOF'
from setuptools import setup, find_packages

setup(
    name="my-driver",
    version="0.1.0",
    description="Driver for [Data Source] with Claude Agent SDK",
    packages=find_packages(),
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
        ]
    }
)
EOF

# Create requirements files
echo "requests>=2.31.0,<3.0.0" > requirements.txt
echo "python-dotenv>=1.0.0,<2.0.0" >> requirements.txt
echo "pytest>=7.0.0" > requirements-dev.txt

# Install in dev mode
python -m venv venv
source venv/bin/activate
pip install -e ".[dev]"
```

### Step 1.2: Set Up Security (30 minutes)

```bash
# Install pre-commit hooks
pip install pre-commit detect-secrets

# Create .pre-commit-config.yaml
cat > .pre-commit-config.yaml << 'EOF'
repos:
  - repo: https://github.com/Yelp/detect-secrets
    rev: v1.4.0
    hooks:
      - id: detect-secrets
        args: ['--baseline', '.secrets.baseline']
EOF

# Initialize pre-commit
pre-commit install

# Create baseline
detect-secrets scan > .secrets.baseline

# Add to .gitignore
cat >> .gitignore << 'EOF'
# Environment
.env
.env.local
*.env

# Python
__pycache__/
*.py[cod]
venv/
.pytest_cache/

# IDE
.vscode/
.idea/
*.swp

# Secrets
.secrets.baseline
EOF
```

### Step 1.3: Implement Logging (1 hour)

```python
# my_driver/logger.py
import logging
import os
import sys

def get_logger(name: str) -> logging.Logger:
    """
    Get configured logger for a module.

    Args:
        name: Module name (use __name__)

    Returns:
        Configured logger instance
    """
    logger = logging.getLogger(name)

    # Prevent duplicate handlers
    if logger.handlers:
        return logger

    # Set level from environment
    level = os.getenv('LOG_LEVEL', 'INFO').upper()
    logger.setLevel(getattr(logging, level, logging.INFO))

    # Create console handler
    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(logging.DEBUG)

    # Create formatter
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    handler.setFormatter(formatter)

    logger.addHandler(handler)
    return logger
```

### Step 1.4: Implement Configuration (1 hour)

```python
# my_driver/config.py
import os
from dataclasses import dataclass
from typing import Optional

@dataclass
class DriverConfig:
    """Driver configuration."""

    # Required
    api_key: str
    project_id: str

    # Optional with defaults
    api_url: str = "https://api.example.com"
    timeout: int = 30
    max_retries: int = 3
    rate_limit_per_minute: int = 240
    rate_limit_per_hour: int = 1200
    log_level: str = "INFO"

    @classmethod
    def from_env(cls) -> 'DriverConfig':
        """
        Load configuration from environment variables.

        Required environment variables:
        - API_KEY: API authentication key
        - PROJECT_ID: Project identifier

        Optional environment variables:
        - API_URL: API base URL
        - TIMEOUT: Request timeout in seconds
        - MAX_RETRIES: Maximum retry attempts
        - LOG_LEVEL: Logging level (DEBUG, INFO, WARNING, ERROR)

        Raises:
            ValueError: If required variables are missing

        Returns:
            Configured DriverConfig instance
        """
        # Required fields
        api_key = os.getenv('API_KEY')
        if not api_key:
            raise ValueError("API_KEY environment variable is required")

        project_id = os.getenv('PROJECT_ID')
        if not project_id:
            raise ValueError("PROJECT_ID environment variable is required")

        # Optional fields with defaults
        return cls(
            api_key=api_key,
            project_id=project_id,
            api_url=os.getenv('API_URL', cls.api_url),
            timeout=int(os.getenv('TIMEOUT', str(cls.timeout))),
            max_retries=int(os.getenv('MAX_RETRIES', str(cls.max_retries))),
            log_level=os.getenv('LOG_LEVEL', cls.log_level),
        )

    def validate(self) -> None:
        """Validate configuration values."""
        if self.timeout <= 0:
            raise ValueError("timeout must be positive")
        if self.max_retries < 0:
            raise ValueError("max_retries must be non-negative")
        if self.rate_limit_per_minute <= 0:
            raise ValueError("rate_limit_per_minute must be positive")
```

### Step 1.5: Implement Exceptions (30 minutes)

```python
# my_driver/exceptions.py
class DriverError(Exception):
    """Base exception for all driver errors."""
    pass

class AuthenticationError(DriverError):
    """API authentication failed."""
    pass

class AuthorizationError(DriverError):
    """Insufficient permissions for operation."""
    pass

class NotFoundError(DriverError):
    """Requested resource not found."""
    pass

class QueryError(DriverError):
    """Query execution failed."""
    pass

class RateLimitError(DriverError):
    """Rate limit exceeded."""
    pass

class ConnectionError(DriverError):
    """Network connection failed."""
    pass

class TimeoutError(DriverError):
    """Request timeout exceeded."""
    pass

class ValidationError(DriverError):
    """Input validation failed."""
    pass
```

**Day 1 Checkpoint:** You now have all foundation infrastructure in place before writing any business logic.

---

## Phase 2: Core Driver (Days 2-3)

### Step 2.1: Implement Rate Limiter (2 hours)

```python
# my_driver/rate_limiter.py
from collections import deque
from time import time
from threading import Lock
from typing import Optional

class RateLimiter:
    """Token bucket rate limiter."""

    def __init__(self, max_requests: int, time_window: int):
        """
        Args:
            max_requests: Maximum requests allowed
            time_window: Time window in seconds
        """
        self.max_requests = max_requests
        self.time_window = time_window
        self.requests = deque()
        self.lock = Lock()

    def acquire(self) -> bool:
        """
        Try to acquire a request slot.

        Returns:
            True if slot acquired, False if rate limited
        """
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
        """
        Wait until a slot is available.

        Args:
            timeout: Maximum wait time in seconds

        Raises:
            TimeoutError: If timeout exceeded
        """
        start = time()
        while True:
            if self.acquire():
                return

            if timeout and (time() - start) > timeout:
                raise TimeoutError("Rate limit wait timeout")

            time.sleep(0.1)
```

### Step 2.2: Implement Circuit Breaker (2 hours)

```python
# my_driver/circuit_breaker.py
from enum import Enum
from datetime import datetime, timedelta
from typing import Callable, Any

class CircuitState(Enum):
    CLOSED = "closed"      # Normal operation
    OPEN = "open"          # Failing, reject requests
    HALF_OPEN = "half_open"  # Testing recovery

class CircuitBreakerError(Exception):
    """Circuit breaker is open."""
    pass

class CircuitBreaker:
    """Circuit breaker pattern implementation."""

    def __init__(
        self,
        failure_threshold: int = 5,
        timeout: int = 60,
        success_threshold: int = 2
    ):
        """
        Args:
            failure_threshold: Failures before opening
            timeout: Seconds before testing recovery
            success_threshold: Successes needed to close
        """
        self.failure_threshold = failure_threshold
        self.timeout = timeout
        self.success_threshold = success_threshold

        self.state = CircuitState.CLOSED
        self.failures = 0
        self.successes = 0
        self.opened_at = None

    def call(self, func: Callable, *args, **kwargs) -> Any:
        """
        Execute function with circuit breaker protection.

        Args:
            func: Function to execute
            *args, **kwargs: Function arguments

        Returns:
            Function result

        Raises:
            CircuitBreakerError: If circuit is open
        """
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
        """Handle successful call."""
        if self.state == CircuitState.HALF_OPEN:
            self.successes += 1
            if self.successes >= self.success_threshold:
                self.state = CircuitState.CLOSED
                self.failures = 0
        else:
            self.failures = 0

    def _on_failure(self):
        """Handle failed call."""
        self.failures += 1
        if self.failures >= self.failure_threshold:
            self.state = CircuitState.OPEN
            self.opened_at = datetime.now()
```

### Step 2.3: Implement Query Builder (3 hours)

**⚠️ CRITICAL: Prevent SQL Injection**

```python
# my_driver/query_builder.py
from typing import List, Dict, Any, Optional

class QueryBuilder:
    """Safe query construction with SQL injection prevention."""

    def __init__(self):
        self.select_parts = []
        self.from_table = None
        self.where_parts = []
        self.group_by_parts = []
        self.order_by_parts = []
        self.limit_value = None

    def select(self, *columns: str) -> 'QueryBuilder':
        """Add SELECT columns."""
        self.select_parts.extend(columns)
        return self

    def from_(self, table: str) -> 'QueryBuilder':
        """Set FROM table."""
        self.from_table = self._escape_identifier(table)
        return self

    def where(self, field: str, operator: str, value: Any) -> 'QueryBuilder':
        """Add WHERE condition with safe escaping."""
        safe_field = self._escape_identifier(field)
        safe_value = self._escape_value(value)

        if operator.upper() not in ['=', '!=', '>', '<', '>=', '<=', 'LIKE', 'IN']:
            raise ValueError(f"Invalid operator: {operator}")

        self.where_parts.append(f"{safe_field} {operator} {safe_value}")
        return self

    def group_by(self, *fields: str) -> 'QueryBuilder':
        """Add GROUP BY fields."""
        safe_fields = [self._escape_identifier(f) for f in fields]
        self.group_by_parts.extend(safe_fields)
        return self

    def order_by(self, field: str, direction: str = 'ASC') -> 'QueryBuilder':
        """Add ORDER BY clause."""
        if direction.upper() not in ['ASC', 'DESC']:
            raise ValueError(f"Invalid direction: {direction}")

        safe_field = self._escape_identifier(field)
        self.order_by_parts.append(f"{safe_field} {direction.upper()}")
        return self

    def limit(self, n: int) -> 'QueryBuilder':
        """Set LIMIT."""
        if not isinstance(n, int) or n < 0:
            raise ValueError("LIMIT must be non-negative integer")
        self.limit_value = n
        return self

    def build(self) -> str:
        """Build final query string."""
        if not self.select_parts:
            raise ValueError("SELECT is required")
        if not self.from_table:
            raise ValueError("FROM is required")

        parts = []

        # SELECT
        parts.append(f"SELECT {', '.join(self.select_parts)}")

        # FROM
        parts.append(f"FROM {self.from_table}")

        # WHERE
        if self.where_parts:
            parts.append(f"WHERE {' AND '.join(self.where_parts)}")

        # GROUP BY
        if self.group_by_parts:
            parts.append(f"GROUP BY {', '.join(self.group_by_parts)}")

        # ORDER BY
        if self.order_by_parts:
            parts.append(f"ORDER BY {', '.join(self.order_by_parts)}")

        # LIMIT
        if self.limit_value is not None:
            parts.append(f"LIMIT {self.limit_value}")

        return ' '.join(parts)

    def _escape_identifier(self, identifier: str) -> str:
        """Escape table/column names."""
        if not isinstance(identifier, str):
            raise ValueError("Identifier must be string")

        # Remove dangerous characters
        identifier = identifier.strip()
        if not identifier:
            raise ValueError("Identifier cannot be empty")

        # Only allow alphanumeric and underscore
        if not all(c.isalnum() or c == '_' for c in identifier):
            raise ValueError(f"Invalid identifier: {identifier}")

        return identifier

    def _escape_value(self, value: Any) -> str:
        """Escape values for SQL."""
        if value is None:
            return "NULL"

        if isinstance(value, bool):
            return "TRUE" if value else "FALSE"

        if isinstance(value, (int, float)):
            return str(value)

        if isinstance(value, str):
            # Escape single quotes by doubling them (SQL standard)
            escaped = value.replace("'", "''")
            return f"'{escaped}'"

        if isinstance(value, (list, tuple)):
            escaped_items = [self._escape_value(v) for v in value]
            return f"({', '.join(escaped_items)})"

        raise ValueError(f"Unsupported value type: {type(value)}")
```

### Step 2.4: Implement Main Client (4-6 hours)

```python
# my_driver/client.py
import requests
import time
import random
from typing import List, Dict, Any, Optional
from .config import DriverConfig
from .logger import get_logger
from .exceptions import *
from .rate_limiter import RateLimiter
from .circuit_breaker import CircuitBreaker
from .query_builder import QueryBuilder

logger = get_logger(__name__)

class Client:
    """Main driver client implementing driver contract."""

    def __init__(self, config: DriverConfig):
        """
        Initialize client.

        Args:
            config: Driver configuration

        Raises:
            ValueError: If configuration is invalid
        """
        config.validate()
        self.config = config

        # Set up HTTP session
        self.session = requests.Session()
        self.session.headers.update({
            'Authorization': f'Bearer {config.api_key}',
            'Content-Type': 'application/json',
        })

        # Set up resilience mechanisms
        self.rate_limiter = RateLimiter(
            max_requests=config.rate_limit_per_minute,
            time_window=60
        )
        self.circuit_breaker = CircuitBreaker(
            failure_threshold=5,
            timeout=60
        )

        logger.info("Client initialized", extra={
            "project_id": config.project_id,
            "api_url": config.api_url
        })

    # =========================================================================
    # DRIVER CONTRACT METHODS
    # =========================================================================

    def list_objects(self) -> List[str]:
        """
        List available entity types.

        Returns:
            List of entity type names

        Example:
            >>> client.list_objects()
            ['events', 'persons', 'cohorts', 'insights']
        """
        logger.info("Listing objects")

        # Return supported entity types
        return [
            'events',
            'persons',
            'cohorts',
            'insights',
            'feature_flags',
            'sessions',
        ]

    def get_fields(self, object_name: str) -> Dict[str, Any]:
        """
        Get schema for an entity type.

        Args:
            object_name: Entity type name

        Returns:
            Schema dictionary with field definitions

        Raises:
            NotFoundError: If object_name not found

        Example:
            >>> client.get_fields('events')
            {
                'event': {'type': 'string', 'description': '...'},
                'timestamp': {'type': 'datetime', ...},
                ...
            }
        """
        logger.info(f"Getting fields for {object_name}")

        schemas = {
            'events': {
                'event': {
                    'type': 'string',
                    'description': 'Event name'
                },
                'timestamp': {
                    'type': 'datetime',
                    'description': 'Event timestamp'
                },
                'distinct_id': {
                    'type': 'string',
                    'description': 'User identifier'
                },
                'properties': {
                    'type': 'object',
                    'description': 'Event properties'
                }
            },
            # ... add other schemas
        }

        if object_name not in schemas:
            raise NotFoundError(f"Object '{object_name}' not found")

        return schemas[object_name]

    def query(self, query_string: str) -> List[Dict[str, Any]]:
        """
        Execute a query.

        Args:
            query_string: Query in native query language

        Returns:
            List of result rows as dictionaries

        Raises:
            ValidationError: If query is invalid
            QueryError: If query execution fails
            RateLimitError: If rate limit exceeded
            TimeoutError: If request times out

        Example:
            >>> client.query("SELECT event, count() FROM events LIMIT 5")
            [
                {'event': 'pageview', 'count': 100},
                {'event': 'signup', 'count': 50},
                ...
            ]
        """
        # Validate input
        if not query_string or not query_string.strip():
            raise ValidationError("Query cannot be empty")

        logger.info("Executing query", extra={
            "query_length": len(query_string)
        })

        # Rate limiting
        self.rate_limiter.wait_and_acquire(timeout=30)

        # Circuit breaker protection
        return self.circuit_breaker.call(
            self._query_with_retry,
            query_string
        )

    # =========================================================================
    # INTERNAL METHODS
    # =========================================================================

    def _query_with_retry(self, query_string: str) -> List[Dict[str, Any]]:
        """Execute query with exponential backoff retry."""
        for attempt in range(self.config.max_retries):
            try:
                return self._execute_query(query_string)

            except (requests.exceptions.Timeout, requests.exceptions.ConnectionError) as e:
                if attempt < self.config.max_retries - 1:
                    wait_time = (2 ** attempt) + random.uniform(0, 1)
                    logger.warning(
                        f"Retry {attempt + 1}/{self.config.max_retries} "
                        f"after {wait_time:.2f}s",
                        extra={"error": str(e)}
                    )
                    time.sleep(wait_time)
                else:
                    logger.error("Max retries exceeded", exc_info=True)
                    raise TimeoutError("Query timeout") from e

    def _execute_query(self, query_string: str) -> List[Dict[str, Any]]:
        """Execute query against API."""
        endpoint = f"{self.config.api_url}/api/projects/{self.config.project_id}/query/"

        payload = {
            'query': {
                'kind': 'QueryType',
                'query': query_string
            }
        }

        try:
            response = self.session.post(
                endpoint,
                json=payload,
                timeout=self.config.timeout
            )

            # Handle HTTP errors
            if response.status_code == 401:
                raise AuthenticationError("Invalid API key")
            elif response.status_code == 403:
                raise AuthorizationError("Insufficient permissions")
            elif response.status_code == 404:
                raise NotFoundError("Endpoint not found")
            elif response.status_code == 429:
                raise RateLimitError("Rate limit exceeded")
            elif response.status_code >= 500:
                raise ConnectionError(f"Server error: {response.status_code}")
            elif response.status_code >= 400:
                raise QueryError(f"Query failed: {response.status_code}")

            response.raise_for_status()

            # Parse response
            data = response.json()
            results = data.get('results', [])

            logger.debug(f"Query returned {len(results)} rows")
            return results

        except requests.exceptions.RequestException as e:
            logger.error("Query execution failed", exc_info=True)
            raise ConnectionError(f"Request failed: {e}") from e

    def health_check(self) -> bool:
        """
        Check if API is accessible.

        Returns:
            True if healthy, False otherwise
        """
        try:
            endpoint = f"{self.config.api_url}/api/projects/{self.config.project_id}/"
            response = self.session.get(endpoint, timeout=5)
            return response.status_code == 200
        except Exception as e:
            logger.warning(f"Health check failed: {e}")
            return False

    def __enter__(self):
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit with cleanup."""
        self.session.close()
        logger.info("Client closed")
```

### Step 2.5: Implement Package API (30 minutes)

```python
# my_driver/__init__.py
"""
My Driver - A driver for [Data Source] with Claude Agent SDK.

This package provides a Python client for [Data Source] that implements
the driver contract pattern for AI agent integration.
"""

from .client import Client
from .config import DriverConfig
from .exceptions import (
    DriverError,
    AuthenticationError,
    AuthorizationError,
    NotFoundError,
    QueryError,
    RateLimitError,
    ConnectionError,
    TimeoutError,
    ValidationError,
)

__version__ = "0.1.0"

__all__ = [
    "Client",
    "DriverConfig",
    "DriverError",
    "AuthenticationError",
    "AuthorizationError",
    "NotFoundError",
    "QueryError",
    "RateLimitError",
    "ConnectionError",
    "TimeoutError",
    "ValidationError",
]
```

**Day 2-3 Checkpoint:** Core driver is complete with all production infrastructure.

---

## Phase 3: Testing (Day 4)

### Step 3.1: Test Fixtures (1 hour)

```python
# tests/conftest.py
import pytest
from unittest.mock import Mock, patch
from my_driver import Client, DriverConfig

@pytest.fixture
def config():
    """Test configuration."""
    return DriverConfig(
        api_key="test_key",
        project_id="test_project"
    )

@pytest.fixture
def mock_client(config):
    """Mock client with patched HTTP."""
    with patch('my_driver.client.requests.Session') as mock_session:
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {'results': []}
        mock_session.return_value.post.return_value = mock_response

        client = Client(config)
        yield client

@pytest.fixture
def sample_events():
    """Sample event data."""
    return [
        {'event': 'pageview', 'count': 100},
        {'event': 'signup', 'count': 50},
    ]
```

### Step 3.2: Core Tests (3-4 hours)

```python
# tests/test_client.py
import pytest
from my_driver import Client, DriverConfig, QueryError, ValidationError

def test_list_objects(mock_client):
    """Test list_objects returns entity types."""
    objects = mock_client.list_objects()
    assert isinstance(objects, list)
    assert 'events' in objects
    assert len(objects) > 0

def test_get_fields(mock_client):
    """Test get_fields returns schema."""
    fields = mock_client.get_fields('events')
    assert isinstance(fields, dict)
    assert 'event' in fields
    assert 'type' in fields['event']

def test_query_validation(mock_client):
    """Test query validates input."""
    with pytest.raises(ValidationError):
        mock_client.query("")

    with pytest.raises(ValidationError):
        mock_client.query("   ")

def test_query_success(mock_client):
    """Test successful query."""
    results = mock_client.query("SELECT * FROM events")
    assert isinstance(results, list)

def test_exponential_backoff(config):
    """Test retry uses exponential backoff."""
    call_times = []

    def mock_request(*args, **kwargs):
        call_times.append(time.time())
        if len(call_times) < 3:
            raise requests.exceptions.Timeout()
        return Mock(status_code=200, json=lambda: {'results': []})

    with patch.object(requests.Session, 'post', side_effect=mock_request):
        client = Client(config)
        client.query("SELECT * FROM events")

    assert len(call_times) == 3
    # Verify increasing delays
    assert call_times[1] - call_times[0] >= 1
    assert call_times[2] - call_times[1] >= 2

def test_rate_limiting(config):
    """Test rate limiter enforced."""
    client = Client(config)

    # Exhaust rate limit
    for _ in range(config.rate_limit_per_minute):
        assert client.rate_limiter.acquire()

    # Next should fail
    assert not client.rate_limiter.acquire()

def test_circuit_breaker(config):
    """Test circuit breaker opens on failures."""
    with patch.object(requests.Session, 'post', side_effect=Exception("Fail")):
        client = Client(config)

        # Trigger failures
        for _ in range(5):
            with pytest.raises(Exception):
                client.query("SELECT * FROM events")

        # Circuit should be open
        assert client.circuit_breaker.state == CircuitState.OPEN

def test_context_manager(config):
    """Test context manager cleanup."""
    with Client(config) as client:
        assert client.session is not None

    # Session should be closed
    # (In real implementation, verify session.close() was called)
```

**Day 4 Checkpoint:** 95%+ test coverage achieved.

---

## Phase 4: Claude Integration (Day 5)

### Step 4.1: Tool Definition (1 hour)

```python
# examples/claude_integration.py
TOOL = {
    "name": "query_data_source",
    "description": """Query [Data Source] analytics using natural language.

    This tool can:
    - List available entity types (events, persons, etc.)
    - Get schema for any entity type
    - Execute queries in native query language
    - Return formatted results

    Examples:
    - "What are the top events in the last 7 days?"
    - "Show me user cohorts"
    - "Get the schema for the events table"

    Note: Results are limited to 1000 rows by default.
    """,
    "input_schema": {
        "type": "object",
        "properties": {
            "operation": {
                "type": "string",
                "enum": ["list_objects", "get_fields", "query"],
                "description": "Operation to perform"
            },
            "object_name": {
                "type": "string",
                "description": "Entity name (for get_fields)"
            },
            "query": {
                "type": "string",
                "description": "Query string (for query operation)"
            }
        },
        "required": ["operation"]
    }
}

SYSTEM_PROMPT = """You are an analytics assistant helping users query [Data Source].

When users ask questions:
1. Use list_objects to discover available entities
2. Use get_fields to understand entity schemas
3. Use query to execute queries and get results
4. Interpret results in business context
5. Provide actionable insights

Always explain your reasoning and suggest follow-up analyses."""
```

### Step 4.2: E2B Integration (2-3 hours)

```python
# examples/e2b_integration.py
from e2b import Sandbox
import os

def execute_in_sandbox(query: str) -> str:
    """Execute query in E2B sandbox."""

    # Create sandbox
    sandbox = Sandbox(api_key=os.getenv('E2B_API_KEY'))

    try:
        # Upload driver
        for filename in ['__init__.py', 'client.py', 'config.py', 'exceptions.py']:
            with open(f'my_driver/{filename}', 'r') as f:
                sandbox.files.write(f'/home/user/my_driver/{filename}', f.read())

        # Install dependencies
        sandbox.commands.run('pip install requests python-dotenv -q')

        # Create query script
        script = f'''
import sys
sys.path.insert(0, '/home/user')
from my_driver import Client, DriverConfig

config = DriverConfig(
    api_key="{os.getenv('API_KEY')}",
    project_id="{os.getenv('PROJECT_ID')}"
)

client = Client(config)
results = client.query("""{query}""")

for row in results:
    print(row)
'''

        # Execute
        sandbox.files.write('/home/user/query.py', script)
        result = sandbox.commands.run('cd /home/user && python3 query.py')

        return result.stdout or result.stderr

    finally:
        sandbox.kill()
```

### Step 4.3: Complete Integration Example (2 hours)

```python
# examples/complete_example.py
from anthropic import Anthropic
from e2b import Sandbox
import os

def main():
    anthropic = Anthropic(api_key=os.getenv('ANTHROPIC_API_KEY'))

    messages = [{
        "role": "user",
        "content": "What are the top 5 events in the last week?"
    }]

    while True:
        response = anthropic.messages.create(
            model="claude-sonnet-4-5-20250929",
            max_tokens=4096,
            system=SYSTEM_PROMPT,
            tools=[TOOL],
            messages=messages
        )

        if response.stop_reason != "tool_use":
            # Final answer
            answer = next((b.text for b in response.content if hasattr(b, "text")), "")
            print(answer)
            break

        # Handle tool calls
        tool_results = []
        for tool_use in [b for b in response.content if b.type == "tool_use"]:
            operation = tool_use.input["operation"]

            if operation == "list_objects":
                result = client.list_objects()
            elif operation == "get_fields":
                result = client.get_fields(tool_use.input["object_name"])
            elif operation == "query":
                result = execute_in_sandbox(tool_use.input["query"])

            tool_results.append({
                "type": "tool_result",
                "tool_use_id": tool_use.id,
                "content": str(result)
            })

        # Continue conversation
        messages.append({"role": "assistant", "content": response.content})
        messages.append({"role": "user", "content": tool_results})

if __name__ == '__main__':
    main()
```

**Day 5 Checkpoint:** Full Claude + E2B integration working.

---

## Phase 5: Documentation (Day 6)

### Step 5.1: README.md (2 hours)

```markdown
# My Driver

Driver for [Data Source] with Claude Agent SDK integration.

## Features

- **Driver Contract**: Standard 3-method interface
- **Production Ready**: Logging, rate limiting, circuit breakers
- **Claude Integration**: Natural language querying
- **E2B Sandbox**: Secure execution
- **Well Tested**: 95%+ coverage

## Installation

\`\`\`bash
pip install my-driver
\`\`\`

## Quick Start

\`\`\`python
from my_driver import Client, DriverConfig

config = DriverConfig.from_env()
client = Client(config)

# Discover entities
objects = client.list_objects()

# Get schema
fields = client.get_fields('events')

# Execute query
results = client.query("SELECT * FROM events LIMIT 5")
\`\`\`

## Environment Variables

\`\`\`bash
export API_KEY="your_api_key"
export PROJECT_ID="your_project_id"
\`\`\`

## Documentation

- [API Reference](docs/API.md)
- [Architecture](docs/ARCHITECTURE.md)
- [Contributing](CONTRIBUTING.md)
- [Security](SECURITY.md)

## License

MIT License - see [LICENSE](LICENSE)
```

### Step 5.2: API Documentation (2 hours)

Create `docs/API.md` with complete API reference for all methods.

### Step 5.3: Essential Documents (2 hours)

- CONTRIBUTING.md - Development setup and guidelines
- SECURITY.md - Security policy and vulnerability reporting
- CHANGELOG.md - Version history starting at v0.1.0

**Day 6 Checkpoint:** Complete documentation ready.

---

# Part 4: PRODUCTION CHECKLIST

## Pre-Deployment Checklist

### Security ✅
- [ ] No hardcoded secrets anywhere
- [ ] All secrets from environment variables
- [ ] Pre-commit hooks for secret detection
- [ ] Git history clean
- [ ] SQL injection prevention implemented
- [ ] Input validation on all user inputs
- [ ] .gitignore includes .env, *.env

### Infrastructure ✅
- [ ] Logging infrastructure complete
- [ ] Exponential backoff with jitter
- [ ] Rate limiting active
- [ ] Circuit breaker implemented
- [ ] Health check endpoint
- [ ] Proper error handling everywhere
- [ ] Timeout configuration per operation

### Code Quality ✅
- [ ] setup.py created
- [ ] Type hints everywhere
- [ ] 95%+ test coverage
- [ ] All tests passing
- [ ] Linting (flake8) passing
- [ ] Type checking (mypy) passing
- [ ] No TODO/FIXME in code

### Documentation ✅
- [ ] LICENSE file
- [ ] README.md with examples
- [ ] CONTRIBUTING.md
- [ ] SECURITY.md
- [ ] CHANGELOG.md
- [ ] API documentation
- [ ] Architecture documentation
- [ ] .env.example with placeholders

### Deployment ✅
- [ ] requirements.txt pinned versions
- [ ] setup.py with version
- [ ] CI/CD pipeline configured
- [ ] Docker image (optional)
- [ ] Deployment guide written

---

## Key Lessons Learned

### What Worked

1. **Foundation First** - Building logging, config, error handling on Day 1 saved weeks
2. **Driver Contract** - Standard interface enabled dynamic discovery
3. **Security by Default** - Pre-commit hooks prevented secret leaks
4. **Test as You Go** - 95% coverage from start, not afterthought

### What Didn't Work

1. **Hardcoded Keys** - Even "just for examples" required full git history rewrite
2. **Linear Retry** - Hammered APIs during outages, exponential backoff essential
3. **No Logging First** - Made debugging impossible, added later with pain
4. **Missing Rate Limiting** - Would have violated limits on day 1 of production

### Time Investment Reality

| Phase | Planned | Actual |
|-------|---------|--------|
| Foundation | 1 day | 1 day ✅ |
| Core Driver | 2 days | 2-3 days |
| Testing | 1 day | 1 day ✅ |
| Claude Integration | 1 day | 1-2 days |
| Documentation | 1 day | 1 day ✅ |
| **Total** | **1 week** | **1-1.5 weeks** |

**Budget 1.5x planned time for production quality.**

---

## Quick Reference

### Development Commands

```bash
# Setup
python -m venv venv
source venv/bin/activate
pip install -e ".[dev]"

# Testing
pytest                          # Run tests
pytest --cov=my_driver          # With coverage
pytest -v                       # Verbose

# Code Quality
black .                         # Format
flake8                          # Lint
mypy my_driver/                 # Type check

# Security
detect-secrets scan             # Scan for secrets
pre-commit run --all-files      # Run hooks
```

### Project Template

Use this repository as a template:
```bash
git clone https://github.com/yourusername/python-driver-template
cd python-driver-template
# Follow Phase 1 implementation plan
```

---

## Resources

- **Claude Agent SDK**: https://docs.anthropic.com/claude/docs
- **E2B Sandboxes**: https://e2b.dev/docs
- **Python Packaging**: https://packaging.python.org/
- **Semantic Versioning**: https://semver.org/

---

**Last Updated:** 2025-11-11
**Status:** Production-Ready Blueprint
**Estimated Time:** 1-1.5 weeks for complete implementation

---

*This guide represents the ideal path from goal to architecture to implementation, incorporating all lessons learned from building the PostHog driver.*
