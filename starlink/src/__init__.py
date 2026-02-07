"""
Starlink - Arduino Leonardo HID Mouse Controller
Hardware-level mouse input with humanization
"""

from .controller import ArduinoMouseController, find_arduino_port

__version__ = "1.0.0"
__all__ = ["ArduinoMouseController", "find_arduino_port"]
