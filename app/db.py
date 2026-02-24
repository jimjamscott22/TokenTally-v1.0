"""Database engine, session management, and initialization."""

import os

from dotenv import load_dotenv
from sqlmodel import Session, SQLModel, create_engine, select

from app.models import Provider

load_dotenv()

# Build MariaDB connection URL from env vars
_host = os.getenv("DB_HOST", "127.0.0.1")
_port = os.getenv("DB_PORT", "3306")
_name = os.getenv("DB_NAME", "tokentally")
_user = os.getenv("DB_USER", "tokentally")
_pass = os.getenv("DB_PASSWORD", "changeme")

DATABASE_URL = f"mysql+pymysql://{_user}:{_pass}@{_host}:{_port}/{_name}?charset=utf8mb4"

engine = create_engine(DATABASE_URL, echo=False, pool_pre_ping=True)


def get_session():
    """FastAPI dependency that yields a database session."""
    with Session(engine) as session:
        yield session


# Provider seed data
SEED_PROVIDERS = [
    {"key": "github_copilot", "display_name": "GitHub Copilot", "mode": "manual_import"},
    {"key": "cursor", "display_name": "Cursor Pro", "mode": "manual_import"},
    {"key": "chatgpt_plus", "display_name": "ChatGPT Plus", "mode": "manual_import"},
    {"key": "claude_pro", "display_name": "Claude Pro", "mode": "manual_import"},
    {"key": "gemini_consumer", "display_name": "Gemini", "mode": "unsupported"},
]


def init_db() -> None:
    """Create tables and seed providers if they don't exist."""
    SQLModel.metadata.create_all(engine)

    with Session(engine) as session:
        for prov_data in SEED_PROVIDERS:
            existing = session.exec(
                select(Provider).where(Provider.key == prov_data["key"])
            ).first()
            if not existing:
                session.add(Provider(**prov_data))
        session.commit()
