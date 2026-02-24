"""Abstract base class for all provider connectors."""

from abc import ABC, abstractmethod
from datetime import datetime, timezone


class BaseConnector(ABC):
    """Interface that every provider connector must implement."""

    key: str
    display_name: str
    mode: str  # "api", "manual_import", "unsupported"

    @abstractmethod
    async def fetch_usage(self, year: int, month: int) -> tuple[dict, dict]:
        """Fetch usage from an official API.

        Returns:
            (metrics_json_dict, raw_payload_dict)

        Raises:
            NotImplementedError: if the provider has no API support.
        """

    def parse_import(self, filename: str, content: bytes) -> tuple[dict, dict]:
        """Parse an uploaded file into normalized metrics.

        Returns:
            (metrics_json_dict, raw_payload_dict)

        Raises:
            NotImplementedError: if file import is not supported.
            ValueError: if the file cannot be parsed.
        """
        raise NotImplementedError(f"{self.display_name} does not support file import")

    def build_manual_entry_metrics(
        self,
        month: str,
        status: str,
        usage_text: str,
        notes: str,
        reset_at: str | None = None,
    ) -> dict:
        """Build a metrics_json dict from a manual self-report form submission.

        This is a shared implementation; connectors can override if they need
        provider-specific normalization.
        """
        return {
            "month": month,
            "usage_units": {
                "requests": None,
                "messages": None,
                "tokens_input": None,
                "tokens_output": None,
                "tokens_total": None,
                "cost_usd": None,
            },
            "limits": {
                "monthly_requests": None,
                "monthly_cost_usd": None,
                "notes": usage_text or None,
            },
            "source": {
                "mode": "manual_entry",
                "details": f"Self-reported at {datetime.now(timezone.utc).isoformat()}",
            },
            "status": status,
            "usage_text": usage_text or None,
            "reset_at": reset_at or None,
            "notes": notes or None,
        }
