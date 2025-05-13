"""
Tests for the send_sms function in main.py
"""
import pytest
from unittest.mock import call
import subprocess
from main import send_sms


def test_send_sms_success(mock_subprocess_run):
    """Test successful SMS sending"""
    # Configure mock to simulate success
    mock_subprocess_run.return_value.returncode = 0
    
    # Call the function
    result = send_sms("+1234567890", "Test message", 3)
    
    # Verify results
    assert result is True
    mock_subprocess_run.assert_called_once()
    
    # Check that ADB command was constructed correctly
    args = mock_subprocess_run.call_args[0][0]
    assert args[0:3] == ["adb", "shell", "service"]
    assert str(3) in args  # Check SIM ID is included
    assert any("+1234567890" in arg for arg in args)  # Check phone number is included
    assert any("Test message" in arg for arg in args)  # Check message is included


def test_send_sms_failure(mock_subprocess_run):
    """Test SMS sending failure"""
    # Configure mock to simulate failure
    mock_subprocess_run.side_effect = subprocess.CalledProcessError(1, "adb shell...")
    
    # Call the function
    result = send_sms("+1234567890", "Test message", 3)
    
    # Verify results
    assert result is False
    mock_subprocess_run.assert_called_once()


def test_send_sms_different_sim_id(mock_subprocess_run):
    """Test SMS sending with different SIM ID"""
    # Configure mock to simulate success
    mock_subprocess_run.return_value.returncode = 0
    
    # Call the function with SIM ID 1
    result = send_sms("+1234567890", "Test message", 1)
    
    # Verify results
    assert result is True
    
    # Check that SIM ID 1 was used
    args = mock_subprocess_run.call_args[0][0]
    assert "i32" in args
    sim_id_index = args.index("i32") + 1
    assert args[sim_id_index] == "1"