"""
API module for handling HTTP API connections to control PTT.
"""
import urllib.request
import urllib.error
import socket
from typing import Optional, Dict, Any, Tuple


class APIConnectionError(Exception):
    """Custom exception for API connection errors"""
    pass


class APIConnection:
    """Handles API connections for PTT control."""
    
    def __init__(self):
        self.base_url = ""
        self.ptt_on_path = ""
        self.ptt_off_path = ""
        self.timeout = 5  # seconds
        self.connected = False
    
    def connect(self, base_url: str, ptt_on_path: str, ptt_off_path: str, timeout: int = 5) -> bool:
        """
        Initialize API connection settings.
        
        Args:
            base_url: Base URL of the API (e.g., 'http://localhost:8080')
            ptt_on_path: Path for PTT ON endpoint (e.g., '/ptt/on')
            ptt_off_path: Path for PTT OFF endpoint (e.g., '/ptt/off')
            timeout: Connection timeout in seconds
            
        Returns:
            bool: True if settings were applied successfully
        """
        self.base_url = base_url.rstrip('/')
        self.ptt_on_path = ptt_on_path.lstrip('/')
        self.ptt_off_path = ptt_off_path.lstrip('/')
        self.timeout = timeout
        self.connected = True
        return True
    
    def disconnect(self) -> None:
        """Close the API connection."""
        self.connected = False
    
    def test_connection(self) -> bool:
        """
        Test the API connection by sending a HEAD request to the base URL.
        
        Returns:
            bool: True if connection test was successful
            
        Raises:
            APIConnectionError: If connection test fails
        """
        if not self.base_url:
            raise APIConnectionError("Base URL is not set")
            
        try:
            req = urllib.request.Request(self.base_url, method='HEAD')
            with urllib.request.urlopen(req, timeout=self.timeout) as response:
                return 200 <= response.status < 400
        except urllib.error.URLError as e:
            raise APIConnectionError(f"Failed to connect to API: {str(e)}")
        except socket.timeout:
            raise APIConnectionError("Connection timed out")
        except Exception as e:
            raise APIConnectionError(f"Unexpected error: {str(e)}")
    
    def _make_request(self, path: str) -> Tuple[int, str]:
        """
        Make an HTTP GET request to the specified path.
        
        Args:
            path: API endpoint path
            
        Returns:
            Tuple[int, str]: Status code and response text
            
        Raises:
            APIConnectionError: If request fails
        """
        if not self.connected:
            raise APIConnectionError("Not connected to API")
            
        url = f"{self.base_url}/{path}"
        
        try:
            req = urllib.request.Request(url, method='GET')
            with urllib.request.urlopen(req, timeout=self.timeout) as response:
                return response.status, response.read().decode('utf-8')
        except urllib.error.URLError as e:
            raise APIConnectionError(f"API request failed: {str(e)}")
        except socket.timeout:
            raise APIConnectionError("Request timed out")
        except Exception as e:
            raise APIConnectionError(f"Unexpected error: {str(e)}")
    
    def ptt_on(self) -> bool:
        """
        Send PTT ON command to the API.
        
        Returns:
            bool: True if command was sent successfully
            
        Raises:
            APIConnectionError: If PTT ON command fails
        """
        status, _ = self._make_request(self.ptt_on_path)
        return 200 <= status < 400
    
    def ptt_off(self) -> bool:
        """
        Send PTT OFF command to the API.
        
        Returns:
            bool: True if command was sent successfully
            
        Raises:
            APIConnectionError: If PTT OFF command fails
        """
        status, _ = self._make_request(self.ptt_off_path)
        return 200 <= status < 400
    
    def get_api_info(self) -> Dict[str, Any]:
        """
        Get connection information.
        
        Returns:
            dict: Dictionary containing connection information
        """
        return {
            'base_url': self.base_url,
            'ptt_on_path': self.ptt_on_path,
            'ptt_off_path': self.ptt_off_path,
            'timeout': self.timeout,
            'connected': self.connected
        }
