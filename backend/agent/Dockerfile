FROM python:3.12-slim

RUN apt-get update && apt-get install -y \
  shadowsocks-libev \
  iptables \
  && rm -rf /var/lib/apt/lists/*

RUN pip install fastapi uvicorn httpx psutil prometheus-client

WORKDIR /agent
COPY main.py auth.py utils.py ./

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "9000"]
