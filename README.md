# TokenTally

TokenTally is a local-first usage dashboard for managing multiple AI subscriptions in one place.

It allows users to manually report usage for services like ChatGPT Plus, Claude Pro, Gemini, Copilot, and Cursor, while supporting future integration with official APIs where available.

The goal is simple: before starting a project, quickly see which provider has capacity, which is nearing limits, and which should be avoided.

## Core Features

- Unified dashboard for multiple AI providers
- Manual usage reporting with monthly snapshots
- Extensible connector architecture (API, manual import, unsupported)
- Local SQLite storage
- Server-Sent Events (SSE) updates via Datastar
- Snapshot history for tracking patterns over time

## Philosophy

Many consumer AI subscriptions do not provide official usage APIs. TokenTally embraces this reality by treating manual reporting as a first-class feature, while remaining extensible for future automation.

This project is local-first, privacy-conscious, and avoids scraping or storing account credentials.

## Tech Stack

- FastAPI (backend)
- Datastar (frontend interactivity)
- SQLite (storage)
- Python 3.11+

## Status

MVP: Manual reporting + provider snapshot dashboard  
Future: API connectors, forecasting, project-based recommendations
