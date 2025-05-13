"""
Tests for the send_bulk_sms function in main.py
"""
import pytest
from unittest.mock import patch, MagicMock
import pandas as pd
from main import send_bulk_sms


def test_send_bulk_sms_success(sample_csv_path, mock_subprocess_run, mock_time_sleep):
    """Test successful bulk SMS sending"""
    # Configure mock to simulate success
    mock_subprocess_run.return_value.returncode = 0
    
    # Call the function
    success, failure = send_bulk_sms(sample_csv_path, 3, 0.5)
    
    # Verify results
    assert success == 2  # Two messages in the sample CSV
    assert failure == 0  # No failures
    assert mock_subprocess_run.call_count == 2  # Two SMS calls
    assert mock_time_sleep.call_count == 1  # Sleep only between messages (not after last)
    mock_time_sleep.assert_called_with(0.5)  # Check delay value


def test_send_bulk_sms_mixed_results(sample_csv_path, monkeypatch, mock_time_sleep):
    """Test bulk SMS sending with mixed results"""
    # Create a mock send_sms function that alternates between success and failure
    calls = []
    
    def mock_send_sms(phone, message, sim_id):
        calls.append((phone, message, sim_id))
        # First call succeeds, second fails
        return len(calls) % 2 == 1
    
    # Patch the send_sms function
    monkeypatch.setattr("main.send_sms", mock_send_sms)
    
    # Call the function
    success, failure = send_bulk_sms(sample_csv_path, 3, 0.5)
    
    # Verify results
    assert success == 1  # One success
    assert failure == 1  # One failure
    assert len(calls) == 2  # Two SMS attempts
    assert calls[0][2] == 3  # Check SIM ID was passed correctly


def test_send_bulk_sms_file_error(monkeypatch, mock_time_sleep):
    """Test bulk SMS sending with a file error"""
    # Mock pd.read_csv to raise an exception
    def mock_read_csv(*args, **kwargs):
        raise FileNotFoundError("File not found")
    
    monkeypatch.setattr("pandas.read_csv", mock_read_csv)
    
    # Call the function with a non-existent path
    success, failure = send_bulk_sms("nonexistent_file.csv", 3, 0.5)
    
    # Verify results
    assert success == 0
    assert failure == 0
    assert mock_time_sleep.call_count == 0  # No sleeps should happen