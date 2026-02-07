"""
Minimal Card/Section Widgets
Clean, simple panels for grouping content
"""

from PyQt6.QtWidgets import QWidget, QVBoxLayout, QLabel, QFrame, QHBoxLayout
from PyQt6.QtCore import Qt


class GlassPanel(QFrame):
    """Simple panel container"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        self.setStyleSheet("""
            QFrame {
                background-color: rgba(255, 255, 255, 0.015);
                border: 1px solid rgba(255, 255, 255, 0.04);
                border-radius: 8px;
            }
        """)
        
        self._layout = QVBoxLayout(self)
        self._layout.setContentsMargins(14, 14, 14, 14)
        self._layout.setSpacing(10)
    
    def addWidget(self, widget: QWidget):
        self._layout.addWidget(widget)
    
    def addLayout(self, layout):
        self._layout.addLayout(layout)
    
    def addSpacing(self, space: int):
        self._layout.addSpacing(space)
    
    def addStretch(self, stretch: int = 1):
        self._layout.addStretch(stretch)


class SectionWidget(QWidget):
    """Card section with title - clean design"""
    
    def __init__(self, title: str, parent=None):
        super().__init__(parent)
        self._title = title
        self._setup_ui()
    
    def _setup_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        
        # Card container
        self._card = QFrame()
        self._card.setStyleSheet("""
            QFrame {
                background-color: rgba(255, 255, 255, 0.018);
                border: 1px solid rgba(255, 255, 255, 0.05);
                border-radius: 8px;
            }
            QFrame:hover {
                border-color: rgba(255, 255, 255, 0.08);
            }
            QLabel {
                background: transparent;
                border: none;
                border-radius: 0px;
            }
        """)
        
        card_layout = QVBoxLayout(self._card)
        card_layout.setContentsMargins(14, 12, 14, 14)
        card_layout.setSpacing(12)
        
        # Title row
        title_row = QHBoxLayout()
        title_row.setSpacing(8)
        
        # Title indicator
        indicator = QFrame()
        indicator.setFixedSize(3, 14)
        indicator.setStyleSheet("background-color: #8b5cf6; border-radius: 1px;")
        title_row.addWidget(indicator)
        
        # Title text
        self._title_label = QLabel(self._title)
        self._title_label.setStyleSheet("""
            color: #94a3b8;
            font-size: 11px;
            font-weight: 600;
        """)
        title_row.addWidget(self._title_label)
        title_row.addStretch()
        
        card_layout.addLayout(title_row)
        
        # Content area
        self._content = QVBoxLayout()
        self._content.setContentsMargins(0, 0, 0, 0)
        self._content.setSpacing(8)
        card_layout.addLayout(self._content)
        
        main_layout.addWidget(self._card)
    
    def addWidget(self, widget: QWidget):
        self._content.addWidget(widget)
    
    def addLayout(self, layout):
        self._content.addLayout(layout)
    
    def addSpacing(self, space: int):
        self._content.addSpacing(space)
    
    def addStretch(self, stretch: int = 1):
        self._content.addStretch(stretch)
    
    def setTitle(self, title: str):
        self._title = title
        self._title_label.setText(title)


class Divider(QFrame):
    """Subtle horizontal line"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedHeight(1)
        self.setStyleSheet("background-color: rgba(255, 255, 255, 0.05);")


class SettingRow(QWidget):
    """Single setting row with label and control"""
    
    def __init__(self, label: str, parent=None):
        super().__init__(parent)
        
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 4, 0, 4)
        layout.setSpacing(12)
        
        self.label = QLabel(label)
        self.label.setStyleSheet("color: #94a3b8; font-size: 11px;")
        layout.addWidget(self.label)
        
        layout.addStretch()
        
        self._controls = QHBoxLayout()
        self._controls.setSpacing(8)
        layout.addLayout(self._controls)
    
    def addControl(self, widget: QWidget):
        self._controls.addWidget(widget)


class StatCard(QFrame):
    """Small stat display card"""
    
    def __init__(self, label: str, value: str = "--", parent=None):
        super().__init__(parent)
        
        self.setStyleSheet("""
            QFrame {
                background-color: rgba(255, 255, 255, 0.015);
                border: 1px solid rgba(255, 255, 255, 0.04);
                border-radius: 6px;
            }
        """)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 10, 12, 10)
        layout.setSpacing(4)
        
        self._label = QLabel(label)
        self._label.setStyleSheet("color: #64748b; font-size: 9px; font-weight: 500;")
        layout.addWidget(self._label)
        
        self._value = QLabel(value)
        self._value.setStyleSheet("""
            color: #e2e8f0;
            font-size: 14px;
            font-weight: 600;
            font-family: 'Consolas', monospace;
        """)
        layout.addWidget(self._value)
    
    def setValue(self, value: str):
        self._value.setText(value)
    
    def setValueColor(self, color: str):
        self._value.setStyleSheet(f"""
            color: {color};
            font-size: 14px;
            font-weight: 600;
            font-family: 'Consolas', monospace;
        """)
