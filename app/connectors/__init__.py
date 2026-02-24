"""Connector registry mapping provider keys to connector instances."""

from app.connectors.github_copilot import GitHubCopilotConnector
from app.connectors.cursor import CursorConnector
from app.connectors.chatgpt_plus import ChatGPTPlusConnector
from app.connectors.claude_pro import ClaudeProConnector
from app.connectors.gemini_consumer import GeminiConsumerConnector
from app.connectors.base import BaseConnector

CONNECTOR_REGISTRY: dict[str, BaseConnector] = {
    "github_copilot": GitHubCopilotConnector(),
    "cursor": CursorConnector(),
    "chatgpt_plus": ChatGPTPlusConnector(),
    "claude_pro": ClaudeProConnector(),
    "gemini_consumer": GeminiConsumerConnector(),
}
