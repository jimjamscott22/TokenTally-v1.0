# TokenTally

TokenTally is a local-first usage dashboard for managing multiple AI subscriptions in one place.

It allows users to manually report usage for services like ChatGPT Plus, Claude Pro, Gemini, Copilot, and Cursor, while supporting future integration with official APIs where available.

The goal is simple: before starting a project, quickly see which provider has capacity, which is nearing limits, and which should be avoided.

## Core Features

- Unified dashboard for multiple AI providers
- Manual usage self-reporting with status, freeform text, and notes
- File import (CSV/JSON) for providers that support data export
- Extensible connector architecture (API, manual import, unsupported)
- MariaDB storage on local network (Raspberry Pi 5)
- Server-Sent Events (SSE) via Datastar for live card updates
- Snapshot history for tracking patterns over time
- HTTP Basic auth for local admin access

## Supported Providers

| Provider | Mode | Notes |
|----------|------|-------|
| GitHub Copilot | Manual Import | CSV import with `date,requests,tokens` columns |
| Cursor Pro | Manual Import | JSON import stub |
| ChatGPT Plus | Manual Import | Conversation count from JSON export |
| Claude Pro | Manual Import | Generic JSON import |
| Gemini | Unsupported | Self-report only |

All providers support **manual self-reporting** regardless of mode.

## Tech Stack

- **Backend:** Python 3.11+ / FastAPI
- **Frontend:** Datastar (HTML data-* attributes + SSE)
- **Database:** MariaDB (on Raspberry Pi 5)
- **Auth:** HTTP Basic (single admin user)

## Quick Start

### 1. MariaDB Setup (on Raspberry Pi)

```sql
CREATE DATABASE tokentally CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE USER 'tokentally'@'%' IDENTIFIED BY 'your_password_here';
GRANT ALL PRIVILEGES ON tokentally.* TO 'tokentally'@'%';
FLUSH PRIVILEGES;
```

### 2. Clone and Install

```bash
git clone <repo-url>
cd TokenTally-v1.0
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

### 3. Configure

```bash
cp .env.example .env
# Edit .env with your MariaDB host IP and password
```

### 4. Run

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Open `http://localhost:8000` in your browser. Login with `admin` / your configured password.

## Usage

### Self-Reporting

1. Click **Report Usage** on any provider card
2. Select a status (Good / Caution / Near Limit / Unknown)
3. Add a usage summary (e.g. "~25 messages left", "$8/$20", "throttled")
4. Optionally add notes and a reset datetime
5. Submit - the card updates immediately via SSE

### File Import

1. Click **Import File** on a supported provider card
2. Upload a CSV or JSON file matching the expected format
3. The file is parsed and a usage snapshot is created

### Sample Import Format (GitHub Copilot CSV)

```csv
date,requests,tokens
2026-02-01,45,12500
2026-02-03,62,18300
2026-02-05,38,9800
```

A sample file is provided at `sample_data/github_copilot_sample.csv`.

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/` | Dashboard HTML |
| GET | `/sse/refresh_all` | SSE stream: refresh all providers |
| GET | `/sse/refresh/{key}` | SSE stream: refresh one provider |
| POST | `/report/{key}` | Manual self-report (form data) |
| POST | `/import/{key}` | File upload and parse |
| GET | `/api/snapshots?provider_key=...&month=YYYY-MM` | Query snapshots |

## Running Tests

```bash
python -m pytest tests/test_parsers.py -v
```

Endpoint tests require a configured test database (see `tests/test_endpoints.py`).

## Architecture

```
app/
  main.py           - FastAPI app, endpoints, SSE streaming
  models.py         - SQLModel tables, Pydantic schemas
  db.py             - MariaDB engine, session, seed data
  auth.py           - HTTP Basic auth
  html_renderer.py  - HTML fragment generators for Datastar morphing
  connectors/
    base.py         - Abstract BaseConnector
    github_copilot.py, cursor.py, chatgpt_plus.py, claude_pro.py, gemini_consumer.py
templates/
  index.html        - Single-page Datastar dashboard
static/
  style.css         - Dark theme styles
```

## Philosophy

Many consumer AI subscriptions do not provide official usage APIs. TokenTally embraces this reality by treating manual reporting as a first-class feature, while remaining extensible for future automation.

This project is local-first, privacy-conscious, and avoids scraping or storing account credentials.

## License

MIT License - Copyright 2026 Jamie Scott
