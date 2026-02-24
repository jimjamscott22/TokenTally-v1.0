"""HTML fragment generators for Datastar SSE morphing.

Each function returns an HTML string with a stable id attribute so that
Datastar's outer-morph (the default patch mode) can match and update it
without a full page reload.
"""

import json
from datetime import datetime, timezone
from html import escape

from app.models import Provider, UsageSnapshot
from app.connectors.base import BaseConnector

# ---------------------------------------------------------------------------
# Status styling
# ---------------------------------------------------------------------------

STATUS_COLORS = {
    "good": "#22c55e",
    "caution": "#f59e0b",
    "near_limit": "#ef4444",
    "unknown": "#94a3b8",
}

STATUS_LABELS = {
    "good": "Good",
    "caution": "Caution",
    "near_limit": "Near Limit",
    "unknown": "Unknown",
}

MODE_LABELS = {
    "api": "API",
    "manual_import": "Manual Import",
    "manual_entry": "Self-Reported",
    "unsupported": "Unsupported",
}


def _format_number(val: int | float | None) -> str:
    if val is None:
        return "-"
    if isinstance(val, float):
        return f"{val:,.2f}"
    return f"{val:,}"


def _parse_metrics(snapshot: UsageSnapshot | None) -> dict | None:
    if not snapshot or not snapshot.metrics_json:
        return None
    try:
        return json.loads(snapshot.metrics_json)
    except (json.JSONDecodeError, TypeError):
        return None


# ---------------------------------------------------------------------------
# Provider card
# ---------------------------------------------------------------------------

def render_provider_card(
    provider: Provider,
    snapshot: UsageSnapshot | None,
    connector: BaseConnector,
) -> str:
    """Render a full provider card with stable id for Datastar morphing."""
    key = provider.key
    metrics = _parse_metrics(snapshot)

    # Determine status
    status = "unknown"
    status_source = ""
    if metrics:
        source_mode = metrics.get("source", {}).get("mode", "")
        status = metrics.get("status") or "unknown"
        status_source = MODE_LABELS.get(source_mode, source_mode)
    else:
        status_source = MODE_LABELS.get(connector.mode, connector.mode)

    color = STATUS_COLORS.get(status, STATUS_COLORS["unknown"])
    label = STATUS_LABELS.get(status, status.replace("_", " ").title())

    # Last refreshed
    if snapshot:
        fetched = snapshot.fetched_at.strftime("%b %d, %Y %H:%M") if snapshot.fetched_at else "Unknown"
    else:
        fetched = "Never"

    # Usage fields
    usage_html = _render_usage_section(metrics)

    # Mode badge
    mode_badge = MODE_LABELS.get(connector.mode, connector.mode)

    # Capabilities disclaimer
    disclaimer = ""
    if connector.mode == "unsupported":
        disclaimer = (
            '<p class="card-disclaimer">No API or import available. '
            'Use self-report only.</p>'
        )
    elif connector.mode == "manual_import":
        disclaimer = (
            '<p class="card-disclaimer">No official usage API. '
            'Import files or self-report.</p>'
        )

    safe_key = escape(key)

    return f'''<div id="card-{safe_key}" class="provider-card">
  <div class="card-header">
    <h3 class="card-title">{escape(provider.display_name)}</h3>
    <span class="badge badge-mode">{escape(mode_badge)}</span>
  </div>

  <div class="card-status" style="border-left: 4px solid {color}; padding-left: 12px;">
    <span class="status-dot" style="background: {color};"></span>
    <span class="status-label">{escape(label)}</span>
    <span class="status-source">({escape(status_source)})</span>
  </div>

  {usage_html}

  <div class="card-meta">
    <span>Last updated: {escape(fetched)}</span>
  </div>

  {disclaimer}

  <div class="card-actions">
    <button class="btn btn-sm btn-outline"
            data-on:click="@get('/sse/refresh/{safe_key}')">
      Refresh
    </button>
    <button class="btn btn-sm btn-primary"
            data-on:click="$showReport{safe_key.replace('_', '')} = !$showReport{safe_key.replace('_', '')}">
      Report Usage
    </button>
    {_render_import_button(connector, safe_key)}
  </div>

  {_render_report_form(safe_key)}
  {_render_import_form(connector, safe_key)}
  {_render_history_section(metrics)}
</div>'''


