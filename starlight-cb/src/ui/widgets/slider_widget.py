"""
Minimal Slider Widgets
Clean, compact sliders with value display
"""

from PyQt6.QtWidgets import QWidget, QHBoxLayout, QVBoxLayout, QLabel, QSlider
from PyQt6.QtCore import Qt, pyqtSignal


class SliderWidget(QWidget):
    """Compact slider with inline value"""
    
    valueChanged = pyqtSignal(float)
    
    def __init__(self, label: str, min_val: float, max_val: float, 
                 default: float = 0, decimals: int = 0, 
                 suffix: str = "", parent=None):
        super().__init__(parent)
        
        self.decimals = decimals
        self.suffix = suffix
        self._multiplier = 10 ** decimals if decimals > 0 else 1
        
        self._setup_ui(label, min_val, max_val, default)
    
    def _setup_ui(self, label: str, min_val: float, max_val: float, default: float):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 2, 0, 2)
        layout.setSpacing(10)
        
        # Label
        self.label = QLabel(label)
        self.label.setStyleSheet("color: #94a3b8; font-size: 11px;")
        self.label.setMinimumWidth(80)
        layout.addWidget(self.label)
        
        # Slider
        self.slider = QSlider(Qt.Orientation.Horizontal)
        self.slider.setMinimum(int(min_val * self._multiplier))
        self.slider.setMaximum(int(max_val * self._multiplier))
        self.slider.setValue(int(default * self._multiplier))
        self.slider.valueChanged.connect(self._on_change)
        self.slider.setFixedHeight(16)
        layout.addWidget(self.slider, stretch=1)
        
        # Value
        self.value_label = QLabel()
        self.value_label.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        self.value_label.setMinimumWidth(45)
        self.value_label.setStyleSheet("""
            color: #8b5cf6;
            font-size: 11px;
            font-weight: 600;
            font-family: 'Consolas', monospace;
        """)
        layout.addWidget(self.value_label)
        
        self._update_display()
    
    def _on_change(self, value: int):
        self._update_display()
        self.valueChanged.emit(self.value())
    
    def _update_display(self):
        val = self.value()
        if self.decimals > 0:
            text = f"{val:.{self.decimals}f}"
        else:
            text = str(int(val))
        if self.suffix:
            text += self.suffix
        self.value_label.setText(text)
    
    def value(self) -> float:
        return self.slider.value() / self._multiplier
    
    def setValue(self, value: float):
        self.slider.setValue(int(value * self._multiplier))
    
    def setRange(self, min_val: float, max_val: float):
        self.slider.setMinimum(int(min_val * self._multiplier))
        self.slider.setMaximum(int(max_val * self._multiplier))


class CompactSlider(QWidget):
    """Compact slider with label above"""
    
    valueChanged = pyqtSignal(float)
    
    def __init__(self, label: str, min_val: float, max_val: float,
                 default: float = 0, decimals: int = 0,
                 suffix: str = "", parent=None):
        super().__init__(parent)
        
        self.decimals = decimals
        self.suffix = suffix
        self._multiplier = 10 ** decimals if decimals > 0 else 1
        
        self._setup_ui(label, min_val, max_val, default)
    
    def _setup_ui(self, label: str, min_val: float, max_val: float, default: float):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)
        
        # Header
        header = QHBoxLayout()
        
        self.label = QLabel(label)
        self.label.setStyleSheet("color: #94a3b8; font-size: 10px;")
        header.addWidget(self.label)
        
        header.addStretch()
        
        self.value_label = QLabel()
        self.value_label.setStyleSheet("""
            color: #8b5cf6;
            font-size: 10px;
            font-weight: 600;
            font-family: 'Consolas', monospace;
        """)
        header.addWidget(self.value_label)
        
        layout.addLayout(header)
        
        # Slider
        self.slider = QSlider(Qt.Orientation.Horizontal)
        self.slider.setMinimum(int(min_val * self._multiplier))
        self.slider.setMaximum(int(max_val * self._multiplier))
        self.slider.setValue(int(default * self._multiplier))
        self.slider.valueChanged.connect(self._on_change)
        self.slider.setFixedHeight(14)
        layout.addWidget(self.slider)
        
        self._update_display()
    
    def _on_change(self, value: int):
        self._update_display()
        self.valueChanged.emit(self.value())
    
    def _update_display(self):
        val = self.value()
        if self.decimals > 0:
            text = f"{val:.{self.decimals}f}"
        else:
            text = str(int(val))
        if self.suffix:
            text += self.suffix
        self.value_label.setText(text)
    
    def value(self) -> float:
        return self.slider.value() / self._multiplier
    
    def setValue(self, value: float):
        self.slider.setValue(int(value * self._multiplier))


