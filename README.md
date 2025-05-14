# AdbSms

A simple Python utility to send SMS messages programmatically using ADB (Android Debug Bridge) to a connected Android device.

## Overview

This tool reads phone numbers and message content from a CSV file and sends SMS messages to the specified recipients using ADB commands. It's useful for:

- Testing SMS functionality
- Bulk messaging scenarios
- Automating SMS sending for development purposes
- Integrating SMS capabilities into web applications via the REST API

## Requirements

- Python 3.12 or higher
- ADB (Android Debug Bridge) installed and in your PATH
- An Android device connected via USB with USB debugging enabled
- Pandas library

## Installation

### Clone the repository

```bash
git clone https://github.com/Ammly/AdbSms.git
cd AdbSms
```

### Using Poetry (recommended)

1. Install Poetry if you don't have it already:
```bash
curl -sSL https://install.python-poetry.org | python3 -
```

2. Create a virtual environment and install dependencies:
```bash
poetry install
```

3. Activate the virtual environment:
```bash
poetry shell
```

### Using pip

1. Create a virtual environment:
```bash
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
```

2. Install pandas:
```bash
pip install pandas
```

### Docker Setup (recommended for API usage)

The easiest way to run the API is using Docker Compose:

1. Make sure Docker and Docker Compose are installed on your system
2. Connect your Android device via USB and ensure it's accessible with ADB
3. Run the following commands:

```bash
# Start the services
docker compose up -d

# Check the logs
docker compose logs -f
```

This will start:
- A PostgreSQL database
- Redis for Celery task queue
- The Flask API with Gunicorn
- Celery worker for sending SMS
- Celery beat for scheduled tasks

## Connecting your Android device

1. Enable USB debugging on your Android device:
   - Go to Settings > About phone
   - Tap "Build number" 7 times to enable Developer options
   - Go back to Settings > System > Developer options
   - Enable "USB debugging"

2. Connect your device via USB and authorize the connection on your phone when prompted

3. Verify the connection:
```bash
adb devices
```
You should see your device listed with "device" status, for example:
```
List of devices attached
0B141JEC216648      device
```

## Usage

### As a Command Line Tool

The script supports various command-line options for flexibility:

```bash
# Send messages from default CSV file (messages.csv)
python main.py

# Send messages from a custom CSV file
python main.py --file custom_messages.csv

# Send a single message directly from command line
python main.py --single --number "+1234567890" --message "Hello from AdbSms!"

# Change SIM ID (if not using eSIM or default)
python main.py --sim-id 1

# Adjust delay between messages
python main.py --delay 2.5

# Just check if ADB connection is working
python main.py --check-only
```

Full list of command-line options:

| Option              | Short | Description                                                      |
| ------------------- | ----- | ---------------------------------------------------------------- |
| `--file FILE`       | `-f`  | CSV file with phone numbers and messages (default: messages.csv) |
| `--sim-id SIM_ID`   | `-s`  | SIM card subId (default: 3 for eSIM)                             |
| `--delay DELAY`     | `-d`  | Delay between messages in seconds (default: 1.0)                 |
| `--single`          |       | Send a single message instead of reading from CSV                |
| `--number NUMBER`   | `-n`  | Phone number for single message mode                             |
| `--message MESSAGE` | `-m`  | Message content for single message mode                          |
| `--check-only`      |       | Only check ADB connection and exit                               |

### Using the REST API

The REST API provides a more robust way to integrate SMS sending into your applications:

#### Authentication

All API requests (except health check) require an API key, which can be provided as:
- Header: `X-API-Key: your-api-key`
- Query parameter: `?api_key=your-api-key`

The default API key is `dev-key-change-me-in-production` (you should change this in production).

#### Sending a Single SMS

```bash
curl -X POST "http://localhost:5000/api/sms" \
  -H "X-API-Key: dev-key-change-me-in-production" \
  -H "Content-Type: application/json" \
  -d '{"phone_number": "+1234567890", "content": "Hello from AdbSms!", "sim_id": 3}'
```

Response:
```json
{
  "message_id": 1,
  "status": "accepted",
  "task_id": "a748f0a3-1d48-4c0f-80b5-91d9830fcbc8",
  "url": "/api/sms/1"
}
```

#### Checking SMS Status

```bash
curl -X GET "http://localhost:5000/api/sms/1" \
  -H "X-API-Key: dev-key-change-me-in-production"
```

Response:
```json
{
  "content": "Hello from AdbSms!",
  "created_at": "2025-05-14T10:32:42.006437",
  "id": 1,
  "phone_number": "+1234567890",
  "sent_at": "2025-05-14T10:32:42.456789",
  "sim_id": 3,
  "status": "sent"
}
```

#### Checking Device Status

```bash
curl -X GET "http://localhost:5000/api/device/status" \
  -H "X-API-Key: dev-key-change-me-in-production"
```

#### Sending Bulk SMS via CSV Upload

