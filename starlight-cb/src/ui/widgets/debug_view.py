"""
Debug View Widget - Minimal Design
Square preview with stats
Optimized for performance - no freezing
"""

import numpy as np
import cv2
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame, QGridLayout
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QImage, QPixmap

# All bone names in order (top to bottom) for debug skeleton overlay
_ALL_BONES = [
    "top_head", "upper_head", "head", "neck",
    "upper_chest", "chest", "lower_chest",
    "upper_stomach", "stomach", "lower_stomach", "pelvis",
]

# Short labels for compact display
_BONE_SHORT = {
    "top_head": "TH", "upper_head": "UH", "head": "HD", "neck": "NK",
    "upper_chest": "UC", "chest": "CH", "lower_chest": "LC",
    "upper_stomach": "US", "stomach": "ST", "lower_stomach": "LS", "pelvis": "PL",
}

# Colors for bone groups (BGR)
_BONE_COLORS = {
    "top_head": (200, 100, 255), "upper_head": (200, 100, 255),
    "head": (0, 0, 255), "neck": (255, 100, 200),
    "upper_chest": (255, 200, 0), "chest": (255, 200, 0), "lower_chest": (255, 200, 0),
    "upper_stomach": (0, 200, 200), "stomach": (0, 200, 200), "lower_stomach": (0, 200, 200),
    "pelvis": (200, 200, 0),
}


