import os
from fastapi import Header, HTTPException, status

AGENT_TOKEN = os.environ.get("AGENT_TOKEN", "")


async def verify_token(x_agent_token: str = Header(...)):
    if not AGENT_TOKEN or x_agent_token != AGENT_TOKEN:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid agent token")
