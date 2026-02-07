"""
Starlink Serial Protocol
Command definitions and helpers
"""

from dataclasses import dataclass
from enum import Enum
from typing import Optional, Tuple


class CommandType(Enum):
    """Available command types"""
    MOVE = "M"
    CLICK = "C"
    PRESS = "P"
    RELEASE = "R"
    JITTER = "J"
    JITTER_ENABLE = "E"
    PING = "?"
    VERSION = "V"
    STATUS = "S"


@dataclass
class MoveCommand:
    """Mouse movement command"""
    dx: float
    dy: float
    
    def to_string(self) -> str:
        return f"M,{self.dx:.2f},{self.dy:.2f}"


@dataclass
class ButtonCommand:
    """Mouse button command"""
    action: str  # "click", "press", "release"
    button: str  # "L", "R", "M"
    
    def to_string(self) -> str:
        action_char = {"click": "C", "press": "P", "release": "R"}.get(self.action, "C")
        return f"{action_char},{self.button}"


@dataclass
class JitterCommand:
    """Jitter configuration command"""
    intensity: float  # 0.0 - 2.0
    enabled: bool
    
    def to_string(self) -> str:
        int_val = int(max(0, min(200, self.intensity * 100)))
        return f"J,{int_val}"


def parse_response(response: str) -> Tuple[str, Optional[str]]:
    """
    Parse Arduino response
    
    Args:
        response: Raw response string
        
    Returns:
        Tuple of (type, value) or (type, None)
    """
    response = response.strip()
    
    if ":" in response:
        parts = response.split(":", 1)
        return (parts[0], parts[1] if len(parts) > 1 else None)
    
    return (response, None)


def validate_port(port: str) -> bool:
    """Check if port string is valid"""
    if not port:
        return False
    
    # Windows COM port
    if port.upper().startswith("COM"):
        try:
            num = int(port[3:])
            return 1 <= num <= 256
        except ValueError:
            return False
    
    # Linux/Mac
    if port.startswith("/dev/"):
        return True
    
    return False
