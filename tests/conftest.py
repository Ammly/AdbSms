"""
Pytest configuration file for the AdbSms tests.
"""
import os
import sys
import pytest
from unittest.mock import MagicMock

# Add the parent directory to the path so we can import the main module
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

@pytest.fixture
def mock_subprocess_run(monkeypatch):
    """Mock for subprocess.run to avoid actual ADB calls during testing"""
    mock_run = MagicMock()
    mock_run.return_value.stdout = "List of devices attached\nABCD1234\tdevice"
    monkeypatch.setattr("subprocess.run", mock_run)
    return mock_run

@pytest.fixture
def mock_time_sleep(monkeypatch):
    """Mock for time.sleep to avoid delays during testing"""
    mock_sleep = MagicMock()
    monkeypatch.setattr("time.sleep", mock_sleep)
    return mock_sleep

@pytest.fixture
def sample_csv_path(tmp_path):
    """Create a sample CSV file for testing"""
    csv_content = "phone_number,message\n"
    csv_content += "+1234567890,Hello World\n"
    csv_content += "+9876543210,Testing AdbSms"
    
    file_path = tmp_path / "test_messages.csv"
    with open(file_path, "w") as f:
        f.write(csv_content)
    
    return str(file_path)