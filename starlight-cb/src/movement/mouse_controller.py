"""
Mouse Controller Module
Unified interface for SendInput (internal) and Arduino hardware mouse
"""

import ctypes
from ctypes import wintypes
import time
from typing import Tuple, Optional
from dataclasses import dataclass
import threading

# Try to import serial for Arduino support
try:
    import serial
    import serial.tools.list_ports
    SERIAL_AVAILABLE = True
except ImportError:
    SERIAL_AVAILABLE = False
    print("Note: pyserial not installed, Arduino mouse not available")


# Windows API Constants
MOUSEEVENTF_MOVE = 0x0001
MOUSEEVENTF_LEFTDOWN = 0x0002
MOUSEEVENTF_LEFTUP = 0x0004
MOUSEEVENTF_RIGHTDOWN = 0x0008
MOUSEEVENTF_RIGHTUP = 0x0010
MOUSEEVENTF_MIDDLEDOWN = 0x0020
MOUSEEVENTF_MIDDLEUP = 0x0040
MOUSEEVENTF_XDOWN = 0x0080
MOUSEEVENTF_XUP = 0x0100
MOUSEEVENTF_WHEEL = 0x0800
MOUSEEVENTF_HWHEEL = 0x01000

INPUT_MOUSE = 0
INPUT_KEYBOARD = 1
INPUT_HARDWARE = 2

# X button constants
XBUTTON1 = 0x0001  # Back button
XBUTTON2 = 0x0002  # Forward button


# Windows API Structures
class MOUSEINPUT(ctypes.Structure):
    _fields_ = [
        ("dx", wintypes.LONG),
        ("dy", wintypes.LONG),
        ("mouseData", wintypes.DWORD),
        ("dwFlags", wintypes.DWORD),
        ("time", wintypes.DWORD),
        ("dwExtraInfo", ctypes.POINTER(ctypes.c_ulong)),
    ]


class KEYBDINPUT(ctypes.Structure):
    _fields_ = [
        ("wVk", wintypes.WORD),
        ("wScan", wintypes.WORD),
        ("dwFlags", wintypes.DWORD),
        ("time", wintypes.DWORD),
        ("dwExtraInfo", ctypes.POINTER(ctypes.c_ulong)),
    ]


class HARDWAREINPUT(ctypes.Structure):
    _fields_ = [
        ("uMsg", wintypes.DWORD),
        ("wParamL", wintypes.WORD),
        ("wParamH", wintypes.WORD),
    ]


class INPUT_UNION(ctypes.Union):
    _fields_ = [
        ("mi", MOUSEINPUT),
        ("ki", KEYBDINPUT),
        ("hi", HARDWAREINPUT),
    ]


class INPUT(ctypes.Structure):
    _fields_ = [
        ("type", wintypes.DWORD),
        ("union", INPUT_UNION),
    ]


@dataclass
class MouseState:
    """Current mouse button state"""
    left: bool = False
    right: bool = False
    middle: bool = False
    x1: bool = False  # Back button
    x2: bool = False  # Forward button


# ============================================================================
# Arduino Mouse Controller
# ============================================================================

def find_arduino_port() -> Optional[str]:
    """Auto-detect Arduino Leonardo port."""
    if not SERIAL_AVAILABLE:
        return None
    
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
        if "arduino" in desc or "leonardo" in desc or "superlight" in desc.lower():
            return port.device
    
    return None


