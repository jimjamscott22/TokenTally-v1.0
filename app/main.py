"""TokenTally FastAPI application - all endpoints and SSE streaming."""

import json
from contextlib import asynccontextmanager
from datetime import date, datetime, timezone
from pathlib import Path
from typing import AsyncGenerator

from dotenv import load_dotenv
from fastapi import Depends, FastAPI, Form, HTTPException, Query, UploadFile, File
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from jinja2 import Environment, FileSystemLoader
from sqlmodel import Session, select

from datastar_py import ServerSentEventGenerator as SSE
from datastar_py.fastapi import DatastarResponse

from app.auth import require_auth
from app.connectors import CONNECTOR_REGISTRY
from app.db import get_session, init_db
from app.html_renderer import render_log_entry, render_provider_card
from app.models import Provider, UsageSnapshot

load_dotenv()

# ---------------------------------------------------------------------------
# App setup
# ---------------------------------------------------------------------------

BASE_DIR = Path(__file__).resolve().parent.parent
TEMPLATES_DIR = BASE_DIR / "templates"
STATIC_DIR = BASE_DIR / "static"

jinja_env = Environment(loader=FileSystemLoader(str(TEMPLATES_DIR)), autoescape=True)


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield

app = FastAPI(title="TokenTally", version="0.1.0", lifespan=lifespan)
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _current_month_str() -> str:
    return date.today().strftime("%Y-%m")


def _month_start_end(month_str: str) -> tuple[date, date]:
    """Return (period_start, period_end) for a YYYY-MM string."""
    year, month = int(month_str[:4]), int(month_str[5:7])
    start = date(year, month, 1)
    if month == 12:
        end = date(year + 1, 1, 1)
    else:
        end = date(year, month + 1, 1)
    return start, end


def _get_latest_snapshots(session: Session) -> dict[str, UsageSnapshot | None]:
    """Get the most recent snapshot per provider key."""
    providers = session.exec(select(Provider)).all()
    result: dict[str, UsageSnapshot | None] = {}
    for p in providers:
        snap = session.exec(
            select(UsageSnapshot)
            .where(UsageSnapshot.provider_id == p.id)
            .order_by(UsageSnapshot.fetched_at.desc())  # type: ignore[union-attr]
        ).first()
        result[p.key] = snap
    return result


def _store_snapshot(
    session: Session,
    provider: Provider,
    metrics: dict,
    raw_payload: dict,
) -> UsageSnapshot:
    """Create and persist a UsageSnapshot."""
    month_str = metrics.get("month", _current_month_str())
    start, end = _month_start_end(month_str)

    snapshot = UsageSnapshot(
        provider_id=provider.id,
        period_start=start,
        period_end=end,
        fetched_at=datetime.now(timezone.utc),
        raw_payload=json.dumps(raw_payload),
        metrics_json=json.dumps(metrics),
    )
    session.add(snapshot)
    session.commit()
    session.refresh(snapshot)
    return snapshot


# ---------------------------------------------------------------------------
# GET / — Dashboard
# ---------------------------------------------------------------------------

@app.get("/", response_class=HTMLResponse)
def dashboard(
    _user: str = Depends(require_auth),
    session: Session = Depends(get_session),
):
    providers = session.exec(select(Provider).order_by(Provider.id)).all()
    snapshots = _get_latest_snapshots(session)

    cards_html = ""
    for p in providers:
        connector = CONNECTOR_REGISTRY.get(p.key)
        if connector:
            cards_html += render_provider_card(p, snapshots.get(p.key), connector)

    template = jinja_env.get_template("index.html")
    return template.render(cards_html=cards_html)


# ---------------------------------------------------------------------------
# SSE: Refresh All
# ---------------------------------------------------------------------------

@app.get("/sse/refresh_all")
async def sse_refresh_all(
    _user: str = Depends(require_auth),
    session: Session = Depends(get_session),
):
    async def stream() -> AsyncGenerator:
        yield SSE.patch_elements(
            render_log_entry("Starting full refresh..."),
            selector="#activity-log",
            mode="prepend",
        )

        providers = session.exec(select(Provider).where(Provider.enabled == True)).all()

        for provider in providers:
            connector = CONNECTOR_REGISTRY.get(provider.key)
            if not connector:
                continue

            yield SSE.patch_elements(
                render_log_entry(f"Refreshing {provider.display_name}..."),
                selector="#activity-log",
                mode="prepend",
            )

            try:
                year, month = date.today().year, date.today().month
                metrics, raw = await connector.fetch_usage(year, month)
                snapshot = _store_snapshot(session, provider, metrics, raw)

                yield SSE.patch_elements(
                    render_provider_card(provider, snapshot, connector)
                )
                yield SSE.patch_elements(
                    render_log_entry(f"{provider.display_name}: updated via API"),
                    selector="#activity-log",
                    mode="prepend",
                )

            except NotImplementedError as e:
                # Expected for manual_import/unsupported providers
                yield SSE.patch_elements(
                    render_log_entry(f"{provider.display_name}: {e}"),
                    selector="#activity-log",
                    mode="prepend",
                )

            except Exception as e:
                yield SSE.patch_elements(
                    render_log_entry(f"{provider.display_name}: Error - {e}"),
                    selector="#activity-log",
                    mode="prepend",
                )

        yield SSE.patch_elements(
            render_log_entry("Refresh complete."),
            selector="#activity-log",
            mode="prepend",
        )

    return DatastarResponse(stream())


# ---------------------------------------------------------------------------
# SSE: Refresh single provider
# ---------------------------------------------------------------------------

