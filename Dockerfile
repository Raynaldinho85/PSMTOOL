FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    BROWSER_PATH=/usr/bin/chromium

RUN apt-get update \
    && apt-get install -y --no-install-recommends chromium ca-certificates fonts-liberation \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY pyproject.toml README.md /app/
COPY src /app/src
COPY .streamlit /app/.streamlit

RUN pip install --upgrade pip \
    && pip install -e .

EXPOSE 8501

CMD ["streamlit", "run", "src/psm_tool/ui/app.py", "--server.address=0.0.0.0", "--server.port=8501"]
