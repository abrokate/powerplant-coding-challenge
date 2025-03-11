# Base stage: Set the timezone, create unprivileged user, and install dependencies
FROM python:3.9-slim as base

# Set timezone (ensure the TZ environment variable is set)
ARG TZ=UTC
RUN ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && echo $TZ > /etc/timezone

# Create unprivileged user
RUN adduser --disabled-password --gecos '' api-user

# Install dependencies
WORKDIR /tmp
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# App stage: copy the application code and set final configuration
FROM base as app
WORKDIR /app

# Copy all application files; set ownership to the unprivileged user
COPY --chown=api-user:api-user . .

# Verify that main.py exists
RUN test -f main.py || { echo "main.py not found"; exit 1; }

# Switch to unprivileged user
USER api-user

# Expose the desired port
EXPOSE 8888

# Health check to ensure the app is running correctly
HEALTHCHECK --interval=30s --timeout=5s --start-period=5s --retries=3 \
  CMD curl -f http://localhost:8888/docs || exit 1

# Command to run the application
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8888"]