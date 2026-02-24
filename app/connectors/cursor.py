"""Cursor Pro connector with JSON import stub."""

import json

from app.connectors.base import BaseConnector


class CursorConnector(BaseConnector):
    key = "cursor"
    display_name = "Cursor Pro"
    mode = "manual_import"

    async def fetch_usage(self, year: int, month: int) -> tuple[dict, dict]:
        raise NotImplementedError(
            "Cursor does not provide a documented usage API. "
            "Use manual import (JSON) or self-report instead."
        )

    def parse_import(self, filename: str, content: bytes) -> tuple[dict, dict]:
        """Parse a JSON file with usage fields.

        Expected format:
            {
                "month": "2026-02",
                "requests": 500,
                "tokens": 120000
            }
        """
        try:
            data = json.loads(content)
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON: {e}")

        month_str = data.get("month")
        if not month_str:
            from datetime import date
            month_str = date.today().strftime("%Y-%m")

        raw_payload = {"filename": filename, "source_format": "json"}

        metrics = {
            "month": month_str,
            "usage_units": {
                "requests": data.get("requests"),
                "messages": data.get("messages"),
                "tokens_input": data.get("tokens_input"),
                "tokens_output": data.get("tokens_output"),
                "tokens_total": data.get("tokens"),
                "cost_usd": data.get("cost_usd"),
            },
            "limits": {
                "monthly_requests": data.get("monthly_requests"),
                "monthly_cost_usd": data.get("monthly_cost_usd"),
                "notes": data.get("notes"),
            },
            "source": {
                "mode": "manual_import",
                "details": f"Imported from {filename}",
            },
        }

        return metrics, raw_payload