@app.get("/sse/refresh/{provider_key}")
async def sse_refresh_one(
    provider_key: str,
    _user: str = Depends(require_auth),
    session: Session = Depends(get_session),
):
    provider = session.exec(
        select(Provider).where(Provider.key == provider_key)
    ).first()
    if not provider:
        raise HTTPException(404, f"Unknown provider: {provider_key}")

    connector = CONNECTOR_REGISTRY.get(provider_key)
    if not connector:
        raise HTTPException(404, f"No connector for: {provider_key}")

    async def stream() -> AsyncGenerator:
        yield SSE.patch_elements(
            render_log_entry(f"Refreshing {provider.display_name}..."),
            selector="#activity-log",
            mode="prepend",
        )

        try:
            year, month = date.today().year, date.today().month
            metrics, raw = await connector.fetch_usage(year, month)
            snapshot = _store_snapshot(session, provider, metrics, raw)

            yield SSE.patch_elements(
                render_provider_card(provider, snapshot, connector)
            )
            yield SSE.patch_elements(
                render_log_entry(f"{provider.display_name}: updated via API"),
                selector="#activity-log",
                mode="prepend",
            )

        except NotImplementedError as e:
            yield SSE.patch_elements(
                render_log_entry(f"{provider.display_name}: {e}"),
                selector="#activity-log",
                mode="prepend",
            )

        except Exception as e:
            yield SSE.patch_elements(
                render_log_entry(f"{provider.display_name}: Error - {e}"),
                selector="#activity-log",
                mode="prepend",
            )

    return DatastarResponse(stream())


# ---------------------------------------------------------------------------
# POST: File import
# ---------------------------------------------------------------------------

@app.post("/import/{provider_key}")
async def import_file(
    provider_key: str,
    file: UploadFile = File(...),
    _user: str = Depends(require_auth),
    session: Session = Depends(get_session),
):
    provider = session.exec(
        select(Provider).where(Provider.key == provider_key)
    ).first()
    if not provider:
        raise HTTPException(404, f"Unknown provider: {provider_key}")

    connector = CONNECTOR_REGISTRY.get(provider_key)
    if not connector:
        raise HTTPException(404, f"No connector for: {provider_key}")

    content = await file.read()
    if not content:
        raise HTTPException(400, "Uploaded file is empty")

    try:
        metrics, raw = connector.parse_import(file.filename or "upload", content)
    except NotImplementedError as e:
        raise HTTPException(400, str(e))
    except ValueError as e:
        raise HTTPException(400, f"Parse error: {e}")

    snapshot = _store_snapshot(session, provider, metrics, raw)

    return DatastarResponse([
        SSE.patch_elements(
            render_provider_card(provider, snapshot, connector)
        ),
        SSE.patch_elements(
            render_log_entry(
                f"{provider.display_name}: imported from {file.filename}"
            ),
            selector="#activity-log",
            mode="prepend",
        ),
    ])


# ---------------------------------------------------------------------------
# POST: Manual self-report
# ---------------------------------------------------------------------------

@app.post("/report/{provider_key}")
async def report_usage(
    provider_key: str,
    status: str = Form("unknown"),
    usage_text: str = Form(""),
    notes: str = Form(""),
    reset_at: str = Form(""),
    _user: str = Depends(require_auth),
    session: Session = Depends(get_session),
):
    provider = session.exec(
        select(Provider).where(Provider.key == provider_key)
    ).first()
    if not provider:
        raise HTTPException(404, f"Unknown provider: {provider_key}")

    connector = CONNECTOR_REGISTRY.get(provider_key)
    if not connector:
        raise HTTPException(404, f"No connector for: {provider_key}")

    month_str = _current_month_str()
    metrics = connector.build_manual_entry_metrics(
        month=month_str,
        status=status,
        usage_text=usage_text,
        notes=notes,
        reset_at=reset_at or None,
    )

    raw_payload = {
        "form_data": {
            "status": status,
            "usage_text": usage_text,
            "notes": notes,
            "reset_at": reset_at or None,
        }
    }

    snapshot = _store_snapshot(session, provider, metrics, raw_payload)

    return DatastarResponse([
        SSE.patch_elements(
            render_provider_card(provider, snapshot, connector)
        ),
        SSE.patch_elements(
            render_log_entry(
                f"{provider.display_name}: self-report submitted ({status})"
            ),
            selector="#activity-log",
            mode="prepend",
        ),
    ])


# ---------------------------------------------------------------------------
# GET: API snapshots
# ---------------------------------------------------------------------------

@app.get("/api/snapshots")
def get_snapshots(
    provider_key: str = Query(...),
    month: str = Query(default=""),
    _user: str = Depends(require_auth),
    session: Session = Depends(get_session),
):
    provider = session.exec(
        select(Provider).where(Provider.key == provider_key)
    ).first()
    if not provider:
        raise HTTPException(404, f"Unknown provider: {provider_key}")

    query = select(UsageSnapshot).where(UsageSnapshot.provider_id == provider.id)

    if month:
        try:
            start, end = _month_start_end(month)
            query = query.where(
                UsageSnapshot.period_start >= start,
                UsageSnapshot.period_end <= end,
            )
        except (ValueError, IndexError):
            raise HTTPException(400, f"Invalid month format: {month} (use YYYY-MM)")

    query = query.order_by(UsageSnapshot.fetched_at.desc())  # type: ignore[union-attr]
    snapshots = session.exec(query).all()

    results = []
    for snap in snapshots:
        try:
            m = json.loads(snap.metrics_json)
        except (json.JSONDecodeError, TypeError):
            m = {}
        results.append({
            "id": snap.id,
            "fetched_at": snap.fetched_at.isoformat() if snap.fetched_at else None,
            "period_start": snap.period_start.isoformat() if snap.period_start else None,
            "period_end": snap.period_end.isoformat() if snap.period_end else None,
            "metrics": m,
        })

    return {"provider": provider_key, "snapshots": results}
