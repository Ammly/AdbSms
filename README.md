# AdbSms

A simple Python utility to send SMS messages programmatically using ADB (Android Debug Bridge) to a connected Android device.

## Overview

This tool reads phone numbers and message content from a CSV file and sends SMS messages to the specified recipients using ADB commands. It's useful for:

- Testing SMS functionality
- Bulk messaging scenarios
- Automating SMS sending for development purposes

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
ABCD123456      device
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

| Option | Short | Description |
|--------|-------|-------------|
| `--file FILE` | `-f` | CSV file with phone numbers and messages (default: messages.csv) |
| `--sim-id SIM_ID` | `-s` | SIM card subId (default: 3 for eSIM) |
| `--delay DELAY` | `-d` | Delay between messages in seconds (default: 1.0) |
| `--single` | | Send a single message instead of reading from CSV |
| `--number NUMBER` | `-n` | Phone number for single message mode |
| `--message MESSAGE` | `-m` | Message content for single message mode |
| `--check-only` | | Only check ADB connection and exit |

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

## Troubleshooting

- If `adb devices` shows no devices or shows as "unauthorized", check your USB connection and ensure you've authorized the debugging connection on your device
- If SMS fails to send, verify that your SIM card works correctly and that the subId is correctly set
- For timeouts or connection issues, try restarting ADB with `adb kill-server` followed by `adb start-server`

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

## License

This project is licensed under the MIT License - see the LICENSE file for details.