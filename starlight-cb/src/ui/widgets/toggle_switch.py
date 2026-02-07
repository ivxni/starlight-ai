"""
Minimal Toggle Switch
Simple, compact toggle
"""

from PyQt6.QtWidgets import QWidget, QHBoxLayout, QLabel
from PyQt6.QtCore import Qt, pyqtSignal, QPropertyAnimation, QEasingCurve, pyqtProperty
from PyQt6.QtGui import QPainter, QColor


class ToggleSwitch(QWidget):
    """Minimal toggle switch"""
    
    toggled = pyqtSignal(bool)
    
    def __init__(self, checked: bool = False, parent=None):
        super().__init__(parent)
        
        self._checked = checked
        self._handle_position = 2 if not checked else 18
        self._hover = False
        
        # Dimensions - smaller
        self._width = 32
        self._height = 16
        self._handle_size = 12
        
        # Animation
        self._animation = QPropertyAnimation(self, b"handle_position", self)
        self._animation.setDuration(150)
        self._animation.setEasingCurve(QEasingCurve.Type.OutCubic)
        
        self.setFixedSize(self._width, self._height)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
    
    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        # Track
        if self._checked:
            painter.setBrush(QColor("#8b5cf6"))
        else:
            painter.setBrush(QColor(255, 255, 255, 10))
        
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawRoundedRect(0, 0, self._width, self._height, 
                                self._height // 2, self._height // 2)
        
        # Handle
        handle_y = (self._height - self._handle_size) // 2
        painter.setBrush(QColor("#ffffff"))
        painter.drawEllipse(int(self._handle_position), handle_y, 
                           self._handle_size, self._handle_size)
    
    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.toggle()
    
    def toggle(self):
        self._checked = not self._checked
        
        self._animation.setStartValue(self._handle_position)
        end_pos = self._width - self._handle_size - 2 if self._checked else 2
        self._animation.setEndValue(end_pos)
        self._animation.start()
        
        self.toggled.emit(self._checked)
    
    def isChecked(self) -> bool:
        return self._checked
    
    def setChecked(self, checked: bool):
        if self._checked != checked:
            self._checked = checked
            self._handle_position = self._width - self._handle_size - 2 if checked else 2
            self.update()
    
    @pyqtProperty(float)
    def handle_position(self) -> float:
        return self._handle_position
    
    @handle_position.setter
    def handle_position(self, pos: float):
        self._handle_position = pos
        self.update()


class LabeledToggle(QWidget):
    """Toggle with label"""
    
    toggled = pyqtSignal(bool)
    
    def __init__(self, label: str, checked: bool = False, parent=None):
        super().__init__(parent)
        
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 2, 0, 2)
        layout.setSpacing(8)
        
        # Toggle
        self.toggle = ToggleSwitch(checked=checked)
        self.toggle.toggled.connect(self.toggled.emit)
        layout.addWidget(self.toggle)
        
        # Label
        self.label = QLabel(label)
        self.label.setStyleSheet("color: #e2e8f0; font-size: 11px;")
        self.label.setCursor(Qt.CursorShape.PointingHandCursor)
        layout.addWidget(self.label)
        
        layout.addStretch()
        
        self.label.mousePressEvent = lambda e: self.toggle.toggle()
    
    def isChecked(self) -> bool:
        return self.toggle.isChecked()
    
    def setChecked(self, checked: bool):
        self.toggle.setChecked(checked)


class ToggleWithStatus(QWidget):
    """Toggle with status text"""
    
    toggled = pyqtSignal(bool)
    
    def __init__(self, label: str, checked: bool = False, 
                 on_text: str = "On", off_text: str = "Off", parent=None):
        super().__init__(parent)
        
        self._on_text = on_text
        self._off_text = off_text
        
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 2, 0, 2)
        layout.setSpacing(8)
        
        # Toggle
        self.toggle = ToggleSwitch(checked=checked)
        self.toggle.toggled.connect(self._on_toggle)
        layout.addWidget(self.toggle)
        
        # Label
        self.label = QLabel(label)
        self.label.setStyleSheet("color: #e2e8f0; font-size: 11px;")
        layout.addWidget(self.label)
        
        layout.addStretch()
        
        # Status
        self.status = QLabel()
        self._update_status(checked)
        layout.addWidget(self.status)
    
    def _on_toggle(self, checked: bool):
        self._update_status(checked)
        self.toggled.emit(checked)
    
    def _update_status(self, checked: bool):
        if checked:
            self.status.setText(self._on_text)
            self.status.setStyleSheet("color: #22c55e; font-size: 10px;")
        else:
            self.status.setText(self._off_text)
            self.status.setStyleSheet("color: #64748b; font-size: 10px;")
    
    def isChecked(self) -> bool:
        return self.toggle.isChecked()
    
    def setChecked(self, checked: bool):
        self.toggle.setChecked(checked)
        self._update_status(checked)
