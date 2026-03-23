import os

AGENT_TOKEN = os.environ.get("AGENT_TOKEN", "")

from fastapi import Header, HTTPException, status
from typing import Optional


async def verify_token(
        x_agent_token: Optional[str] = Header(None),
        authorization: Optional[str] = Header(None),
):
    # Проверяем X-Agent-Token
    if x_agent_token and x_agent_token == AGENT_TOKEN:
        return

    # Проверяем Authorization: Bearer <token>
    if authorization and authorization == f"Bearer {AGENT_TOKEN}":
        return

    raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")