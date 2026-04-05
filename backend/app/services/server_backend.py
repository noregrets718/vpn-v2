import logging


import httpx

from app.models import Server

logger = logging.getLogger(__name__)

class RemoteAgentBackend:
  def __init__(self, url: str, token: str):
      self.url = url.rstrip("/")
      self._headers = {"X-Agent-Token": token}

  async def start_instance(self, port: int, password: str, method: str) -> bool:
      try:
          async with httpx.AsyncClient(timeout=10.0) as client:
              r = await client.post(
                  f"{self.url}/instances",
                  json={"port": port, "password": password, "method": method},
                  headers=self._headers,
              )
              return r.status_code == 201
      except Exception as e:
          logger.error(f"RemoteAgent start_instance failed: {e}")
          return False

  async def stop_instance(self, port: int) -> bool:
      try:
          async with httpx.AsyncClient(timeout=10.0) as client:
              r = await client.delete(
                  f"{self.url}/instances/{port}",
                  headers=self._headers,
              )
              return r.status_code == 204
      except Exception as e:
          logger.error(f"RemoteAgent stop_instance failed: {e}")
          return False

  async def get_all_traffic(self) -> dict[int, dict[str, int]]:
      try:
          async with httpx.AsyncClient(timeout=10.0) as client:
              r = await client.get(f"{self.url}/traffic", headers=self._headers)
              if r.status_code == 200:
                  return {int(k): v for k, v in r.json().items()}
      except Exception as e:
          logger.error(f"RemoteAgent get_all_traffic failed: {e}")
      return {}

  async def health_check(self) -> dict:
      try:
          async with httpx.AsyncClient(timeout=5.0) as client:
              r = await client.get(f"{self.url}/health", headers=self._headers)
              if r.status_code == 200:
                  return r.json()
      except Exception as e:
          logger.error(f"RemoteAgent health_check failed: {e}")
      return {"status": "offline", "active_instances": 0}

  @classmethod
  def from_server(cls, server: Server) -> "RemoteAgentBackend":
      return cls(server.agent_url, server.agent_token)


