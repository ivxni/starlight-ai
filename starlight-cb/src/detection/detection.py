"""
Detection dataclass - shared between AI and Color detection

Simple center-of-bbox targeting. Designed for multi-class models
(head/body) where the model provides separate detections per body part.
"""

from dataclasses import dataclass
from typing import Tuple


@dataclass
class Detection:
    """Single detection result"""
    x1: float  # Left
    y1: float  # Top
    x2: float  # Right
    y2: float  # Bottom
    confidence: float
    class_id: int
    
    @property
    def width(self) -> float:
        return self.x2 - self.x1
    
    @property
    def height(self) -> float:
        return self.y2 - self.y1
    
    @property
    def center_x(self) -> float:
        return (self.x1 + self.x2) / 2
    
    @property
    def center_y(self) -> float:
        return (self.y1 + self.y2) / 2
    
    @property
    def center(self) -> Tuple[float, float]:
        return (self.center_x, self.center_y)
    
    @property
    def area(self) -> float:
        return self.width * self.height
    
    @property
    def aspect_ratio(self) -> float:
        """Height / Width ratio."""
        w = self.width
        return self.height / w if w > 0 else 2.5
    
    def get_aim_point(self, bone: str = "head", bone_scale: float = 1.0) -> Tuple[float, float]:
        """
        Get aim point - center of bounding box.
        
        With multi-class models (head/body), each class has its own bbox,
        so center-of-bbox IS the correct aim point:
        - Head detection -> center = head center (perfect headshot)
        - Body detection -> center = center mass
        
        Args:
            bone: Ignored (kept for API compatibility)
            bone_scale: Vertical offset multiplier (1.0 = center, <1 = higher, >1 = lower)
            
        Returns:
            (x, y) coordinates for aim point
        """
        cx = self.center_x
        cy = self.center_y
        
        # bone_scale shifts aim point vertically from center
        # 1.0 = exact center, 0.8 = 20% higher, 1.2 = 20% lower
        if bone_scale != 1.0:
            # Offset from center (positive = lower)
            offset = (bone_scale - 1.0) * self.height * 0.5
            cy += offset
        
        return (cx, cy)
    
    def get_bone_zone(self, bone: str = "head") -> Tuple[float, float]:
        """
        Get trigger zone size as a percentage of the bbox.
        
        With multi-class models, the bbox already tightly wraps the body part,
        so the zone is just a percentage of the bbox itself.
        
        Returns:
            (zone_width, zone_height) in pixels
        """
        # Zone is 70% of bbox dimensions (tight but forgiving)
        return (self.width * 0.70, self.height * 0.70)
    
    def get_stance_label(self) -> str:
        """Return human-readable stance estimate."""
        ar = self.aspect_ratio
        if ar >= 2.5:
            return "standing"
        elif ar <= 1.5:
            return "crouching"
        else:
            return "partial"
