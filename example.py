#!/usr/bin/env python3
"""
Example script showing how to use AdbSms to send a single SMS message.
This can be used as a quick test to verify your setup is working.
"""

from main import send_sms, check_adb_connection

if __name__ == "__main__":
    if check_adb_connection():
        # Test by sending a message to your own number
        send_sms(
            "+1234567890",  # Replace with a valid phone number
            "Hello from AdbSms example script!",
            3               # Change to your SIM subId if needed
        )
    else:
        print("ADB connection failed. Please check your device connection.")