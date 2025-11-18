# Services Runbook

This runbook explains how to operate the decoupled Prismind control plane and workers.

## Components

- **redis**: message broker for job queues
- **api**: FastAPI control service exposing `/jobs/*` endpoints
- **worker-***: RQ workers for publishers, rewriters, and collectors
- **svelte**: control panel UI (calls the API rather than executing jobs inline)

## Environment

Create a `.env` file with the usual application settings plus:

```
REDIS_URL=redis://redis:6379/0
API_BASE_URL=http://localhost:8000
QUEUE_COLLECTOR_THREADS=collector_threads
QUEUE_COLLECTOR_TWITTER=collector_twitter
QUEUE_REWRITER=rewriter
QUEUE_PUBLISHER=publisher
ENABLE_TELEGRAM_CHANNELS=false
```

## Docker Compose

Build and run everything locally:

```bash
docker compose build
docker compose up
```

This starts Redis, the API, four workers (publisher, rewriter, threads collector, twitter collector) and Svelte on `http://localhost:8501`.

## Manual Processes (without Docker)

If Docker is unavailable (e.g. quick test on macOS):

```bash
# Start Redis
redis-server

# API (in a virtualenv)
uvicorn services.api.app:app --host 0.0.0.0 --port 8000

# Workers
python services/worker/run_worker.py --queue publisher
python services/worker/run_worker.py --queue rewriter
python services/worker/run_worker.py --queue collector_threads
python services/worker/run_worker.py --queue collector_twitter

# Svelte UI
svelte run src/web/app.py
```

Each worker can listen on multiple queues by repeating `--queue` flags.

## API Endpoints

- `POST /jobs/collect {"platform": "threads"|"twitter", "force_once": false}`
- `POST /jobs/process_backlog {"profiles": ["cryptoniard"], "posts_per_profile": 3}`
- `POST /jobs/publish_due {}`
- `GET /jobs/{job_id}` for status
- `GET /health`

## Svelte Changes

- Collection buttons enqueue jobs when `API_BASE_URL` is set
- Publish button enqueues `/jobs/publish_due`
- Legacy local execution remains as fallback when the API is unavailable

## Notes

- Telegram publishing is disabled by default (`ENABLE_TELEGRAM_CHANNELS=false`) to avoid 403 loops
- Workers install Playwright Chromium dependencies for the collectors
- Update `.env` and queue names as needed for production
