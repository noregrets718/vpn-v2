import asyncio
import json
import logging
import os
import re
import secrets
import signal
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models.access_key import AccessKey

logger = logging.getLogger(__name__)


class ShadowsocksManager:
    def __init__(self):
        self._processes: dict[int, asyncio.subprocess.Process] = {}
        self._config_dir = Path(settings.SS_CONFIG_DIR)
        self._config_dir.mkdir(parents=True, exist_ok=True)

    @staticmethod
    def generate_password(length: int = 32) -> str:
        return secrets.token_urlsafe(length)

    def _config_path(self, port: int) -> Path:
        return self._config_dir / f"ss-{port}.json"

    def _create_config(self, port: int, password: str, method: str) -> Path:
        config = {
            "server": "0.0.0.0",
            "server_port": port,
            "password": password,
            "method": method,
            "timeout": 300,
            "fast_open": True,
            "mode": "tcp_and_udp",
        }
        path = self._config_path(port)
        path.write_text(json.dumps(config, indent=2))
        return path

    async def start_instance(self, port: int, password: str, method: str = "chacha20-ietf-poly1305") -> bool:
        if port in self._processes:
            proc = self._processes[port]
            if proc.returncode is None:
                logger.warning(f"SS instance already running on port {port}")
                return True

        config_path = self._create_config(port, password, method)
        try:
            proc = await asyncio.create_subprocess_exec(
                settings.SS_BINARY_PATH, "-c", str(config_path),
                stdout=asyncio.subprocess.DEVNULL,
                stderr=asyncio.subprocess.PIPE,
            )
            self._processes[port] = proc
            await self._setup_traffic_counter(port)
            logger.info(f"Started SS instance on port {port}, PID={proc.pid}")
            return True
        except Exception as e:
            logger.error(f"Failed to start SS on port {port}: {e}")
            return False

    async def stop_instance(self, port: int) -> bool:
        proc = self._processes.pop(port, None)
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

        config_path = self._config_path(port)
        if config_path.exists():
            config_path.unlink()

        await self._remove_traffic_counter(port)
        logger.info(f"Stopped SS instance on port {port}")
        return True

    async def _setup_traffic_counter(self, port: int) -> None:
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

    async def _remove_traffic_counter(self, port: int) -> None:
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

    async def get_traffic_bytes(self, port: int) -> dict[str, int]:
        comment = f"ss-traffic-{port}"
        proc = await asyncio.create_subprocess_shell(
            "iptables -L -v -n -x",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.DEVNULL,
        )
        stdout, _ = await proc.communicate()
        output = stdout.decode()

        upload = 0
        download = 0

        for line in output.splitlines():
            if comment not in line:
                continue
            parts = line.split()
            if len(parts) < 8:
                continue
            bytes_val = int(parts[1])
            # INPUT (dport) = download, OUTPUT (sport) = upload
            if f"dpt:{port}" in line:
                download += bytes_val
            elif f"spt:{port}" in line:
                upload += bytes_val

        return {"upload": upload, "download": download}

    async def get_all_traffic(self) -> dict[int, dict[str, int]]:
        proc = await asyncio.create_subprocess_shell(
            "iptables -L -v -n -x",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.DEVNULL,
        )
        stdout, _ = await proc.communicate()
        output = stdout.decode()

        traffic: dict[int, dict[str, int]] = {}
        pattern = re.compile(r"ss-traffic-(\d+)")

        for line in output.splitlines():
            match = pattern.search(line)
            if not match:
                continue
            port = int(match.group(1))
            if port not in traffic:
                traffic[port] = {"upload": 0, "download": 0}

            parts = line.split()
            if len(parts) < 8:
                continue
            bytes_val = int(parts[1])

            if f"dpt:{port}" in line:
                traffic[port]["download"] += bytes_val
            elif f"spt:{port}" in line:
                traffic[port]["upload"] += bytes_val

        return traffic

    async def get_next_free_port(self, db: AsyncSession, server_id) -> int:
        result = await db.execute(
            select(AccessKey.ss_port)
            .where(AccessKey.server_id == server_id)  # noqa: E712
            .order_by(AccessKey.ss_port.desc())
            .limit(1)
        )
        last_port = result.scalar_one_or_none()

        if last_port is None:
            return settings.PORT_RANGE_START

        next_port = last_port + 1
        if next_port > settings.PORT_RANGE_END:
            # Try to find a gap
            result = await db.execute(
                select(AccessKey.ss_port)
                .where(AccessKey.server_id == server_id, AccessKey.is_active == True)  # noqa: E712
                .order_by(AccessKey.ss_port)
            )
            used_ports = {row[0] for row in result.all()}
            for port in range(settings.PORT_RANGE_START, settings.PORT_RANGE_END + 1):
                if port not in used_ports:
                    return port
            raise ValueError("No free ports available")

        return next_port

    async def restore_instances(self, db: AsyncSession) -> int:
        result = await db.execute(
            select(AccessKey).where(AccessKey.is_active == True)  # noqa: E712
        )
        keys = result.scalars().all()
        restored = 0
        for key in keys:
            success = await self.start_instance(key.ss_port, key.ss_password, key.ss_method)
            if success:
                restored += 1
            else:
                logger.error(f"Failed to restore SS instance for key {key.id} on port {key.ss_port}")
        logger.info(f"Restored {restored}/{len(keys)} SS instances")
        return restored

    async def shutdown(self) -> None:
        for port in list(self._processes.keys()):
            await self.stop_instance(port)


ss_manager = ShadowsocksManager()
