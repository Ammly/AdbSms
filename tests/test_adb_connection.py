"""
Tests for the check_adb_connection function in main.py
"""
import pytest
import subprocess
from main import check_adb_connection


def test_adb_connection_success(monkeypatch):
    """Test successful ADB connection check with device connected"""
    # Mock subprocess.run to simulate a successful ADB connection
    def mock_run(*args, **kwargs):
        mock_result = subprocess.CompletedProcess(
            args=args[0],
            returncode=0,
            stdout="List of devices attached\nABCD1234\tdevice\n"
        )
        return mock_result
    
    monkeypatch.setattr("subprocess.run", mock_run)
    
    # Check result
    result = check_adb_connection()
    assert result is True


def test_adb_connection_no_devices(monkeypatch):
    """Test ADB connection check with no devices connected"""
    # Mock subprocess.run to simulate no devices connected
    def mock_run(*args, **kwargs):
        mock_result = subprocess.CompletedProcess(
            args=args[0],
            returncode=0,
            stdout="List of devices attached\n"
        )
        return mock_result
    
    monkeypatch.setattr("subprocess.run", mock_run)
    
    # Check result
    result = check_adb_connection()
    assert result is False


def test_adb_connection_unauthorized_device(monkeypatch):
    """Test ADB connection check with unauthorized device"""
    # Mock subprocess.run to simulate unauthorized device
    def mock_run(*args, **kwargs):
        mock_result = subprocess.CompletedProcess(
            args=args[0],
            returncode=0,
            stdout="List of devices attached\nABCD1234\tunauthorized\n"
        )
        return mock_result
    
    monkeypatch.setattr("subprocess.run", mock_run)
    
    # Check result
    result = check_adb_connection()
    assert result is False


def test_adb_connection_offline_device(monkeypatch):
    """Test ADB connection check with offline device"""
    # Mock subprocess.run to simulate offline device
    def mock_run(*args, **kwargs):
        mock_result = subprocess.CompletedProcess(
            args=args[0],
            returncode=0,
            stdout="List of devices attached\nABCD1234\toffline\n"
        )
        return mock_result
    
    monkeypatch.setattr("subprocess.run", mock_run)
    
    # Check result
    result = check_adb_connection()
    assert result is False


def test_adb_connection_adb_not_found(monkeypatch):
    """Test ADB connection check when ADB is not installed"""
    # Mock subprocess.run to simulate ADB not found
    def mock_run(*args, **kwargs):
        raise FileNotFoundError("ADB not found")
    
    monkeypatch.setattr("subprocess.run", mock_run)
    
    # Check result
    result = check_adb_connection()
    assert result is False


def test_adb_connection_adb_error(monkeypatch):
    """Test ADB connection check when ADB returns an error"""
    # Mock subprocess.run to simulate ADB error
    def mock_run(*args, **kwargs):
        raise subprocess.CalledProcessError(1, "adb devices", "Error output")
    
    monkeypatch.setattr("subprocess.run", mock_run)
    
    # Check result
    result = check_adb_connection()
    assert result is False