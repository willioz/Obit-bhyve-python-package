FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    mosquitto-clients \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN python -m pip install --upgrade pip setuptools wheel \
    && pip install --no-cache-dir -r requirements.txt

# Copy the package
COPY . .

# Install the package (non-editable) and clean any stray egg-info
RUN find . -maxdepth 3 -type d -name "*.egg-info" -exec rm -rf {} + \
    && pip install --no-cache-dir .

# Create non-root user
RUN useradd -m -u 1000 bhyve && chown -R bhyve:bhyve /app
USER bhyve

# Default command (can be overridden)
CMD ["python", "-m", "orbit_bhyve.gateway"]
