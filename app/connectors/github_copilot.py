"""GitHub Copilot connector with CSV import support."""

import csv
import io

from app.connectors.base import BaseConnector


class GitHubCopilotConnector(BaseConnector):
    key = "github_copilot"
    display_name = "GitHub Copilot"
    mode = "manual_import"

    async def fetch_usage(self, year: int, month: int) -> tuple[dict, dict]:
        raise NotImplementedError(
            "GitHub Copilot does not provide a documented consumer usage API. "
            "Use manual import (CSV) or self-report instead."
        )

    def parse_import(self, filename: str, content: bytes) -> tuple[dict, dict]:
        """Parse a CSV file with columns: date, requests, tokens.

        Expected format:
            date,requests,tokens
            2026-02-01,150,45000
            2026-02-15,200,60000

        Rows are summed to produce monthly totals.
        """
        try:
            text = content.decode("utf-8-sig")
        except UnicodeDecodeError:
            text = content.decode("latin-1")

        reader = csv.DictReader(io.StringIO(text))
        required = {"date", "requests", "tokens"}
        if not reader.fieldnames or not required.issubset(
            {f.strip().lower() for f in reader.fieldnames}
        ):
            raise ValueError(
                f"CSV must have columns: {', '.join(sorted(required))}. "
                f"Found: {reader.fieldnames}"
            )

        total_requests = 0
        total_tokens = 0
        rows_parsed = 0
        month_str = None

        for row in reader:
            date_val = row.get("date", "").strip()
            if date_val and not month_str:
                month_str = date_val[:7]  # "YYYY-MM"
            try:
                total_requests += int(row.get("requests", 0) or 0)
                total_tokens += int(row.get("tokens", 0) or 0)
                rows_parsed += 1
            except (ValueError, TypeError):
                continue

        if rows_parsed == 0:
            raise ValueError("CSV contained no parseable data rows")

        if not month_str:
            from datetime import date
            month_str = date.today().strftime("%Y-%m")

        raw_payload = {
            "filename": filename,
            "rows_parsed": rows_parsed,
            "source_format": "csv",
        }

        metrics = {
            "month": month_str,
            "usage_units": {
                "requests": total_requests,
                "messages": None,
                "tokens_input": None,
                "tokens_output": None,
                "tokens_total": total_tokens,
                "cost_usd": None,
            },
            "limits": {
                "monthly_requests": None,
                "monthly_cost_usd": None,
                "notes": None,
            },
            "source": {
                "mode": "manual_import",
                "details": f"Imported from {filename} ({rows_parsed} rows)",
            },
        }

        return metrics, raw_payload
