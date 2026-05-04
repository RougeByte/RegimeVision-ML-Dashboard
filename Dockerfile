# Step 1: Use a combined image or install Go in Python image
FROM python:3.12-slim

# Install Go
COPY --from=golang:1.22-bookworm /usr/local/go/ /usr/local/go/
ENV PATH="/usr/local/go/bin:${PATH}"

# Set working directory
WORKDIR /app

# Copy all project files
COPY . .

# Install Python dependencies
RUN pip install --no-cache-dir -r backend/requirements.txt

# Build the Go Ingestor
RUN go build -o backend/ingestor backend/ingestor.go

# Expose the port FastAPI will run on
EXPOSE 8000

# Start the application
CMD ["uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8000"]