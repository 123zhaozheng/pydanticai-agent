# ==============================================================================
# Pydantic Deep Agent - Main Application Image
# ==============================================================================

FROM python:3.12-slim

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    # Set app directory
    APP_HOME=/app

# Install system dependencies
# We need curl/wget/git for general purpose, and basic build tools just in case
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    git \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Install uv (optional but good for fast installs, though we use pip here for standard reqs)
# COPY --from=ghcr.io/astral-sh/uv:latest /uv /bin/uv

# Set work directory
WORKDIR $APP_HOME

# Copy requirements
COPY requirements.txt .

# Install dependencies
RUN pip install -r requirements.txt

# Copy application code
COPY . .

# Expose port
EXPOSE 8000

# Create directories for persistence
RUN mkdir -p $APP_HOME/uploads \
    && mkdir -p $APP_HOME/intermediate \
    && mkdir -p $APP_HOME/skills \
    && mkdir -p $APP_HOME/data

# Command to run the application
# We use src/main.py as the entrypoint
CMD ["python", "src/main.py"]
