"""Unit tests for connector import parsers and manual entry."""

import json
import pytest

from app.connectors.github_copilot import GitHubCopilotConnector
from app.connectors.cursor import CursorConnector
from app.connectors.chatgpt_plus import ChatGPTPlusConnector
from app.connectors.claude_pro import ClaudeProConnector
from app.connectors.gemini_consumer import GeminiConsumerConnector
from app.connectors.base import BaseConnector


# ---------------------------------------------------------------------------
# GitHubCopilotConnector
# ---------------------------------------------------------------------------

class TestGitHubCopilotParser:

    def setup_method(self):
        self.connector = GitHubCopilotConnector()

    def test_parse_valid_csv(self):
        csv_content = b"date,requests,tokens\n2026-02-01,150,45000\n2026-02-15,200,60000\n"
        metrics, raw = self.connector.parse_import("test.csv", csv_content)

        assert metrics["month"] == "2026-02"
        assert metrics["usage_units"]["requests"] == 350
        assert metrics["usage_units"]["tokens_total"] == 105000
        assert metrics["source"]["mode"] == "manual_import"
        assert raw["rows_parsed"] == 2

    def test_parse_csv_with_bom(self):
        csv_content = b"\xef\xbb\xbfdate,requests,tokens\n2026-02-01,100,30000\n"
        metrics, raw = self.connector.parse_import("bom.csv", csv_content)

        assert metrics["usage_units"]["requests"] == 100
        assert raw["rows_parsed"] == 1

    def test_parse_empty_csv_raises(self):
        csv_content = b"date,requests,tokens\n"
        with pytest.raises(ValueError, match="no parseable data"):
            self.connector.parse_import("empty.csv", csv_content)

    def test_parse_missing_columns_raises(self):
        csv_content = b"name,value\nfoo,bar\n"
        with pytest.raises(ValueError, match="CSV must have columns"):
            self.connector.parse_import("bad.csv", csv_content)

    def test_parse_skips_bad_rows(self):
        csv_content = b"date,requests,tokens\n2026-02-01,abc,def\n2026-02-02,50,15000\n"
        metrics, raw = self.connector.parse_import("mixed.csv", csv_content)

        assert metrics["usage_units"]["requests"] == 50
        assert raw["rows_parsed"] == 1


# ---------------------------------------------------------------------------
# CursorConnector
# ---------------------------------------------------------------------------

class TestCursorParser:

    def setup_method(self):
        self.connector = CursorConnector()

    def test_parse_valid_json(self):
        data = {"month": "2026-02", "requests": 500, "tokens": 120000}
        content = json.dumps(data).encode()
        metrics, raw = self.connector.parse_import("cursor.json", content)

        assert metrics["month"] == "2026-02"
        assert metrics["usage_units"]["requests"] == 500
        assert metrics["usage_units"]["tokens_total"] == 120000

    def test_parse_invalid_json_raises(self):
        with pytest.raises(ValueError, match="Invalid JSON"):
            self.connector.parse_import("bad.json", b"not json")


# ---------------------------------------------------------------------------
# ChatGPTPlusConnector
# ---------------------------------------------------------------------------

class TestChatGPTPlusParser:

    def setup_method(self):
        self.connector = ChatGPTPlusConnector()

    def test_parse_conversation_list(self):
        data = [
            {"title": "Chat 1", "message_count": 12},
            {"title": "Chat 2", "message_count": 8},
        ]
        content = json.dumps(data).encode()
        metrics, raw = self.connector.parse_import("export.json", content)

        assert metrics["usage_units"]["messages"] == 20
        assert raw["conversations_count"] == 2

    def test_parse_wrapped_format(self):
        data = {
            "month": "2026-01",
            "conversations": [
                {"title": "A", "message_count": 5},
            ],
        }
        content = json.dumps(data).encode()
        metrics, raw = self.connector.parse_import("export.json", content)

        assert metrics["month"] == "2026-01"
        assert metrics["usage_units"]["messages"] == 5

    def test_parse_empty_conversations(self):
        content = json.dumps([]).encode()
        metrics, raw = self.connector.parse_import("empty.json", content)

        assert metrics["usage_units"]["messages"] is None
        assert raw["conversations_count"] == 0


# ---------------------------------------------------------------------------
# ClaudeProConnector
# ---------------------------------------------------------------------------

class TestClaudeProParser:

    def setup_method(self):
        self.connector = ClaudeProConnector()

    def test_parse_simple_json(self):
        data = {"month": "2026-02", "messages": 150, "cost_usd": 20.00}
        content = json.dumps(data).encode()
        metrics, raw = self.connector.parse_import("claude.json", content)

        assert metrics["month"] == "2026-02"
        assert metrics["usage_units"]["messages"] == 150
        assert metrics["usage_units"]["cost_usd"] == 20.00


# ---------------------------------------------------------------------------
# GeminiConsumerConnector
# ---------------------------------------------------------------------------

class TestGeminiConsumerParser:

    def setup_method(self):
        self.connector = GeminiConsumerConnector()

    def test_parse_raises_not_implemented(self):
        with pytest.raises(NotImplementedError, match="not yet supported"):
            self.connector.parse_import("file.csv", b"data")


# ---------------------------------------------------------------------------
# BaseConnector manual entry
# ---------------------------------------------------------------------------

class TestManualEntry:

    def setup_method(self):
        self.connector = GitHubCopilotConnector()

    def test_build_manual_entry_metrics(self):
        metrics = self.connector.build_manual_entry_metrics(
            month="2026-02",
            status="caution",
            usage_text="~25 messages left",
            notes="Throttled after heavy use",
            reset_at="2026-03-01T00:00",
        )

        assert metrics["month"] == "2026-02"
        assert metrics["status"] == "caution"
        assert metrics["usage_text"] == "~25 messages left"
        assert metrics["notes"] == "Throttled after heavy use"
        assert metrics["reset_at"] == "2026-03-01T00:00"
        assert metrics["source"]["mode"] == "manual_entry"
        assert metrics["limits"]["notes"] == "~25 messages left"

    def test_build_manual_entry_defaults(self):
        metrics = self.connector.build_manual_entry_metrics(
            month="2026-02",
            status="good",
            usage_text="",
            notes="",
        )

        assert metrics["status"] == "good"
        assert metrics["usage_text"] is None
        assert metrics["notes"] is None
        assert metrics["reset_at"] is None
