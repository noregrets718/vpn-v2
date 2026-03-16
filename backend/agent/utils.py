import asyncio
import re


async def _read_iptables_traffic() -> dict[int, dict[str, int]]:
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
        p = int(match.group(1))
        if p not in traffic:
            traffic[p] = {"upload": 0, "download": 0}
        parts = line.split()
        if len(parts) < 8:
            continue
        bytes_val = int(parts[1])
        if f"dpt:{p}" in line:
            traffic[p]["download"] += bytes_val
        elif f"spt:{p}" in line:
            traffic[p]["upload"] += bytes_val
    return traffic
