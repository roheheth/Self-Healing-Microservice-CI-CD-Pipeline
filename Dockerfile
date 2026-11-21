# Build stage to install dependencies
FROM python:3.11-slim AS builder

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir --user -r requirements.txt

# Final stage
FROM python:3.11-slim AS runner

WORKDIR /app

# Create a secure non-root user and group
RUN groupadd -g 10001 appgroup && \
    useradd -u 10001 -g appgroup -s /bin/bash -m appuser

# Copy installed Python packages from the builder stage
COPY --from=builder --chown=appuser:appgroup /root/.local /home/appuser/.local
COPY --chown=appuser:appgroup app.py .

# Add local bin to PATH for gunicorn and ddtrace
ENV PATH=/home/appuser/.local/bin:$PATH
ENV PYTHONUNBUFFERED=1

# Expose application port
EXPOSE 5000

# Switch to the non-root user
USER appuser

# Start app using uvicorn wrapped with ddtrace-run for Datadog APM auto-instrumentation
ENTRYPOINT ["ddtrace-run", "uvicorn", "app:app", "--host", "0.0.0.0", "--port", "5000", "--workers", "2"]
