"""
Starlink Arduino Mouse Controller v2.0
Advanced HID mouse control with humanization
"""

import serial
import serial.tools.list_ports
import time
import threading
from typing import Optional, Tuple


def find_arduino_port() -> Optional[str]:
    """
    Auto-detect Arduino Leonardo port.
    Checks for both original Arduino VID/PID and spoofed Logitech VID/PID.
    """
    # VID:PID combinations to search for
    known_ids = [
        ("2341", "8036"),  # Arduino Leonardo (original)
        ("2341", "8037"),  # Arduino Leonardo bootloader
        ("046D", "C094"),  # Logitech G Pro X Superlight (spoofed)
        ("1532", "00B6"),  # Razer DeathAdder V3 (spoofed)
    ]
    
    ports = serial.tools.list_ports.comports()
    
    for port in ports:
        vid = f"{port.vid:04X}" if port.vid else ""
        pid = f"{port.pid:04X}" if port.pid else ""
        
        for known_vid, known_pid in known_ids:
            if vid.upper() == known_vid.upper() and pid.upper() == known_pid.upper():
                return port.device
    
    # Fallback: check for "Arduino" or "Leonardo" in description
    for port in ports:
        desc = (port.description or "").lower()
        if "arduino" in desc or "leonardo" in desc:
            return port.device
    
    return None


def list_serial_ports() -> list:
    """List all available serial ports with details."""
    ports = serial.tools.list_ports.comports()
    result = []
    
    for port in ports:
        info = {
            "port": port.device,
            "description": port.description,
            "vid": f"{port.vid:04X}" if port.vid else "N/A",
            "pid": f"{port.pid:04X}" if port.pid else "N/A",
            "manufacturer": port.manufacturer or "N/A"
        }
        result.append(info)
    
    return result


