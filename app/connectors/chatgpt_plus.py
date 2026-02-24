"""ChatGPT Plus connector with conversation export parser."""

import json

from app.connectors.base import BaseConnector


class ChatGPTPlusConnector(BaseConnector):
    key = "chatgpt_plus"
    display_name = "ChatGPT Plus"
    mode = "manual_import"

    async def fetch_usage(self, year: int, month: int) -> tuple[dict, dict]:
        raise NotImplementedError(
            "ChatGPT Plus (consumer) does not provide a usage API. "
            "Use manual import or self-report instead."
        )

    def parse_import(self, filename: str, content: bytes) -> tuple[dict, dict]:
        """Parse a JSON export file with conversation data.

        Accepts either:
        - A list of conversations: [{"title": "...", "message_count": 12}, ...]
        - A single object: {"conversations": [...], "month": "2026-02"}

        Counts total messages across all conversations.
        Token counts are NOT claimed as accurate since the export
        typically does not include token data.
        """
        try:
            data = json.loads(content)
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON: {e}")

        conversations = []
        month_str = None

        if isinstance(data, list):
            conversations = data
        elif isinstance(data, dict):
            conversations = data.get("conversations", [])
            month_str = data.get("month")

        if not month_str:
            from datetime import date
            month_str = date.today().strftime("%Y-%m")

        total_messages = 0
        for conv in conversations:
            total_messages += int(conv.get("message_count", 0))

        raw_payload = {
            "filename": filename,
            "conversations_count": len(conversations),
            "source_format": "json",
        }

        metrics = {
            "month": month_str,
            "usage_units": {
                "requests": None,
                "messages": total_messages or None,
                "tokens_input": None,
                "tokens_output": None,
                "tokens_total": None,
                "cost_usd": None,
            },
            "limits": {
                "monthly_requests": None,
                "monthly_cost_usd": None,
                "notes": f"{len(conversations)} conversations parsed (token counts not available from export)",
            },
            "source": {
                "mode": "manual_import",
                "details": f"Imported from {filename} ({len(conversations)} conversations)",
            },
        }

        return metrics, raw_payload
