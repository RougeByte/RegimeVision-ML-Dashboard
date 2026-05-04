FROM python:3.12-slim

# Install Go compiler
COPY --from=golang:1.22-bookworm /usr/local/go/ /usr/local/go/
ENV PATH="/usr/local/go/bin:${PATH}"

WORKDIR /app
COPY . .

# 1. Install system-level dependencies for yfinance/pandas
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc python3-dev && \
    rm -rf /var/lib/apt/lists/*

# 2. Ensure permissions are recursive and explicit
RUN mkdir -p backend/cache_data && \
    chmod -R 777 /app/backend && \
    pip install --no-cache-dir -r backend/requirements.txt

# 3. Build with a static flag to ensure it runs anywhere in the container
RUN cd backend && \
    go build -o ingestor ingestor.go && \
    chmod +x ingestor

EXPOSE 8000
CMD ["uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8000"]