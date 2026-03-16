import asyncio
import json
import logging
import os
import re
import secrets
import signal
from pathlib import Path
import httpx
import time
import psutil

from fastapi import FastAPI, Depends, HTTPException, status
from pydantic import BaseModel

from auth import verify_token
from utils import _read_iptables_traffic

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

SS_BINARY = os.environ.get("SS_BINARY_PATH", "/usr/bin/ss-server")
CONFIG_DIR = Path(os.environ.get("SS_CONFIG_DIR", "/etc/shadowsocks-libev/users"))
CONFIG_DIR.mkdir(parents=True, exist_ok=True)

app = FastAPI(title="VPN Node Agent")

_processes: dict[int, asyncio.subprocess.Process] = {}
_prev_traffic: dict[int, dict[str, int]] = {}
_prev_traffic_time: float = 0.0


class InstanceRequest(BaseModel):
  port: int
  password: str
  method: str = "chacha20-ietf-poly1305"


def _config_path(port: int) -> Path:
  return CONFIG_DIR / f"ss-{port}.json"


def _write_config(port: int, password: str, method: str) -> Path:
  config = {
      "server": "0.0.0.0",
      "server_port": port,
      "password": password,
      "method": method,
      "timeout": 300,
      "fast_open": True,
      "mode": "tcp_and_udp",
  }
  path = _config_path(port)
  path.write_text(json.dumps(config, indent=2))
  return path


async def _setup_iptables(port: int):
  comment = f"ss-traffic-{port}"
  rules = [
      f"iptables -A INPUT -p tcp --dport {port} -m comment --comment {comment} -j ACCEPT",
      f"iptables -A OUTPUT -p tcp --sport {port} -m comment --comment {comment} -j ACCEPT",
      f"iptables -A INPUT -p udp --dport {port} -m comment --comment {comment} -j ACCEPT",
      f"iptables -A OUTPUT -p udp --sport {port} -m comment --comment {comment} -j ACCEPT",
  ]
  for rule in rules:
      proc = await asyncio.create_subprocess_shell(rule, stdout=asyncio.subprocess.DEVNULL, stderr=asyncio.subprocess.DEVNULL)
      await proc.wait()


async def _remove_iptables(port: int):
  comment = f"ss-traffic-{port}"
  rules = [
      f"iptables -D INPUT -p tcp --dport {port} -m comment --comment {comment} -j ACCEPT",
      f"iptables -D OUTPUT -p tcp --sport {port} -m comment --comment {comment} -j ACCEPT",
      f"iptables -D INPUT -p udp --dport {port} -m comment --comment {comment} -j ACCEPT",
      f"iptables -D OUTPUT -p udp --sport {port} -m comment --comment {comment} -j ACCEPT",
  ]
  for rule in rules:
      proc = await asyncio.create_subprocess_shell(rule, stdout=asyncio.subprocess.DEVNULL, stderr=asyncio.subprocess.DEVNULL)
      await proc.wait()


@app.post("/instances", status_code=status.HTTP_201_CREATED, dependencies=[Depends(verify_token)])
async def start_instance(req: InstanceRequest):
  port = req.port
  if port in _processes and _processes[port].returncode is None:
      return {"port": port, "status": "already running"}

  config_path = _write_config(port, req.password, req.method)
  try:
      proc = await asyncio.create_subprocess_exec(
          SS_BINARY, "-c", str(config_path),
          stdout=asyncio.subprocess.DEVNULL,
          stderr=asyncio.subprocess.PIPE,
      )
      _processes[port] = proc
      await _setup_iptables(port)
      logger.info(f"Started SS on port {port}, PID={proc.pid}")
      return {"port": port, "status": "started"}
  except Exception as e:
      logger.error(f"Failed to start SS on port {port}: {e}")
      raise HTTPException(status_code=500, detail=str(e))


@app.delete("/instances/{port}", status_code=status.HTTP_204_NO_CONTENT, dependencies=[Depends(verify_token)])
async def stop_instance(port: int):
  proc = _processes.pop(port, None)
  if proc and proc.returncode is None:
      try:
          proc.send_signal(signal.SIGTERM)
          try:
              await asyncio.wait_for(proc.wait(), timeout=5)
          except asyncio.TimeoutError:
              proc.kill()
              await proc.wait()
      except ProcessLookupError:
          pass

  config = _config_path(port)
  if config.exists():
      config.unlink()
  await _remove_iptables(port)
  logger.info(f"Stopped SS on port {port}")


@app.get("/traffic", dependencies=[Depends(verify_token)])
async def get_traffic():
  return await _read_iptables_traffic()


@app.get("/health", dependencies=[Depends(verify_token)])
async def health():
  active = len([p for p, proc in _processes.items() if proc.returncode is None])
  return {"status": "ok", "active_instances": active}


@app.get("/info", dependencies=[Depends(verify_token)])
async def get_info():
  async with httpx.AsyncClient(timeout=5.0) as client:
      r = await client.get("https://api.ipify.org?format=json")
      public_ip = r.json()["ip"]
      logger.info(f"server ip{public_ip}")
  return {"ip": public_ip}

@app.get("/metrics", dependencies=[Depends(verify_token)])
async def get_metrics():
  global _prev_traffic, _prev_traffic_time

  cpu = psutil.cpu_percent(interval=0.1)
  ram = psutil.virtual_memory()
  disk = psutil.disk_usage("/")
  uptime = time.time() - psutil.boot_time()
  active = len([p for p, proc in _processes.items() if proc.returncode is None])

  current_traffic = await _read_iptables_traffic()

  now = time.time()
  elapsed = now - _prev_traffic_time if _prev_traffic_time else 1.0
  ports_speed: dict[str, dict[str, float]] = {}
  for p, counters in current_traffic.items():
      prev = _prev_traffic.get(p, {"upload": 0, "download": 0})
      ports_speed[str(p)] = {
          "upload_bps": max(0, counters["upload"] - prev["upload"]) / elapsed,
          "download_bps": max(0, counters["download"] - prev["download"]) / elapsed,
      }

  _prev_traffic = current_traffic
  _prev_traffic_time = now

  return {
      "cpu_percent": cpu,
      "ram_used": ram.used,
      "ram_total": ram.total,
      "disk_used": disk.used,
      "disk_total": disk.total,
      "uptime_seconds": uptime,
      "active_instances": active,
      "ports": ports_speed,
  }
