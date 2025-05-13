"""
Tests for the command-line interface functionality in main.py
"""
import pytest
import sys
from unittest.mock import patch
import main


def test_cli_check_only(monkeypatch):
    """Test --check-only flag"""
    # Mock sys.argv
    test_args = ["main.py", "--check-only"]
    monkeypatch.setattr(sys, "argv", test_args)
    
    # Mock check_adb_connection to return True
    monkeypatch.setattr(main, "check_adb_connection", lambda: True)
    
    # Capture stdout to check output
    with patch("sys.stdout") as mock_stdout:
        # Call main() and check the return code
        exit_code = main.main()
        assert exit_code == 0
        
        # Check that the correct message was printed
        output = "".join(call.args[0] for call in mock_stdout.write.call_args_list if call.args)
        assert "ADB connection successful" in output


def test_cli_single_sms(monkeypatch):
    """Test sending a single SMS via command line"""
    # Mock sys.argv
    test_args = ["main.py", "--single", "--number", "+1234567890", "--message", "Test message"]
    monkeypatch.setattr(sys, "argv", test_args)
    
    # Mock check_adb_connection and send_sms
    monkeypatch.setattr(main, "check_adb_connection", lambda: True)
    monkeypatch.setattr(main, "send_sms", lambda phone, msg, sim_id: True)
    
    # Call main() and check the return code
    exit_code = main.main()
    assert exit_code == 0


def test_cli_single_sms_missing_args(monkeypatch):
    """Test sending a single SMS with missing arguments"""
    # Mock sys.argv
    test_args = ["main.py", "--single"]  # Missing --number and --message
    monkeypatch.setattr(sys, "argv", test_args)
    
    # Mock check_adb_connection
    monkeypatch.setattr(main, "check_adb_connection", lambda: True)
    
    # Call main() and check the return code
    exit_code = main.main()
    assert exit_code == 1


def test_cli_bulk_sms(monkeypatch):
    """Test sending bulk SMS via command line"""
    # Mock sys.argv
    test_args = ["main.py", "--file", "messages.csv", "--sim-id", "2", "--delay", "0.5"]
    monkeypatch.setattr(sys, "argv", test_args)
    
    # Mock check_adb_connection and send_bulk_sms
    monkeypatch.setattr(main, "check_adb_connection", lambda: True)
    monkeypatch.setattr(main, "send_bulk_sms", lambda file, sim_id, delay: (3, 0))  # 3 success, 0 failures
    
    # Call main() and check the return code
    exit_code = main.main()
    assert exit_code == 0


def test_cli_bulk_sms_with_failures(monkeypatch):
    """Test sending bulk SMS with some failures"""
    # Mock sys.argv
    test_args = ["main.py"]  # Use defaults
    monkeypatch.setattr(sys, "argv", test_args)
    
    # Mock check_adb_connection and send_bulk_sms
    monkeypatch.setattr(main, "check_adb_connection", lambda: True)
    monkeypatch.setattr(main, "send_bulk_sms", lambda file, sim_id, delay: (2, 1))  # 2 success, 1 failure
    
    # Call main() and check the return code
    exit_code = main.main()
    assert exit_code == 1


def test_cli_adb_connection_failure(monkeypatch):
    """Test CLI behavior when ADB connection fails"""
    # Mock sys.argv
    test_args = ["main.py"]
    monkeypatch.setattr(sys, "argv", test_args)
    
    # Mock check_adb_connection to return False
    monkeypatch.setattr(main, "check_adb_connection", lambda: False)
    
    # Call main() and check the return code
    exit_code = main.main()
    assert exit_code == 1