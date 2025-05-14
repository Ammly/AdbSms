FROM python:3.12-slim

# Install ADB and other dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    android-tools-adb \
    build-essential \
    usbutils \
    iproute2 \
    iputils-ping \
    net-tools \
    libusb-1.0-0 \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install Poetry
RUN pip install --no-cache-dir poetry && \
    poetry config virtualenvs.create false

# Copy only dependency definition files first for better layer caching
COPY pyproject.toml poetry.toml README.md ./

# Install ALL dependencies (both main and dev)
RUN poetry install --no-root

# Also directly install packages that might be missing
RUN pip install --no-cache-dir \
    flask-cors \
    flask-limiter \
    flask-swagger-ui \
    redis \
    gunicorn==21.2.0  # Install specified LTS version of gunicorn

# Copy the rest of the application code
COPY . .

# Create ADB configuration directory with proper permissions
RUN mkdir -p /root/.android && \
    chmod 700 /root/.android && \
    touch /root/.android/adbkey

# Create and give access to tmp directory for ADB socket
RUN mkdir -p /tmp/adb && \
    chmod 777 /tmp/adb

# Add ADB server initialization script
COPY docker-entrypoint.sh /docker-entrypoint.sh
RUN chmod +x /docker-entrypoint.sh

EXPOSE 5000

ENTRYPOINT ["/docker-entrypoint.sh"]
# Use Gunicorn instead of Flask development server
CMD ["gunicorn", "--bind", "0.0.0.0:5000", "--workers", "4", "--threads", "2", "--timeout", "60", "api.app:app"]