class ArduinoMouse:
    """Arduino Leonardo HID mouse controller with micro-humanization."""
    
    def __init__(self, port: Optional[str] = None, baudrate: int = 115200):
        self.port = port
        self.baudrate = baudrate
        self.serial: Optional['serial.Serial'] = None
        self.connected = False
        
        # Sub-pixel accumulator
        self.accum_x = 0.0
        self.accum_y = 0.0
        
        # State
        self.humanization_enabled = True
        self.jitter_intensity = 30
        self.tremor_amplitude = 15
        
        # Thread safety
        self._lock = threading.Lock()
        
        # Stats
        self.moves_sent = 0
        self.last_latency_ms = 0.0
        
        # Background flush thread
        self._flush_thread: Optional[threading.Thread] = None
        self._flush_running = False
    
    def connect(self, timeout: float = 2.0) -> bool:
        """Connect to Arduino."""
        if not SERIAL_AVAILABLE:
            print("Error: pyserial not installed")
            return False
        
        try:
            # Auto-detect port if not specified
            if not self.port:
                self.port = find_arduino_port()
                if self.port is None:
                    print("Error: No Arduino found")
                    return False
            
            # Open serial connection with SHORT timeouts for responsiveness
            self.serial = serial.Serial(
                port=self.port,
                baudrate=self.baudrate,
                timeout=0.05,  # 50ms read timeout (short!)
                write_timeout=0.05  # 50ms write timeout
            )
            
            # Wait for Arduino reset
            time.sleep(0.3)
            
            # Clear buffers
            self.serial.reset_input_buffer()
            self.serial.reset_output_buffer()
            
            # Verify connection with ping
            if self._ping():
                self.connected = True
                
                # Start background buffer manager
                self._start_buffer_manager()
                
                print(f"Arduino connected on {self.port}")
                return True
            else:
                self.serial.close()
                print("Error: Arduino did not respond")
                return False
                
        except Exception as e:
            print(f"Arduino connection error: {e}")
            return False
    
    def _start_buffer_manager(self):
        """Start background thread to manage serial buffers."""
        self._flush_running = True
        self._flush_thread = threading.Thread(target=self._buffer_manager_loop, daemon=True)
        self._flush_thread.start()
    
    def _buffer_manager_loop(self):
        """Background loop to periodically flush serial buffers."""
        while self._flush_running and self.connected:
            try:
                if self.serial and self.serial.is_open:
                    # Clear any responses we haven't read (prevent buffer overflow)
                    if self.serial.in_waiting > 0:
                        self.serial.reset_input_buffer()
                    # Flush output
                    self.serial.flush()
            except:
                pass
            time.sleep(0.05)  # Every 50ms
    
    def disconnect(self):
        """Disconnect from Arduino."""
        self._flush_running = False
        self.connected = False
        
        if self._flush_thread:
            self._flush_thread.join(timeout=0.2)
            self._flush_thread = None
        
        if self.serial and self.serial.is_open:
            try:
                self.serial.close()
            except:
                pass
        self.serial = None
    
    def _ping(self) -> bool:
        """Send ping and check for response."""
        try:
            response = self._send_command("?")
            return response is not None and "OK" in response
        except:
            return False
    
    def _send_command(self, cmd: str) -> Optional[str]:
        """Send command to Arduino and get response (blocking - use sparingly!)."""
        if not self.serial or not self.serial.is_open:
            return None
        
        with self._lock:
            try:
                self.serial.write(f"{cmd}\n".encode())
                self.serial.flush()
                
                start = time.perf_counter()
                response = self.serial.readline().decode().strip()
                self.last_latency_ms = (time.perf_counter() - start) * 1000
                
                return response if response else None
            except:
                return None
    
    def _send_fast(self, cmd: str):
        """Send command WITHOUT waiting for response (non-blocking, fast!)."""
        if not self.serial or not self.serial.is_open:
            return
        
        with self._lock:
            try:
                self.serial.write(f"{cmd}\n".encode())
                # NO flush, NO readline - fire and forget!
                self.moves_sent += 1
            except:
                pass
    
    def move(self, dx: float, dy: float):
        """Move mouse by relative amount (non-blocking)."""
        if not self.connected:
            return
        
        # Sub-pixel accumulation
        self.accum_x += dx
        self.accum_y += dy
        
        # Only send if meaningful movement
        if abs(self.accum_x) >= 0.5 or abs(self.accum_y) >= 0.5:
            self._send_fast(f"M,{self.accum_x:.2f},{self.accum_y:.2f}")
            self.accum_x -= int(self.accum_x)
            self.accum_y -= int(self.accum_y)
    
    def click(self, button: str = "left"):
        """Click mouse button (non-blocking for speed!)."""
        if not self.connected:
            return
        btn = {"left": "L", "right": "R", "middle": "M"}.get(button.lower(), "L")
        self._send_fast(f"C,{btn}")  # Fire and forget!
    
    def press(self, button: str = "left"):
        """Press and hold mouse button (non-blocking)."""
        if not self.connected:
            return
        btn = {"left": "L", "right": "R", "middle": "M"}.get(button.lower(), "L")
        self._send_fast(f"P,{btn}")
    
    def release(self, button: str = "left"):
        """Release mouse button (non-blocking)."""
        if not self.connected:
            return
        btn = {"left": "L", "right": "R", "middle": "M"}.get(button.lower(), "L")
        self._send_fast(f"R,{btn}")
    
    def set_humanization(self, jitter: int = 30, tremor: int = 15, enabled: bool = True):
        """Configure humanization settings."""
        self.jitter_intensity = max(0, min(100, jitter))
        self.tremor_amplitude = max(0, min(100, tremor))
        self.humanization_enabled = enabled
        
        if self.connected:
            self._send_command(f"H,{self.jitter_intensity},{self.tremor_amplitude},{1 if enabled else 0}")
    
    def reset(self):
        """Reset state."""
        self.accum_x = 0.0
        self.accum_y = 0.0
        if self.connected:
            self._send_command("X")
    
    @property
    def is_connected(self) -> bool:
        return self.connected and self.serial is not None and self.serial.is_open


