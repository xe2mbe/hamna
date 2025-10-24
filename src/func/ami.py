"""
AMI (Asterisk Manager Interface) module for handling AMI connections.
"""
import socket
import ssl
from typing import Optional, Dict, Any


class AMIConnectionError(Exception):
    """Custom exception for AMI connection errors"""
    pass


class AMIConnection:
    """Handles AMI (Asterisk Manager Interface) connections and commands."""
    
    def __init__(self):
        self.socket = None
        self.connected = False
        self.host = None
        self.port = None
        self.username = None
        self.password = None
    
    def connect(self, host: str, port: int, username: str, secret: str, use_ssl: bool = False) -> bool:
        """
        Connect to the AMI server.
        
        Args:
            host: AMI server hostname or IP
            port: AMI server port
            username: AMI username
            secret: AMI secret/password
            use_ssl: Whether to use SSL/TLS
            
        Returns:
            bool: True if connection and login were successful, False otherwise
        """
        self.host = host
        self.port = port
        self.username = username
        self.password = secret
        
        try:
            # Create socket connection
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            
            if use_ssl:
                context = ssl.create_default_context()
                self.socket = context.wrap_socket(sock, server_hostname=host)
            else:
                self.socket = sock
            
            # Connect to server
            self.socket.connect((host, port))
            
            # Read welcome message
            welcome = self._read_response()
            
            # Login to AMI
            login_action = (
                f"Action: Login\r\n"
                f"Username: {username}\r\n"
                f"Secret: {secret}\r\n"
                f"Events: off\r\n"
                f"\r\n"
            )
            
            self.socket.send(login_action.encode('utf-8'))
            login_response = self._read_response()
            
            if 'Success' in login_response:
                self.connected = True
                return True
            else:
                raise AMIConnectionError("Login failed: " + login_response)
                
        except Exception as e:
            self.connected = False
            if self.socket:
                self.socket.close()
                self.socket = None
            raise AMIConnectionError(f"Failed to connect to AMI: {str(e)}")
    
    def disconnect(self) -> None:
        """Disconnect from the AMI server."""
        if self.connected and self.socket:
            try:
                self.socket.send(b"Action: Logoff\r\n\r\n")
                self.socket.close()
            except:
                pass
            finally:
                self.socket = None
                self.connected = False
    
    def test_connection(self, host: str, port: int, username: str, secret: str, 
                       timeout: int = 5, use_ssl: bool = False) -> bool:
        """
        Test connection to AMI server.
        
        Args:
            host: AMI server hostname or IP
            port: AMI server port
            username: AMI username
            secret: AMI secret/password
            timeout: Connection timeout in seconds
            use_ssl: Whether to use SSL/TLS
            
        Returns:
            bool: True if connection test was successful, False otherwise
        """
        try:
            # Create a test connection
            test_conn = AMIConnection()
            
            # Set socket timeout
            socket.setdefaulttimeout(timeout)
            
            # Try to connect
            connected = test_conn.connect(host, port, username, secret, use_ssl)
            
            # Clean up
            test_conn.disconnect()
            
            return connected
            
        except Exception as e:
            return False
    
    def send_command(self, command: str, params: Optional[Dict[str, str]] = None) -> str:
        """
        Send a command to the AMI server.
        
        Args:
            command: AMI command to execute
            params: Optional parameters for the command
            
        Returns:
            str: Server response
            
        Raises:
            AMIConnectionError: If not connected or error sending command
        """
        if not self.connected or not self.socket:
            raise AMIConnectionError("Not connected to AMI server")
        
        try:
            # Build command string
            cmd = f"Action: {command}\r\n"
            
            # Add parameters if any
            if params:
                for key, value in params.items():
                    cmd += f"{key}: {value}\r\n"
            
            # Add final newlines
            cmd += "\r\n"
            
            # Send command
            self.socket.send(cmd.encode('utf-8'))
            
            # Read and return response
            return self._read_response()
            
        except Exception as e:
            self.connected = False
            raise AMIConnectionError(f"Error sending command: {str(e)}")
    
    def _read_response(self) -> str:
        """
        Read response from AMI server.
        
        Returns:
            str: Raw response from server
            
        Raises:
            AMIConnectionError: If error reading response
        """
        if not self.socket:
            raise AMIConnectionError("Not connected to AMI server")
        
        try:
            response = b""
            while True:
                chunk = self.socket.recv(4096)
                if not chunk:
                    break
                response += chunk
                if b"\r\n\r\n" in response:
                    break
            
            return response.decode('utf-8', errors='ignore')
            
        except Exception as e:
            self.connected = False
            raise AMIConnectionError(f"Error reading response: {str(e)}")
    
    def is_connected(self) -> bool:
        """Check if connected to AMI server."""
        return self.connected
    
    def get_connection_info(self) -> Dict[str, Any]:
        """
        Get connection information.
        
        Returns:
            dict: Connection information
        """
        return {
            'host': self.host,
            'port': self.port,
            'username': self.username,
            'connected': self.connected
        }
