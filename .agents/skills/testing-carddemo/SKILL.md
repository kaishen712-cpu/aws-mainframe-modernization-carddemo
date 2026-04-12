# CardDemo Testing Skill

## Overview
The CardDemo project is a Django-based COBOL-to-Python migration for a mainframe credit card management system. Testing involves linting, type checking, a pytest test suite with coverage enforcement, Docker builds, and Django settings verification.

## Prerequisites
- Python 3.12+
- Dependencies installed via `pip install -e ".[dev]"`
- No database required for unit/integration tests (testing settings use SQLite in-memory)

## Devin Secrets Needed
- None required for local testing
- For production deployment: `DJANGO_SECRET_KEY`, `DJANGO_ALLOWED_HOSTS`, `DATABASE_URL`, `REDIS_URL`

## Running Checks Locally

### 1. Linting (Ruff)
```bash
ruff check .          # Lint rules
ruff format --check . # Format check
```
- The `pyproject.toml` excludes `python/*` and `build/*` directories (pre-existing code from earlier phases)
- If ruff format fails on pre-existing files, run `ruff format .` to auto-fix
- Warning about `TCH003` remapped to `TC003` is expected and harmless

### 2. Type Checking (Mypy)
```bash
mypy .
```
- `environ` and `factory` modules have mypy overrides for missing stubs (configured in `pyproject.toml`)
- `tests.*` modules have relaxed type checking (`disallow_untyped_calls=false`, `disallow_any_generics=false`, `disable_error_code=["attr-defined"]`)
- If you see duplicate module errors, check that `build/` directory is excluded in `[tool.mypy]` config

### 3. Test Suite
```bash
# Full suite with coverage (70% threshold)
DJANGO_SETTINGS_MODULE=carddemo.settings.testing pytest tests/ --cov=batch --cov-report=term-missing --cov-fail-under=70

# Security-module coverage (90% threshold)
DJANGO_SETTINGS_MODULE=carddemo.settings.testing pytest tests/unit/test_record_cache.py tests/unit/test_batch_account_updater.py tests/unit/test_batch_post_transactions.py tests/unit/test_batch_interest.py --cov=batch.services --cov-report=term-missing --cov-fail-under=90
```
- Tests use SQLite in-memory (testing.py settings), no PostgreSQL needed locally
- `testpaths = ["tests"]` in pyproject.toml prevents collecting pre-existing `python/tests/` directory
- 122 tests expected (as of Phase 8)

### 4. Docker Build
```bash
docker build -t carddemo-test .
```
- Multi-stage build: builder stage installs deps, runtime stage copies only what's needed
- `collectstatic` runs during build with placeholder env vars
- Non-root user `carddemo:1000`

### 5. Django Settings Verification
```bash
DJANGO_SETTINGS_MODULE=carddemo.settings.testing python -c "from django.conf import settings; print(settings.DEBUG, settings.DATABASES)"
```

## Coverage Requirements
- **70% overall** — enforced by `--cov-fail-under=70` in CI
- **90% for batch.services** — enforced as a hard CI gate (no `|| echo` escape)
- Security-sensitive modules: auth, session management, transaction processing, interest calc, RecordCache, BatchAccountUpdater

## Common Issues
- **`ruff format` fails on batch/ files**: Pre-existing files from Phase 1 may need formatting. Run `ruff format .` to auto-fix.
- **mypy `attr-defined` errors on `factory.Sequence`**: The `factory-boy` library lacks proper type stubs. These are suppressed in `tests.*` via pyproject.toml overrides.
- **`environ.Env()` mypy error**: Suppressed with `# type: ignore[attr-defined]` on line 20 of `base.py`.
- **pytest collects `python/tests/`**: Fixed by `testpaths = ["tests"]` in pyproject.toml. If you see `ModuleNotFoundError` from `python/tests/`, check this config.

## JSON Log Formatter
The `carddemo/logging.py` module provides a `JSONFormatter` that produces real JSON output (not plain text). To verify:
```bash
DJANGO_SETTINGS_MODULE=carddemo.settings.testing python -c "
import logging, json
from carddemo.logging import JSONFormatter
fmt = JSONFormatter()
record = logging.LogRecord('test', logging.INFO, 'test.py', 1, 'msg', (), None)
print(json.loads(fmt.format(record)))
"
```

## CPS 234 Compliance
- All test data must be synthetic — NEVER use real customer data
- Never log account numbers, card numbers, or transaction amounts in plain text
- Tag the security lead on PRs that touch credit card processing, transaction posting, authentication, or balance calculations
