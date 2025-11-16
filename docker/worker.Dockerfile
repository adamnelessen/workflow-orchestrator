FROM python:3.11-slim

WORKDIR /app

# Copy project files for installation
COPY pyproject.toml .
COPY coordinator/ ./coordinator/
COPY worker/ ./worker/
COPY shared/ ./shared/
COPY client/ ./client/

# Install the package
RUN pip install --no-cache-dir .

# Copy remaining files
COPY . .

# Set environment variables
ENV LOG_LEVEL=INFO

# Run the worker
CMD ["python", "-u", "-m", "worker.main"]