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

from fastapi import FastAPI, Depends, HTTPException, status, Request
from pydantic import BaseModel

from auth import verify_token
from utils import _read_iptables_traffic
from prometheus_client import Gauge, Counter, generate_latest, CONTENT_TYPE_LATEST
from fastapi.responses import Response

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

SS_BINARY = os.environ.get("SS_BINARY_PATH", "/usr/bin/ss-server")
CONFIG_DIR = Path(os.environ.get("SS_CONFIG_DIR", "/etc/shadowsocks-libev/users"))
CONFIG_DIR.mkdir(parents=True, exist_ok=True)

app = FastAPI(title="VPN Node Agent")

_processes: dict[int, asyncio.subprocess.Process] = {}
_prev_traffic: dict[int, dict[str, int]] = {}
_prev_traffic_time: float = 0.0

_prom_cpu = Gauge("agent_cpu_percent", "CPU usage percent")
_prom_ram_used = Gauge("agent_ram_used_bytes", "RAM used bytes")
_prom_ram_total = Gauge("agent_ram_total_bytes", "RAM total bytes")
_prom_disk_used = Gauge("agent_disk_used_bytes", "Disk used bytes")
_prom_disk_total = Gauge("agent_disk_total_bytes", "Disk total bytes")
_prom_active_instances = Gauge("agent_active_instances", "Active SS instances")
_prom_traffic_upload = Counter("agent_traffic_upload_bytes_total", "Upload bytes total", ["port"])
_prom_traffic_download = Counter("agent_traffic_download_bytes_total", "Download bytes total", ["port"])
_prom_prev_upload: dict[int, int] = {}
_prom_prev_download: dict[int, int] = {}

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


def _find_pid_by_port(port: int) -> int | None:
    """Ищем живой ss-server процесс слушающий на нужном порту."""
    for proc in psutil.process_iter(["pid", "name"]):
        try:
            if "ss-server" not in (proc.info["name"] or ""):
                continue
            for conn in proc.net_connections():
                if conn.laddr.port == port:
                    return proc.info["pid"]
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue
    return None


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
  if _find_pid_by_port(req.port):
      return {"port": port, "status": "already running"}

  config_path = _write_config(port, req.password, req.method)
  try:
      proc = await asyncio.create_subprocess_exec(
          SS_BINARY, "-c", str(config_path),
          stdout=asyncio.subprocess.DEVNULL,
          stderr=asyncio.subprocess.PIPE,
      )
      await _setup_iptables(port)
      logger.info(f"Started SS on port {port}, PID={proc.pid}")
      return {"port": port, "status": "started"}
  except Exception as e:
      logger.error(f"Failed to start SS on port {port}: {e}")
      raise HTTPException(status_code=500, detail=str(e))


@app.delete("/instances/{port}", status_code=status.HTTP_204_NO_CONTENT, dependencies=[Depends(verify_token)])
async def stop_instance(port: int):
    pid = _find_pid_by_port(port)
    if pid:
        try:
            os.kill(pid, signal.SIGTERM)
            psutil.Process(pid).wait(timeout=5)
        except psutil.TimeoutExpired:
            os.kill(pid, signal.SIGKILL)
        except (psutil.NoSuchProcess, ProcessLookupError):
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
    active = sum(
        1 for proc in psutil.process_iter(["name"])
        if "ss-server" in (proc.info["name"] or "")
    )
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

@app.get("/metrics-prom")
async def get_metrics_prom(request: Request):


  cpu = psutil.cpu_percent(interval=0.1)
  ram = psutil.virtual_memory()
  disk = psutil.disk_usage("/")
  active = sum(
      1 for proc in psutil.process_iter(["name"])
      if "ss-server" in (proc.info["name"] or "")
  )

  _prom_cpu.set(cpu)
  _prom_ram_used.set(ram.used)
  _prom_ram_total.set(ram.total)
  _prom_disk_used.set(disk.used)
  _prom_disk_total.set(disk.total)
  _prom_active_instances.set(active)

  current_traffic = await _read_iptables_traffic()
  for port, counters in current_traffic.items():
      prev_up = _prom_prev_upload.get(port, 0)
      prev_down = _prom_prev_download.get(port, 0)
      delta_up = max(0, counters["upload"] - prev_up)
      delta_down = max(0, counters["download"] - prev_down)
      if delta_up > 0:
          _prom_traffic_upload.labels(port=str(port)).inc(delta_up)
      if delta_down > 0:
          _prom_traffic_download.labels(port=str(port)).inc(delta_down)
      _prom_prev_upload[port] = counters["upload"]
      _prom_prev_download[port] = counters["download"]

  return Response(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)

