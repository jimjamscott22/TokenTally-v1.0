"""Gemini consumer connector - unsupported placeholder."""

from app.connectors.base import BaseConnector


class GeminiConsumerConnector(BaseConnector):
    key = "gemini_consumer"
    display_name = "Gemini"
    mode = "unsupported"

    async def fetch_usage(self, year: int, month: int) -> tuple[dict, dict]:
        raise NotImplementedError(
            "Google Gemini consumer/edu plans do not provide a documented usage API. "
            "Self-report is available; file import is not yet supported."
        )

    def parse_import(self, filename: str, content: bytes) -> tuple[dict, dict]:
        raise NotImplementedError(
            "Gemini consumer file import is not yet supported. "
            "Use the 'Report Usage' button to manually log your usage."
        )
