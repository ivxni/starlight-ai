"""
PID Controller for smooth aim stabilization
"""

import time
from dataclasses import dataclass


@dataclass
class PIDState:
    """PID controller state"""
    last_error_x: float = 0.0
    last_error_y: float = 0.0
    integral_x: float = 0.0
    integral_y: float = 0.0
    last_time: float = 0.0


class PIDController:
    """
    PID Controller for aim stabilization
    Reduces jitter and provides smooth, stable aim movements
    """
    
    def __init__(self, kp: float = 0.0002, ki: float = 0.0, kd: float = 0.0006,
                 activation_distance: int = 10):
        """
        Initialize PID controller
        
        Args:
            kp: Proportional gain (responsiveness)
            ki: Integral gain (steady-state error correction)
            kd: Derivative gain (damping/smoothing)
            activation_distance: Distance at which PID engages (pixels)
        """
        self.kp = kp
        self.ki = ki
        self.kd = kd
        self.activation_distance = activation_distance
        
        self._state = PIDState()
        self._enabled = True
        
        # Integral windup prevention
        self._integral_max = 100.0
    
    def update(self, error_x: float, error_y: float) -> tuple:
        """
        Calculate PID output for given error
        
        Args:
            error_x: Horizontal distance to target
            error_y: Vertical distance to target
            
        Returns:
            (correction_x, correction_y) - Additional smoothing factors
        """
        if not self._enabled:
            return (0.0, 0.0)
        
        # Check if within activation distance
        distance = (error_x ** 2 + error_y ** 2) ** 0.5
        if distance > self.activation_distance:
            # Reset state when far from target
            self._state = PIDState()
            return (0.0, 0.0)
        
        current_time = time.perf_counter()
        dt = current_time - self._state.last_time if self._state.last_time > 0 else 0.016
        dt = max(0.001, min(0.1, dt))  # Clamp dt
        
        # Proportional
        p_x = self.kp * error_x
        p_y = self.kp * error_y
        
        # Integral (with windup prevention)
        self._state.integral_x += error_x * dt
        self._state.integral_y += error_y * dt
        self._state.integral_x = max(-self._integral_max, min(self._integral_max, self._state.integral_x))
        self._state.integral_y = max(-self._integral_max, min(self._integral_max, self._state.integral_y))
        
        i_x = self.ki * self._state.integral_x
        i_y = self.ki * self._state.integral_y
        
        # Derivative
        d_x = self.kd * (error_x - self._state.last_error_x) / dt if dt > 0 else 0
        d_y = self.kd * (error_y - self._state.last_error_y) / dt if dt > 0 else 0
        
        # Store state for next iteration
        self._state.last_error_x = error_x
        self._state.last_error_y = error_y
        self._state.last_time = current_time
        
        # Combined PID output
        output_x = p_x + i_x + d_x
        output_y = p_y + i_y + d_y
        
        return (output_x, output_y)
    
    def reset(self):
        """Reset PID state"""
        self._state = PIDState()
    
    def set_gains(self, kp: float, ki: float, kd: float):
        """Update PID gains"""
        self.kp = kp
        self.ki = ki
        self.kd = kd
    
    @property
    def enabled(self) -> bool:
        return self._enabled
    
    @enabled.setter
    def enabled(self, value: bool):
        self._enabled = value
        if not value:
            self.reset()
