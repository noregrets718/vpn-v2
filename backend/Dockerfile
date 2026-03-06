FROM python:3.12-slim

COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

# System deps: shadowsocks-libev for VPN, iptables for traffic counting
RUN apt-get update && apt-get install -y --no-install-recommends \
    shadowsocks-libev \
    iptables \
    iproute2 \
    procps \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Create dirs for SS configs and PIDs
RUN mkdir -p /etc/shadowsocks-libev/users

WORKDIR /app

# Install Python deps (cached layer)
COPY pyproject.toml uv.lock .python-version ./
RUN uv sync --frozen --no-dev

# Copy application
COPY . .

EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=5s --retries=3 \
    CMD curl -f http://localhost:8000/api/health || exit 1

CMD ["uv", "run", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
