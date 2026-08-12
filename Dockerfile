FROM python:3.12.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

RUN groupadd --gid 10001 orchestrator \
    && useradd --uid 10001 --gid orchestrator --create-home orchestrator

WORKDIR /app
COPY pyproject.toml README.md ./
COPY src ./src
RUN pip install --no-cache-dir .

USER 10001:10001
EXPOSE 8088
CMD ["uvicorn", "orchestrator.api.main:app", "--host", "0.0.0.0", "--port", "8088"]
