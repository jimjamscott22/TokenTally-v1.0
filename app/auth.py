"""Simple HTTP Basic authentication for TokenTally MVP."""

import os
import secrets

from dotenv import load_dotenv
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBasic, HTTPBasicCredentials

load_dotenv()

security = HTTPBasic()

ADMIN_USERNAME = "admin"
ADMIN_PASSWORD = os.getenv("TOKENTALLY_PASSWORD", "changeme")


def require_auth(
    credentials: HTTPBasicCredentials = Depends(security),
) -> str:
    """Dependency that enforces HTTP Basic auth. Returns username on success."""
    username_ok = secrets.compare_digest(
        credentials.username.encode("utf-8"),
        ADMIN_USERNAME.encode("utf-8"),
    )
    password_ok = secrets.compare_digest(
        credentials.password.encode("utf-8"),
        ADMIN_PASSWORD.encode("utf-8"),
    )
    if not (username_ok and password_ok):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials",
            headers={"WWW-Authenticate": "Basic"},
        )
    return credentials.username
