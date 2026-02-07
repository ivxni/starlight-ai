"""
Main Assistant Control Loop
Coordinates capture, detection, and mouse movement
"""

import time
import threading
import random
import ctypes
import cv2
import numpy as np
from typing import Optional, Tuple, Callable
from dataclasses import dataclass

from ..capture.screen_capture import ScreenCapture
from ..detection.detection import Detection
from ..detection.ai_engine import AIEngine
from ..detection.enemy_color_filter import EnemyColorFilter
from ..detection.target_selector import TargetSelector, Target
from ..movement.mouse_controller import MouseController, get_mouse_controller, configure_mouse_controller
from ..movement.humanizer import Humanizer
from ..movement.pid_controller import PIDController
from ..input.input_blocker import InputBlocker, get_input_blocker
from .config import Config, get_config

# Windows API for mouse button state
GetAsyncKeyState = ctypes.windll.user32.GetAsyncKeyState

# Virtual key codes
VK_LBUTTON = 0x01   # Left mouse
VK_RBUTTON = 0x02   # Right mouse
VK_MBUTTON = 0x04   # Middle mouse
VK_XBUTTON1 = 0x05  # X1 (Back)
VK_XBUTTON2 = 0x06  # X2 (Forward)


@dataclass
class AssistantState:
    """Current state of the assistant"""
    aim_active: bool = False
    flick_active: bool = False
    trigger_active: bool = False
    current_target: Optional[Target] = None
    flick_target: Optional[Target] = None
    aim_key_down: bool = False
    flick_key_down: bool = False
    trigger_key_down: bool = False
    lifecycle_state: str = "Idle"
    
    # Performance metrics
    capture_fps: float = 0.0
    detection_fps: float = 0.0
    loop_fps: float = 0.0
    latency_ms: float = 0.0
    frame_age_ms: float = 0.0
    detector_device: str = ""
    active_bone: str = "upper_head"
    bone_scale: float = 1.0
    always_on_active: bool = False  # True when AO is pulling toward a target


