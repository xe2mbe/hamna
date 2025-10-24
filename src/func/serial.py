import serial
import serial.tools.list_ports
from typing import List, Optional, Dict, Any
import time

class SerialInterface:
    def __init__(self):
        self.serial_connection = None
        self.port = None
        self.baudrate = 9600
        self.ptt_state = False
        self.cos_state = False
        self.running = False
        self.invert_ptt = False
        self.invert_cos = False
        self.timeout = 1.0  # seconds

    def list_ports(self) -> List[Dict[str, str]]:
        """Return a list of available serial ports with their descriptions"""
        ports = []
        for port in serial.tools.list_ports.comports():
            port_info = {
                'device': port.device,
                'name': port.name,
                'description': port.description,
                'hwid': port.hwid,
                'vid': port.vid,
                'pid': port.pid,
                'serial_number': port.serial_number,
                'manufacturer': port.manufacturer,
                'product': port.product,
                'interface': port.interface
            }
            ports.append(port_info)
        return ports

    def connect_serial(self, port: str, baudrate: int = 9600) -> bool:
        """Connect to the specified serial port"""
        if self.serial_connection and self.serial_connection.is_open:
            self.disconnect_serial()
        
        try:
            self.serial_connection = serial.Serial(
                port=port,
                baudrate=baudrate,
                bytesize=serial.EIGHTBITS,
                parity=serial.PARITY_NONE,
                stopbits=serial.STOPBITS_ONE,
                timeout=self.timeout,
                write_timeout=self.timeout,
                rtscts=False,
                dsrdtr=False
            )
            self.port = port
            self.baudrate = baudrate
            self.running = True
            return True
            
        except (serial.SerialException, OSError) as e:
            print(f"Error connecting to {port}: {e}")
            self.serial_connection = None
            return False

    def disconnect_serial(self) -> None:
        """Close the serial connection"""
        self.running = False
        if self.serial_connection and self.serial_connection.is_open:
            try:
                self.set_ptt(False)  # Turn off PTT before disconnecting
                self.serial_connection.close()
            except Exception as e:
                print(f"Error disconnecting: {e}")
        self.serial_connection = None
        self.ptt_state = False
        self.cos_state = False

    def set_ptt(self, state: bool) -> bool:
        """Set PTT state (True = ON, False = OFF)"""
        if not self.serial_connection or not self.serial_connection.is_open:
            return False
            
        try:
            # Apply inversion if needed
            actual_state = not state if self.invert_ptt else state
            
            # Try to use RTS or DTR if available
            if hasattr(self.serial_connection, 'rts'):
                self.serial_connection.rts = actual_state
                self.ptt_state = state
                return True
                
            # Fallback to sending commands if RTS/DTR not available
            command = b'HIGH\r\n' if actual_state else b'LOW\r\n'
            # Clear buffers
            self.serial_connection.reset_input_buffer()
            self.serial_connection.reset_output_buffer()
            
            # Send command
            self.serial_connection.write(command)
            self.serial_connection.flush()
            
            self.ptt_state = state
            return True
            
        except Exception as e:
            print(f"Error setting PTT: {e}")
            return False

    def read_cos(self) -> Optional[bool]:
        """Read COS state from the serial port"""
        if not self.serial_connection or not self.serial_connection.is_open:
            return None
            
        try:
            # Try to read CTS/DSR first
            if hasattr(self.serial_connection, 'cts'):
                cos_state = self.serial_connection.cts
                # Apply inversion if needed
                cos_state = not cos_state if self.invert_cos else cos_state
                self.cos_state = cos_state
                return cos_state
                
            # Fallback to reading from the serial port
            # This assumes the device sends 'COS_HIGH' or 'COS_LOW' when COS changes
            if self.serial_connection.in_waiting > 0:
                line = self.serial_connection.readline().decode('ascii', errors='ignore').strip()
                if 'COS_HIGH' in line:
                    cos_state = True
                elif 'COS_LOW' in line:
                    cos_state = False
                else:
                    return self.cos_state  # Return last known state
                
                # Apply inversion if needed
                cos_state = not cos_state if self.invert_cos else cos_state
                self.cos_state = cos_state
                return cos_state
                
            return self.cos_state  # Return last known state if no new data
            
        except Exception as e:
            print(f"Error reading COS: {e}")
            return None

    def is_connected(self) -> bool:
        """Check if the serial connection is active"""
        return self.serial_connection is not None and self.serial_connection.is_open

    def set_invert_ptt(self, invert: bool) -> None:
        """Set PTT signal inversion"""
        self.invert_ptt = invert

    def set_invert_cos(self, invert: bool) -> None:
        """Set COS signal inversion"""
        self.invert_cos = invert

    def get_port_info(self) -> Dict[str, Any]:
        """Get current port information"""
        if not self.serial_connection:
            return {}
            
        return {
            'port': self.serial_connection.port,
            'baudrate': self.serial_connection.baudrate,
            'bytesize': self.serial_connection.bytesize,
            'parity': self.serial_connection.parity,
            'stopbits': self.serial_connection.stopbits,
            'timeout': self.serial_connection.timeout,
            'is_open': self.serial_connection.is_open
        }
