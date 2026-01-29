# ---------- Stage 1: build dependencies ----------
FROM python:3.12-slim AS builder

WORKDIR /app

# Create virtual env in builder and install deps
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# ---------- Stage 2: runtime image ----------
FROM python:3.12-slim AS runtime

WORKDIR /app

# Copy venv from builder
COPY --from=builder /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Copy application
COPY . .

# Optional: create non-root user
RUN useradd -m appuser
USER appuser

EXPOSE 8000

# Gunicorn (prod)
CMD ["gunicorn", "-w", "2", "-k", "uvicorn.workers.UvicornWorker", "-b", "0.0.0.0:8000", "main:app"]
