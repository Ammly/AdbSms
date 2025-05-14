#!/bin/bash
set -e

# Function to log messages
log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1"
}

# Ensure proper permissions
log "Setting up ADB environment..."

# Wait for any previous ADB processes to fully terminate before starting a new server
log "Ensuring ADB server is properly stopped..."
adb kill-server || true
sleep 2  # Add delay to ensure the server has time to fully terminate

# Start ADB server with proper settings
log "Starting ADB server with proper permissions..."
# Create necessary directories with proper permissions
mkdir -p /root/.android
chmod 700 /root/.android

# Set ADB server socket to localhost only
export ANDROID_ADB_SERVER_HOST=127.0.0.1
export ANDROID_ADB_SERVER_PORT=5037

# Start ADB server explicitly
log "Starting ADB server..."
adb start-server

# Wait for ADB server to fully initialize
sleep 2

# Make sure environment has the specific device to use
if [ -z "$ANDROID_SERIAL" ]; then
    log "ANDROID_SERIAL not set, will try to use 0B141JEC216648"
    export ANDROID_SERIAL="0B141JEC216648"
fi

log "Using Android device: $ANDROID_SERIAL"

# Check if we can see the devices
log "Checking for connected devices..."
adb devices

# Verify that our target device is connected
if adb devices | grep -q "$ANDROID_SERIAL"; then
    log "Successfully connected to device $ANDROID_SERIAL"
else
    log "Warning: Could not find device $ANDROID_SERIAL"
    log "Available devices:"
    adb devices
    
    # Try to restart ADB in USB mode to detect devices
    log "Attempting to restart ADB to detect USB devices..."
    adb kill-server
    sleep 2
    adb -a start-server
    sleep 1
    log "Checking devices again..."
    adb devices
fi

# Execute the command passed to docker run
log "Starting application..."
exec "$@"