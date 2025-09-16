# Configuration Reference

This document provides a comprehensive reference for all configuration options available in PrisMind.

## Table of Contents
- [Environment Variables](#environment-variables)
- [Application Settings](#application-settings)
- [Database Configuration](#database-configuration)
- [Authentication](#authentication)
- [API Configuration](#api-configuration)
- [Caching](#caching)
- [Logging](#logging)
- [External Services](#external-services)
- [Rate Limiting](#rate-limiting)
- [Security](#security)
- [Performance](#performance)

## Environment Variables

All configuration is done through environment variables. You can set these in your `.env` file or in your deployment environment.

## Application Settings

| Variable | Type | Default | Description |
|----------|------|---------|-------------|
| `DEBUG` | bool | `False` | Enable debug mode (not for production) |
| `ENVIRONMENT` | string | `development` | Application environment (`development`, `staging`, `production`) |
| `SECRET_KEY` | string | (auto-generated) | Secret key for cryptographic operations |
| `ALLOWED_HOSTS` | list | `[]` | List of allowed hostnames |
| `TIME_ZONE` | string | `UTC` | Default timezone |
| `DEFAULT_LOCALE` | string | `en-us` | Default locale |

## Database Configuration

| Variable | Type | Default | Description |
|----------|------|---------|-------------|
| `DATABASE_URL` | URL | `sqlite:///db.sqlite3` | Database connection URL |
| `DATABASE_POOL_SIZE` | int | `5` | Connection pool size |
| `DATABASE_MAX_OVERFLOW` | int | `10` | Maximum overflow connections |
| `DATABASE_ECHO` | bool | `False` | Log SQL queries |

## Authentication

| Variable | Type | Default | Description |
|----------|------|---------|-------------|
| `AUTH_ENABLED` | bool | `True` | Enable authentication |
| `AUTH_TOKEN_EXPIRE_MINUTES` | int | `1440` | Token expiration in minutes |
| `PASSWORD_RESET_TIMEOUT` | int | `86400` | Password reset token timeout in seconds |
| `REQUIRE_EMAIL_VERIFICATION` | bool | `True` | Require email verification |

## API Configuration

| Variable | Type | Default | Description |
|----------|------|---------|-------------|
| `API_PREFIX` | string | `/api/v1` | API URL prefix |
| `API_DOCS_ENABLED` | bool | `True` | Enable API documentation |
| `CORS_ORIGINS` | list | `[]` | Allowed CORS origins |
| `CORS_ALLOW_CREDENTIALS` | bool | `True` | Allow credentials in CORS |

## Caching

| Variable | Type | Default | Description |
|----------|------|---------|-------------|
| `CACHE_ENABLED` | bool | `True` | Enable caching |
| `CACHE_URL` | URL | `redis://localhost:6379/1` | Cache server URL |
| `CACHE_DEFAULT_TIMEOUT` | int | `300` | Default cache timeout in seconds |

## Logging

| Variable | Type | Default | Description |
|----------|------|---------|-------------|
| `LOG_LEVEL` | string | `INFO` | Logging level |
| `LOG_FORMAT` | string | `json` | Log format (`json` or `text`) |
| `LOG_FILE` | string | `None` | Log file path |
| `SENTRY_DSN` | string | `None` | Sentry DSN for error tracking |

## External Services

### SMTP (Email)

| Variable | Type | Default | Description |
|----------|------|---------|-------------|
| `SMTP_SERVER` | string | `smtp.gmail.com` | SMTP server |
| `SMTP_PORT` | int | `587` | SMTP port |
| `SMTP_USERNAME` | string | `None` | SMTP username |
| `SMTP_PASSWORD` | string | `None` | SMTP password |
| `EMAIL_FROM` | string | `noreply@example.com` | Sender email address |

### Storage

| Variable | Type | Default | Description |
|----------|------|---------|-------------|
| `STORAGE_TYPE` | string | `local` | Storage type (`local`, `s3`, `gcs`) |
| `STORAGE_LOCATION` | string | `./storage` | Local storage path |
| `AWS_ACCESS_KEY_ID` | string | `None` | AWS access key |
| `AWS_SECRET_ACCESS_KEY` | string | `None` | AWS secret key |
| `AWS_STORAGE_BUCKET_NAME` | string | `None` | S3 bucket name |
| `AWS_S3_REGION_NAME` | string | `None` | AWS region |

## Rate Limiting

| Variable | Type | Default | Description |
|----------|------|---------|-------------|
| `RATE_LIMIT_ENABLED` | bool | `True` | Enable rate limiting |
| `RATE_LIMIT_DEFAULT` | string | `100/minute` | Default rate limit |
| `RATE_LIMIT_AUTHENTICATED` | string | `1000/minute` | Rate limit for authenticated users |
| `RATE_LIMIT_ANONYMOUS` | string | `10/minute` | Rate limit for anonymous users |

## Security

| Variable | Type | Default | Description |
|----------|------|---------|-------------|
| `SECURE_SSL_REDIRECT` | bool | `True` | Redirect HTTP to HTTPS |
| `SESSION_COOKIE_SECURE` | bool | `True` | Secure session cookies |
| `CSRF_COOKIE_SECURE` | bool | `True` | Secure CSRF cookies |
| `SECURE_HSTS_SECONDS` | int | `31536000` | HSTS header lifetime |
| `SECURE_HSTS_INCLUDE_SUBDOMAINS` | bool | `True` | Include subdomains in HSTS |
| `SECURE_HSTS_PRELOAD` | bool | `True` | Enable HSTS preload |
| `SECURE_CONTENT_TYPE_NOSNIFF` | bool | `True` | Add X-Content-Type-Options header |
| `X_FRAME_OPTIONS` | string | `DENY` | X-Frame-Options header |
| `CONTENT_SECURITY_POLICY` | string | `None` | Content-Security-Policy header |

## Performance

| Variable | Type | Default | Description |
|----------|------|---------|-------------|
| `WORKERS` | int | `4` | Number of worker processes |
| `THREADS` | int | `2` | Threads per worker |
| `WORKER_CLASS` | string | `uvicorn.workers.UvicornWorker` | Worker class |
| `WORKER_TIMEOUT` | int | `120` | Worker timeout in seconds |
| `MAX_REQUESTS` | int | `1000` | Max requests per worker before restart |
| `MAX_REQUESTS_JITTER` | int | `100` | Jitter for max requests |

## Example Configuration

```env
# Application
DEBUG=False
ENVIRONMENT=production
SECRET_KEY=your-secret-key
ALLOWED_HOSTS=example.com,www.example.com

# Database
DATABASE_URL=postgresql://user:password@localhost:5432/prismind
DATABASE_POOL_SIZE=10
DATABASE_MAX_OVERFLOW=20

# Caching
CACHE_ENABLED=True
CACHE_URL=redis://localhost:6379/1

# Email
SMTP_SERVER=smtp.example.com
SMTP_PORT=587
SMTP_USERNAME=user@example.com
SMTP_PASSWORD=your-password
EMAIL_FROM=noreply@example.com

# Security
SECURE_SSL_REDIRECT=True
SESSION_COOKIE_SECURE=True
CSRF_COOKIE_SECURE=True
```

## Configuration Validation

Configuration is validated on application startup. If any required variables are missing or invalid, the application will fail to start with a descriptive error message.

## Environment-Specific Configuration

You can create environment-specific `.env` files:
- `.env` - Base configuration
- `.env.development` - Development overrides
- `.env.production` - Production overrides
- `.env.local` - Local overrides (ignored by git)

Variables are loaded in the following order (later values override earlier ones):
1. `.env`
2. `.env.${ENVIRONMENT}`
3. `.env.local`
4. Environment variables