class ArduinoMouseController:
    """
    Controller for Starlink Arduino mouse firmware.
    Handles serial communication and provides high-level mouse control API.
    """
    
    VERSION = "2.0.0"
    
    def __init__(self, port: Optional[str] = None, baudrate: int = 115200):
        """
        Initialize controller.
        
        Args:
            port: Serial port (auto-detect if None)
            baudrate: Serial baudrate (default 115200)
        """
        self.port = port
        self.baudrate = baudrate
        self.serial: Optional[serial.Serial] = None
        self.connected = False
        
        # Sub-pixel accumulator (Python-side for precision)
        self.accum_x = 0.0
        self.accum_y = 0.0
        
        # State
        self.humanization_enabled = True
        self.jitter_intensity = 50
        self.tremor_amplitude = 50
        
        # Thread safety
        self._lock = threading.Lock()
        
        # Stats
        self.moves_sent = 0
        self.last_latency_ms = 0.0
    
    def connect(self, timeout: float = 2.0) -> bool:
        """
        Connect to Arduino.
        
        Args:
            timeout: Connection timeout in seconds
            
        Returns:
            True if connected successfully
        """
        try:
            # Auto-detect port if not specified
            if self.port is None:
                self.port = find_arduino_port()
                if self.port is None:
                    print("Error: No Arduino found")
                    return False
            
            # Open serial connection
            self.serial = serial.Serial(
                port=self.port,
                baudrate=self.baudrate,
                timeout=timeout,
                write_timeout=timeout
            )
            
            # Wait for Arduino reset
            time.sleep(0.5)
            
            # Clear buffers
            self.serial.reset_input_buffer()
            self.serial.reset_output_buffer()
            
            # Verify connection with ping
            if self._ping():
                self.connected = True
                print(f"Connected to Starlink on {self.port}")
                return True
            else:
                self.serial.close()
                print("Error: Device did not respond to ping")
                return False
                
        except serial.SerialException as e:
            print(f"Serial error: {e}")
            return False
        except Exception as e:
            print(f"Connection error: {e}")
            return False
    
    def disconnect(self):
        """Disconnect from Arduino."""
        if self.serial and self.serial.is_open:
            try:
                self.serial.close()
            except:
                pass
        self.connected = False
        self.serial = None
        print("Disconnected from Starlink")
    
    def _ping(self) -> bool:
        """Send ping and check for response."""
        try:
            response = self._send_command("?")
            return response is not None and "OK" in response
        except:
            return False
    
    def _send_command(self, cmd: str) -> Optional[str]:
        """
        Send command to Arduino and get response.
        
        Args:
            cmd: Command string
            
        Returns:
            Response string or None
        """
        if not self.serial or not self.serial.is_open:
            return None
        
        with self._lock:
            try:
                # Send command
                self.serial.write(f"{cmd}\n".encode())
                self.serial.flush()
                
                # Read response (with short timeout)
                start = time.perf_counter()
                response = self.serial.readline().decode().strip()
                self.last_latency_ms = (time.perf_counter() - start) * 1000
                
                return response if response else None
                
            except serial.SerialException:
                return None
            except Exception:
                return None
    
    def _send_move(self, cmd: str):
        """Send move command without waiting for response (faster)."""
        if not self.serial or not self.serial.is_open:
            return
        
        with self._lock:
            try:
                start = time.perf_counter()
                self.serial.write(f"{cmd}\n".encode())
                # Don't flush for speed - let buffer handle it
                self.last_latency_ms = (time.perf_counter() - start) * 1000
                self.moves_sent += 1
            except:
                pass
    
    def move(self, dx: float, dy: float):
        """
        Move mouse by relative amount.
        
        Args:
            dx: Horizontal movement (positive = right)
            dy: Vertical movement (positive = down)
        """
        if not self.connected:
            return
        
        # Python-side sub-pixel accumulation for extra precision
        self.accum_x += dx
        self.accum_y += dy
        
        # Only send if we have meaningful movement
        if abs(self.accum_x) >= 0.5 or abs(self.accum_y) >= 0.5:
            # Send accumulated movement
            self._send_move(f"M,{self.accum_x:.2f},{self.accum_y:.2f}")
            
            # Keep sub-pixel remainder
            self.accum_x -= int(self.accum_x)
            self.accum_y -= int(self.accum_y)
    
    def move_smooth(self, dx: float, dy: float, steps: int = 5, 
                    interval_ms: float = 2.0):
        """
        Move mouse smoothly over multiple steps.
        
        Args:
            dx: Total horizontal movement
            dy: Total vertical movement
            steps: Number of steps to divide movement into
            interval_ms: Delay between steps in milliseconds
        """
        if not self.connected or steps < 1:
            return
        
        step_dx = dx / steps
        step_dy = dy / steps
        
        for _ in range(steps):
            self.move(step_dx, step_dy)
            if interval_ms > 0:
                time.sleep(interval_ms / 1000.0)
    
    def click(self, button: str = "L"):
        """
        Click mouse button.
        
        Args:
            button: "L" (left), "R" (right), or "M" (middle)
        """
        if self.connected:
            self._send_command(f"C,{button}")
    
    def press(self, button: str = "L"):
        """
        Press and hold mouse button.
        
        Args:
            button: "L" (left), "R" (right), or "M" (middle)
        """
        if self.connected:
            self._send_command(f"P,{button}")
    
    def release(self, button: str = "L"):
        """
        Release mouse button.
        
        Args:
            button: "L" (left), "R" (right), or "M" (middle)
        """
        if self.connected:
            self._send_command(f"R,{button}")
    
    def set_jitter(self, intensity: int):
        """
        Set jitter intensity.
        
        Args:
            intensity: 0-100 (0 = minimal, 100 = maximum)
        """
        intensity = max(0, min(100, intensity))
        self.jitter_intensity = intensity
        if self.connected:
            self._send_command(f"J,{intensity}")
    
    def set_tremor(self, amplitude: int):
        """
        Set hand tremor amplitude.
        
        Args:
            amplitude: 0-100 (0 = off, 100 = maximum)
        """
        amplitude = max(0, min(100, amplitude))
        self.tremor_amplitude = amplitude
        if self.connected:
            self._send_command(f"T,{amplitude}")
    
    def set_humanization(self, enabled: bool = True, 
                         jitter: Optional[int] = None,
                         tremor: Optional[int] = None):
        """
        Configure humanization settings.
        
        Args:
            enabled: Enable/disable all humanization
            jitter: Jitter intensity (0-100)
            tremor: Tremor amplitude (0-100)
        """
        self.humanization_enabled = enabled
        
        if jitter is not None:
            self.jitter_intensity = max(0, min(100, jitter))
        if tremor is not None:
            self.tremor_amplitude = max(0, min(100, tremor))
        
        if self.connected:
            self._send_command(
                f"H,{self.jitter_intensity},{self.tremor_amplitude},{1 if enabled else 0}"
            )
    
    def enable_humanization(self, enabled: bool = True):
        """Enable or disable humanization."""
        self.humanization_enabled = enabled
        if self.connected:
            self._send_command(f"E,{1 if enabled else 0}")
    
    def reset(self):
        """Reset Arduino state (accumulators, velocity, etc.)."""
        self.accum_x = 0.0
        self.accum_y = 0.0
        if self.connected:
            self._send_command("X")
    
    def get_version(self) -> Optional[str]:
        """Get firmware version."""
        if self.connected:
            response = self._send_command("V")
            if response and "VER:" in response:
                return response.split("VER:")[1]
        return None
    
    def get_status(self) -> Optional[dict]:
        """Get current device status."""
        if not self.connected:
            return None
        
        response = self._send_command("S")
        if response and "STATUS:" in response:
            try:
                status_str = response.split("STATUS:")[1]
                parts = status_str.split(",")
                status = {}
                for part in parts:
                    key, val = part.split("=")
                    status[key] = val
                return status
            except:
                pass
        return None
    
    @property
    def is_connected(self) -> bool:
        """Check if connected to Arduino."""
        return self.connected and self.serial is not None and self.serial.is_open


# Convenience function
def create_controller(port: Optional[str] = None) -> Optional[ArduinoMouseController]:
    """
    Create and connect to Arduino mouse controller.
    
    Args:
        port: Serial port (auto-detect if None)
        
    Returns:
        Connected controller or None if failed
    """
    controller = ArduinoMouseController(port=port)
    if controller.connect():
        return controller
    return None
