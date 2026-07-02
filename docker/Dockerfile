FROM python:3.12-slim

LABEL org.opencontainers.image.title="ComputeForge"
LABEL org.opencontainers.image.description="Open-source, extensible Computer-Use Agent Platform"
LABEL org.opencontainers.image.licenses="Apache-2.0"

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PLAYWRIGHT_BROWSERS_PATH=/opt/ms-playwright \
    COMPUTEFORGE_WORKSPACE_DIR=/data/computeforge

WORKDIR /app

# Install system dependencies for Playwright, PyAutoGUI, MSS
RUN apt-get update && apt-get install -y --no-install-recommends \
    libnss3 libnspr4 libatk1.0-0 libatk-bridge2.0-0 \
    libcups2 libdrm2 libdbus-1-3 libxkbcommon0 \
    libxcomposite1 libxdamage1 libxfixes3 libxrandr2 \
    libgbm1 libpango-1.0-0 libcairo2 libasound2 \
    libegl1 libxshmfence1 libglib2.0-0 \
    xvfb x11vnc python3-tk python3-dev \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY pyproject.toml README.md ./
COPY src/ ./src/
RUN pip install --no-cache-dir -e ".[all]" && \
    playwright install chromium

# Create data directory
RUN mkdir -p /data/computeforge

EXPOSE 7860 8000

# Default: start the FastAPI server
CMD ["uvicorn", "computeforge.api.server:app", "--host", "0.0.0.0", "--port", "8000"]
