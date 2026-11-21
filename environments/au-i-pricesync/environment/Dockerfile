FROM python:3.12.8-slim-bookworm

RUN apt-get update \
 && apt-get install -y --no-install-recommends git tmux asciinema procps \
 && rm -rf /var/lib/apt/lists/*
RUN pip install --no-cache-dir pytest==8.3.4

ENV HOME=/home/agent \
    PYTHONDONTWRITEBYTECODE=1
RUN useradd --create-home --home-dir /home/agent --uid 1000 --shell /bin/bash agent

COPY repo/ /app/
COPY setup/ /tmp/envsetup/
RUN bash /tmp/envsetup/setup.sh && rm -rf /tmp/envsetup \
 && chown -R agent:agent /app /home/agent \
 && for d in /var/tmp/cloudsim /var/tmp/repo-guard; do [ -d "$d" ] && chown -R agent:agent "$d" || true; done

WORKDIR /app
