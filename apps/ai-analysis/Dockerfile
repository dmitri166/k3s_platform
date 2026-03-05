FROM python:3.11-slim

# Security: run as non-root
RUN groupadd --gid 1000 appuser && \
    useradd  --uid 1000 --gid 1000 --no-create-home appuser

WORKDIR /app

# Install dependencies first (layer cache friendly)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY config.py   ./
COPY analyze.py  ./

# Reports directory (will be overridden by PVC mount in K8s)
RUN mkdir -p /reports && chown appuser:appuser /reports

USER appuser

ENTRYPOINT ["python", "analyze.py"]
