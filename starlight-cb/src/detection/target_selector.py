"""
Target Selection Module
Selects the best target from detections based on various criteria
"""

import math
from typing import Optional, List, Tuple
from dataclasses import dataclass
from .detection import Detection


@dataclass
class Target:
    """Selected target with aim point"""
    detection: Detection
    aim_x: float
    aim_y: float
    distance_to_crosshair: float
    priority: float
    
    @property
    def center(self) -> Tuple[float, float]:
        return (self.aim_x, self.aim_y)


class TargetSelector:
    """
    Selects the best target from a list of detections
    Uses configurable criteria like distance to crosshair, FOV, and class priority
    """
    
    def __init__(self, frame_width: int, frame_height: int):
        """
        Initialize target selector
        
        Args:
            frame_width: Width of the capture frame
            frame_height: Height of the capture frame
        """
        self.frame_width = frame_width
        self.frame_height = frame_height
        
        # Crosshair is at frame center
        self.crosshair_x = frame_width / 2
        self.crosshair_y = frame_height / 2
        
        # Configuration
        self.aim_fov = 25  # FOV radius in pixels
        self.aim_bone = "upper_head"
        self.bone_scale = 1.0
        
        # Class filtering
        self.enabled_classes: List[int] = [0, 1, 2, 3]
        self.disabled_classes: List[int] = []
        self.class_priorities: dict = {0: 1.0, 1: 0.9, 2: 0.8, 3: 0.7}
    
    def select_target(self, detections: List[Detection], 
                      aim_fov: Optional[int] = None) -> Optional[Target]:
        """
        Select the best target from detections
        
        Args:
            detections: List of Detection objects
            aim_fov: Override FOV radius (optional)
            
        Returns:
            Target object or None if no valid target
        """
        if not detections:
            return None
        
        fov = aim_fov if aim_fov is not None else self.aim_fov
        
        best_target: Optional[Target] = None
        best_score = float('inf')
        
        for detection in detections:
            # Check class filtering
            if not self._is_class_valid(detection.class_id):
                continue
            
            # Get aim point
            aim_x, aim_y = detection.get_aim_point(self.aim_bone, self.bone_scale)
            
            # Calculate distance to crosshair
            distance = self._distance_to_crosshair(aim_x, aim_y)
            
            # Check if within FOV
            if distance > fov:
                continue
            
            # Calculate priority score (lower is better)
            class_priority = self.class_priorities.get(detection.class_id, 1.0)
            score = distance / class_priority
            
            if score < best_score:
                best_score = score
                best_target = Target(
                    detection=detection,
                    aim_x=aim_x,
                    aim_y=aim_y,
                    distance_to_crosshair=distance,
                    priority=class_priority
                )
        
        return best_target
    
    def select_target_for_trigger(self, detections: List[Detection],
                                   trigger_scale: int = 24) -> Optional[Target]:
        """
        Select target for triggerbot (stricter criteria)
        
        Args:
            detections: List of Detection objects
            trigger_scale: How close crosshair must be to target center
            
        Returns:
            Target object or None if crosshair not on target
        """
        for detection in detections:
            if not self._is_class_valid(detection.class_id):
                continue
            
            # Check if crosshair is inside detection box (with scale)
            scaled_width = detection.width * (trigger_scale / 100)
            scaled_height = detection.height * (trigger_scale / 100)
            
            center_x, center_y = detection.center
            
            half_w = scaled_width / 2
            half_h = scaled_height / 2
            
            if (center_x - half_w <= self.crosshair_x <= center_x + half_w and
                center_y - half_h <= self.crosshair_y <= center_y + half_h):
                
                aim_x, aim_y = detection.get_aim_point(self.aim_bone, self.bone_scale)
                distance = self._distance_to_crosshair(aim_x, aim_y)
                
                return Target(
                    detection=detection,
                    aim_x=aim_x,
                    aim_y=aim_y,
                    distance_to_crosshair=distance,
                    priority=1.0
                )
        
        return None
    
    def get_all_targets_in_fov(self, detections: List[Detection],
                               aim_fov: Optional[int] = None) -> List[Target]:
        """
        Get all valid targets within FOV
        
        Args:
            detections: List of Detection objects
            aim_fov: Override FOV radius (optional)
            
        Returns:
            List of Target objects sorted by distance
        """
        fov = aim_fov if aim_fov is not None else self.aim_fov
        targets = []
        
        for detection in detections:
            if not self._is_class_valid(detection.class_id):
                continue
            
            aim_x, aim_y = detection.get_aim_point(self.aim_bone, self.bone_scale)
            distance = self._distance_to_crosshair(aim_x, aim_y)
            
            if distance <= fov:
                targets.append(Target(
                    detection=detection,
                    aim_x=aim_x,
                    aim_y=aim_y,
                    distance_to_crosshair=distance,
                    priority=self.class_priorities.get(detection.class_id, 1.0)
                ))
        
        # Sort by distance
        targets.sort(key=lambda t: t.distance_to_crosshair)
        return targets
    
    def _distance_to_crosshair(self, x: float, y: float) -> float:
        """Calculate distance from point to crosshair"""
        dx = x - self.crosshair_x
        dy = y - self.crosshair_y
        return math.sqrt(dx * dx + dy * dy)
    
    def _is_class_valid(self, class_id: int) -> bool:
        """Check if class is enabled and not disabled"""
        if class_id in self.disabled_classes:
            return False
        if self.enabled_classes and class_id not in self.enabled_classes:
            return False
        return True
    
    def update_frame_size(self, width: int, height: int):
        """Update frame dimensions"""
        self.frame_width = width
        self.frame_height = height
        self.crosshair_x = width / 2
        self.crosshair_y = height / 2
    
    def set_aim_bone(self, bone: str, scale: float = 1.0):
        """Set aim bone and scale"""
        self.aim_bone = bone
        self.bone_scale = scale
    
    def set_fov(self, fov: int):
        """Set aim FOV"""
        self.aim_fov = fov
    
    def set_class_filter(self, enabled: List[int], disabled: List[int]):
        """Set class filtering"""
        self.enabled_classes = enabled
        self.disabled_classes = disabled
    
    def calculate_delta(self, target: Target) -> Tuple[float, float]:
        """
        Calculate mouse delta to reach target
        
        Args:
            target: Target object
            
        Returns:
            (delta_x, delta_y) pixels to move
        """
        delta_x = target.aim_x - self.crosshair_x
        delta_y = target.aim_y - self.crosshair_y
        return (delta_x, delta_y)