# ============================================================================
# Unified Mouse Controller
# ============================================================================

class MouseController:
    """
    Unified mouse controller supporting:
    - Internal (Windows SendInput API)
    - Arduino (Hardware HID via serial)
    """
    
    def __init__(self, device: str = "internal"):
        """
        Initialize mouse controller.
        
        Args:
            device: "internal" for SendInput, "arduino" for hardware mouse
        """
        self._device_mode = device
        
        # Windows API (for internal mode)
        self._user32 = ctypes.windll.user32
        self._kernel32 = ctypes.windll.kernel32
        
        # Extra info pointer (required for some games)
        self._extra = ctypes.c_ulong(0)
        
        # Movement accumulator for sub-pixel precision
        self._accumulated_x: float = 0.0
        self._accumulated_y: float = 0.0
        
        # Rate limiting
        self._last_move_time: float = 0.0
        self._min_move_interval: float = 0.001  # 1ms minimum between moves
        
        # Lock for thread safety
        self._lock = threading.Lock()
        
        # State tracking
        self._state = MouseState()
        
        # Sensitivity normalization
        self.sens_multiplier: float = 1.0
        self.dpi_value: int = 800
        self.in_game_sens: float = 0.41
        self.reference_sens: float = 0.70
        self.normalization_enabled: bool = True
        
        # Arduino controller (lazy init)
        self._arduino: Optional[ArduinoMouse] = None
        self._arduino_port: str = ""
        self._arduino_jitter: int = 30
        self._arduino_tremor: int = 15
        self._arduino_humanization: bool = True
    
    def set_device(self, device: str, port: str = "", jitter: int = 30, 
                   tremor: int = 15, humanization: bool = True):
        """
        Set mouse device mode.
        
        Args:
            device: "internal" or "arduino"
            port: COM port for arduino (auto-detect if empty)
            jitter: Arduino jitter intensity 0-100
            tremor: Arduino tremor intensity 0-100
            humanization: Enable Arduino micro-humanization
        """
        self._device_mode = device
        self._arduino_port = port
        self._arduino_jitter = jitter
        self._arduino_tremor = tremor
        self._arduino_humanization = humanization
        
        if device == "arduino":
            self._init_arduino()
        elif self._arduino:
            self._arduino.disconnect()
            self._arduino = None
    
    def _init_arduino(self):
        """Initialize Arduino connection."""
        if self._arduino and self._arduino.is_connected:
            return  # Already connected
        
        self._arduino = ArduinoMouse(port=self._arduino_port or None)
        if self._arduino.connect():
            # Configure humanization
            self._arduino.set_humanization(
                jitter=self._arduino_jitter,
                tremor=self._arduino_tremor,
                enabled=self._arduino_humanization
            )
            print(f"Arduino mode active (jitter={self._arduino_jitter}, tremor={self._arduino_tremor})")
        else:
            print("Failed to connect to Arduino, falling back to internal")
            self._arduino = None
            self._device_mode = "internal"
    
    @property
    def device_mode(self) -> str:
        """Get current device mode."""
        return self._device_mode
    
    @property
    def arduino_connected(self) -> bool:
        """Check if Arduino is connected."""
        return self._arduino is not None and self._arduino.is_connected
    
    def _send_input(self, input_struct: INPUT) -> int:
        """Send a single input event"""
        return self._user32.SendInput(1, ctypes.byref(input_struct), ctypes.sizeof(INPUT))
    
    def _create_mouse_input(self, dx: int = 0, dy: int = 0, flags: int = 0, 
                           mouse_data: int = 0) -> INPUT:
        """Create a mouse input structure"""
        mi = MOUSEINPUT(
            dx=dx,
            dy=dy,
            mouseData=mouse_data,
            dwFlags=flags,
            time=0,
            dwExtraInfo=ctypes.pointer(self._extra)
        )
        
        input_struct = INPUT()
        input_struct.type = INPUT_MOUSE
        input_struct.union.mi = mi
        
        return input_struct
    
    def move(self, dx: float, dy: float) -> bool:
        """
        Move mouse by relative amount.
        
        Uses either SendInput (internal) or Arduino based on device mode.
        
        Args:
            dx: Horizontal movement in pixels (can be fractional)
            dy: Vertical movement in pixels (can be fractional)
            
        Returns:
            True if movement was sent
        """
        # Apply sensitivity normalization
        if self.normalization_enabled:
            multiplier = self._calculate_normalization()
            dx *= multiplier
            dy *= multiplier
        
        # Apply sens multiplier
        dx *= self.sens_multiplier
        dy *= self.sens_multiplier
        
        # Route to appropriate device
        if self._device_mode == "arduino" and self._arduino and self._arduino.is_connected:
            return self._move_arduino(dx, dy)
        else:
            return self._move_internal(dx, dy)
    
    def _move_arduino(self, dx: float, dy: float) -> bool:
        """Move via Arduino."""
        if self._arduino:
            self._arduino.move(dx, dy)
            return True
        return False
    
    def _move_internal(self, dx: float, dy: float) -> bool:
        """Move via Windows SendInput."""
        with self._lock:
            # Accumulate fractional movement for sub-pixel precision
            self._accumulated_x += dx
            self._accumulated_y += dy
            
            # Get integer movement
            move_x = int(self._accumulated_x)
            move_y = int(self._accumulated_y)
            
            # Keep fractional remainder
            self._accumulated_x -= move_x
            self._accumulated_y -= move_y
            
            # Skip if no integer movement
            if move_x == 0 and move_y == 0:
                return False
            
            # Rate limiting
            now = time.perf_counter()
            if now - self._last_move_time < self._min_move_interval:
                return False
            self._last_move_time = now
            
            # Send move
            input_struct = self._create_mouse_input(
                dx=move_x,
                dy=move_y,
                flags=MOUSEEVENTF_MOVE
            )
            
            result = self._send_input(input_struct)
            return result > 0
    
    def move_smooth(self, dx: float, dy: float, smooth_x: float, smooth_y: float) -> Tuple[float, float]:
        """
        Move mouse with smoothing applied
        
        Args:
            dx: Target horizontal movement
            dy: Target vertical movement
            smooth_x: Horizontal smoothing factor (higher = slower)
            smooth_y: Vertical smoothing factor (higher = slower)
            
        Returns:
            Tuple of (actual_dx, actual_dy) that was moved
        """
        # Apply smoothing (divide by smooth factor)
        smooth_x = max(1.0, smooth_x)
        smooth_y = max(1.0, smooth_y)
        
        actual_dx = dx / smooth_x
        actual_dy = dy / smooth_y
        
        self.move(actual_dx, actual_dy)
        
        return (actual_dx, actual_dy)
    
    def click(self, button: str = "left"):
        """
        Perform a mouse click.
        
        Uses Arduino for left/right/middle clicks when in arduino mode.
        X1/X2 buttons always use SendInput (Arduino doesn't have side buttons).
        
        Args:
            button: "left", "right", "middle", "x1" (back), "x2" (forward)
        """
        # Arduino can only do left/right/middle clicks
        if (self._device_mode == "arduino" and self._arduino and 
            self._arduino.is_connected and button.lower() in ("left", "right", "middle")):
            self._arduino.click(button)
            return
        
        # Internal SendInput for all buttons
        import random
        down_flag, up_flag, mouse_data = self._get_button_flags(button)
        
        # Press
        input_down = self._create_mouse_input(
            flags=down_flag,
            mouse_data=mouse_data
        )
        self._send_input(input_down)
        
        # Realistic one-tap hold: 8-20ms (fast click)
        hold_time = random.uniform(0.008, 0.020)
        time.sleep(hold_time)
        
        # Release
        input_up = self._create_mouse_input(
            flags=up_flag,
            mouse_data=mouse_data
        )
        self._send_input(input_up)
    
    def press(self, button: str = "left"):
        """Press and hold a mouse button."""
        # Arduino for basic buttons
        if (self._device_mode == "arduino" and self._arduino and 
            self._arduino.is_connected and button.lower() in ("left", "right", "middle")):
            self._arduino.press(button)
            self._update_state(button, True)
            return
        
        # Internal
        down_flag, _, mouse_data = self._get_button_flags(button)
        
        input_struct = self._create_mouse_input(
            flags=down_flag,
            mouse_data=mouse_data
        )
        self._send_input(input_struct)
        
        self._update_state(button, True)
    
    def release(self, button: str = "left"):
        """Release a mouse button."""
        # Arduino for basic buttons
        if (self._device_mode == "arduino" and self._arduino and 
            self._arduino.is_connected and button.lower() in ("left", "right", "middle")):
            self._arduino.release(button)
            self._update_state(button, False)
            return
        
        # Internal
        _, up_flag, mouse_data = self._get_button_flags(button)
        
        input_struct = self._create_mouse_input(
            flags=up_flag,
            mouse_data=mouse_data
        )
        self._send_input(input_struct)
        
        self._update_state(button, False)
    
    def _get_button_flags(self, button: str) -> Tuple[int, int, int]:
        """Get Windows flags for a button"""
        buttons = {
            "left": (MOUSEEVENTF_LEFTDOWN, MOUSEEVENTF_LEFTUP, 0),
            "right": (MOUSEEVENTF_RIGHTDOWN, MOUSEEVENTF_RIGHTUP, 0),
            "middle": (MOUSEEVENTF_MIDDLEDOWN, MOUSEEVENTF_MIDDLEUP, 0),
            "x1": (MOUSEEVENTF_XDOWN, MOUSEEVENTF_XUP, XBUTTON1),
            "x2": (MOUSEEVENTF_XDOWN, MOUSEEVENTF_XUP, XBUTTON2),
            "back": (MOUSEEVENTF_XDOWN, MOUSEEVENTF_XUP, XBUTTON1),
            "forward": (MOUSEEVENTF_XDOWN, MOUSEEVENTF_XUP, XBUTTON2),
        }
        return buttons.get(button.lower(), buttons["left"])
    
    def _update_state(self, button: str, pressed: bool):
        """Update internal button state"""
        button = button.lower()
        if button == "left":
            self._state.left = pressed
        elif button == "right":
            self._state.right = pressed
        elif button == "middle":
            self._state.middle = pressed
        elif button in ("x1", "back"):
            self._state.x1 = pressed
        elif button in ("x2", "forward"):
            self._state.x2 = pressed
    
    def _calculate_normalization(self) -> float:
        """
        Calculate sensitivity normalization multiplier
        
        This ensures consistent aim feel regardless of DPI/sensitivity
        """
        if not self.normalization_enabled:
            return 1.0
        
        # Calculate eDPI (effective DPI)
        edpi = self.dpi_value * self.in_game_sens
        reference_edpi = self.dpi_value * self.reference_sens
        
        # Normalization ratio
        if edpi > 0:
            return reference_edpi / edpi
        return 1.0
    
    def set_sensitivity(self, dpi: int, in_game: float, reference: float):
        """Set sensitivity normalization values"""
        self.dpi_value = dpi
        self.in_game_sens = in_game
        self.reference_sens = reference
    
    def reset_accumulator(self):
        """Reset fractional movement accumulator"""
        with self._lock:
            self._accumulated_x = 0.0
            self._accumulated_y = 0.0
    
    @property
    def state(self) -> MouseState:
        """Get current mouse button state"""
        return self._state
    
    def is_button_pressed(self, button: str) -> bool:
        """Check if a button is currently pressed"""
        button = button.lower()
        if button == "left":
            return self._state.left
        elif button == "right":
            return self._state.right
        elif button == "middle":
            return self._state.middle
        elif button in ("x1", "back"):
            return self._state.x1
        elif button in ("x2", "forward"):
            return self._state.x2
        return False