def _render_usage_section(metrics: dict | None) -> str:
    if not metrics:
        return '<div class="card-usage"><p class="no-data">No data yet</p></div>'

    units = metrics.get("usage_units", {})
    limits = metrics.get("limits", {})
    usage_text = metrics.get("usage_text")
    month = metrics.get("month", "")

    rows = []
    if month:
        rows.append(f'<div class="usage-row"><span class="usage-key">Period</span><span class="usage-val">{escape(month)}</span></div>')
    if usage_text:
        rows.append(f'<div class="usage-row usage-text-highlight"><span class="usage-key">Status</span><span class="usage-val">{escape(usage_text)}</span></div>')
    if units.get("requests") is not None:
        rows.append(f'<div class="usage-row"><span class="usage-key">Requests</span><span class="usage-val">{_format_number(units["requests"])}</span></div>')
    if units.get("messages") is not None:
        rows.append(f'<div class="usage-row"><span class="usage-key">Messages</span><span class="usage-val">{_format_number(units["messages"])}</span></div>')
    if units.get("tokens_total") is not None:
        rows.append(f'<div class="usage-row"><span class="usage-key">Tokens</span><span class="usage-val">{_format_number(units["tokens_total"])}</span></div>')
    if units.get("cost_usd") is not None:
        rows.append(f'<div class="usage-row"><span class="usage-key">Cost</span><span class="usage-val">${_format_number(units["cost_usd"])}</span></div>')
    if limits.get("notes"):
        rows.append(f'<div class="usage-row"><span class="usage-key">Notes</span><span class="usage-val">{escape(str(limits["notes"]))}</span></div>')

    notes_val = metrics.get("notes")
    if notes_val:
        rows.append(f'<div class="usage-row"><span class="usage-key">Report Notes</span><span class="usage-val">{escape(notes_val)}</span></div>')

    reset_at = metrics.get("reset_at")
    if reset_at:
        rows.append(f'<div class="usage-row"><span class="usage-key">Resets</span><span class="usage-val">{escape(reset_at)}</span></div>')

    if not rows:
        return '<div class="card-usage"><p class="no-data">No data yet</p></div>'

    return f'<div class="card-usage">{"".join(rows)}</div>'


def _render_import_button(connector: BaseConnector, safe_key: str) -> str:
    if connector.mode == "unsupported":
        return ""
    signal = f"$showImport{safe_key.replace('_', '')}"
    return (
        f'<button class="btn btn-sm btn-outline" '
        f'data-on:click="{signal} = !{signal}">'
        f'Import File</button>'
    )


def _render_report_form(safe_key: str) -> str:
    signal = f"$showReport{safe_key.replace('_', '')}"
    return f'''
  <div class="card-form" data-show="{signal}">
    <form id="report-form-{safe_key}"
          data-on:submit__prevent="@post('/report/{safe_key}', {{contentType: 'form'}})">
      <div class="form-group">
        <label>Status</label>
        <select name="status">
          <option value="good">Good</option>
          <option value="caution">Caution</option>
          <option value="near_limit">Near Limit</option>
          <option value="unknown">Unknown</option>
        </select>
      </div>
      <div class="form-group">
        <label>Usage summary</label>
        <input type="text" name="usage_text"
               placeholder="e.g. ~25 messages left, $8/$20, throttled" />
      </div>
      <div class="form-group">
        <label>Notes</label>
        <input type="text" name="notes" placeholder="Optional notes" />
      </div>
      <div class="form-group">
        <label>Resets at</label>
        <input type="datetime-local" name="reset_at" />
      </div>
      <button type="submit" class="btn btn-primary">Submit Report</button>
    </form>
  </div>'''


def _render_import_form(connector: BaseConnector, safe_key: str) -> str:
    if connector.mode == "unsupported":
        return ""
    signal = f"$showImport{safe_key.replace('_', '')}"
    return f'''
  <div class="card-form" data-show="{signal}">
    <form id="import-form-{safe_key}" enctype="multipart/form-data"
          action="/import/{safe_key}" method="post">
      <div class="form-group">
        <label>Upload file (CSV or JSON)</label>
        <input type="file" name="file" accept=".csv,.json,.txt" />
      </div>
      <button type="submit" class="btn btn-outline">Upload &amp; Import</button>
    </form>
  </div>'''


def _render_history_section(metrics: dict | None) -> str:
    """Placeholder for snapshot history - shows source info."""
    if not metrics:
        return ""
    source = metrics.get("source", {})
    details = source.get("details", "")
    if details:
        return f'<div class="card-history"><small>{escape(details)}</small></div>'
    return ""


# ---------------------------------------------------------------------------
# Activity log entry
# ---------------------------------------------------------------------------

def render_log_entry(message: str) -> str:
    """Render a single activity log line."""
    ts = datetime.now(timezone.utc).strftime("%H:%M:%S")
    return (
        f'<div class="log-entry">'
        f'<span class="log-time">{ts}</span> '
        f'<span class="log-msg">{escape(message)}</span>'
        f'</div>'
    )
