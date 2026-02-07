"""
Enemy Color Filter
Filters AI detections by checking for enemy outline colors
Used to exclude teammates from targeting
"""

import numpy as np
import cv2
from typing import List, Tuple, Optional
from .detection import Detection


# Enemy color presets (HSV ranges)
# OpenCV format: H=0-180, S=0-255, V=0-255
ENEMY_COLOR_PRESETS = {
    # Purple enemy outline (Valorant default)
    "purple": {
        "h_min": 125, "h_max": 155,
        "s_min": 80, "s_max": 255,
        "v_min": 100, "v_max": 255,
    },
    # Alternative purple (tighter range)
    "purple_tight": {
        "h_min": 130, "h_max": 145,
        "s_min": 100, "s_max": 255,
        "v_min": 120, "v_max": 255,
    },
    # Pink/Magenta
    "pink": {
        "h_min": 145, "h_max": 170,
        "s_min": 80, "s_max": 255,
        "v_min": 100, "v_max": 255,
    },
    # Yellow enemy outline
    "yellow": {
        "h_min": 20, "h_max": 40,
        "s_min": 150, "s_max": 255,
        "v_min": 180, "v_max": 255,
    },
    # Red enemy outline
    "red": {
        "h_min": 0, "h_max": 10,
        "s_min": 100, "s_max": 255,
        "v_min": 100, "v_max": 255,
    },
    # Red (high hue range)
    "red_high": {
        "h_min": 170, "h_max": 180,
        "s_min": 100, "s_max": 255,
        "v_min": 100, "v_max": 255,
    },
}


class EnemyColorFilter:
    """
    Filters detections based on enemy outline color
    Checks if detection bounding box contains the expected enemy color
    """
    
    def __init__(self, color: str = "purple", min_color_ratio: float = 0.01):
        """
        Initialize filter
        
        Args:
            color: Enemy color preset name
            min_color_ratio: Minimum ratio of colored pixels required (0-1)
        """
        self.color = color
        self.min_color_ratio = min_color_ratio
        
        # Load color preset
        self._load_preset(color)
    
    def _load_preset(self, color: str):
        """Load color preset"""
        self.color = color
        
        # Handle red which spans both ends of hue spectrum
        if color in ["red", "red_low"]:
            preset = ENEMY_COLOR_PRESETS.get("red", ENEMY_COLOR_PRESETS["purple"])
            self.h_ranges = [(preset["h_min"], preset["h_max"])]
            # Also include high hue range for red
            high_preset = ENEMY_COLOR_PRESETS.get("red_high")
            if high_preset:
                self.h_ranges.append((high_preset["h_min"], high_preset["h_max"]))
            self.s_range = (preset["s_min"], preset["s_max"])
            self.v_range = (preset["v_min"], preset["v_max"])
        else:
            preset = ENEMY_COLOR_PRESETS.get(color, ENEMY_COLOR_PRESETS["purple"])
            self.h_ranges = [(preset["h_min"], preset["h_max"])]
            self.s_range = (preset["s_min"], preset["s_max"])
            self.v_range = (preset["v_min"], preset["v_max"])
    
    def set_color(self, color: str):
        """Set enemy color"""
        self._load_preset(color)
    
    def set_custom_range(self, h_min: int, h_max: int, s_min: int, s_max: int,
                         v_min: int, v_max: int):
        """Set custom HSV range"""
        self.h_ranges = [(h_min, h_max)]
        self.s_range = (s_min, s_max)
        self.v_range = (v_min, v_max)
    
    def check_detection(self, frame: np.ndarray, detection: Detection,
                        expand_ratio: float = 0.1) -> bool:
        """
        Check if detection contains enemy color
        
        Args:
            frame: BGR image
            detection: Detection to check
            expand_ratio: Ratio to expand bounding box for checking
            
        Returns:
            True if enemy color is found
        """
        h, w = frame.shape[:2]
        
        # Get bounding box with expansion
        box_w = detection.x2 - detection.x1
        box_h = detection.y2 - detection.y1
        expand_x = box_w * expand_ratio
        expand_y = box_h * expand_ratio
        
        x1 = max(0, int(detection.x1 - expand_x))
        y1 = max(0, int(detection.y1 - expand_y))
        x2 = min(w, int(detection.x2 + expand_x))
        y2 = min(h, int(detection.y2 + expand_y))
        
        if x2 <= x1 or y2 <= y1:
            return False
        
        # Extract region
        roi = frame[y1:y2, x1:x2]
        if roi.size == 0:
            return False
        
        # Convert to HSV
        hsv = cv2.cvtColor(roi, cv2.COLOR_BGR2HSV)
        
        # Create mask for each hue range
        mask = None
        for h_min, h_max in self.h_ranges:
            lower = np.array([h_min, self.s_range[0], self.v_range[0]])
            upper = np.array([h_max, self.s_range[1], self.v_range[1]])
            range_mask = cv2.inRange(hsv, lower, upper)
            
            if mask is None:
                mask = range_mask
            else:
                mask = cv2.bitwise_or(mask, range_mask)
        
        # Calculate color ratio
        total_pixels = roi.shape[0] * roi.shape[1]
        color_pixels = cv2.countNonZero(mask)
        color_ratio = color_pixels / total_pixels
        
        return color_ratio >= self.min_color_ratio
    
    def filter_detections(self, frame: np.ndarray, detections: List[Detection],
                          expand_ratio: float = 0.1) -> List[Detection]:
        """
        Filter detections by enemy color
        
        Args:
            frame: BGR image
            detections: List of detections to filter
            expand_ratio: Ratio to expand bounding box for checking
            
        Returns:
            List of detections that contain enemy color
        """
        if not detections:
            return []
        
        filtered = []
        for detection in detections:
            if self.check_detection(frame, detection, expand_ratio):
                filtered.append(detection)
        
        return filtered
    
    def get_color_mask(self, frame: np.ndarray) -> np.ndarray:
        """
        Get color mask for entire frame (for debugging)
        
        Args:
            frame: BGR image
            
        Returns:
            Binary mask of detected color
        """
        hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
        
        mask = None
        for h_min, h_max in self.h_ranges:
            lower = np.array([h_min, self.s_range[0], self.v_range[0]])
            upper = np.array([h_max, self.s_range[1], self.v_range[1]])
            range_mask = cv2.inRange(hsv, lower, upper)
            
            if mask is None:
                mask = range_mask
            else:
                mask = cv2.bitwise_or(mask, range_mask)
        
        return mask
    
    @staticmethod
    def get_available_colors() -> List[str]:
        """Get list of available color presets"""
        return list(ENEMY_COLOR_PRESETS.keys())
