# Use an official Python runtime as a parent image
FROM python:3.9-slim

# Set the working directory in the container
WORKDIR /app

# Copy the requirements file into the container at /app
COPY requirements.txt /app/

# Install any needed packages specified in requirements.txt
# Using --no-cache-dir to reduce layer size
# Using --default-timeout to prevent timeouts on slow networks if any system deps for weasyprint are fetched
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt --default-timeout=300

# WeasyPrint requires system dependencies for font rendering, graphics, etc.
# These are for Debian/Ubuntu based images like python:3.9-slim.
# This list might need adjustment based on exact WeasyPrint version and features needed.
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpango-1.0-0 \
    libpangoft2-1.0-0 \
    libpangocairo-1.0-0 \
    libharfbuzz0b \
    libfontconfig1 \
    libfreetype6 \
    libjpeg62-turbo \
    libpng16-16 \
    libffi-dev \
    # Add any other specific dependencies WeasyPrint might need for full functionality
    # For example, for complex scripts or specific image formats.
    # libxml2-dev libxslt1-dev (often needed for lxml, which WeasyPrint uses)
    # but pip should handle lxml's binary wheels if available for the platform.
    # The core ones are usually pango, cairo, fontconfig, freetype.
 && rm -rf /var/lib/apt/lists/*

# Copy the rest of the application code into the container at /app
COPY . /app/

# Make port 5000 available to the world outside this container
# This is the port Gunicorn will listen on, as configured in gunicorn_config.py and config.json
EXPOSE 5000

# Define environment variables (can be overridden at runtime)
ENV FLASK_APP=app.py
# ENV FLASK_ENV=production # Already handled by not running in debug mode
ENV DATABASE_URL=sqlite:////app/data/mikrotik_dashboard_users.db
# Ensure the /app/data directory exists for the SQLite DB
RUN mkdir -p /app/data

# Command to run the application using Gunicorn
# The gunicorn_config.py should pick up host/port from config.json or defaults.
# Ensure config.json is present or created on first run correctly.
# For production, config.json should be mounted as a volume or managed via other config means.
CMD ["gunicorn", "--config", "gunicorn_config.py", "app:app"]
