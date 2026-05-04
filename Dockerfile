FROM python:3.12-slim

# Install Go compiler
COPY --from=golang:1.22-bookworm /usr/local/go/ /usr/local/go/
ENV PATH="/usr/local/go/bin:${PATH}"
# CRITICAL: Define Go Cache and Home for Render
ENV GOCACHE=/root/.cache/go-build
ENV GOPATH=/root/go

WORKDIR /app
COPY . .

# Ensure the cache directory for CSVs exists with full permissions
RUN mkdir -p backend/cache_data && chmod -R 777 backend/cache_data

# Install Python requirements
RUN pip install --no-cache-dir -r backend/requirements.txt

# Pre-compile the Go Ingestor so we don't have to use 'go run'
RUN cd backend && go build -o ingestor ingestor.go && chmod +x ingestor

EXPOSE 8000

# Start the app
CMD ["uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8000"]