# ---------------------------------------------------------------------------
# CardDemo Django Application — Multi-stage Docker Build
# ---------------------------------------------------------------------------
# Stage 1: Build dependencies
# Stage 2: Production runtime with gunicorn
# ---------------------------------------------------------------------------

# ---- Stage 1: Builder ----
FROM python:3.12-slim AS builder

WORKDIR /app

# Install build dependencies
RUN apt-get update && \
    apt-get install -y --no-install-recommends gcc libpq-dev && \
    rm -rf /var/lib/apt/lists/*

COPY pyproject.toml ./
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir .

# ---- Stage 2: Production Runtime ----
FROM python:3.12-slim AS runtime

# Security: run as non-root user
RUN groupadd --gid 1000 carddemo && \
    useradd --uid 1000 --gid carddemo --shell /bin/bash --create-home carddemo

# Install runtime dependencies only
RUN apt-get update && \
    apt-get install -y --no-install-recommends libpq5 curl && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy installed packages from builder
COPY --from=builder /usr/local/lib/python3.12/site-packages /usr/local/lib/python3.12/site-packages
COPY --from=builder /usr/local/bin/gunicorn /usr/local/bin/gunicorn

# Copy application code
COPY . .

# Collect static files
RUN DJANGO_SECRET_KEY=build-placeholder DJANGO_SETTINGS_MODULE=carddemo.settings.production \
    DJANGO_ALLOWED_HOSTS=localhost \
    python manage.py collectstatic --noinput 2>/dev/null || true

# Switch to non-root user
USER carddemo

# Expose the application port
EXPOSE 8000

# Health check -- verifies gunicorn is responding
HEALTHCHECK --interval=30s --timeout=10s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:8000/admin/login/ || exit 1

# Graceful shutdown via gunicorn's SIGTERM handling
STOPSIGNAL SIGTERM

# Start gunicorn with proper signal handling
CMD ["gunicorn", "carddemo.wsgi:application", \
     "--bind", "0.0.0.0:8000", \
     "--workers", "4", \
     "--timeout", "120", \
     "--graceful-timeout", "30", \
     "--access-logfile", "-", \
     "--error-logfile", "-"]