class Assistant:
    """
    Main assistant that coordinates all subsystems
    """
    
    def __init__(self, config: Optional[Config] = None):
        """
        Initialize assistant
        
        Args:
            config: Configuration object (uses global if not provided)
        """
        self.config = config or get_config()
        
        # Subsystems
        self.capture: Optional[ScreenCapture] = None
        self.detector: Optional[AIEngine] = None
        self.color_filter: Optional[EnemyColorFilter] = None
        self.selector: Optional[TargetSelector] = None
        self.mouse: MouseController = get_mouse_controller()
        self.aim_humanizer: Humanizer = Humanizer()
        self.flick_humanizer: Humanizer = Humanizer()
        self.input_blocker: InputBlocker = get_input_blocker()
        self.pid_controller: PIDController = PIDController()
        
        # State
        self.state = AssistantState()
        self._running = False
        self._paused = False
        
        # Threading
        self._main_thread: Optional[threading.Thread] = None
        self._lock = threading.Lock()
        
        # Input callbacks
        self._aim_key_pressed = False
        self._flick_key_pressed = False
        self._trigger_key_pressed = False
        
        # Timing
        self._last_aim_time = 0.0
        self._aim_start_time = 0.0
        self._loop_count = 0
        self._last_fps_time = 0.0
        self._last_trigger_time = 0.0  # Trigger cooldown
        self._warmup_frames_left = 0
        
        # Trigger state tracking
        self._trigger_key_press_time = 0.0  # When trigger key was pressed
        self._trigger_first_detection_time = 0.0  # When color was first detected WHILE holding trigger
        self._trigger_was_on_color = False  # Was crosshair on color in previous frame?
        self._trigger_next_shot_delay = 0.0  # Chosen delay for next shot (randomized once per shot)
        
        # Callbacks for UI updates
        self.on_state_change: Optional[Callable[[AssistantState], None]] = None
        self.on_detection: Optional[Callable[[list], None]] = None
    
    def initialize(self) -> bool:
        """Initialize all subsystems"""
        try:
            self.state.lifecycle_state = "Initializing"
            # BetterCam (DXGI Desktop Duplication) conflicts with ALL GPU inference
            # providers - both DirectML and CUDA create D3D11 devices that break DXGI.
            # Force MSS (GDI-based) capture when any GPU provider is configured.
            onnx_provider = getattr(self.config.detection, 'onnx_provider', 'cuda')
            is_gpu_provider = onnx_provider in ('cuda', 'directml', 'tensorrt')
            needs_mss = is_gpu_provider  # Always force MSS for GPU providers
            if needs_mss:
                print(f"GPU provider '{onnx_provider}' - using MSS capture (D3D conflict avoidance)")
            
            # Initialize screen capture
            self.capture = ScreenCapture(
                capture_width=self.config.capture.capture_width,
                capture_height=self.config.capture.capture_height,
                target_fps=self.config.capture.max_fps,
                monitor=self.config.capture.monitor,
                mode=self.config.capture.capture_mode,
                window_name=self.config.capture.window_name,
                obs_stream_url=getattr(self.config.capture, "obs_stream_url", ""),
                capture_buffer_size=getattr(self.config.capture, "capture_buffer_size", 1),
                max_frame_age_ms=getattr(self.config.capture, "max_frame_age_ms", 0),
                force_mss=needs_mss  # Only force MSS if DirectML EP is truly available
            )
            
            # Prepare detector (model loaded later in start() to avoid D3D conflict with capture)
            self._init_detector(defer_model=True)
            
            # Initialize target selector
            self.selector = TargetSelector(
                frame_width=self.config.capture.capture_width,
                frame_height=self.config.capture.capture_height
            )
            
            # Configure mouse device (internal or arduino)
            self.mouse = configure_mouse_controller(
                device=self.config.mouse.device,
                port=self.config.mouse.arduino_port,
                jitter=self.config.mouse.arduino_jitter,
                tremor=self.config.mouse.arduino_tremor,
                humanization=self.config.mouse.arduino_humanization
            )
            
            # Configure mouse sensitivity
            self.mouse.set_sensitivity(
                dpi=self.config.mouse.dpi_value,
                in_game=self.config.mouse.in_game_sens,
                reference=self.config.mouse.reference_sens
            )
            self.mouse.normalization_enabled = self.config.mouse.sens_normalization_enabled
            self.mouse.sens_multiplier = self.config.mouse.sens_multiplier
            
            # Configure humanizers
            self._configure_humanizer(self.aim_humanizer, self.config.humanizer)
            self._configure_humanizer(self.flick_humanizer, self.config.flick_humanizer)
            
            # Configure input blocker (hide hotkeys from game)
            self._configure_input_blocker()
            
            print("Assistant initialized successfully")
            return True
            
        except Exception as e:
            print(f"Failed to initialize assistant: {e}")
            return False
    
    def _configure_humanizer(self, humanizer: Humanizer, config):
        """Configure a humanizer from config - ALL settings"""
        # Use the load_from_config method which handles all settings
        humanizer.load_from_config(config)
    
    def _configure_mouse_device(self):
        """Configure mouse device (internal or arduino)"""
        self.mouse = configure_mouse_controller(
            device=self.config.mouse.device,
            port=self.config.mouse.arduino_port,
            jitter=self.config.mouse.arduino_jitter,
            tremor=self.config.mouse.arduino_tremor,
            humanization=self.config.mouse.arduino_humanization
        )
        
        # Also update sensitivity
        self.mouse.set_sensitivity(
            dpi=self.config.mouse.dpi_value,
            in_game=self.config.mouse.in_game_sens,
            reference=self.config.mouse.reference_sens
        )
        self.mouse.normalization_enabled = self.config.mouse.sens_normalization_enabled
        self.mouse.sens_multiplier = self.config.mouse.sens_multiplier
        
        print(f"Mouse device: {self.mouse.device_mode}" + 
              (f" (Arduino connected)" if self.mouse.arduino_connected else ""))
    
    def _configure_input_blocker(self):
        """Configure input blocker based on config settings"""
        self.input_blocker.clear_blocked_buttons()
        
        if not self.config.mouse.input_blocking_enabled:
            print("Input blocking: DISABLED")
            return
        
        # Add blocked buttons based on config
        m = self.config.mouse
        
        if m.block_left_click:
            self.input_blocker.add_blocked_button("left_button")
        if m.block_right_click:
            self.input_blocker.add_blocked_button("right_button")
        if m.block_middle_click:
            self.input_blocker.add_blocked_button("middle_button")
        if m.block_forward_button:
            self.input_blocker.add_blocked_button("forward_button")
        if m.block_back_button:
            self.input_blocker.add_blocked_button("back_button")
        
        if self.input_blocker._blocked_buttons:
            print(f"Input blocking: ENABLED for {self.input_blocker._blocked_buttons}")
        else:
            print("Input blocking: ENABLED but no buttons selected")
    
    def _init_detector(self, defer_model: bool = False):
        """Initialize AI Detection Engine
        
        Args:
            defer_model: If True, only prepare engine without loading model.
                        Model will be loaded in start() after capture is ready.
        """
        if defer_model:
            # Create engine without loading model yet
            self.detector = AIEngine()
            self.detector.backend = getattr(self.config.detection, 'backend', 'onnx')
            self.detector.model_path = getattr(self.config.detection, 'model_file', '')
            self.detector.confidence_threshold = getattr(self.config.detection, 'confidence', 60) / 100.0
        else:
            self.detector = AIEngine(config=self.config.detection)
        
        # Initialize enemy color filter
        self.color_filter = EnemyColorFilter(
            color=self.config.filtering.enemy_color,
            min_color_ratio=0.01
        )
        
        # Log status
        if self.detector.is_loaded:
            print(f"AI Detection - Backend: {self.detector.backend}, Model: {self.config.detection.model_file}")
            self.state.detector_device = self.detector.backend.upper()
        else:
            if defer_model and self.detector.model_path:
                print(f"AI Detection - Model will load on Start: {self.detector.model_path}")
            else:
                print("AI Detection - No model loaded (select a model in Settings)")
            self.state.detector_device = "No Model"
    
    def reload_detector(self):
        """Reload detector (call when detection mode changes)"""
        self._init_detector()
        print("Detector reloaded")
    
    def start(self) -> bool:
        """Start the assistant"""
        if self._running:
            return True
        
        self.state.lifecycle_state = "Initializing"
        
        # Reconfigure mouse device (in case settings changed)
        self._configure_mouse_device()
        
        # Reconfigure input blocker
        self._configure_input_blocker()
        
        # Load AI model first (MSS capture doesn't conflict with GPU providers)
        if self.detector and not self.detector.is_loaded and self.detector.model_path:
            import os
            model_path = self.detector.model_path
            if os.path.exists(model_path):
                print(f"Loading AI model: {model_path}")
                try:
                    self.detector.load_from_config(self.config.detection)
                    if self.detector.is_loaded:
                        print(f"AI Detection - Backend: {self.detector.backend}, Model: {model_path}")
                        self.state.detector_device = self.detector.backend.upper()
                    else:
                        print("AI model failed to load")
                except Exception as e:
                    print(f"AI model load error: {e}")
        
        # Start capture after model is loaded
        if not self.capture.start():
            print("Failed to start screen capture")
            self.state.lifecycle_state = "Idle"
            return False
        
        # Start input blocker (if enabled)
        if self.config.mouse.input_blocking_enabled:
            self.input_blocker.start()
        
        # Start main loop
        self._running = True
        self._warmup_frames_left = max(0, int(getattr(self.config.capture, "startup_warmup_frames", 0)))
        self._last_fps_time = time.perf_counter()  # Initialize FPS timer
        self._loop_count = 0
        self._main_thread = threading.Thread(target=self._main_loop, daemon=True)
        self._main_thread.start()
        
        print("Assistant started")
        return True
    
    def stop(self):
        """Stop the assistant"""
        self.state.lifecycle_state = "Stopping"
        self._running = False
        
        if self._main_thread:
            self._main_thread.join(timeout=2.0)
            self._main_thread = None
        
        if self.capture:
            self.capture.stop()
        
        # Stop input blocker
        self.input_blocker.stop()
        
        self.reset_state()
        
        print("Assistant stopped")
    
    def pause(self):
        """Pause the assistant"""
        self._paused = True
    
    def resume(self):
        """Resume the assistant"""
        self._paused = False
    
    def _main_loop(self):
        """Main processing loop"""
        _first_frame = True
        _no_frame_count = 0
        
        while self._running:
            start_time = time.perf_counter()
            
            if self._paused:
                time.sleep(0.01)
                continue
            
            try:
                # Check input state (mouse buttons)
                self._check_input_state()
                
                # Get frame
                frame, frame_ts = self.capture.get_frame_with_timestamp()
                if frame is None or frame_ts == 0:
                    _no_frame_count += 1
                    if _no_frame_count == 100:
                        print(f"Warning: No frames received after {_no_frame_count} attempts")
                    if _no_frame_count == 1000:
                        print(f"Warning: Still no frames after {_no_frame_count} attempts. Capture backend: {self.capture.backend}")
                    time.sleep(0.001)
                    continue
                
                if _first_frame:
                    print(f"First frame received: {frame.shape[1]}x{frame.shape[0]} (age: {(time.perf_counter() - frame_ts)*1000:.0f}ms)")
                    _first_frame = False
                
                # Drop stale frames (reduce perceived lag)
                frame_age_ms = (time.perf_counter() - frame_ts) * 1000
                self.state.frame_age_ms = frame_age_ms
                max_age = getattr(self.config.capture, "max_frame_age_ms", 0)
                if max_age and frame_age_ms > max_age:
                    continue
                
                # Warmup (ignore first frames to stabilize)
                if self._warmup_frames_left > 0:
                    self._warmup_frames_left -= 1
                    self.state.lifecycle_state = "Warmup"
                    self._update_metrics(start_time)
                    continue
                else:
                    self.state.lifecycle_state = "Running"
                
                # Run AI detection
                detections = []
                if self.detector and self.detector.is_loaded:
                    detections = self.detector.detect(frame)
                    
                    # Apply enemy color filter if enabled
                    if self.config.filtering.enemy_color_enabled and self.color_filter and detections:
                        self.color_filter.set_color(self.config.filtering.enemy_color)
                        detections = self.color_filter.filter_detections(frame, detections)
                    
                    # Refresh device status
                    self.state.detector_device = self.detector.backend.upper()
                    
                    # Callback for visualization
                    if self.on_detection:
                        self.on_detection(detections)
                
                # Update selector config (live updates)
                self.selector.set_fov(self.config.aim.aim_fov)
                active_bone = self._get_enabled_bone()
                bone_scale = self.config.detection.bone_scale
                self.selector.set_aim_bone(active_bone, bone_scale)
                self.state.active_bone = active_bone
                self.state.bone_scale = bone_scale
                
                # Update class filtering based on config
                enabled_classes = []
                disabled_classes = []
                d = self.config.detection
                if d.class_filter_0: enabled_classes.append(0)
                if d.class_filter_1: enabled_classes.append(1)
                if d.class_filter_2: enabled_classes.append(2)
                if d.class_filter_3: enabled_classes.append(3)
                if d.class_disable_0: disabled_classes.append(0)
                if d.class_disable_1: disabled_classes.append(1)
                if d.class_disable_2: disabled_classes.append(2)
                if d.class_disable_3: disabled_classes.append(3)
                self.selector.set_class_filter(enabled_classes, disabled_classes)
                
                # Update mouse sensitivity (live)
                self.mouse.set_sensitivity(
                    dpi=self.config.mouse.dpi_value,
                    in_game=self.config.mouse.in_game_sens,
                    reference=self.config.mouse.reference_sens
                )
                self.mouse.normalization_enabled = self.config.mouse.sens_normalization_enabled
                self.mouse.sens_multiplier = self.config.mouse.sens_multiplier
                
                # Update AI detector confidence (live)
                if self.detector:
                    self.detector.set_confidence(self.config.detection.confidence / 100.0)
                
                # Update humanizers (live)
                self._configure_humanizer(self.aim_humanizer, self.config.humanizer)
                self._configure_humanizer(self.flick_humanizer, self.config.flick_humanizer)
                
                # Process aim
                if self._aim_key_pressed and self.config.aim.enabled:
                    self._process_aim(detections)
                else:
                    self.state.aim_active = False
                    self._aim_start_time = 0
                
                # Process flick
                if self._flick_key_pressed and self.config.flick.enabled:
                    self._process_flick(detections)
                else:
                    self.state.flick_active = False
                
                # Process trigger
                if self._trigger_key_pressed and self.config.trigger.enabled:
                    self._process_trigger(detections, frame)
                else:
                    self.state.trigger_active = False
                
                # Process Always On (runs even without key press)
                # Only when regular aim/flick is NOT active (they take priority)
                if (self.config.always_on.enabled
                    and not self.state.aim_active 
                    and not self.state.flick_active):
                    self._process_always_on(detections)
                
                # Update metrics
                self._update_metrics(start_time)
                
            except Exception as e:
                print(f"Error in main loop: {e}")
                time.sleep(0.01)
    
    def _process_aim(self, detections: list):
        """Process aim assist with Sticky Aim and PID"""
        # Reaction time delay
        if self._aim_start_time == 0:
            self._aim_start_time = time.perf_counter()
        
        elapsed_ms = (time.perf_counter() - self._aim_start_time) * 1000
        if elapsed_ms < self.config.aim.reaction_time:
            return
        
        # Max aim time check
        if self.config.aim.max_aim_time_enabled:
            if elapsed_ms > self.config.aim.max_aim_time * 1000:
                self.state.aim_active = False
                return
        
        # Select target
        target = self.selector.select_target(
            detections,
            aim_fov=self.config.aim.aim_fov
        )
        
        if target is None:
            self.state.aim_active = False
            self.state.current_target = None
            self.pid_controller.reset()
            return
        
        self.state.aim_active = True
        self.state.current_target = target
        
        # Calculate delta
        delta_x, delta_y = self.selector.calculate_delta(target)
        distance = target.distance_to_crosshair
        
        # Determine smoothing based on Sticky Aim (Close/Far)
        if self.config.aim.sticky_aim_enabled:
            sticky_zone = self.config.aim.sticky_aim_zone
            
            if distance <= sticky_zone:
                # Close to target - use close smoothing (more responsive)
                smooth_x = self.config.aim.smooth_x_close
                smooth_y = self.config.aim.smooth_y_close
            else:
                # Far from target - interpolate between close and far
                t = min(1.0, (distance - sticky_zone) / sticky_zone)
                smooth_x = self.config.aim.smooth_x_close + t * (self.config.aim.smooth_x_far - self.config.aim.smooth_x_close)
                smooth_y = self.config.aim.smooth_y_close + t * (self.config.aim.smooth_y_far - self.config.aim.smooth_y_close)
        else:
            # Use standard smoothing
            smooth_x = self.config.aim.smooth_x
            smooth_y = self.config.aim.smooth_y
        
        # Apply humanization
        if self.config.humanizer.enabled:
            # Check for random pause
            pause = self.aim_humanizer.should_pause()
            if pause:
                time.sleep(pause / 1000)
                return
            
            # Check proximity pause
            prox_pause = self.aim_humanizer.should_proximity_pause(distance)
            if prox_pause:
                time.sleep(prox_pause / 1000)
                return
            
            # Humanize movement
            h_dx, h_dy = self.aim_humanizer.humanize_movement(
                delta_x, delta_y,
                smooth_x,
                smooth_y
            )
        else:
            # Basic smoothing only
            h_dx = delta_x / max(1.0, smooth_x)
            h_dy = delta_y / max(1.0, smooth_y)
        
        # Apply PID stabilization
        if self.config.aim.pid_enabled:
            # Update PID gains from config
            self.pid_controller.set_gains(
                self.config.aim.pid_kp,
                self.config.aim.pid_ki,
                self.config.aim.pid_kd
            )
            self.pid_controller.activation_distance = self.config.aim.pid_activation_dist
            
            # Get PID correction
            pid_x, pid_y = self.pid_controller.update(delta_x, delta_y)
            h_dx += pid_x
            h_dy += pid_y
        
        # Apply tracking deadzone
        if abs(delta_x) < self.config.tracking.tracking_deadzone and \
           abs(delta_y) < self.config.tracking.tracking_deadzone:
            return
        
        # Move mouse
        self.mouse.move(h_dx, h_dy)
        
        # Delay
        if self.config.mouse.aim_delay > 0:
            time.sleep(self.config.mouse.aim_delay / 1000)
    
    def _process_flick(self, detections: list):
        """Process flick assist"""
        target = self.selector.select_target(
            detections,
            aim_fov=self.config.flick.flick_fov
        )
        
        if target is None:
            self.state.flick_active = False
            self.state.flick_target = None
            return
        
        self.state.flick_active = True
        self.state.flick_target = target
        
        # Calculate delta
        delta_x, delta_y = self.selector.calculate_delta(target)
        
        # Apply humanization if enabled
        if self.config.flick_humanizer.enabled:
            # Check for random pause
            pause = self.flick_humanizer.should_pause()
            if pause:
                time.sleep(pause / 1000)
                return
            
            # Humanize movement
            h_dx, h_dy = self.flick_humanizer.humanize_movement(
                delta_x, delta_y,
                self.config.flick.smooth_x,
                self.config.flick.smooth_y
            )
        else:
            # Basic smoothing only
            h_dx = delta_x / max(1.0, self.config.flick.smooth_x)
            h_dy = delta_y / max(1.0, self.config.flick.smooth_y)
        
        # Apply tracking deadzone
        if abs(delta_x) < self.config.tracking.tracking_deadzone and \
           abs(delta_y) < self.config.tracking.tracking_deadzone:
            return
        
        # Move mouse
        self.mouse.move(h_dx, h_dy)
        
        # Delay
        if self.config.mouse.flick_delay > 0:
            time.sleep(self.config.mouse.flick_delay / 1000)
    
    def _process_trigger(self, detections: list, frame=None):
        """
        Process triggerbot - AI-BASED (STANCE-AWARE BONE ZONE CHECK)
        
        Uses Detection.get_bone_zone() which automatically adapts to stance:
        - Standing character → tight head zone at ~8% from top
        - Crouching character → proportionally adjusted zones
        - trigger_scale is a multiplier (100 = natural size, 50 = tighter, 150 = looser)
        
        Reaction Time Logic:
        - If target already on crosshair when you press trigger → INSTANT shot
        - If you HOLD trigger and target APPEARS → apply reaction time delay
        - Multi-shot delay applies between all subsequent shots (for tap-firing)
        """
        if not detections:
            self.state.trigger_active = False
            self._trigger_was_on_color = False
            return
        
        # trigger_scale is a multiplier on bone zone size (100 = natural, 50 = tighter)
        trigger_scale = max(1, min(200, self.config.trigger.trigger_scale)) / 100.0
        
        # Get crosshair position (center of frame)
        frame_w = self.config.capture.capture_width
        frame_h = self.config.capture.capture_height
        crosshair_x = frame_w / 2
        crosshair_y = frame_h / 2
        
        # Get current bone settings
        active_bone = self.state.active_bone
        bone_scale = self.state.bone_scale
        
        is_on_target = False
        for det in detections:
            # Get the bone aim point (stance-aware)
            aim_x, aim_y = det.get_aim_point(active_bone, bone_scale)
            
            # Get bone zone size (stance-aware, returns pixels)
            zone_w, zone_h = det.get_bone_zone(active_bone)
            
            # Apply trigger_scale multiplier
            trigger_radius_x = (zone_w * trigger_scale) / 2
            trigger_radius_y = (zone_h * trigger_scale) / 2
            
            # Elliptical check: is crosshair within the trigger zone?
            dx = (crosshair_x - aim_x) / max(trigger_radius_x, 1)
            dy = (crosshair_y - aim_y) / max(trigger_radius_y, 1)
            
            if (dx * dx + dy * dy) <= 1.0:
                is_on_target = True
                break
        
        now = time.perf_counter() * 1000  # Current time in ms
        
        if not is_on_target:
            self.state.trigger_active = False
            self._trigger_was_on_color = False
            return
        
        self.state.trigger_active = True
        
        # === MULTI-SHOT DELAY CHECK (MUST BE FIRST) ===
        if self._last_trigger_time > 0:
            elapsed_since_shot = now - self._last_trigger_time
            if elapsed_since_shot < self._trigger_next_shot_delay:
                return  # Not enough time passed since last shot
        
        # === REACTION TIME LOGIC ===
        if not self._trigger_was_on_color:
            self._trigger_first_detection_time = now
            self._trigger_was_on_color = True
            
            time_since_key_press = now - self._trigger_key_press_time
            
            if time_since_key_press > 50:  # Key was pressed before target appeared
                reaction_delay = random.uniform(
                    self.config.trigger.first_shot_delay_min,
                    self.config.trigger.first_shot_delay_max
                )
                time.sleep(reaction_delay / 1000)
        
        # FIRE!
        self.mouse.click("left")
        
        # Record shot time and randomize NEXT shot's delay
        self._last_trigger_time = time.perf_counter() * 1000
        self._trigger_next_shot_delay = random.uniform(
            self.config.trigger.multi_shot_delay_min,
            self.config.trigger.multi_shot_delay_max
        )
    
    def _process_always_on(self, detections: list):
        """
        Always-On passive aim assist.
        Subtly nudges crosshair toward the bone aim point (red dot).
        
        Formula: move = (delta / smoothing) * strength
        - smoothing=5 → move 1/5th of distance per frame  
        - strength=1.0 → full speed, 0.5 → half speed
        - max_correction clamps per-frame movement
        """
        self.state.always_on_active = False
        
        if not detections:
            return
        
        ao = self.config.always_on
        
        # Select nearest target within Always On FOV (uses bone aim point)
        target = self.selector.select_target(detections, aim_fov=ao.fov)
        if target is None:
            return
        
        # Calculate delta to bone aim point (this IS the red dot position)
        delta_x, delta_y = self.selector.calculate_delta(target)
        distance = target.distance_to_crosshair
        
        # Debug: log AO activations periodically
        ao_count = getattr(self, '_ao_debug_count', 0)
        if ao_count < 20:
            self._ao_debug_count = ao_count + 1
            print(f"[AO] dist={distance:.1f} delta=({delta_x:.1f},{delta_y:.1f}) "
                  f"str={ao.strength} smooth={ao.smoothing} fov={ao.fov} max={ao.max_correction}")
        
        # Deadzone - ignore tiny corrections (looks more human)
        if distance < ao.deadzone:
            self.state.always_on_active = True  # In zone but too close
            return
        
        # Smoothing: move fraction of distance per frame
        # smoothing=5 → move 1/5th per frame, smoothing=10 → 1/10th
        smooth = max(1.0, ao.smoothing)
        move_x = (delta_x / smooth) * ao.strength
        move_y = (delta_y / smooth) * ao.strength
        
        # Clamp max correction per frame (prevents snappy movements)
        max_corr = ao.max_correction
        move_x = max(-max_corr, min(max_corr, move_x))
        move_y = max(-max_corr, min(max_corr, move_y))
        
        # Add micro-randomization for human feel (±15% variation)
        move_x *= 1.0 + random.uniform(-0.15, 0.15)
        move_y *= 1.0 + random.uniform(-0.15, 0.15)
        
        # Randomly skip ~8% of frames for human feel
        if random.random() < 0.08:
            return
        
        # Mark as active (for debug view indicator)
        self.state.always_on_active = True
        
        # Move mouse toward bone aim point
        self.mouse.move(move_x, move_y)
    
    def _get_enabled_bone(self) -> str:
        """Get the first enabled bone from config, or default to upper_head"""
        d = self.config.detection
        
        # Check head bones first (priority order)
        if d.bone_top_head: return "top_head"
        if d.bone_upper_head: return "upper_head"
        if d.bone_head: return "head"
        if d.bone_neck: return "neck"
        
        # Then torso bones
        if d.bone_upper_chest: return "upper_chest"
        if d.bone_chest: return "chest"
        if d.bone_lower_chest: return "lower_chest"
        if d.bone_upper_stomach: return "upper_stomach"
        if d.bone_stomach: return "stomach"
        if d.bone_lower_stomach: return "lower_stomach"
        if d.bone_pelvis: return "pelvis"
        
        # Default
        return "upper_head"
    
    def _update_metrics(self, start_time: float):
        """Update performance metrics"""
        self._loop_count += 1
        now = time.perf_counter()
        
        # Update FPS calculation every 100ms for smoother display
        if now - self._last_fps_time >= 0.1:
            elapsed = now - self._last_fps_time
            self.state.loop_fps = self._loop_count / elapsed
            self._loop_count = 0
            self._last_fps_time = now
            
            # Get subsystem FPS
            if self.capture:
                self.state.capture_fps = self.capture.fps
            # DET = actual loop iterations/sec (real DPS, not theoretical)
            self.state.detection_fps = self.state.loop_fps
            
            # Callback - fires every 100ms now
            if self.on_state_change:
                self.on_state_change(self.state)
        
        self.state.latency_ms = (now - start_time) * 1000

    def reset_state(self):
        """Reset internal state and counters"""
        self.state = AssistantState()
        self._paused = False
        self._aim_key_pressed = False
        self._flick_key_pressed = False
        self._trigger_key_pressed = False
        self._aim_start_time = 0.0
        self._last_trigger_time = 0.0
        self._loop_count = 0
        self._last_fps_time = 0.0
        self._warmup_frames_left = 0
        
        # Trigger state
        self._trigger_key_press_time = 0.0
        self._trigger_first_detection_time = 0.0
        self._trigger_was_on_color = False
        self._trigger_next_shot_delay = 0.0
        
        self.aim_humanizer.reset()
        self.flick_humanizer.reset()
        self.pid_controller.reset()
        
        if self.detector and hasattr(self.detector, "reset"):
            try:
                self.detector.reset()
            except Exception:
                pass
    
    # Input handling
    def set_aim_key_state(self, pressed: bool):
        """Set aim key state"""
        with self._lock:
            if pressed and not self._aim_key_pressed:
                self._aim_start_time = 0
                self.aim_humanizer.reset()
            self._aim_key_pressed = pressed
    
    def set_flick_key_state(self, pressed: bool):
        """Set flick key state"""
        with self._lock:
            if pressed and not self._flick_key_pressed:
                self.flick_humanizer.reset()
            self._flick_key_pressed = pressed
    
    def set_trigger_key_state(self, pressed: bool):
        """Set trigger key state"""
        with self._lock:
            self._trigger_key_pressed = pressed
    
    def reload_config(self):
        """Reload configuration"""
        self.config = get_config()
        
        # Update subsystems
        if self.selector:
            self.selector.set_fov(self.config.aim.aim_fov)
            self.selector.set_aim_bone(
                self.config.detection.aim_bone,
                self.config.detection.bone_scale
            )
        
        self.mouse.set_sensitivity(
            dpi=self.config.mouse.dpi_value,
            in_game=self.config.mouse.in_game_sens,
            reference=self.config.mouse.reference_sens
        )
        
        self._configure_humanizer(self.aim_humanizer, self.config.humanizer)
        self._configure_humanizer(self.flick_humanizer, self.config.flick_humanizer)
    
    @property
    def is_running(self) -> bool:
        """Check if assistant is running"""
        return self._running
    
    @property  
    def is_paused(self) -> bool:
        """Check if assistant is paused"""
        return self._paused
    
    def _check_input_state(self):
        """Check mouse button states - uses InputBlocker for blocked buttons"""
        # Map config key names to virtual key codes
        key_map = {
            "left_click": VK_LBUTTON,
            "right_click": VK_RBUTTON,
            "middle_click": VK_MBUTTON,
            "forward_button": VK_XBUTTON2,
            "back_button": VK_XBUTTON1,
        }
        
        # Helper to check button state (uses blocker if enabled)
        def is_button_pressed(button_name: str) -> bool:
            # Prefer hook state if available (works reliably for X buttons)
            if self.input_blocker.is_running and self.input_blocker.has_state(button_name):
                return self.input_blocker.is_button_pressed(button_name)
            # Otherwise use Windows API
            vk = key_map.get(button_name, VK_XBUTTON2)
            return bool(GetAsyncKeyState(vk) & 0x8000)
        
        # Check aim key
        aim_pressed = is_button_pressed(self.config.aim.aim_key)
        
        if aim_pressed != self._aim_key_pressed:
            if aim_pressed and not self._aim_key_pressed:
                self._aim_start_time = 0
                self.aim_humanizer.reset()
            self._aim_key_pressed = aim_pressed
        self.state.aim_key_down = self._aim_key_pressed
        
        # Check flick key
        flick_pressed = is_button_pressed(self.config.flick.flick_key)
        
        if flick_pressed != self._flick_key_pressed:
            if flick_pressed and not self._flick_key_pressed:
                self.flick_humanizer.reset()
            self._flick_key_pressed = flick_pressed
        self.state.flick_key_down = self._flick_key_pressed
        
        # Check trigger key
        trigger_pressed = is_button_pressed(self.config.trigger.trigger_key)
        
        # Track when trigger key was FIRST pressed (for reaction time logic)
        if trigger_pressed and not self._trigger_key_pressed:
            # Key just pressed - record time
            self._trigger_key_press_time = time.perf_counter() * 1000
            self._trigger_first_detection_time = 0  # Reset detection tracking
            self._trigger_was_on_color = False
        elif not trigger_pressed and self._trigger_key_pressed:
            # Key RELEASED - reset everything including last shot time
            # This is the ONLY place where _last_trigger_time should reset!
            self._trigger_key_press_time = 0
            self._trigger_first_detection_time = 0
            self._trigger_was_on_color = False
            self._last_trigger_time = 0  # Reset shot timer on key release
            self._trigger_next_shot_delay = 0  # Reset delay so next trigger press shoots instantly
        
        self._trigger_key_pressed = trigger_pressed
        self.state.trigger_key_down = self._trigger_key_pressed
