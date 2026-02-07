"""
Humanizer Tab - Minimal Design
Complete humanization settings
"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QComboBox, QScrollArea, QFrame, QTabWidget,
    QDoubleSpinBox, QSpinBox, QGridLayout
)
from PyQt6.QtCore import Qt

from ..widgets.section_widget import SectionWidget
from ..widgets.slider_widget import SliderWidget
from ..widgets.toggle_switch import LabeledToggle, ToggleWithStatus
from ...core.config import Config


class HumanizerSubTab(QWidget):
    """Complete humanizer settings"""
    
    def __init__(self, config: Config, is_flick: bool = False, parent=None):
        super().__init__(parent)
        self.config = config
        self.is_flick = is_flick
        self._hum = config.flick_humanizer if is_flick else config.humanizer
        self._setup_ui()
        self._load_config()
        self._connect()
    
    def _spin(self, min_v: float, max_v: float, val: float, dec: int = 2, width: int = 60) -> QDoubleSpinBox:
        """Create compact spinbox"""
        s = QDoubleSpinBox()
        s.setRange(min_v, max_v)
        s.setDecimals(dec)
        s.setValue(val)
        s.setFixedWidth(width)
        s.setButtonSymbols(QDoubleSpinBox.ButtonSymbols.NoButtons)
        s.setKeyboardTracking(False)
        return s
    
    def _ispin(self, min_v: int, max_v: int, val: int, width: int = 50) -> QSpinBox:
        """Create compact int spinbox"""
        s = QSpinBox()
        s.setRange(min_v, max_v)
        s.setValue(val)
        s.setFixedWidth(width)
        s.setButtonSymbols(QSpinBox.ButtonSymbols.NoButtons)
        s.setKeyboardTracking(False)
        return s
    
    def _lbl(self, text: str) -> QLabel:
        l = QLabel(text)
        l.setStyleSheet("color: #64748b; font-size: 10px;")
        return l
    
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
        enable = SectionWidget("Humanization")
        prefix = "Flick" if self.is_flick else "Aim"
        self.enabled = ToggleWithStatus(f"{prefix} Humanizer", False, "On", "Off")
        enable.addWidget(self.enabled)
        
        mode_row = QHBoxLayout()
        mode_row.addWidget(self._lbl("Mode"))
        mode_row.addStretch()
        self.mode = QComboBox()
        self.mode.addItems(["Traditional"])
        self.mode.setFixedWidth(120)
        mode_row.addWidget(self.mode)
        enable.addLayout(mode_row)
        layout.addWidget(enable)
        
        # WindMouse
        wm = SectionWidget("WindMouse Algorithm")
        self.wm_enabled = LabeledToggle("Enable WindMouse")
        wm.addWidget(self.wm_enabled)
        
        # Grid for windmouse params
        wm_grid = QGridLayout()
        wm_grid.setSpacing(6)
        
        wm_grid.addWidget(self._lbl("Gravity"), 0, 0)
        self.min_grav = self._spin(0, 50, 5.0)
        wm_grid.addWidget(self.min_grav, 0, 1)
        wm_grid.addWidget(self._lbl("-"), 0, 2)
        self.max_grav = self._spin(0, 50, 12.0)
        wm_grid.addWidget(self.max_grav, 0, 3)
        
        wm_grid.addWidget(self._lbl("Wind"), 1, 0)
        self.min_wind = self._spin(0, 50, 5.0)
        wm_grid.addWidget(self.min_wind, 1, 1)
        wm_grid.addWidget(self._lbl("-"), 1, 2)
        self.max_wind = self._spin(0, 50, 16.0)
        wm_grid.addWidget(self.max_wind, 1, 3)
        
        wm_grid.addWidget(self._lbl("Speed"), 2, 0)
        self.min_speed = self._spin(0, 100, 15.0)
        wm_grid.addWidget(self.min_speed, 2, 1)
        wm_grid.addWidget(self._lbl("-"), 2, 2)
        self.max_speed = self._spin(0, 100, 25.0)
        wm_grid.addWidget(self.max_speed, 2, 3)
        
        wm_grid.addWidget(self._lbl("Damp"), 3, 0)
        self.min_damp = self._spin(0, 10, 1.0)
        wm_grid.addWidget(self.min_damp, 3, 1)
        wm_grid.addWidget(self._lbl("-"), 3, 2)
        self.max_damp = self._spin(0, 10, 2.0)
        wm_grid.addWidget(self.max_damp, 3, 3)
        
        wm_grid.setColumnStretch(4, 1)
        wm.addLayout(wm_grid)
        layout.addWidget(wm)
        
        # Advanced
        adv = SectionWidget("Advanced (Always-On)")
        self.momentum = LabeledToggle("Momentum Tracking")
        adv.addWidget(self.momentum)
        layout.addWidget(adv)
        
        # Stop/Pause + Pattern (side by side)
        dual1 = QHBoxLayout()
        dual1.setSpacing(10)
        
        stop = SectionWidget("Stop/Pause")
        self.stop_enabled = LabeledToggle("Enable")
        stop.addWidget(self.stop_enabled)
        
        stop_row = QHBoxLayout()
        stop_row.addWidget(self._lbl("Chance"))
        self.stop_chance = self._spin(0, 1, 0.002, 3)
        stop_row.addWidget(self.stop_chance)
        stop_row.addStretch()
        stop.addLayout(stop_row)
        
        stop_row2 = QHBoxLayout()
        stop_row2.addWidget(self._lbl("Pause"))
        self.stop_min = self._spin(0, 500, 1.0, 1, 50)
        stop_row2.addWidget(self.stop_min)
        stop_row2.addWidget(self._lbl("-"))
        self.stop_max = self._spin(0, 500, 120.0, 1, 50)
        stop_row2.addWidget(self.stop_max)
        stop_row2.addStretch()
        stop.addLayout(stop_row2)
        dual1.addWidget(stop)
        
        pattern = SectionWidget("Pattern Masking")
        self.pattern_enabled = LabeledToggle("Enable")
        pattern.addWidget(self.pattern_enabled)
        
        pat_row = QHBoxLayout()
        pat_row.addWidget(self._lbl("Intensity"))
        self.pat_int = self._spin(0, 10, 1.0, 1, 50)
        pat_row.addWidget(self.pat_int)
        pat_row.addWidget(self._lbl("Scale"))
        self.pat_scale = self._spin(0, 10, 1.0, 2, 50)
        pat_row.addWidget(self.pat_scale)
        pat_row.addStretch()
        pattern.addLayout(pat_row)
        dual1.addWidget(pattern)
        
        layout.addLayout(dual1)
        
        # Sub-Movement + Proximity
        dual2 = QHBoxLayout()
        dual2.setSpacing(10)
        
        sub = SectionWidget("Sub-Movement")
        self.sub_enabled = LabeledToggle("Enable")
        sub.addWidget(self.sub_enabled)
        
        sub_row = QHBoxLayout()
        sub_row.addWidget(self._lbl("Pause"))
        self.sub_min = self._spin(0, 500, 50.0, 1, 50)
        sub_row.addWidget(self.sub_min)
        sub_row.addWidget(self._lbl("-"))
        self.sub_max = self._spin(0, 500, 150.0, 1, 50)
        sub_row.addWidget(self.sub_max)
        sub_row.addStretch()
        sub.addLayout(sub_row)
        
        sub_row2 = QHBoxLayout()
        sub_row2.addWidget(self._lbl("Dist"))
        self.sub_dist = self._spin(0, 200, 30.0, 1, 50)
        sub_row2.addWidget(self.sub_dist)
        sub_row2.addWidget(self._lbl("Chance%"))
        self.sub_chance = self._spin(0, 100, 35.0, 1, 50)
        sub_row2.addWidget(self.sub_chance)
        sub_row2.addStretch()
        sub.addLayout(sub_row2)
        dual2.addWidget(sub)
        
        prox = SectionWidget("Proximity Pause")
        self.prox_enabled = LabeledToggle("Enable")
        prox.addWidget(self.prox_enabled)
        
        prox_row = QHBoxLayout()
        prox_row.addWidget(self._lbl("Thresh"))
        self.prox_thresh = self._ispin(1, 100, 15, 40)
        prox_row.addWidget(self.prox_thresh)
        prox_row.addWidget(self._lbl("Chance%"))
        self.prox_chance = self._spin(0, 100, 27.0, 1, 50)
        prox_row.addWidget(self.prox_chance)
        prox_row.addStretch()
        prox.addLayout(prox_row)
        
        prox_row2 = QHBoxLayout()
        prox_row2.addWidget(self._lbl("Pause"))
        self.prox_min = self._spin(0, 500, 50.0, 1, 50)
        prox_row2.addWidget(self.prox_min)
        prox_row2.addWidget(self._lbl("-"))
        self.prox_max = self._spin(0, 500, 150.0, 1, 50)
        prox_row2.addWidget(self.prox_max)
        prox_row2.addStretch()
        prox.addLayout(prox_row2)
        
        prox_row3 = QHBoxLayout()
        prox_row3.addWidget(self._lbl("Cooldown"))
        self.prox_cd = self._spin(0, 1000, 300.0, 1)
        prox_row3.addWidget(self.prox_cd)
        prox_row3.addStretch()
        prox.addLayout(prox_row3)
        dual2.addWidget(prox)
        
        layout.addLayout(dual2)
        
        # Easing
        ease = SectionWidget("Easing System")
        ease_row = QHBoxLayout()
        ease_row.addWidget(self._lbl("Out"))
        self.ease_out = self._spin(0, 500, 80.0, 1, 50)
        ease_row.addWidget(self.ease_out)
        ease_row.addWidget(self._lbl("In"))
        self.ease_in = self._spin(0, 500, 80.0, 1, 50)
        ease_row.addWidget(self.ease_in)
        ease_row.addWidget(self._lbl("Curve"))
        self.ease_curve = self._spin(0.1, 10, 3.0, 1, 50)
        ease_row.addWidget(self.ease_curve)
        ease_row.addStretch()
        ease.addLayout(ease_row)
        layout.addWidget(ease)
        
        # Momentum System
        mom = SectionWidget("Momentum System")
        mom_row = QHBoxLayout()
        mom_row.addWidget(self._lbl("Decay"))
        self.mom_decay = self._spin(0, 1, 0.88, 2, 50)
        mom_row.addWidget(self.mom_decay)
        mom_row.addWidget(self._lbl("Lead"))
        self.mom_lead = self._spin(0, 5, 1.18, 2, 50)
        mom_row.addWidget(self.mom_lead)
        mom_row.addWidget(self._lbl("Dead"))
        self.mom_dead = self._spin(0, 50, 4.0, 1, 50)
        mom_row.addWidget(self.mom_dead)
        mom_row.addStretch()
        mom.addLayout(mom_row)
        
        mom_row2 = QHBoxLayout()
        mom_row2.addWidget(self._lbl("CorrProb"))
        self.mom_prob = self._spin(0, 1, 0.52, 2, 50)
        mom_row2.addWidget(self.mom_prob)
        mom_row2.addWidget(self._lbl("CorrStr"))
        self.mom_str = self._spin(0, 2, 0.42, 2, 50)
        mom_row2.addWidget(self.mom_str)
        mom_row2.addStretch()
        mom.addLayout(mom_row2)
        layout.addWidget(mom)
        
        # Entropy
        entropy = SectionWidget("Entropy-Aware")
        
        # Speed Variance
        sv_row = QHBoxLayout()
        self.sv_enabled = LabeledToggle("Speed Var")
        sv_row.addWidget(self.sv_enabled)
        sv_row.addWidget(self._lbl("Min"))
        self.sv_min = self._spin(0, 2, 0.46, 2, 45)
        sv_row.addWidget(self.sv_min)
        sv_row.addWidget(self._lbl("Max"))
        self.sv_max = self._spin(0, 2, 0.90, 2, 45)
        sv_row.addWidget(self.sv_max)
        sv_row.addWidget(self._lbl("Freq"))
        self.sv_fmin = self._spin(0, 1, 0.09, 2, 45)
        sv_row.addWidget(self.sv_fmin)
        sv_row.addWidget(self._lbl("-"))
        self.sv_fmax = self._spin(0, 1, 0.30, 2, 45)
        sv_row.addWidget(self.sv_fmax)
        sv_row.addStretch()
        entropy.addLayout(sv_row)
        
        # Path Curvature
        pc_row = QHBoxLayout()
        self.pc_enabled = LabeledToggle("Path Curv")
        pc_row.addWidget(self.pc_enabled)
        pc_row.addWidget(self._lbl("Min"))
        self.pc_min = self._spin(0, 10, 1.1, 1, 45)
        pc_row.addWidget(self.pc_min)
        pc_row.addWidget(self._lbl("Max"))
        self.pc_max = self._spin(0, 10, 3.0, 1, 45)
        pc_row.addWidget(self.pc_max)
        pc_row.addWidget(self._lbl("Freq"))
        self.pc_fmin = self._spin(0, 1, 0.04, 2, 45)
        pc_row.addWidget(self.pc_fmin)
        pc_row.addWidget(self._lbl("-"))
        self.pc_fmax = self._spin(0, 1, 0.28, 2, 45)
        pc_row.addWidget(self.pc_fmax)
        pc_row.addStretch()
        entropy.addLayout(pc_row)
        
        # Endpoint
        ep_row = QHBoxLayout()
        self.ep_enabled = LabeledToggle("Endpoint")
        ep_row.addWidget(self.ep_enabled)
        ep_row.addWidget(self._lbl("Dist"))
        self.ep_dist = self._spin(0, 50, 9.0, 1, 45)
        ep_row.addWidget(self.ep_dist)
        ep_row.addWidget(self._lbl("Int"))
        self.ep_int = self._spin(0, 10, 2.5, 2, 45)
        ep_row.addWidget(self.ep_int)
        ep_row.addStretch()
        entropy.addLayout(ep_row)
        
        layout.addWidget(entropy)
        layout.addStretch()
        
        scroll.setWidget(content)
        
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.addWidget(scroll)
    
    def _connect(self):
        h = self._hum
        
        self.enabled.toggled.connect(lambda v: setattr(h, 'enabled', v))
        
        # WindMouse
        self.wm_enabled.toggled.connect(lambda v: setattr(h.wind_mouse, 'enabled', v))
        self.min_grav.valueChanged.connect(lambda v: setattr(h.wind_mouse, 'min_gravity', v))
        self.max_grav.valueChanged.connect(lambda v: setattr(h.wind_mouse, 'max_gravity', v))
        self.min_wind.valueChanged.connect(lambda v: setattr(h.wind_mouse, 'min_wind', v))
        self.max_wind.valueChanged.connect(lambda v: setattr(h.wind_mouse, 'max_wind', v))
        self.min_speed.valueChanged.connect(lambda v: setattr(h.wind_mouse, 'min_speed', v))
        self.max_speed.valueChanged.connect(lambda v: setattr(h.wind_mouse, 'max_speed', v))
        self.min_damp.valueChanged.connect(lambda v: setattr(h.wind_mouse, 'min_damp', v))
        self.max_damp.valueChanged.connect(lambda v: setattr(h.wind_mouse, 'max_damp', v))
        
        self.momentum.toggled.connect(lambda v: setattr(h, 'momentum_tracking', v))
        
        # Stop/Pause
        self.stop_enabled.toggled.connect(lambda v: setattr(h, 'stop_pause_enabled', v))
        self.stop_chance.valueChanged.connect(lambda v: setattr(h, 'stop_pause_chance', v))
        self.stop_min.valueChanged.connect(lambda v: setattr(h, 'stop_pause_min', v))
        self.stop_max.valueChanged.connect(lambda v: setattr(h, 'stop_pause_max', v))
        
        # Pattern
        self.pattern_enabled.toggled.connect(lambda v: setattr(h, 'pattern_masking_enabled', v))
        self.pat_int.valueChanged.connect(lambda v: setattr(h, 'pattern_masking_intensity', v))
        self.pat_scale.valueChanged.connect(lambda v: setattr(h, 'pattern_masking_scale', v))
        
        # Sub-Movement
        self.sub_enabled.toggled.connect(lambda v: setattr(h, 'sub_movements_enabled', v))
        self.sub_min.valueChanged.connect(lambda v: setattr(h, 'sub_movements_min_pause', v))
        self.sub_max.valueChanged.connect(lambda v: setattr(h, 'sub_movements_max_pause', v))
        self.sub_dist.valueChanged.connect(lambda v: setattr(h, 'sub_movements_min_dist', v))
        self.sub_chance.valueChanged.connect(lambda v: setattr(h, 'sub_movements_chance', v / 100))
        
        # Proximity
        self.prox_enabled.toggled.connect(lambda v: setattr(h, 'proximity_pause_enabled', v))
        self.prox_thresh.valueChanged.connect(lambda v: setattr(h, 'proximity_threshold', v))
        self.prox_chance.valueChanged.connect(lambda v: setattr(h, 'proximity_chance', v / 100))
        self.prox_min.valueChanged.connect(lambda v: setattr(h, 'proximity_min_pause', v))
        self.prox_max.valueChanged.connect(lambda v: setattr(h, 'proximity_max_pause', v))
        self.prox_cd.valueChanged.connect(lambda v: setattr(h, 'proximity_cooldown', v))
        
        # Easing
        self.ease_out.valueChanged.connect(lambda v: setattr(h, 'ease_out', v))
        self.ease_in.valueChanged.connect(lambda v: setattr(h, 'ease_in', v))
        self.ease_curve.valueChanged.connect(lambda v: setattr(h, 'ease_curve', v))
        
        # Momentum
        self.mom_decay.valueChanged.connect(lambda v: setattr(h, 'momentum_decay', v))
        self.mom_lead.valueChanged.connect(lambda v: setattr(h, 'momentum_lead_bias', v))
        self.mom_dead.valueChanged.connect(lambda v: setattr(h, 'momentum_deadzone', v))
        self.mom_prob.valueChanged.connect(lambda v: setattr(h, 'momentum_corr_prob', v))
        self.mom_str.valueChanged.connect(lambda v: setattr(h, 'momentum_corr_str', v))
        
        # Entropy
        self.sv_enabled.toggled.connect(lambda v: setattr(h, 'speed_variance_enabled', v))
        self.sv_min.valueChanged.connect(lambda v: setattr(h, 'speed_variance_min', v))
        self.sv_max.valueChanged.connect(lambda v: setattr(h, 'speed_variance_max', v))
        self.sv_fmin.valueChanged.connect(lambda v: setattr(h, 'speed_variance_freq_min', v))
        self.sv_fmax.valueChanged.connect(lambda v: setattr(h, 'speed_variance_freq_max', v))
        
        self.pc_enabled.toggled.connect(lambda v: setattr(h, 'path_curvature_enabled', v))
        self.pc_min.valueChanged.connect(lambda v: setattr(h, 'path_curvature_min', v))
        self.pc_max.valueChanged.connect(lambda v: setattr(h, 'path_curvature_max', v))
        self.pc_fmin.valueChanged.connect(lambda v: setattr(h, 'path_curvature_freq_min', v))
        self.pc_fmax.valueChanged.connect(lambda v: setattr(h, 'path_curvature_freq_max', v))
        
        self.ep_enabled.toggled.connect(lambda v: setattr(h, 'endpoint_settling_enabled', v))
        self.ep_dist.valueChanged.connect(lambda v: setattr(h, 'endpoint_settling_dist', v))
        self.ep_int.valueChanged.connect(lambda v: setattr(h, 'endpoint_settling_intensity', v))
    
    def _load_config(self):
        # Collect all input widgets and block signals
        widgets = [
            self.enabled, self.wm_enabled, self.min_grav, self.max_grav, 
            self.min_wind, self.max_wind, self.min_speed, self.max_speed,
            self.min_damp, self.max_damp, self.momentum, self.stop_enabled,
            self.stop_chance, self.stop_min, self.stop_max, self.pattern_enabled,
            self.pat_int, self.pat_scale, self.sub_enabled, self.sub_min,
            self.sub_max, self.sub_dist, self.sub_chance, self.prox_enabled,
            self.prox_thresh, self.prox_chance, self.prox_min, self.prox_max,
            self.prox_cd, self.ease_out, self.ease_in, self.ease_curve,
            self.mom_decay, self.mom_lead, self.mom_dead, self.mom_prob,
            self.mom_str, self.sv_enabled, self.sv_min, self.sv_max,
            self.sv_fmin, self.sv_fmax, self.pc_enabled, self.pc_min,
            self.pc_max, self.pc_fmin, self.pc_fmax, self.ep_enabled,
            self.ep_dist, self.ep_int
        ]
        for w in widgets:
            w.blockSignals(True)
        
        h = self._hum
        
        self.enabled.setChecked(h.enabled)
        
        # WindMouse
        self.wm_enabled.setChecked(h.wind_mouse.enabled)
        self.min_grav.setValue(h.wind_mouse.min_gravity)
        self.max_grav.setValue(h.wind_mouse.max_gravity)
        self.min_wind.setValue(h.wind_mouse.min_wind)
        self.max_wind.setValue(h.wind_mouse.max_wind)
        self.min_speed.setValue(h.wind_mouse.min_speed)
        self.max_speed.setValue(h.wind_mouse.max_speed)
        self.min_damp.setValue(h.wind_mouse.min_damp)
        self.max_damp.setValue(h.wind_mouse.max_damp)
        
        self.momentum.setChecked(h.momentum_tracking)
        
        # Stop/Pause
        self.stop_enabled.setChecked(h.stop_pause_enabled)
        self.stop_chance.setValue(h.stop_pause_chance)
        self.stop_min.setValue(h.stop_pause_min)
        self.stop_max.setValue(h.stop_pause_max)
        
        # Pattern
        self.pattern_enabled.setChecked(h.pattern_masking_enabled)
        self.pat_int.setValue(h.pattern_masking_intensity)
        self.pat_scale.setValue(h.pattern_masking_scale)
        
        # Sub-Movement
        self.sub_enabled.setChecked(h.sub_movements_enabled)
        self.sub_min.setValue(h.sub_movements_min_pause)
        self.sub_max.setValue(h.sub_movements_max_pause)
        self.sub_dist.setValue(h.sub_movements_min_dist)
        self.sub_chance.setValue(h.sub_movements_chance * 100)
        
        # Proximity
        self.prox_enabled.setChecked(h.proximity_pause_enabled)
        self.prox_thresh.setValue(h.proximity_threshold)
        self.prox_chance.setValue(h.proximity_chance * 100)
        self.prox_min.setValue(h.proximity_min_pause)
        self.prox_max.setValue(h.proximity_max_pause)
        self.prox_cd.setValue(h.proximity_cooldown)
        
        # Easing
        self.ease_out.setValue(h.ease_out)
        self.ease_in.setValue(h.ease_in)
        self.ease_curve.setValue(h.ease_curve)
        
        # Momentum
        self.mom_decay.setValue(h.momentum_decay)
        self.mom_lead.setValue(h.momentum_lead_bias)
        self.mom_dead.setValue(h.momentum_deadzone)
        self.mom_prob.setValue(h.momentum_corr_prob)
        self.mom_str.setValue(h.momentum_corr_str)
        
        # Entropy
        self.sv_enabled.setChecked(h.speed_variance_enabled)
        self.sv_min.setValue(h.speed_variance_min)
        self.sv_max.setValue(h.speed_variance_max)
        self.sv_fmin.setValue(h.speed_variance_freq_min)
        self.sv_fmax.setValue(h.speed_variance_freq_max)
        
        self.pc_enabled.setChecked(h.path_curvature_enabled)
        self.pc_min.setValue(h.path_curvature_min)
        self.pc_max.setValue(h.path_curvature_max)
        self.pc_fmin.setValue(h.path_curvature_freq_min)
        self.pc_fmax.setValue(h.path_curvature_freq_max)
        
        self.ep_enabled.setChecked(h.endpoint_settling_enabled)
        self.ep_dist.setValue(h.endpoint_settling_dist)
        self.ep_int.setValue(h.endpoint_settling_intensity)
        
        # Unblock signals
        for w in widgets:
            w.blockSignals(False)


class HumanizerTab(QWidget):
    """Humanizer with Aim/Flick tabs"""
    
    def __init__(self, config: Config, parent=None):
        super().__init__(parent)
        self.config = config
        self._setup_ui()
    
    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        self.tabs = QTabWidget()
        self.tabs.setStyleSheet("""
            QTabWidget::pane { border: none; background: transparent; }
            QTabBar::tab {
                background: transparent;
                border: none;
                border-radius: 4px;
                padding: 5px 12px;
                margin-right: 4px;
                color: #64748b;
                font-size: 11px;
            }
            QTabBar::tab:hover { background: rgba(255,255,255,0.04); color: #94a3b8; }
            QTabBar::tab:selected { background: #8b5cf6; color: white; }
        """)
        
        self.tabs.addTab(HumanizerSubTab(self.config, False), "Aim Humanizer")
        self.tabs.addTab(HumanizerSubTab(self.config, True), "Flick Humanizer")
        
        layout.addWidget(self.tabs)
