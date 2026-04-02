FROM python:3.12-slim

# Install Vale
RUN apt-get update && apt-get install -y wget && \
    wget -qO- https://github.com/errata-ai/vale/releases/download/v3.14.1/vale_3.14.1_Linux_64-bit.tar.gz | tar xz -C /usr/local/bin vale && \
    apt-get remove -y wget && apt-get autoremove -y && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy package
COPY pyproject.toml README.md LICENSE ./
COPY src/ src/
COPY .vale/ .vale/

# Install dependencies
RUN pip install --no-cache-dir ".[api]" && \
    pip install --no-cache-dir "markitdown[all]"

# Expose API port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')"

# Run API server
CMD ["uvicorn", "fincompliance.api.server:app", "--host", "0.0.0.0", "--port", "8000"]