class RangeSliderWidget(QWidget):
    """Two sliders for min/max"""
    
    rangeChanged = pyqtSignal(float, float)
    
    def __init__(self, label: str, min_val: float, max_val: float,
                 default_min: float, default_max: float,
                 decimals: int = 0, suffix: str = "", parent=None):
        super().__init__(parent)
        
        self.decimals = decimals
        self.suffix = suffix
        self._multiplier = 10 ** decimals if decimals > 0 else 1
        
        self._setup_ui(label, min_val, max_val, default_min, default_max)
    
    def _setup_ui(self, label: str, min_val: float, max_val: float,
                  default_min: float, default_max: float):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 2, 0, 2)
        layout.setSpacing(4)
        
        # Label
        self.label = QLabel(label)
        self.label.setStyleSheet("color: #e2e8f0; font-size: 11px;")
        layout.addWidget(self.label)
        
        # Min row
        min_row = QHBoxLayout()
        min_row.setSpacing(8)
        min_label = QLabel("Min")
        min_label.setStyleSheet("color: #64748b; font-size: 10px; min-width: 24px;")
        min_row.addWidget(min_label)
        
        self.min_slider = QSlider(Qt.Orientation.Horizontal)
        self.min_slider.setMinimum(int(min_val * self._multiplier))
        self.min_slider.setMaximum(int(max_val * self._multiplier))
        self.min_slider.setValue(int(default_min * self._multiplier))
        self.min_slider.valueChanged.connect(self._on_min_change)
        self.min_slider.setFixedHeight(14)
        min_row.addWidget(self.min_slider, stretch=1)
        
        self.min_value = QLabel()
        self.min_value.setStyleSheet("color: #8b5cf6; font-size: 10px; font-family: 'Consolas'; min-width: 40px;")
        self.min_value.setAlignment(Qt.AlignmentFlag.AlignRight)
        min_row.addWidget(self.min_value)
        
        layout.addLayout(min_row)
        
        # Max row
        max_row = QHBoxLayout()
        max_row.setSpacing(8)
        max_label = QLabel("Max")
        max_label.setStyleSheet("color: #64748b; font-size: 10px; min-width: 24px;")
        max_row.addWidget(max_label)
        
        self.max_slider = QSlider(Qt.Orientation.Horizontal)
        self.max_slider.setMinimum(int(min_val * self._multiplier))
        self.max_slider.setMaximum(int(max_val * self._multiplier))
        self.max_slider.setValue(int(default_max * self._multiplier))
        self.max_slider.valueChanged.connect(self._on_max_change)
        self.max_slider.setFixedHeight(14)
        max_row.addWidget(self.max_slider, stretch=1)
        
        self.max_value = QLabel()
        self.max_value.setStyleSheet("color: #8b5cf6; font-size: 10px; font-family: 'Consolas'; min-width: 40px;")
        self.max_value.setAlignment(Qt.AlignmentFlag.AlignRight)
        max_row.addWidget(self.max_value)
        
        layout.addLayout(max_row)
        
        self._update_display()
    
    def _on_min_change(self, value: int):
        if value > self.max_slider.value():
            self.max_slider.setValue(value)
        self._update_display()
        self.rangeChanged.emit(self.minValue(), self.maxValue())
    
    def _on_max_change(self, value: int):
        if value < self.min_slider.value():
            self.min_slider.setValue(value)
        self._update_display()
        self.rangeChanged.emit(self.minValue(), self.maxValue())
    
    def _update_display(self):
        min_val = self.minValue()
        max_val = self.maxValue()
        
        if self.decimals > 0:
            min_text = f"{min_val:.{self.decimals}f}"
            max_text = f"{max_val:.{self.decimals}f}"
        else:
            min_text = str(int(min_val))
            max_text = str(int(max_val))
        
        if self.suffix:
            min_text += self.suffix
            max_text += self.suffix
        
        self.min_value.setText(min_text)
        self.max_value.setText(max_text)
    
    def minValue(self) -> float:
        return self.min_slider.value() / self._multiplier
    
    def maxValue(self) -> float:
        return self.max_slider.value() / self._multiplier
    
    def setMinValue(self, value: float):
        self.min_slider.setValue(int(value * self._multiplier))
    
    def setMaxValue(self, value: float):
        self.max_slider.setValue(int(value * self._multiplier))
