"""
Humanizer Module
Implements various algorithms to make mouse movement appear natural and human-like
"""

import math
import random
import time
from typing import List, Tuple, Optional, Generator
from dataclasses import dataclass


@dataclass
class MovementPoint:
    """A point along a humanized movement path"""
    x: float
    y: float
    delay_ms: float = 0  # Delay before this point


class Humanizer:
    """
    Humanizes mouse movement to appear natural and human-like
    Implements multiple algorithms that can be combined
    """
    
    def __init__(self):
        """Initialize humanizer with default settings"""
        # WindMouse settings
        self.wind_mouse_enabled = False
        self.min_gravity = 5.0
        self.max_gravity = 12.0
        self.min_wind = 5.0
        self.max_wind = 16.0
        self.min_speed = 15.0
        self.max_speed = 25.0
        self.min_damp = 1.0
        self.max_damp = 2.0
        
        # Momentum tracking
        self.momentum_enabled = False
        self.momentum_decay = 0.88
        self.momentum_lead_bias = 1.18
        self.momentum_deadzone = 4.0
        self.momentum_corr_prob = 0.52
        self.momentum_corr_str = 0.42
        self._momentum_x = 0.0
        self._momentum_y = 0.0
        
        # Stop/Pause system
        self.stop_pause_enabled = True
        self.stop_pause_chance = 0.002
        self.stop_pause_min_ms = 1.0
        self.stop_pause_max_ms = 120.0
        
        # Pattern masking (micro-jitter)
        self.pattern_masking_enabled = False
        self.pattern_masking_intensity = 1.0
        self.pattern_masking_scale = 1.0
        
        # Sub-movement decomposition
        self.sub_movements_enabled = False
        self.sub_movements_min_pause = 50.0
        self.sub_movements_max_pause = 150.0
        self.sub_movements_min_dist = 30.0
        self.sub_movements_chance = 0.35
        
        # Proximity pause
        self.proximity_pause_enabled = False
        self.proximity_threshold = 15
        self.proximity_chance = 0.27
        self.proximity_min_pause = 50.0
        self.proximity_max_pause = 150.0
        self.proximity_cooldown = 300.0
        self._last_proximity_pause = 0.0
        
        # Easing system
        self.ease_out = 80.0
        self.ease_in = 80.0
        self.ease_curve = 3.0
        
        # Entropy-aware humanization
        self.speed_variance_enabled = True
        self.speed_variance_min = 0.46
        self.speed_variance_max = 0.90
        self.speed_variance_freq_min = 0.09
        self.speed_variance_freq_max = 0.30
        
        self.path_curvature_enabled = True
        self.path_curvature_min = 1.1
        self.path_curvature_max = 3.0
        self.path_curvature_freq_min = 0.04
        self.path_curvature_freq_max = 0.28
        
        self.endpoint_settling_enabled = False
        self.endpoint_settling_dist = 9.0
        self.endpoint_settling_intensity = 2.5
        
        # Internal state
        self._noise_phase = random.random() * 2 * math.pi
    
    def humanize_movement(self, dx: float, dy: float, 
                         smooth_x: float, smooth_y: float) -> Tuple[float, float]:
        """
        Apply humanization to a single movement step
        
        Args:
            dx: Raw horizontal movement
            dy: Raw vertical movement
            smooth_x: Horizontal smoothing factor
            smooth_y: Vertical smoothing factor
            
        Returns:
            Tuple of (humanized_dx, humanized_dy)
        """
        # Start with base smoothing
        h_dx = dx / max(1.0, smooth_x)
        h_dy = dy / max(1.0, smooth_y)
        
        # Apply momentum tracking
        if self.momentum_enabled:
            h_dx, h_dy = self._apply_momentum(h_dx, h_dy)
        
        # Apply pattern masking (micro-jitter)
        if self.pattern_masking_enabled:
            h_dx, h_dy = self._apply_pattern_masking(h_dx, h_dy)
        
        # Apply speed variance (entropy)
        if self.speed_variance_enabled:
            h_dx, h_dy = self._apply_speed_variance(h_dx, h_dy)
        
        # Apply path curvature
        if self.path_curvature_enabled:
            h_dx, h_dy = self._apply_path_curvature(h_dx, h_dy, dx, dy)
        
        return (h_dx, h_dy)
    
    def generate_wind_mouse_path(self, start_x: float, start_y: float,
                                  dest_x: float, dest_y: float) -> List[MovementPoint]:
        """
        Generate a complete WindMouse path from start to destination
        
        The WindMouse algorithm simulates mouse movement as a physical object
        affected by gravity (pull toward target) and wind (random perturbation)
        
        Args:
            start_x, start_y: Starting position
            dest_x, dest_y: Destination position
            
        Returns:
            List of MovementPoints along the path
        """
        if not self.wind_mouse_enabled:
            return [MovementPoint(dest_x, dest_y, 0)]
        
        # Random parameters within configured ranges
        gravity = random.uniform(self.min_gravity, self.max_gravity)
        wind = random.uniform(self.min_wind, self.max_wind)
        min_speed = self.min_speed
        max_speed = self.max_speed
        damp = random.uniform(self.min_damp, self.max_damp)
        
        points = []
        
        current_x = start_x
        current_y = start_y
        velocity_x = 0.0
        velocity_y = 0.0
        wind_x = 0.0
        wind_y = 0.0
        
        distance = math.hypot(dest_x - start_x, dest_y - start_y)
        target_area = max(10.0, distance / 10.0)
        
        while True:
            # Calculate distance to target
            dist = math.hypot(dest_x - current_x, dest_y - current_y)
            
            if dist < 1:
                break
            
            # Apply wind force (random perturbation)
            wind_x = wind_x / math.sqrt(3) + (random.random() * (wind * 2 + 1) - wind) / math.sqrt(5)
            wind_y = wind_y / math.sqrt(3) + (random.random() * (wind * 2 + 1) - wind) / math.sqrt(5)
            
            # Apply gravity force (pull toward target)
            if dist < target_area:
                # Closer to target: stronger gravity, less wind
                gravity_factor = gravity * (dist / target_area)
                wind_x /= damp
                wind_y /= damp
            else:
                gravity_factor = gravity
            
            # Direction to target
            dir_x = (dest_x - current_x) / dist
            dir_y = (dest_y - current_y) / dist
            
            # Update velocity
            velocity_x += wind_x + gravity_factor * dir_x
            velocity_y += wind_y + gravity_factor * dir_y
            
            # Clamp speed
            speed = math.hypot(velocity_x, velocity_y)
            if speed > max_speed:
                velocity_x = (velocity_x / speed) * max_speed
                velocity_y = (velocity_y / speed) * max_speed
            elif speed < min_speed and dist > target_area:
                velocity_x = (velocity_x / speed) * min_speed
                velocity_y = (velocity_y / speed) * min_speed
            
            # Move
            current_x += velocity_x
            current_y += velocity_y
            
            # Add point with small delay
            delay = random.uniform(0.5, 2.0)
            points.append(MovementPoint(current_x, current_y, delay))
            
            # Limit iterations
            if len(points) > 1000:
                break
        
        # Ensure we end exactly at destination
        points.append(MovementPoint(dest_x, dest_y, 0))
        
        return points
    
    def should_pause(self) -> Optional[float]:
        """
        Check if a random pause should occur
        
        Returns:
            Pause duration in ms, or None if no pause
        """
        if not self.stop_pause_enabled:
            return None
        
        if random.random() < self.stop_pause_chance:
            return random.uniform(self.stop_pause_min_ms, self.stop_pause_max_ms)
        
        return None
    
    def should_proximity_pause(self, distance: float) -> Optional[float]:
        """
        Check if a proximity pause should occur (near target)
        
        Args:
            distance: Distance to target in pixels
            
        Returns:
            Pause duration in ms, or None if no pause
        """
        if not self.proximity_pause_enabled:
            return None
        
        # Check cooldown
        now = time.time() * 1000
        if now - self._last_proximity_pause < self.proximity_cooldown:
            return None
        
        # Check if within threshold
        if distance > self.proximity_threshold:
            return None
        
        # Random chance
        if random.random() < self.proximity_chance:
            self._last_proximity_pause = now
            return random.uniform(self.proximity_min_pause, self.proximity_max_pause)
        
        return None
    
    def decompose_movement(self, dx: float, dy: float) -> List[Tuple[float, float, float]]:
        """
        Decompose a large movement into smaller sub-movements
        
        Args:
            dx, dy: Total movement to decompose
            
        Returns:
            List of (sub_dx, sub_dy, delay_ms) tuples
        """
        distance = math.hypot(dx, dy)
        
        if not self.sub_movements_enabled or distance < self.sub_movements_min_dist:
            return [(dx, dy, 0)]
        
        if random.random() > self.sub_movements_chance:
            return [(dx, dy, 0)]
        
        # Decompose into 2-4 segments
        num_segments = random.randint(2, 4)
        segments = []
        
        remaining_x = dx
        remaining_y = dy
        
        for i in range(num_segments - 1):
            # Random portion of remaining
            portion = random.uniform(0.2, 0.5)
            seg_x = remaining_x * portion
            seg_y = remaining_y * portion
            
            remaining_x -= seg_x
            remaining_y -= seg_y
            
            delay = random.uniform(self.sub_movements_min_pause, self.sub_movements_max_pause)
            segments.append((seg_x, seg_y, delay))
        
        # Final segment
        segments.append((remaining_x, remaining_y, 0))
        
        return segments
    
    def apply_easing(self, progress: float, direction: str = "out") -> float:
        """
        Apply easing curve to movement progress
        
        Args:
            progress: Progress from 0.0 to 1.0
            direction: "in" for acceleration, "out" for deceleration
            
        Returns:
            Eased progress value
        """
        curve = self.ease_curve
        
        if direction == "out":
            # Ease out (decelerate)
            return 1.0 - pow(1.0 - progress, curve)
        else:
            # Ease in (accelerate)
            return pow(progress, curve)
    
    def generate_endpoint_settling(self) -> Generator[Tuple[float, float], None, None]:
        """
        Generate settling micro-movements at endpoint
        
        Yields:
            (dx, dy) micro-movements
        """
        if not self.endpoint_settling_enabled:
            return
        
        # Generate damped oscillation
        amplitude = self.endpoint_settling_intensity
        steps = int(self.endpoint_settling_dist)
        
        for i in range(steps):
            # Damped oscillation
            decay = 1.0 - (i / steps)
            angle = random.random() * 2 * math.pi
            
            dx = math.cos(angle) * amplitude * decay
            dy = math.sin(angle) * amplitude * decay
            
            yield (dx, dy)
            amplitude *= 0.7  # Decay
    
    def _apply_momentum(self, dx: float, dy: float) -> Tuple[float, float]:
        """Apply momentum-based smoothing"""
        # Decay existing momentum
        self._momentum_x *= self.momentum_decay
        self._momentum_y *= self.momentum_decay
        
        # Add new momentum
        self._momentum_x += dx * self.momentum_lead_bias
        self._momentum_y += dy * self.momentum_lead_bias
        
        # Deadzone
        if abs(self._momentum_x) < self.momentum_deadzone:
            self._momentum_x *= 0.5
        if abs(self._momentum_y) < self.momentum_deadzone:
            self._momentum_y *= 0.5
        
        # Correction
        if random.random() < self.momentum_corr_prob:
            correction_x = (dx - self._momentum_x) * self.momentum_corr_str
            correction_y = (dy - self._momentum_y) * self.momentum_corr_str
            self._momentum_x += correction_x
            self._momentum_y += correction_y
        
        return (self._momentum_x, self._momentum_y)
    
    def _apply_pattern_masking(self, dx: float, dy: float) -> Tuple[float, float]:
        """Apply micro-jitter to mask patterns"""
        intensity = self.pattern_masking_intensity * self.pattern_masking_scale
        
        jitter_x = (random.random() - 0.5) * intensity
        jitter_y = (random.random() - 0.5) * intensity
        
        return (dx + jitter_x, dy + jitter_y)
    
    def _apply_speed_variance(self, dx: float, dy: float) -> Tuple[float, float]:
        """Apply speed variance for entropy"""
        # Smooth noise using phase
        self._noise_phase += random.uniform(
            self.speed_variance_freq_min,
            self.speed_variance_freq_max
        )
        
        noise = math.sin(self._noise_phase)
        variance = self.speed_variance_min + (noise + 1) / 2 * (
            self.speed_variance_max - self.speed_variance_min
        )
        
        return (dx * variance, dy * variance)
    
    def _apply_path_curvature(self, dx: float, dy: float,
                               raw_dx: float, raw_dy: float) -> Tuple[float, float]:
        """Apply sinusoidal curvature perpendicular to movement"""
        if abs(raw_dx) < 0.1 and abs(raw_dy) < 0.1:
            return (dx, dy)
        
        # Perpendicular direction
        length = math.hypot(raw_dx, raw_dy)
        perp_x = -raw_dy / length
        perp_y = raw_dx / length
        
        # Sinusoidal offset
        freq = random.uniform(self.path_curvature_freq_min, self.path_curvature_freq_max)
        amplitude = random.uniform(self.path_curvature_min, self.path_curvature_max)
        
        offset = math.sin(time.time() * freq * 100) * amplitude
        
        return (dx + perp_x * offset, dy + perp_y * offset)
    
    def reset(self):
        """Reset internal state"""
        self._momentum_x = 0.0
        self._momentum_y = 0.0
        self._noise_phase = random.random() * 2 * math.pi
        self._last_proximity_pause = 0.0
    
    def load_from_config(self, hum_config):
        """
        Load all settings from a HumanizerConfig or FlickHumanizerConfig
        
        Args:
            hum_config: HumanizerConfig or FlickHumanizerConfig instance
        """
        # WindMouse
        self.wind_mouse_enabled = hum_config.wind_mouse.enabled
        self.min_gravity = hum_config.wind_mouse.min_gravity
        self.max_gravity = hum_config.wind_mouse.max_gravity
        self.min_wind = hum_config.wind_mouse.min_wind
        self.max_wind = hum_config.wind_mouse.max_wind
        self.min_speed = hum_config.wind_mouse.min_speed
        self.max_speed = hum_config.wind_mouse.max_speed
        self.min_damp = hum_config.wind_mouse.min_damp
        self.max_damp = hum_config.wind_mouse.max_damp
        
        # Momentum tracking
        self.momentum_enabled = hum_config.momentum_tracking
        self.momentum_decay = hum_config.momentum_decay
        self.momentum_lead_bias = hum_config.momentum_lead_bias
        self.momentum_deadzone = hum_config.momentum_deadzone
        self.momentum_corr_prob = hum_config.momentum_corr_prob
        self.momentum_corr_str = hum_config.momentum_corr_str
        
        # Stop/Pause system
        self.stop_pause_enabled = hum_config.stop_pause_enabled
        self.stop_pause_chance = hum_config.stop_pause_chance
        self.stop_pause_min_ms = hum_config.stop_pause_min
        self.stop_pause_max_ms = hum_config.stop_pause_max
        
        # Pattern masking
        self.pattern_masking_enabled = hum_config.pattern_masking_enabled
        self.pattern_masking_intensity = hum_config.pattern_masking_intensity
        self.pattern_masking_scale = hum_config.pattern_masking_scale
        
        # Sub-movement decomposition
        self.sub_movements_enabled = hum_config.sub_movements_enabled
        self.sub_movements_min_pause = hum_config.sub_movements_min_pause
        self.sub_movements_max_pause = hum_config.sub_movements_max_pause
        self.sub_movements_min_dist = hum_config.sub_movements_min_dist
        self.sub_movements_chance = hum_config.sub_movements_chance
        
        # Proximity pause
        self.proximity_pause_enabled = hum_config.proximity_pause_enabled
        self.proximity_threshold = hum_config.proximity_threshold
        self.proximity_chance = hum_config.proximity_chance
        self.proximity_min_pause = hum_config.proximity_min_pause
        self.proximity_max_pause = hum_config.proximity_max_pause
        self.proximity_cooldown = hum_config.proximity_cooldown
        
        # Easing system
        self.ease_out = hum_config.ease_out
        self.ease_in = hum_config.ease_in
        self.ease_curve = hum_config.ease_curve
        
        # Entropy-aware humanization
        self.speed_variance_enabled = hum_config.speed_variance_enabled
        self.speed_variance_min = hum_config.speed_variance_min
        self.speed_variance_max = hum_config.speed_variance_max
        self.speed_variance_freq_min = hum_config.speed_variance_freq_min
        self.speed_variance_freq_max = hum_config.speed_variance_freq_max
        
        self.path_curvature_enabled = hum_config.path_curvature_enabled
        self.path_curvature_min = hum_config.path_curvature_min
        self.path_curvature_max = hum_config.path_curvature_max
        self.path_curvature_freq_min = hum_config.path_curvature_freq_min
        self.path_curvature_freq_max = hum_config.path_curvature_freq_max
        
        self.endpoint_settling_enabled = hum_config.endpoint_settling_enabled
        self.endpoint_settling_dist = hum_config.endpoint_settling_dist
        self.endpoint_settling_intensity = hum_config.endpoint_settling_intensity
