"""
Aim Tab - Minimal Design
"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
    QComboBox, QScrollArea, QFrame
)
from PyQt6.QtCore import Qt

from ..widgets.section_widget import SectionWidget
from ..widgets.slider_widget import SliderWidget
from ..widgets.toggle_switch import LabeledToggle, ToggleWithStatus
from ...core.config import Config


class AimTab(QWidget):
    """Aim assist config"""
    
    def __init__(self, config: Config, parent=None):
        super().__init__(parent)
        self.config = config
        self._setup_ui()
        self._load_config()
    
    def _setup_ui(self):
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setStyleSheet("background-color: transparent;")
        
        content = QWidget()
        content.setStyleSheet("background-color: transparent;")
        layout = QVBoxLayout(content)
        layout.setSpacing(10)
        layout.setContentsMargins(0, 0, 10, 0)
        
        # Enable
        enable = SectionWidget("Aim Assist")
        
        self.enabled = ToggleWithStatus("Enable Aim Assist", False, "Active", "Off")
        self.enabled.toggled.connect(lambda v: setattr(self.config.aim, 'enabled', v))
        enable.addWidget(self.enabled)
        
        key_row = QHBoxLayout()
        key_row.addWidget(QLabel("Key"))
        key_row.addStretch()
        self.key = QComboBox()
        self.key.addItems(["Left Click", "Right Click", "Forward Button", "Back Button"])
        self.key.setFixedWidth(120)
        self.key.currentTextChanged.connect(self._on_key)
        key_row.addWidget(self.key)
        enable.addLayout(key_row)
        
        mode_row = QHBoxLayout()
        mode_row.addWidget(QLabel("Mode"))
        mode_row.addStretch()
        self.mode = QComboBox()
        self.mode.addItems(["Hold", "Toggle"])
        self.mode.setFixedWidth(120)
        self.mode.currentTextChanged.connect(lambda v: setattr(self.config.aim, 'aim_mode', v.lower()))
        mode_row.addWidget(self.mode)
        enable.addLayout(mode_row)
        
        layout.addWidget(enable)
        
        # Targeting
        targeting = SectionWidget("Targeting")
        
        self.fov = SliderWidget("FOV", 5, 150, 25)
        self.fov.valueChanged.connect(lambda v: setattr(self.config.aim, 'aim_fov', int(v)))
        targeting.addWidget(self.fov)
        
        self.x_offset = SliderWidget("X Offset", -100, 100, 0)
        self.x_offset.valueChanged.connect(lambda v: setattr(self.config.aim, 'x_offset', int(v)))
        targeting.addWidget(self.x_offset)
        
        self.y_offset = SliderWidget("Y Offset", -100, 100, 0)
        self.y_offset.valueChanged.connect(lambda v: setattr(self.config.aim, 'y_offset', int(v)))
        targeting.addWidget(self.y_offset)
        
        self.dynamic_fov = LabeledToggle("Dynamic FOV")
        self.dynamic_fov.toggled.connect(lambda v: setattr(self.config.aim, 'dynamic_fov_enabled', v))
        targeting.addWidget(self.dynamic_fov)
        
        layout.addWidget(targeting)
        
        # Smoothing
        smooth = SectionWidget("Smoothing")
        
        type_row = QHBoxLayout()
        type_row.addWidget(QLabel("Type"))
        type_row.addStretch()
        self.aim_type = QComboBox()
        self.aim_type.addItems(["Aim V2", "Legacy"])
        self.aim_type.setFixedWidth(120)
        self.aim_type.currentTextChanged.connect(self._on_type)
        type_row.addWidget(self.aim_type)
        smooth.addLayout(type_row)
        
        self.reaction = SliderWidget("Reaction", 0, 200, 60, suffix="ms")
        self.reaction.valueChanged.connect(lambda v: setattr(self.config.aim, 'reaction_time', int(v)))
        smooth.addWidget(self.reaction)
        
        self.smooth_x = SliderWidget("Smooth X", 1, 500, 40, decimals=1)
        self.smooth_x.valueChanged.connect(lambda v: setattr(self.config.aim, 'smooth_x', v))
        smooth.addWidget(self.smooth_x)
        
        self.smooth_y = SliderWidget("Smooth Y", 1, 500, 80, decimals=1)
        self.smooth_y.valueChanged.connect(lambda v: setattr(self.config.aim, 'smooth_y', v))
        smooth.addWidget(self.smooth_y)
        
        layout.addWidget(smooth)
        
        # Sticky Aim (Close/Far Smoothing)
        sticky = SectionWidget("Sticky Aim")
        
        self.sticky_enabled = LabeledToggle("Enable Sticky Aim")
        self.sticky_enabled.toggled.connect(lambda v: setattr(self.config.aim, 'sticky_aim_enabled', v))
        sticky.addWidget(self.sticky_enabled)
        
        self.sticky_zone = SliderWidget("Sticky Zone", 5, 100, 25, suffix="px")
        self.sticky_zone.valueChanged.connect(lambda v: setattr(self.config.aim, 'sticky_aim_zone', int(v)))
        sticky.addWidget(self.sticky_zone)
        
        self.smooth_x_close = SliderWidget("Smooth X (Close)", 0.1, 50, 5.2, decimals=1)
        self.smooth_x_close.valueChanged.connect(lambda v: setattr(self.config.aim, 'smooth_x_close', v))
        sticky.addWidget(self.smooth_x_close)
        
        self.smooth_x_far = SliderWidget("Smooth X (Far)", 0.1, 50, 7.4, decimals=1)
        self.smooth_x_far.valueChanged.connect(lambda v: setattr(self.config.aim, 'smooth_x_far', v))
        sticky.addWidget(self.smooth_x_far)
        
        self.smooth_y_close = SliderWidget("Smooth Y (Close)", 0.1, 50, 10.2, decimals=1)
        self.smooth_y_close.valueChanged.connect(lambda v: setattr(self.config.aim, 'smooth_y_close', v))
        sticky.addWidget(self.smooth_y_close)
        
        self.smooth_y_far = SliderWidget("Smooth Y (Far)", 0.1, 50, 16.1, decimals=1)
        self.smooth_y_far.valueChanged.connect(lambda v: setattr(self.config.aim, 'smooth_y_far', v))
        sticky.addWidget(self.smooth_y_far)
        
        layout.addWidget(sticky)
        
        # PID Controller
        pid = SectionWidget("PID Stabilization")
        
        self.pid_enabled = LabeledToggle("Enable PID")
        self.pid_enabled.toggled.connect(lambda v: setattr(self.config.aim, 'pid_enabled', v))
        pid.addWidget(self.pid_enabled)
        
        self.pid_kp = SliderWidget("Kp (Response)", 0.0, 0.01, 0.0002, decimals=4)
        self.pid_kp.valueChanged.connect(lambda v: setattr(self.config.aim, 'pid_kp', v))
        pid.addWidget(self.pid_kp)
        
        self.pid_ki = SliderWidget("Ki (Steady)", 0.0, 0.01, 0.0, decimals=4)
        self.pid_ki.valueChanged.connect(lambda v: setattr(self.config.aim, 'pid_ki', v))
        pid.addWidget(self.pid_ki)
        
        self.pid_kd = SliderWidget("Kd (Damping)", 0.0, 0.01, 0.0006, decimals=4)
        self.pid_kd.valueChanged.connect(lambda v: setattr(self.config.aim, 'pid_kd', v))
        pid.addWidget(self.pid_kd)
        
        self.pid_dist = SliderWidget("Activation Dist", 1, 50, 10, suffix="px")
        self.pid_dist.valueChanged.connect(lambda v: setattr(self.config.aim, 'pid_activation_dist', int(v)))
        pid.addWidget(self.pid_dist)
        
        layout.addWidget(pid)
        
        # ============ Always On ============
        always_on = SectionWidget("Always On (Passive Aim)")
        
        self.ao_enabled = ToggleWithStatus("Enable Always On", False, "Active", "Off")
        self.ao_enabled.toggled.connect(lambda v: setattr(self.config.always_on, 'enabled', v))
        always_on.addWidget(self.ao_enabled)
        
        self.ao_fov = SliderWidget("FOV", 5, 60, 30, suffix="px")
        self.ao_fov.valueChanged.connect(lambda v: setattr(self.config.always_on, 'fov', int(v)))
        always_on.addWidget(self.ao_fov)
        
        self.ao_strength = SliderWidget("Strength", 0.1, 1.0, 0.8, decimals=2)
        self.ao_strength.valueChanged.connect(lambda v: setattr(self.config.always_on, 'strength', v))
        always_on.addWidget(self.ao_strength)
        
        self.ao_smoothing = SliderWidget("Smoothing", 1.0, 30.0, 6.0, decimals=1)
        self.ao_smoothing.valueChanged.connect(lambda v: setattr(self.config.always_on, 'smoothing', v))
        always_on.addWidget(self.ao_smoothing)
        
        self.ao_deadzone = SliderWidget("Deadzone", 0, 10, 2, suffix="px")
        self.ao_deadzone.valueChanged.connect(lambda v: setattr(self.config.always_on, 'deadzone', int(v)))
        always_on.addWidget(self.ao_deadzone)
        
        self.ao_max_corr = SliderWidget("Max Correction", 0.5, 8.0, 2.0, decimals=1, suffix="px")
        self.ao_max_corr.valueChanged.connect(lambda v: setattr(self.config.always_on, 'max_correction', v))
        always_on.addWidget(self.ao_max_corr)
        
        layout.addWidget(always_on)
        layout.addStretch()
        
        scroll.setWidget(content)
        
        main = QVBoxLayout(self)
        main.setContentsMargins(0, 0, 0, 0)
        main.addWidget(scroll)
    
    def _load_config(self):
        # Block signals during loading
        widgets = [self.enabled, self.fov, self.x_offset, self.y_offset, 
                   self.dynamic_fov, self.reaction, self.smooth_x, self.smooth_y,
                   self.key, self.mode, self.aim_type,
                   self.sticky_enabled, self.sticky_zone, self.smooth_x_close, self.smooth_x_far,
                   self.smooth_y_close, self.smooth_y_far,
                   self.pid_enabled, self.pid_kp, self.pid_ki, self.pid_kd, self.pid_dist,
                   self.ao_enabled, self.ao_fov, self.ao_strength, self.ao_smoothing,
                   self.ao_deadzone, self.ao_max_corr]
        for w in widgets:
            w.blockSignals(True)
        
        c = self.config.aim
        self.enabled.setChecked(c.enabled)
        self.fov.setValue(c.aim_fov)
        self.x_offset.setValue(c.x_offset)
        self.y_offset.setValue(c.y_offset)
        self.dynamic_fov.setChecked(c.dynamic_fov_enabled)
        self.reaction.setValue(c.reaction_time)
        self.smooth_x.setValue(c.smooth_x)
        self.smooth_y.setValue(c.smooth_y)
        
        # Sticky Aim
        self.sticky_enabled.setChecked(c.sticky_aim_enabled)
        self.sticky_zone.setValue(c.sticky_aim_zone)
        self.smooth_x_close.setValue(c.smooth_x_close)
        self.smooth_x_far.setValue(c.smooth_x_far)
        self.smooth_y_close.setValue(c.smooth_y_close)
        self.smooth_y_far.setValue(c.smooth_y_far)
        
        # PID
        self.pid_enabled.setChecked(c.pid_enabled)
        self.pid_kp.setValue(c.pid_kp)
        self.pid_ki.setValue(c.pid_ki)
        self.pid_kd.setValue(c.pid_kd)
        self.pid_dist.setValue(c.pid_activation_dist)
        
        key_map = {"left_click": "Left Click", "right_click": "Right Click",
                   "forward_button": "Forward Button", "back_button": "Back Button"}
        self.key.setCurrentText(key_map.get(c.aim_key, "Forward Button"))
        self.mode.setCurrentText(c.aim_mode.capitalize())
        
        type_map = {"aim_v2": "Aim V2", "legacy": "Legacy"}
        self.aim_type.setCurrentText(type_map.get(c.aim_type, "Aim V2"))
        
        # Always On
        ao = self.config.always_on
        self.ao_enabled.setChecked(ao.enabled)
        self.ao_fov.setValue(ao.fov)
        self.ao_strength.setValue(ao.strength)
        self.ao_smoothing.setValue(ao.smoothing)
        self.ao_deadzone.setValue(ao.deadzone)
        self.ao_max_corr.setValue(ao.max_correction)
        
        # Unblock signals
        for w in widgets:
            w.blockSignals(False)
    
    def _on_key(self, text):
        key_map = {"Left Click": "left_click", "Right Click": "right_click",
                   "Forward Button": "forward_button", "Back Button": "back_button"}
        self.config.aim.aim_key = key_map.get(text, "forward_button")
    
    def _on_type(self, text):
        type_map = {"Aim V2": "aim_v2", "Legacy": "legacy"}
        self.config.aim.aim_type = type_map.get(text, "aim_v2")
