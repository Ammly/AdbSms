#!/usr/bin/env python3
"""
AdbSms - A utility to send SMS messages using ADB.

This script can be used as a command-line tool or imported as a module.
"""

import argparse
import pandas as pd
import subprocess
import shlex
import time
import sys
from typing import List, Optional, Dict, Union, Tuple


def send_sms(phone_number: str, message: str, sim_id: int = 3) -> bool:
    """
    Send a single SMS message using ADB.
    
    Args:
        phone_number: The recipient's phone number
        message: The message to send
        sim_id: SIM card subId (default: 3 for eSIM)
        
    Returns:
        bool: True if message was sent successfully, False otherwise
    """
    # Build the token list, shell-escaping each piece
    cmd_tokens = [
        "adb", "shell",
        "service", "call", "isms", "5",
        "i32", str(sim_id),                            # SIM subId
        "s16", shlex.quote("com.android.mms.service"), # calling package
        "s16", shlex.quote("null"),                    # default SMSC
        "s16", shlex.quote(phone_number),              # recipient
        "s16", shlex.quote("null"),                    # no scAddr override
        "s16", shlex.quote(message),                   # message body
        "s16", shlex.quote("null"),                    # no sentIntent
        "s16", shlex.quote("null"),                    # no deliveryIntent
        "i32", "0",                                    # flags (Android 11+)
        "i64", "0",                                    # timestamp (Android 11+)
    ]

    # Execute
    print(f"Sending to {phone_number!r}: {message!r}")
    try:
        subprocess.run(cmd_tokens, check=True)
        print("  ✅ Sent")
        return True
    except subprocess.CalledProcessError as e:
        print(f"  ❌ Failed: {e}")
        return False


def send_bulk_sms(csv_path: str, sim_id: int = 3, delay: float = 1.0) -> Tuple[int, int]:
    """
    Send multiple SMS messages from a CSV file.
    
    Args:
        csv_path: Path to the CSV file with phone_number and message columns
        sim_id: SIM card subId (default: 3 for eSIM)
        delay: Time to wait between messages in seconds
        
    Returns:
        Tuple[int, int]: Count of (success, failure) messages
    """
    try:
        # Load the CSV, forcing phone_number and message to strings
        df = pd.read_csv(
            csv_path,
            dtype={
                'phone_number': str,
                'message': str
            }
        )
    except Exception as e:
        print(f"Error reading CSV file: {e}")
        return 0, 0

    success_count = 0
    failure_count = 0

    # Iterate and send
    for index, row in df.iterrows():
        # Ensure we have strings (in case of stray NaNs or numeric parsing)
        phone_number = str(row['phone_number'])
        message = str(row['message'])

        result = send_sms(phone_number, message, sim_id)
        if result:
            success_count += 1
        else:
            failure_count += 1

        # Throttle to avoid flooding
        if index < len(df) - 1:  # Don't sleep after the last message
            time.sleep(delay)

    return success_count, failure_count


def check_adb_connection() -> bool:
    """Check if ADB is working and a device is connected."""
    try:
        result = subprocess.run(
            ["adb", "devices"], 
            capture_output=True, 
            text=True, 
            check=True
        )
        
        # Check if any device is connected (more than just the "List of devices attached" line)
        lines = result.stdout.strip().split('\n')
        if len(lines) <= 1:
            print("No devices connected. Please connect an Android device.")
            return False
            
        # Check that at least one device is in "device" state (not offline or unauthorized)
        device_found = False
        for line in lines[1:]:  # Skip the header line
            if line.strip() and "\tdevice" in line:
                device_found = True
                print(f"Connected device found: {line.strip()}")
                break
                
        if not device_found:
            print("Device found but not authorized or offline. Check your device.")
            # Print the actual devices output to help diagnose
            for line in lines:
                print(f"  > {line}")
            return False
            
        return True
    except subprocess.CalledProcessError as e:
        print(f"ADB command error: {e}")
        print(f"Error output: {e.stderr}")
        return False
    except FileNotFoundError:
        print("ADB not found or not working properly. Make sure ADB is installed and in your PATH.")
        return False
    except Exception as e:
        print(f"Error checking ADB connection: {e}")
        import traceback
        print(traceback.format_exc())
        return False


def parse_arguments():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="Send SMS messages using ADB to a connected Android device."
    )
    
    # Add arguments
    parser.add_argument(
        "-f", "--file", 
        default="messages.csv",
        help="CSV file with phone_number and message columns (default: messages.csv)"
    )
    parser.add_argument(
        "-s", "--sim-id", 
        type=int, 
        default=3,
        help="SIM card subId (default: 3 for eSIM, others typically 0 or 1)"
    )
    parser.add_argument(
        "-d", "--delay", 
        type=float, 
        default=1.0,
        help="Delay between messages in seconds (default: 1.0)"
    )
    parser.add_argument(
        "--single", 
        action="store_true",
        help="Send a single message instead of reading from CSV"
    )
    parser.add_argument(
        "-n", "--number",
        help="Phone number for single message mode"
    )
    parser.add_argument(
        "-m", "--message",
        help="Message content for single message mode"
    )
    parser.add_argument(
        "--check-only",
        action="store_true",
        help="Only check ADB connection and exit"
    )
    
    return parser.parse_args()


def main():
    """
    Main entry point for the script.
    
    Returns:
        int: Exit code (0 for success, 1 for failure)
    """
    args = parse_arguments()
    
    # Check ADB connection first
    if not check_adb_connection():
        return 1
        
    if args.check_only:
        print("✅ ADB connection successful")
        return 0
    
    if args.single:
        if not args.number or not args.message:
            print("Error: --number and --message are required with --single")
            return 1
        
        success = send_sms(args.number, args.message, args.sim_id)
        return 0 if success else 1
    else:
        # Bulk mode
        print(f"Sending messages from {args.file} with SIM ID {args.sim_id} and {args.delay}s delay")
        success, failure = send_bulk_sms(args.file, args.sim_id, args.delay)
        print(f"Completed: {success} succeeded, {failure} failed")
        return 1 if failure > 0 else 0


if __name__ == "__main__":
    sys.exit(main())
