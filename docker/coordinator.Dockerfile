FROM python:3.11-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Expose the coordinator port
EXPOSE 8000

# Set environment variables
ENV LOG_LEVEL=INFO

# Run the coordinator service
CMD ["python", "-u", "-m", "coordinator.main"]