class DebugView(QWidget):
    """Minimal debug view - square preview (optimized)"""
    
    # Trigger zones are now computed dynamically via Detection.get_bone_zone()
    # which adapts to stance (standing vs crouching) automatically
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        self._frame = None
        self._frame_dirty = False  # Only redraw when new frame arrives
        self._detections = []
        self._aim_target = None
        self._flick_target = None
        self._aim_fov = 25
        self._flick_fov = 30
        self._aim_bone = "upper_head"
        self._bone_scale = 1.0
        self._trigger_scale = 50  # Trigger zone percentage
        self._always_on_fov = 10
        self._always_on_enabled = False
        self._always_on_active = False  # True when AO is pulling toward target
        self._debug_bones = False  # Show all bone positions + zones overlay
        self._debug_trigger_zone = True  # Show trigger zone ellipse
        self._aim_key_down = False
        self._flick_key_down = False
        self._trigger_key_down = False
        # Feature enabled states
        self._aim_enabled = True
        self._flick_enabled = True
        self._trigger_enabled = True
        
        self._capture_fps = 0.0
        self._detection_fps = 0.0
        self._latency_ms = 0.0
        self._program_latency_ms = 0.0
        self._frame_age_ms = 0.0
        self._lifecycle_state = "Idle"
        
        # Performance: only redraw when new frame available
        # Timer controls max fps, dirty flag prevents redundant draws
        
        self._setup_ui()
        
        # Timer at ~120fps for smooth debug display
        self._timer = QTimer()
        self._timer.timeout.connect(self._update_display)
        self._timer.start(16)  # ~60fps (matches frame timer)
    
    def _setup_ui(self):
        self.setStyleSheet("""
            QWidget {
                background-color: rgba(255, 255, 255, 0.02);
                border: 1px solid rgba(255, 255, 255, 0.04);
                border-radius: 6px;
            }
        """)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(8)
        
        # Header
        header = QLabel("Debug")
        header.setStyleSheet("""
            color: #64748b;
            font-size: 9px;
            font-weight: 600;
            background: transparent;
            border: none;
        """)
        layout.addWidget(header)
        
        # Frame - square container
        self.frame_container = QFrame()
        self.frame_container.setStyleSheet("""
            QFrame {
                background-color: rgba(0, 0, 0, 0.3);
                border: 1px solid rgba(255, 255, 255, 0.04);
                border-radius: 4px;
            }
        """)
        # Make it square - match width
        self.frame_container.setMinimumSize(240, 240)
        self.frame_container.setMaximumSize(280, 280)
        
        frame_layout = QVBoxLayout(self.frame_container)
        frame_layout.setContentsMargins(0, 0, 0, 0)
        
        self.frame_label = QLabel()
        self.frame_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.frame_label.setStyleSheet("background: transparent; border: none;")
        frame_layout.addWidget(self.frame_label)
        
        layout.addWidget(self.frame_container)
        
        # Stats - compact grid
        stats = QFrame()
        stats.setStyleSheet("""
            QFrame {
                background-color: rgba(255, 255, 255, 0.01);
                border: 1px solid rgba(255, 255, 255, 0.03);
                border-radius: 4px;
            }
        """)
        
        stats_layout = QGridLayout(stats)
        stats_layout.setContentsMargins(8, 6, 8, 6)
        stats_layout.setSpacing(4)
        
        # Row 1
        stats_layout.addWidget(self._stat_label("CAP"), 0, 0)
        self.cap_fps = self._value_label("#22c55e")
        stats_layout.addWidget(self.cap_fps, 0, 1)
        
        stats_layout.addWidget(self._stat_label("DPS"), 0, 2)
        self.det_fps = self._value_label("#22c55e")
        stats_layout.addWidget(self.det_fps, 0, 3)
        
        # Row 2
        stats_layout.addWidget(self._stat_label("INF"), 1, 0)
        self.inf_ms = self._value_label("#eab308")
        stats_layout.addWidget(self.inf_ms, 1, 1)
        
        stats_layout.addWidget(self._stat_label("LAT"), 1, 2)
        self.lat_ms = self._value_label("#eab308")
        stats_layout.addWidget(self.lat_ms, 1, 3)

        # Row 3
        stats_layout.addWidget(self._stat_label("AGE"), 2, 0)
        self.age_ms = self._value_label("#eab308")
        stats_layout.addWidget(self.age_ms, 2, 1)

        stats_layout.addWidget(self._stat_label("STATE"), 2, 2)
        self.state_lbl = self._value_label("#22c55e")
        stats_layout.addWidget(self.state_lbl, 2, 3)

        # Row 4
        stats_layout.addWidget(self._stat_label("DEV"), 3, 0)
        self.dev_lbl = self._value_label("#22c55e")
        stats_layout.addWidget(self.dev_lbl, 3, 1)
        
        layout.addWidget(stats)
        
        # Status
        self.status = QLabel("Idle")
        self.status.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.status.setStyleSheet("color: #64748b; font-size: 9px; background: transparent; border: none;")
        layout.addWidget(self.status)
    
    def _stat_label(self, text: str) -> QLabel:
        lbl = QLabel(text)
        lbl.setStyleSheet("color: #475569; font-size: 9px; background: transparent; border: none;")
        return lbl
    
    def _value_label(self, color: str) -> QLabel:
        lbl = QLabel("--")
        lbl.setStyleSheet(f"color: {color}; font-size: 10px; font-family: 'Consolas'; font-weight: 600; background: transparent; border: none;")
        return lbl
    
    def update_frame(self, frame: np.ndarray):
        """Update frame - uses reference, copies only when displaying"""
        if frame is not None:
            # Store reference, don't copy here (copy in _update_display)
            self._frame = frame
            self._frame_dirty = True
    
    def update_detections(self, detections: list, target=None):
        self._detections = detections
        # Backward compatibility: old call passes aim target as `target`
        self._aim_target = target
    
    def update_targets(self, aim_target=None, flick_target=None):
        self._aim_target = aim_target
        self._flick_target = flick_target
    
    def update_bone_settings(self, bone: str, scale: float, trigger_scale: int = 50):
        self._aim_bone = bone
        self._bone_scale = scale
        self._trigger_scale = trigger_scale
    
    def update_metrics(self, capture_fps: float, detection_fps: float,
                       latency_ms: float, program_latency_ms: float = 0,
                       frame_age_ms: float = 0, lifecycle_state: str = "Idle",
                       detector_device: str = ""):
        self._capture_fps = capture_fps
        self._detection_fps = detection_fps
        self._latency_ms = latency_ms
        self._program_latency_ms = program_latency_ms
        self._frame_age_ms = frame_age_ms
        self._lifecycle_state = lifecycle_state
        
        self.cap_fps.setText(f"{capture_fps:.0f}")
        self.det_fps.setText(f"{detection_fps:.0f}")
        self.inf_ms.setText(f"{latency_ms:.1f}ms")
        self.lat_ms.setText(f"{program_latency_ms:.1f}ms")
        self.age_ms.setText(f"{frame_age_ms:.1f}ms")
        self.state_lbl.setText(lifecycle_state)
        self.dev_lbl.setText(detector_device or "--")
        
        if capture_fps > 0 or lifecycle_state != "Idle":
            # Only show key states for enabled features
            keys_parts = []
            if self._aim_enabled:
                keys_parts.append(f"A:{int(self._aim_key_down)}")
            if self._flick_enabled:
                keys_parts.append(f"F:{int(self._flick_key_down)}")
            if self._trigger_enabled:
                keys_parts.append(f"T:{int(self._trigger_key_down)}")
            if self._always_on_enabled:
                keys_parts.append(f"AO:{'ON' if self._always_on_active else '--'}")
            keys = " ".join(keys_parts) if keys_parts else "No features"
            self.status.setText(f"{lifecycle_state} | {keys}")
            self.status.setStyleSheet("color: #22c55e; font-size: 9px; background: transparent; border: none;")
        else:
            self.status.setText("Idle")
            self.status.setStyleSheet("color: #64748b; font-size: 9px; background: transparent; border: none;")

    def update_key_states(self, aim_down: bool, flick_down: bool, trigger_down: bool):
        self._aim_key_down = aim_down
        self._flick_key_down = flick_down
        self._trigger_key_down = trigger_down
    
    def set_aim_fov(self, fov: int):
        self._aim_fov = fov
    
    def set_flick_fov(self, fov: int):
        self._flick_fov = fov
    
    def set_feature_enabled(self, aim: bool, flick: bool, trigger: bool):
        """Set which features are enabled (only show FOV for enabled features)"""
        self._aim_enabled = aim
        self._flick_enabled = flick
        self._trigger_enabled = trigger
    
    def _update_display(self):
        """Update display - heavily optimized to prevent UI freezing"""
        if self._frame is None:
            return
        
        # Skip if no new frame available
        if not self._frame_dirty:
            return
        
        self._frame_dirty = False
        
        try:
            # Get target display size (small!)
            target_size = 240
            
            # Get original frame dimensions
            orig_h, orig_w = self._frame.shape[:2]
            
            # Calculate scale factor
            scale = target_size / max(orig_h, orig_w)
            new_w = int(orig_w * scale)
            new_h = int(orig_h * scale)
            
            # RESIZE FIRST - much faster to process small image
            # Use INTER_NEAREST for speed (INTER_LINEAR is slower but smoother)
            small = cv2.resize(self._frame, (new_w, new_h), interpolation=cv2.INTER_NEAREST)
            
            # Calculate center and scaled FOV for small image
            cx, cy = new_w // 2, new_h // 2
            scaled_aim_fov = int(self._aim_fov * scale)
            scaled_flick_fov = int(self._flick_fov * scale)
            
            # FOV circles - only show if feature is enabled
            if self._aim_enabled and scaled_aim_fov > 1:
                cv2.circle(small, (cx, cy), scaled_aim_fov, (139, 92, 246), 1, cv2.LINE_4)
            if self._flick_enabled and scaled_flick_fov > 1:
                cv2.circle(small, (cx, cy), scaled_flick_fov, (34, 211, 238), 1, cv2.LINE_4)
            # Always On FOV circle - green when actively pulling, white when idle
            if self._always_on_enabled:
                scaled_ao_fov = int(self._always_on_fov * scale)
                if scaled_ao_fov > 1:
                    ao_color = (0, 255, 100) if self._always_on_active else (200, 200, 200)
                    ao_thick = 2 if self._always_on_active else 1
                    cv2.circle(small, (cx, cy), scaled_ao_fov, ao_color, ao_thick, cv2.LINE_4)
            
            # Detections - limit to first 5 for performance
            for det in self._detections[:5]:
                # Scale detection coordinates
                x1 = int(det.x1 * scale)
                y1 = int(det.y1 * scale)
                x2 = int(det.x2 * scale)
                y2 = int(det.y2 * scale)
                
                is_aim = bool(self._aim_enabled and self._aim_target and det == self._aim_target.detection)
                is_flick = bool(self._flick_enabled and self._flick_target and det == self._flick_target.detection)
                
                if is_aim:
                    color = (0, 255, 0)
                    thick = 2
                elif is_flick:
                    color = (255, 255, 0)
                    thick = 2
                else:
                    color = (0, 255, 255)
                    thick = 1
                cv2.rectangle(small, (x1, y1), (x2, y2), color, thick, cv2.LINE_4)
                
                # === Debug Bones Overlay ===
                if self._debug_bones:
                    self._draw_bone_skeleton(small, det, scale, x1, x2)
                
                # Draw aim bone point (red dot) on every detection
                aim_px, aim_py = det.get_aim_point(self._aim_bone, self._bone_scale)
                dot_x = int(aim_px * scale)
                dot_y = int(aim_py * scale)
                
                # Draw trigger zone ellipse around bone point (orange, stance-aware)
                if self._trigger_enabled and self._debug_trigger_zone:
                    zone_w, zone_h = det.get_bone_zone(self._aim_bone)
                    ts_mult = self._trigger_scale / 100.0  # trigger_scale as multiplier
                    tr_rx = max(1, int((zone_w * ts_mult) / 2 * scale))
                    tr_ry = max(1, int((zone_h * ts_mult) / 2 * scale))
                    cv2.ellipse(small, (dot_x, dot_y), (tr_rx, tr_ry), 0, 0, 360, (0, 140, 255), 1, cv2.LINE_AA)
                
                if is_aim or is_flick:
                    # Active target: larger bright red dot with outline
                    cv2.circle(small, (dot_x, dot_y), 4, (0, 0, 255), -1, cv2.LINE_AA)
                    cv2.circle(small, (dot_x, dot_y), 4, (255, 255, 255), 1, cv2.LINE_AA)
                else:
                    # Non-target: smaller red dot
                    cv2.circle(small, (dot_x, dot_y), 3, (0, 0, 200), -1, cv2.LINE_AA)
                
                # Show confidence, class, and stance for AI detection
                conf = getattr(det, 'confidence', 0)
                class_id = getattr(det, 'class_id', 0)
                if conf > 0:
                    stance = det.get_stance_label()[0].upper()  # S/C/P
                    label = f"C{class_id}:{conf*100:.0f}% {stance}"
                    # Draw label background
                    (tw, th), _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.3, 1)
                    cv2.rectangle(small, (x1, y1-th-2), (x1+tw+2, y1), color, -1, cv2.LINE_4)
                    cv2.putText(small, label, (x1+1, y1-2), cv2.FONT_HERSHEY_SIMPLEX, 0.3, (0, 0, 0), 1, cv2.LINE_AA)
            
            # Target line - scaled
            if self._aim_enabled and self._aim_target:
                tx = int(self._aim_target.aim_x * scale)
                ty = int(self._aim_target.aim_y * scale)
                cv2.line(small, (cx, cy), (tx, ty), (0, 255, 0), 1, cv2.LINE_4)
            if self._flick_enabled and self._flick_target:
                tx = int(self._flick_target.aim_x * scale)
                ty = int(self._flick_target.aim_y * scale)
                cv2.line(small, (cx, cy), (tx, ty), (255, 255, 0), 1, cv2.LINE_4)
            
            # Convert BGR to RGB - on small image, very fast
            rgb = cv2.cvtColor(small, cv2.COLOR_BGR2RGB)
            
            # Create QImage directly from numpy array
            qimg = QImage(rgb.data, new_w, new_h, 3 * new_w, QImage.Format.Format_RGB888)
            
            # Convert to pixmap - must copy since rgb array will go out of scope
            pixmap = QPixmap.fromImage(qimg.copy())
            
            self.frame_label.setPixmap(pixmap)
            
        except Exception:
            # Silently ignore display errors
            pass
    
    def _draw_bone_skeleton(self, img, det, scale: float, box_x1: int, box_x2: int):
        """
        Draw all bone positions + zones on a detection for debug visualization.
        
        Shows:
        - Every bone as a colored dot with label
        - The active bone's zone as a filled semi-transparent ellipse
        - Connecting line (spine) between all bones
        - Stance info
        """
        active = self._aim_bone
        bone_scale = self._bone_scale
        
        prev_pt = None
        
        for bone in _ALL_BONES:
            # Get bone position
            bx, by = det.get_aim_point(bone, bone_scale)
            sx = int(bx * scale)
            sy = int(by * scale)
            
            bone_color = _BONE_COLORS.get(bone, (180, 180, 180))
            is_active = (bone == active)
            
            # Draw connecting spine line
            if prev_pt is not None:
                cv2.line(img, prev_pt, (sx, sy), (100, 100, 100), 1, cv2.LINE_AA)
            prev_pt = (sx, sy)
            
            # Draw bone zone ellipse for active bone (semi-transparent fill effect)
            if is_active:
                zone_w, zone_h = det.get_bone_zone(bone)
                zrx = max(1, int(zone_w / 2 * scale))
                zry = max(1, int(zone_h / 2 * scale))
                # Draw filled ellipse with low opacity by drawing thin layers
                cv2.ellipse(img, (sx, sy), (zrx, zry), 0, 0, 360, bone_color, 2, cv2.LINE_AA)
                # Inner fill (dashed style via smaller ellipse)
                cv2.ellipse(img, (sx, sy), (max(1, zrx - 1), max(1, zry - 1)), 0, 0, 360, bone_color, 1, cv2.LINE_AA)
            
            # Draw bone dot
            if is_active:
                # Active bone: big bright dot with white outline
                cv2.circle(img, (sx, sy), 4, bone_color, -1, cv2.LINE_AA)
                cv2.circle(img, (sx, sy), 4, (255, 255, 255), 1, cv2.LINE_AA)
            else:
                # Other bones: small dot
                cv2.circle(img, (sx, sy), 2, bone_color, -1, cv2.LINE_AA)
            
            # Draw label to the right of the bbox
            label = _BONE_SHORT.get(bone, bone[:2].upper())
            lx = box_x2 + 3
            ly = sy + 3
            
            if is_active:
                # Active bone label: bright with background
                (tw, th), _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.28, 1)
                cv2.rectangle(img, (lx - 1, ly - th - 1), (lx + tw + 1, ly + 1), bone_color, -1)
                cv2.putText(img, label, (lx, ly), cv2.FONT_HERSHEY_SIMPLEX, 0.28, (0, 0, 0), 1, cv2.LINE_AA)
            else:
                # Other bone labels: dim
                cv2.putText(img, label, (lx, ly), cv2.FONT_HERSHEY_SIMPLEX, 0.22, (120, 120, 120), 1, cv2.LINE_AA)
    
    def start(self):
        if not self._timer.isActive():
            self._timer.start()
    
    def stop(self):
        self._timer.stop()