```bash
curl -X POST "http://localhost:5000/api/sms/bulk" \
  -H "X-API-Key: dev-key-change-me-in-production" \
  -F "file=@messages.csv" \
  -F "sim_id=3" \
  -F "delay=1.0"
```

#### API Documentation

The API includes Swagger documentation accessible at http://localhost:5000/api/docs

### As a Python Module

You can also import the script and use its functions in your own Python code:

```python
from main import send_sms, send_bulk_sms, check_adb_connection

# Check if ADB is working and device is connected
if check_adb_connection():
    # Send a single SMS
    send_sms("+1234567890", "Hello from my custom script!", sim_id=3)
    
    # Send multiple SMS messages from a CSV file
    success, failure = send_bulk_sms("my_messages.csv", sim_id=3, delay=1.5)
    print(f"Sent {success} messages successfully, {failure} failed")
```

### Example CSV format

The CSV file should have the following format:

```
phone_number,message
+2547123456,"Hello there"
+9876543210,"Another message"
```

## Configuration

By default, the script uses subId=3 for the SIM card (eSIM). If you need to use a different SIM, you can:

1. Specify it via command line: `python main.py --sim-id 1`
2. Change the default in the code:
```python
# Change the default value in the send_sms function
def send_sms(phone_number: str, message: str, sim_id: int = 1):
```

### Docker and API Configuration

When using the Docker setup, you can configure the API using environment variables:

```yaml
environment:
  - FLASK_APP=api.app
  - FLASK_DEBUG=0  # Set to 1 for development
  - DATABASE_URL=postgresql://username:password@host/dbname
  - CELERY_BROKER_URL=redis://redis:6379/0
  - CELERY_RESULT_BACKEND=redis://redis:6379/1
  - ADBSMS_API_KEY=your-custom-api-key
  - ANDROID_SERIAL=your-device-id  # Set to your specific Android device ID
```

## Troubleshooting

### USB Device Connection Issues

- If `adb devices` shows no devices or shows as "unauthorized", check your USB connection and ensure you've authorized the debugging connection on your device
- If SMS fails to send, verify that your SIM card works correctly and that the subId is correctly set
- For timeouts or connection issues, try restarting ADB with `adb kill-server` followed by `adb start-server`

### Docker-specific Issues

If you're using the Docker setup and have issues connecting to your Android device:

1. Ensure your host machine can see the device properly:
```bash
adb devices
```

2. Make sure you've set the correct device ID in `docker-compose.yml`:
```yaml
environment:
  - ANDROID_SERIAL=your-device-id
```

3. If still having issues, restart everything:
```bash
docker compose down
adb kill-server
adb start-server
docker compose up -d
```

## Testing

The tests cover all major functionality including SMS sending, ADB connection checking, and command-line interface operations.

### Running Tests

You can run the tests using pytest:

```bash
# Using Poetry (recommended)
poetry run pytest

# With more detailed output
poetry run pytest -v

# Run a specific test file
poetry run pytest tests/test_send_sms.py

# Run a specific test
poetry run pytest tests/test_send_sms.py::test_send_sms_success
```

### Test Coverage

The tests use mocking to avoid actual ADB calls during testing, allowing you to run the tests without a connected device. The test suite includes:

- Unit tests for all core functions
- CLI argument parsing tests
- Error handling tests
- Edge case handling

## Technical Details

The utility works by using ADB to call the Android SMS service via the `service call` command. Specifically, it uses the `isms` service's method 5 which corresponds to the `sendText` function in the [ISms.aidl](https://android.googlesource.com/platform/frameworks/base/+/refs/heads/android10-d4-s1-release/telephony/java/com/android/internal/telephony/ISms.aidl) interface.

The command structure is:
```
adb shell service call isms 5 [arguments...]
```

Where the arguments correspond to:
- `i32 [simId]` - The SIM card ID to use (default: 3 for eSIM)
- `s16 "com.android.mms.service"` - The calling package name
- `s16 "null"` - Default SMSC (Short Message Service Center)
- `s16 [recipient]` - The recipient's phone number
- `s16 "null"` - No scAddr override
- `s16 [message]` - The actual message content
- `s16 "null"` - No sentIntent
- `s16 "null"` - No deliveryIntent
- `i32 0` - Flags (for Android 11+)
- `i64 0` - Timestamp (for Android 11+)

This approach does not require any special permissions beyond standard ADB access to your device with USB debugging enabled.

## Architecture

The project consists of two main components:

1. **Command-line tool**: A simple Python script (`main.py`) that can be used to send SMS messages directly from the command line

2. **REST API**: A Flask-based API that provides:
   - SMS sending endpoints
   - Device status monitoring
   - Bulk SMS processing via CSV uploads
   - Swagger documentation

The API uses:
- Flask for HTTP handling
- SQLAlchemy for database operations
- Celery for asynchronous task processing
- Redis as a message broker
- PostgreSQL for data storage
- Gunicorn as a WSGI server

## License

This project is licensed under the MIT License - see the LICENSE file for details.