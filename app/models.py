"""SQLModel tables and Pydantic schemas for TokenTally."""

from datetime import date, datetime, timezone
from typing import Optional

from pydantic import BaseModel
from sqlmodel import Field, SQLModel, Column, Text


# ---------------------------------------------------------------------------
# Database tables
# ---------------------------------------------------------------------------

class Provider(SQLModel, table=True):
    """An AI service provider (e.g. GitHub Copilot, Cursor)."""

    __tablename__ = "providers"

    id: int | None = Field(default=None, primary_key=True)
    key: str = Field(unique=True, index=True, max_length=64)
    display_name: str = Field(max_length=128)
    mode: str = Field(max_length=32)  # "api", "manual_import", "unsupported"
    enabled: bool = Field(default=True)


class UsageSnapshot(SQLModel, table=True):
    """A point-in-time usage record for a provider."""

    __tablename__ = "usage_snapshots"

    id: int | None = Field(default=None, primary_key=True)
    provider_id: int = Field(foreign_key="providers.id", index=True)
    period_start: date
    period_end: date
    fetched_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    raw_payload: str = Field(default="{}", sa_column=Column(Text))
    metrics_json: str = Field(default="{}", sa_column=Column(Text))


class Setting(SQLModel, table=True):
    """Key-value application settings."""

    __tablename__ = "settings"

    id: int | None = Field(default=None, primary_key=True)
    key: str = Field(unique=True, index=True, max_length=128)
    value: str = Field(default="", sa_column=Column(Text))


# ---------------------------------------------------------------------------
# Pydantic schemas (not DB tables)
# ---------------------------------------------------------------------------

class UsageUnits(BaseModel):
    requests: int | None = None
    messages: int | None = None
    tokens_input: int | None = None
    tokens_output: int | None = None
    tokens_total: int | None = None
    cost_usd: float | None = None


class UsageLimits(BaseModel):
    monthly_requests: int | None = None
    monthly_cost_usd: float | None = None
    notes: str | None = None


class UsageSource(BaseModel):
    mode: str  # "api", "manual_import", "manual_entry", "unsupported"
    details: str = ""


class MetricsPayload(BaseModel):
    """Normalized metrics format stored in UsageSnapshot.metrics_json."""

    month: str  # "YYYY-MM"
    usage_units: UsageUnits = UsageUnits()
    limits: UsageLimits = UsageLimits()
    source: UsageSource
    # Manual entry fields
    status: str | None = None  # "good", "caution", "near_limit", "unknown"
    usage_text: str | None = None
    reset_at: Optional[str] = None
