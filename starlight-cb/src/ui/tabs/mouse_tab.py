"""
Mouse Device Tab - Configure mouse device and button blocking
"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame, QScrollArea,
    QComboBox, QPushButton, QLineEdit
)
from PyQt6.QtCore import Qt

from ..widgets.section_widget import SectionWidget
from ..widgets.toggle_switch import LabeledToggle
from ..widgets.slider_widget import SliderWidget
from ...core.config import Config


class MouseDeviceTab(QWidget):
    """Mouse device configuration tab"""
    
    def __init__(self, config: Config, parent=None):
        super().__init__(parent)
        self.config = config
        self._setup_ui()
        self._load_config()
    
    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(16)
        
        # Scroll area
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setStyleSheet("background-color: transparent;")
        
        content = QWidget()
        content.setStyleSheet("background-color: transparent;")
        content_layout = QVBoxLayout(content)
        content_layout.setSpacing(12)
        content_layout.setContentsMargins(0, 0, 10, 0)
        
        # Header
        header = QLabel("Mouse Device")
        header.setStyleSheet("color: #e2e8f0; font-size: 18px; font-weight: 600;")
        content_layout.addWidget(header)
        
        desc = QLabel("Configure mouse input device and button blocking.")
        desc.setStyleSheet("color: #64748b; font-size: 11px;")
        desc.setWordWrap(True)
        content_layout.addWidget(desc)
        content_layout.addSpacing(8)
        
        # ==================== Device Selection ====================
        device_section = SectionWidget("Input Device")
        
        # Device mode dropdown
        device_row = QHBoxLayout()
        device_label = QLabel("Device Mode:")
        device_label.setStyleSheet("color: #94a3b8; font-size: 11px;")
        device_label.setFixedWidth(100)
        device_row.addWidget(device_label)
        
        self.device_mode = QComboBox()
        self.device_mode.addItem("Internal (SendInput)", "internal")
        self.device_mode.addItem("Arduino (Hardware HID)", "arduino")
        self.device_mode.setFixedWidth(180)
        self.device_mode.currentIndexChanged.connect(self._on_device_change)
        device_row.addWidget(self.device_mode)
        device_row.addStretch()
        device_section.addLayout(device_row)
        
        device_info = QLabel("Internal: Software-based input\nArduino: Hardware HID (undetectable)")
        device_info.setStyleSheet("color: #64748b; font-size: 9px;")
        device_section.addWidget(device_info)
        
        content_layout.addWidget(device_section)
        
        # ==================== Arduino Settings ====================
        self.arduino_section = SectionWidget("Arduino Settings")
        
        # Port selection
        port_row = QHBoxLayout()
        port_label = QLabel("COM Port:")
        port_label.setStyleSheet("color: #94a3b8; font-size: 11px;")
        port_label.setFixedWidth(100)
        port_row.addWidget(port_label)
        
        self.arduino_port = QLineEdit()
        self.arduino_port.setPlaceholderText("Auto-detect")
        self.arduino_port.setFixedWidth(100)
        self.arduino_port.textChanged.connect(lambda v: setattr(self.config.mouse, 'arduino_port', v))
        port_row.addWidget(self.arduino_port)
        
        self.detect_btn = QPushButton("Detect")
        self.detect_btn.setFixedWidth(60)
        self.detect_btn.clicked.connect(self._detect_arduino)
        port_row.addWidget(self.detect_btn)
        port_row.addStretch()
        self.arduino_section.addLayout(port_row)
        
        # Arduino status
        self.arduino_status = QLabel("Not connected")
        self.arduino_status.setStyleSheet("color: #64748b; font-size: 10px;")
        self.arduino_section.addWidget(self.arduino_status)
        
        # Humanization toggle
        self.arduino_humanization = LabeledToggle("Micro-Humanization")
        self.arduino_humanization.setChecked(True)
        self.arduino_humanization.toggled.connect(lambda v: setattr(self.config.mouse, 'arduino_humanization', v))
        self.arduino_section.addWidget(self.arduino_humanization)
        
        # Jitter slider
        self.arduino_jitter = SliderWidget("Jitter Intensity", 0, 100, 30)
        self.arduino_jitter.valueChanged.connect(lambda v: setattr(self.config.mouse, 'arduino_jitter', int(v)))
        self.arduino_section.addWidget(self.arduino_jitter)
        
        # Tremor slider  
        self.arduino_tremor = SliderWidget("Tremor Intensity", 0, 100, 15)
        self.arduino_tremor.valueChanged.connect(lambda v: setattr(self.config.mouse, 'arduino_tremor', int(v)))
        self.arduino_section.addWidget(self.arduino_tremor)
        
        content_layout.addWidget(self.arduino_section)
        
        # Master Toggle
        master = SectionWidget("Input Blocking")
        
        self.blocking_enabled = LabeledToggle("Enable Input Blocking")
        self.blocking_enabled.setChecked(True)
        self.blocking_enabled.toggled.connect(self._on_master_toggle)
        master.addWidget(self.blocking_enabled)
        
        info = QLabel("When enabled, selected buttons will be intercepted and hidden from games")
        info.setStyleSheet("color: #64748b; font-size: 9px;")
        info.setWordWrap(True)
        master.addWidget(info)
        
        content_layout.addWidget(master)
        
        # Side Buttons Section (commonly used as hotkeys)
        side = SectionWidget("Side Buttons (Recommended)")
        
        side_info = QLabel("These buttons are commonly used as hotkeys and should be blocked")
        side_info.setStyleSheet("color: #94a3b8; font-size: 10px;")
        side_info.setWordWrap(True)
        side.addWidget(side_info)
        
        self.forward_button = LabeledToggle("Forward Button (X2)")
        self.forward_button.setChecked(True)
        self.forward_button.toggled.connect(lambda v: setattr(self.config.mouse, 'block_forward_button', v))
        side.addWidget(self.forward_button)
        
        self.back_button = LabeledToggle("Back Button (X1)")
        self.back_button.setChecked(True)
        self.back_button.toggled.connect(lambda v: setattr(self.config.mouse, 'block_back_button', v))
        side.addWidget(self.back_button)
        
        self.middle_button = LabeledToggle("Middle Button (Scroll Click)")
        self.middle_button.setChecked(False)
        self.middle_button.toggled.connect(lambda v: setattr(self.config.mouse, 'block_middle_click', v))
        side.addWidget(self.middle_button)
        
        content_layout.addWidget(side)
        
        # Primary Buttons Section (use with caution)
        primary = SectionWidget("Primary Buttons (Caution)")
        
        warn_label = QLabel("⚠ Blocking these may prevent normal gameplay!")
        warn_label.setStyleSheet("color: #f59e0b; font-size: 10px; font-weight: 500;")
        primary.addWidget(warn_label)
        
        self.left_button = LabeledToggle("Left Click")
        self.left_button.setChecked(False)
        self.left_button.toggled.connect(lambda v: setattr(self.config.mouse, 'block_left_click', v))
        primary.addWidget(self.left_button)
        
        self.right_button = LabeledToggle("Right Click")
        self.right_button.setChecked(False)
        self.right_button.toggled.connect(lambda v: setattr(self.config.mouse, 'block_right_click', v))
        primary.addWidget(self.right_button)
        
        content_layout.addWidget(primary)
        
        # Status Section
        status = SectionWidget("Status")
        
        self.status_label = QLabel("Blocked buttons: Forward, Back")
        self.status_label.setStyleSheet("color: #22c55e; font-size: 10px;")
        status.addWidget(self.status_label)
        
        content_layout.addWidget(status)
        content_layout.addStretch()
        
        scroll.setWidget(content)
        layout.addWidget(scroll)
    
    def _load_config(self):
        """Load config values into UI"""
        m = self.config.mouse
        
        # Block signals
        widgets = [self.blocking_enabled, self.forward_button, self.back_button,
                   self.middle_button, self.left_button, self.right_button,
                   self.arduino_humanization, self.arduino_jitter, self.arduino_tremor]
        for w in widgets:
            w.blockSignals(True)
        
        # Device mode
        idx = self.device_mode.findData(m.device)
        if idx >= 0:
            self.device_mode.setCurrentIndex(idx)
        
        # Arduino settings
        self.arduino_port.setText(m.arduino_port)
        self.arduino_humanization.setChecked(m.arduino_humanization)
        self.arduino_jitter.setValue(m.arduino_jitter)
        self.arduino_tremor.setValue(m.arduino_tremor)
        
        # Input blocking
        self.blocking_enabled.setChecked(m.input_blocking_enabled)
        self.forward_button.setChecked(m.block_forward_button)
        self.back_button.setChecked(m.block_back_button)
        self.middle_button.setChecked(m.block_middle_click)
        self.left_button.setChecked(m.block_left_click)
        self.right_button.setChecked(m.block_right_click)
        
        # Unblock signals
        for w in widgets:
            w.blockSignals(False)
        
        self._update_status()
        self._update_enabled_state()
        self._update_arduino_visibility()
    
    def _on_master_toggle(self, enabled: bool):
        """Handle master toggle change"""
        self.config.mouse.input_blocking_enabled = enabled
        self._update_enabled_state()
        self._update_status()
    
    def _update_enabled_state(self):
        """Enable/disable button toggles based on master toggle"""
        enabled = self.config.mouse.input_blocking_enabled
        
        self.forward_button.setEnabled(enabled)
        self.back_button.setEnabled(enabled)
        self.middle_button.setEnabled(enabled)
        self.left_button.setEnabled(enabled)
        self.right_button.setEnabled(enabled)
    
    def _update_status(self):
        """Update status label"""
        if not self.config.mouse.input_blocking_enabled:
            self.status_label.setText("Input blocking is disabled")
            self.status_label.setStyleSheet("color: #64748b; font-size: 10px;")
            return
        
        blocked = []
        m = self.config.mouse
        
        if m.block_left_click:
            blocked.append("Left")
        if m.block_right_click:
            blocked.append("Right")
        if m.block_middle_click:
            blocked.append("Middle")
        if m.block_forward_button:
            blocked.append("Forward")
        if m.block_back_button:
            blocked.append("Back")
        
        if blocked:
            self.status_label.setText(f"Blocked: {', '.join(blocked)}")
            self.status_label.setStyleSheet("color: #22c55e; font-size: 10px;")
        else:
            self.status_label.setText("No buttons selected for blocking")
            self.status_label.setStyleSheet("color: #f59e0b; font-size: 10px;")
    
    def _on_device_change(self, idx: int):
        """Handle device mode change."""
        device = self.device_mode.currentData()
        self.config.mouse.device = device
        self._update_arduino_visibility()
    
    def _update_arduino_visibility(self):
        """Show/hide Arduino settings based on device mode."""
        is_arduino = self.config.mouse.device == "arduino"
        self.arduino_section.setVisible(is_arduino)
    
    def _detect_arduino(self):
        """Auto-detect Arduino port."""
        try:
            from ...movement.mouse_controller import find_arduino_port, list_arduino_ports
            
            # Try to find Arduino
            port = find_arduino_port()
            
            if port:
                self.arduino_port.setText(port)
                self.config.mouse.arduino_port = port
                self.arduino_status.setText(f"Found: {port}")
                self.arduino_status.setStyleSheet("color: #22c55e; font-size: 10px;")
            else:
                # List all ports
                ports = list_arduino_ports()
                if ports:
                    port_list = ", ".join([p["port"] for p in ports])
                    self.arduino_status.setText(f"Available: {port_list}")
                    self.arduino_status.setStyleSheet("color: #f59e0b; font-size: 10px;")
                else:
                    self.arduino_status.setText("No serial ports found")
                    self.arduino_status.setStyleSheet("color: #ef4444; font-size: 10px;")
        except Exception as e:
            self.arduino_status.setText(f"Error: {e}")
            self.arduino_status.setStyleSheet("color: #ef4444; font-size: 10px;")
