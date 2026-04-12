# CardDemo Production Deployment Guide

## Overview

This guide covers deploying the CardDemo Django application to a production environment with PostgreSQL, Redis, and gunicorn behind a reverse proxy.

## Prerequisites

- Python 3.12+
- PostgreSQL 16+
- Redis 7+ (optional, for session caching)
- Docker and Docker Compose (recommended)
- A reverse proxy (nginx, Caddy, or cloud load balancer)

## Environment Variables

All configuration is via environment variables. **Never commit secrets to source control.**

| Variable | Required | Default | Description |
|---|---|---|---|
| `DJANGO_SECRET_KEY` | **Yes** (production) | `insecure-change-me-in-production` | Django secret key — generate with `python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"` |
| `DJANGO_SETTINGS_MODULE` | No | `carddemo.settings.development` | Settings module to use |
| `DJANGO_DEBUG` | No | `False` | Enable debug mode (NEVER in production) |
| `DJANGO_ALLOWED_HOSTS` | **Yes** (production) | `*` | Comma-separated list of allowed hostnames |
| `DATABASE_URL` | No | `postgres://carddemo:carddemo@localhost:5432/carddemo` | PostgreSQL connection URL |
| `DJANGO_CONN_MAX_AGE` | No | `600` | Database connection pooling lifetime (seconds) |
| `REDIS_URL` | No | _(empty)_ | Redis URL for session caching (e.g., `redis://localhost:6379/0`) |
| `DJANGO_SECURE_SSL_REDIRECT` | No | `True` | Redirect HTTP to HTTPS |

## Option 1: Docker Compose (Recommended)

### Quick Start

```bash
# Clone the repository
git clone https://github.com/kaishen712-cpu/aws-mainframe-modernization-carddemo.git
cd aws-mainframe-modernization-carddemo

# Set your secret key
export DJANGO_SECRET_KEY=$(python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())")

# Start all services
docker compose up -d

# Run database migrations
docker compose exec web python manage.py migrate

# Create a superuser (optional)
docker compose exec web python manage.py createsuperuser

# Verify health
docker compose ps
curl http://localhost:8000/admin/login/
```

### Architecture

```
┌─────────┐     ┌──────────┐     ┌──────────────┐
│  nginx   │────▶│  gunicorn │────▶│  PostgreSQL   │
│  (proxy) │     │  (Django) │     │  (port 5432)  │
└─────────┘     └──────────┘     └──────────────┘
                     │
                     ▼
                ┌──────────┐
                │   Redis   │
                │  (sessions│
                │  port 6379│
                └──────────┘
```

### Stopping Services

```bash
docker compose down           # Stop containers
docker compose down -v        # Stop and remove volumes (deletes data!)
```

## Option 2: Manual Deployment

### 1. PostgreSQL Setup

```bash
# Install PostgreSQL
sudo apt-get install postgresql postgresql-contrib

# Create database and user
sudo -u postgres createuser carddemo
sudo -u postgres createdb -O carddemo carddemo
sudo -u postgres psql -c "ALTER USER carddemo WITH PASSWORD 'your-secure-password';"
```

### 2. Application Setup

```bash
# Install Python dependencies
pip install .

# Set environment variables
export DJANGO_SETTINGS_MODULE=carddemo.settings.production
export DJANGO_SECRET_KEY='your-secret-key-here'
export DJANGO_ALLOWED_HOSTS='yourdomain.com,www.yourdomain.com'
export DATABASE_URL='postgres://carddemo:your-secure-password@localhost:5432/carddemo'

# Run migrations
python manage.py migrate

# Collect static files
python manage.py collectstatic --noinput

# Create superuser
python manage.py createsuperuser
```

### 3. Gunicorn Configuration

```bash
# Start gunicorn
gunicorn carddemo.wsgi:application \
    --bind 0.0.0.0:8000 \
    --workers 4 \
    --timeout 120 \
    --graceful-timeout 30 \
    --access-logfile - \
    --error-logfile -
```

### 4. Systemd Service (Optional)

Create `/etc/systemd/system/carddemo.service`:

```ini
[Unit]
Description=CardDemo Django Application
After=network.target postgresql.service

[Service]
User=carddemo
Group=carddemo
WorkingDirectory=/opt/carddemo
Environment="DJANGO_SETTINGS_MODULE=carddemo.settings.production"
Environment="DJANGO_SECRET_KEY=your-secret-key"
Environment="DJANGO_ALLOWED_HOSTS=yourdomain.com"
Environment="DATABASE_URL=postgres://carddemo:password@localhost:5432/carddemo"
ExecStart=/opt/carddemo/venv/bin/gunicorn carddemo.wsgi:application \
    --bind 0.0.0.0:8000 \
    --workers 4 \
    --timeout 120
Restart=always
RestartSec=3

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl daemon-reload
sudo systemctl enable carddemo
sudo systemctl start carddemo
```

### 5. Nginx Reverse Proxy

```nginx
server {
    listen 80;
    server_name yourdomain.com;
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl;
    server_name yourdomain.com;

    ssl_certificate /etc/letsencrypt/live/yourdomain.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/yourdomain.com/privkey.pem;

    location /static/ {
        alias /opt/carddemo/staticfiles/;
    }

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

## Running Batch Jobs

Batch jobs are Django management commands, replacing the original JCL jobs:

```bash
# Post daily transactions
python manage.py post_transactions

# Calculate interest
python manage.py calc_interest

# Generate statements
python manage.py gen_statements

# Generate transaction report
python manage.py gen_transaction_report

# Export data
python manage.py export_data

# Import data
python manage.py import_data
```

### Scheduling with Cron

```cron
# Daily batch processing (runs at 2 AM)
0 2 * * * cd /opt/carddemo && /opt/carddemo/venv/bin/python manage.py post_transactions
15 2 * * * cd /opt/carddemo && /opt/carddemo/venv/bin/python manage.py calc_interest
30 2 * * * cd /opt/carddemo && /opt/carddemo/venv/bin/python manage.py gen_statements
```

## Security Considerations

- **Never commit secrets** — all credentials via environment variables
- **HTTPS required** — `SECURE_SSL_REDIRECT=True` enforced in production settings
- **HSTS enabled** — 1-year HSTS with preload
- **Secure cookies** — `SESSION_COOKIE_SECURE=True`, `CSRF_COOKIE_SECURE=True`
- **Connection pooling** — `CONN_MAX_AGE=600` prevents connection exhaustion
- **Never log sensitive data** — account numbers, card numbers, and transaction amounts must never appear in plain text in logs (CPS 234 requirement)
- **Password hashing** — Django uses PBKDF2 by default; consider Argon2 for production
- **CSRF protection** — enabled by default in Django middleware

## Monitoring

### Health Checks

- Docker: Built-in health checks on all services
- Application: `GET /admin/login/` returns 200 when healthy
- PostgreSQL: `pg_isready -U carddemo -d carddemo`
- Redis: `redis-cli ping`

### Logs

```bash
# Docker Compose
docker compose logs -f web

# Systemd
journalctl -u carddemo -f
```

## Backup & Recovery

```bash
# Database backup
pg_dump -U carddemo carddemo > backup_$(date +%Y%m%d).sql

# Database restore
psql -U carddemo carddemo < backup_20250115.sql
```