# Global instance
_mouse_controller: Optional[MouseController] = None


def get_mouse_controller() -> MouseController:
    """Get the global mouse controller instance."""
    global _mouse_controller
    if _mouse_controller is None:
        _mouse_controller = MouseController()
    return _mouse_controller


def configure_mouse_controller(device: str = "internal", port: str = "",
                               jitter: int = 30, tremor: int = 15,
                               humanization: bool = True) -> MouseController:
    """
    Configure the global mouse controller.
    
    Args:
        device: "internal" for SendInput, "arduino" for hardware HID
        port: COM port for Arduino (auto-detect if empty)
        jitter: Arduino jitter intensity (0-100)
        tremor: Arduino tremor intensity (0-100)
        humanization: Enable Arduino micro-humanization
        
    Returns:
        Configured MouseController instance
    """
    global _mouse_controller
    if _mouse_controller is None:
        _mouse_controller = MouseController()
    
    _mouse_controller.set_device(device, port, jitter, tremor, humanization)
    return _mouse_controller


def cleanup_mouse_controller():
    """Cleanup mouse controller (disconnect Arduino if connected)."""
    global _mouse_controller
    if _mouse_controller and _mouse_controller._arduino:
        _mouse_controller._arduino.disconnect()
    _mouse_controller = None


def list_arduino_ports() -> list:
    """List available Arduino-compatible serial ports."""
    if not SERIAL_AVAILABLE:
        return []
    
    ports = serial.tools.list_ports.comports()
    result = []
    
    for port in ports:
        info = {
            "port": port.device,
            "description": port.description,
            "vid": f"{port.vid:04X}" if port.vid else "N/A",
            "pid": f"{port.pid:04X}" if port.pid else "N/A",
        }
        result.append(info)
    
    return result
