"""
Flick & Trigger Tab - Minimal Design
"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QComboBox, QScrollArea, QFrame
)
from PyQt6.QtCore import Qt

from ..widgets.section_widget import SectionWidget
from ..widgets.slider_widget import SliderWidget, RangeSliderWidget
from ..widgets.toggle_switch import LabeledToggle, ToggleWithStatus
from ...core.config import Config


class FlickTriggerTab(QWidget):
    """Flick and trigger config"""
    
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
        
        # Flick
        flick = SectionWidget("Flick Assist")
        
        self.flick_enabled = ToggleWithStatus("Enable Flick", False, "Active", "Off")
        self.flick_enabled.toggled.connect(lambda v: setattr(self.config.flick, 'enabled', v))
        flick.addWidget(self.flick_enabled)
        
        key_row = QHBoxLayout()
        key_row.addWidget(QLabel("Key"))
        key_row.addStretch()
        self.flick_key = QComboBox()
        self.flick_key.addItems(["Left Click", "Right Click", "Forward Button", "Back Button"])
        self.flick_key.setFixedWidth(120)
        self.flick_key.currentTextChanged.connect(self._on_flick_key)
        key_row.addWidget(self.flick_key)
        flick.addLayout(key_row)
        
        self.flick_fov = SliderWidget("FOV", 5, 200, 30)
        self.flick_fov.valueChanged.connect(lambda v: setattr(self.config.flick, 'flick_fov', int(v)))
        flick.addWidget(self.flick_fov)
        
        self.flick_reaction = SliderWidget("Reaction", 0, 200, 60, suffix="ms")
        self.flick_reaction.valueChanged.connect(lambda v: setattr(self.config.flick, 'reaction_time', int(v)))
        flick.addWidget(self.flick_reaction)
        
        self.flick_smooth_x = SliderWidget("Smooth X", 1, 500, 200)
        self.flick_smooth_x.valueChanged.connect(lambda v: setattr(self.config.flick, 'smooth_x', v))
        flick.addWidget(self.flick_smooth_x)
        
        self.flick_smooth_y = SliderWidget("Smooth Y", 1, 500, 200)
        self.flick_smooth_y.valueChanged.connect(lambda v: setattr(self.config.flick, 'smooth_y', v))
        flick.addWidget(self.flick_smooth_y)
        
        layout.addWidget(flick)
        
        # Trigger
        trigger = SectionWidget("Triggerbot")
        
        self.trigger_enabled = ToggleWithStatus("Enable Trigger", False, "Active", "Off")
        self.trigger_enabled.toggled.connect(lambda v: setattr(self.config.trigger, 'enabled', v))
        trigger.addWidget(self.trigger_enabled)
        
        tkey_row = QHBoxLayout()
        tkey_row.addWidget(QLabel("Key"))
        tkey_row.addStretch()
        self.trigger_key = QComboBox()
        self.trigger_key.addItems(["Left Click", "Right Click", "Forward Button", "Back Button"])
        self.trigger_key.setFixedWidth(120)
        self.trigger_key.currentTextChanged.connect(self._on_trigger_key)
        tkey_row.addWidget(self.trigger_key)
        trigger.addLayout(tkey_row)
        
        self.trigger_scale = SliderWidget("Trigger Scale", 1, 100, 50, suffix="%")
        self.trigger_scale.setToolTip("How much of the bounding box crosshair must be within\nLow (10-30%) = stricter, must be near center\nHigh (50-80%) = more lenient")
        self.trigger_scale.valueChanged.connect(lambda v: setattr(self.config.trigger, 'trigger_scale', int(v)))
        trigger.addWidget(self.trigger_scale)
        
        layout.addWidget(trigger)
        
        # Timing
        timing = SectionWidget("Trigger Timing")
        
        self.first_shot = RangeSliderWidget("1st Shot Delay", 0, 300, 82, 124, suffix="ms")
        self.first_shot.rangeChanged.connect(self._on_first_shot)
        timing.addWidget(self.first_shot)
        
        self.multi_shot = RangeSliderWidget("Multi-Shot Delay", 0, 5000, 170, 210, suffix="ms")
        self.multi_shot.rangeChanged.connect(self._on_multi_shot)
        timing.addWidget(self.multi_shot)
        
        layout.addWidget(timing)
        layout.addStretch()
        
        scroll.setWidget(content)
        
        main = QVBoxLayout(self)
        main.setContentsMargins(0, 0, 0, 0)
        main.addWidget(scroll)
    
    def _load_config(self):
        # Block signals during loading
        widgets = [self.flick_enabled, self.flick_fov, self.flick_reaction, 
                   self.flick_smooth_x, self.flick_smooth_y, self.flick_key,
                   self.trigger_enabled, self.trigger_scale, self.trigger_key,
                   self.first_shot, self.multi_shot]
        for w in widgets:
            w.blockSignals(True)
        
        f = self.config.flick
        t = self.config.trigger
        
        self.flick_enabled.setChecked(f.enabled)
        self.flick_fov.setValue(f.flick_fov)
        self.flick_reaction.setValue(f.reaction_time)
        self.flick_smooth_x.setValue(f.smooth_x)
        self.flick_smooth_y.setValue(f.smooth_y)
        
        key_map = {"left_click": "Left Click", "right_click": "Right Click",
                   "forward_button": "Forward Button", "back_button": "Back Button"}
        self.flick_key.setCurrentText(key_map.get(f.flick_key, "Back Button"))
        
        self.trigger_enabled.setChecked(t.enabled)
        self.trigger_scale.setValue(getattr(t, 'trigger_scale', 50))
        self.trigger_key.setCurrentText(key_map.get(t.trigger_key, "Back Button"))
        self.first_shot.setMinValue(t.first_shot_delay_min)
        self.first_shot.setMaxValue(t.first_shot_delay_max)
        self.multi_shot.setMinValue(t.multi_shot_delay_min)
        self.multi_shot.setMaxValue(t.multi_shot_delay_max)
        
        # Unblock signals
        for w in widgets:
            w.blockSignals(False)
    
    def _on_flick_key(self, text):
        key_map = {"Left Click": "left_click", "Right Click": "right_click",
                   "Forward Button": "forward_button", "Back Button": "back_button"}
        self.config.flick.flick_key = key_map.get(text, "back_button")
    
    def _on_trigger_key(self, text):
        key_map = {"Left Click": "left_click", "Right Click": "right_click",
                   "Forward Button": "forward_button", "Back Button": "back_button"}
        self.config.trigger.trigger_key = key_map.get(text, "back_button")
    
    def _on_first_shot(self, min_v, max_v):
        self.config.trigger.first_shot_delay_min = int(min_v)
        self.config.trigger.first_shot_delay_max = int(max_v)
    
    def _on_multi_shot(self, min_v, max_v):
        self.config.trigger.multi_shot_delay_min = int(min_v)
        self.config.trigger.multi_shot_delay_max = int(max_v)
