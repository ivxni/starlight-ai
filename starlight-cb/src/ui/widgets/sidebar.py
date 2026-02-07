"""
Minimal Sidebar - Always expanded with FA icons
"""

from PyQt6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame, QPushButton
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QPainter, QColor


class NavItem(QWidget):
    """Simple nav item with icon and text"""
    
    clicked = pyqtSignal()
    
    # Simple unicode icons that work everywhere
    ICONS = {
        'aim': '◎',       # target/crosshair
        'flick': '⚡',     # lightning
        'humanizer': '☰', # sliders/menu
        'mouse': '🖱',    # mouse
        'settings': '⚙',  # gear
    }
    
    def __init__(self, icon_key: str, text: str, parent=None):
        super().__init__(parent)
        
        self._icon = self.ICONS.get(icon_key, '●')
        self._text = text
        self._active = False
        self._hover = False
        
        self.setFixedHeight(40)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self._setup_ui()
    
    def _setup_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(16, 0, 16, 0)
        layout.setSpacing(12)
        
        # Icon
        self._icon_label = QLabel(self._icon)
        self._icon_label.setFixedWidth(20)
        self._icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._icon_label.setStyleSheet("color: #64748b; font-size: 14px;")
        layout.addWidget(self._icon_label)
        
        # Text
        self._text_label = QLabel(self._text)
        self._text_label.setStyleSheet("color: #64748b; font-size: 12px; font-weight: 500;")
        layout.addWidget(self._text_label)
        
        layout.addStretch()
    
    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        if self._active:
            # Active background
            painter.setBrush(QColor(139, 92, 246, 20))
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawRoundedRect(8, 4, self.width() - 16, self.height() - 8, 6, 6)
            
            # Left indicator
            painter.setBrush(QColor("#8b5cf6"))
            painter.drawRoundedRect(0, 8, 3, self.height() - 16, 1, 1)
            
        elif self._hover:
            painter.setBrush(QColor(255, 255, 255, 6))
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawRoundedRect(8, 4, self.width() - 16, self.height() - 8, 6, 6)
        
        super().paintEvent(event)
    
    def enterEvent(self, event):
        self._hover = True
        self.update()
    
    def leaveEvent(self, event):
        self._hover = False
        self.update()
    
    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit()
    
    def setActive(self, active: bool):
        self._active = active
        color = "#e2e8f0" if active else "#64748b"
        self._icon_label.setStyleSheet(f"color: {color};")
        self._text_label.setStyleSheet(f"color: {color}; font-size: 12px; font-weight: {'600' if active else '500'};")
        self.update()


class Sidebar(QFrame):
    """Simple sidebar - always expanded"""
    
    pageChanged = pyqtSignal(int)
    exitRequested = pyqtSignal()
    clearRequested = pyqtSignal()
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        self.setFixedWidth(180)
        self._setup_ui()
    
    def _setup_ui(self):
        self.setStyleSheet("""
            QFrame {
                background-color: rgba(255, 255, 255, 0.01);
                border-right: 1px solid rgba(255, 255, 255, 0.04);
            }
        """)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 16, 0, 16)
        layout.setSpacing(4)
        
        # Logo/Brand
        brand = QHBoxLayout()
        brand.setContentsMargins(16, 0, 16, 0)
        
        logo = QLabel("S")
        logo.setStyleSheet("""
            color: #8b5cf6;
            font-size: 20px;
            font-weight: bold;
            background-color: rgba(139, 92, 246, 0.15);
            border-radius: 6px;
            padding: 4px 10px;
        """)
        brand.addWidget(logo)
        
        title = QLabel("Starlight")
        title.setStyleSheet("color: #e2e8f0; font-size: 14px; font-weight: 600; margin-left: 8px;")
        brand.addWidget(title)
        brand.addStretch()
        
        layout.addLayout(brand)
        layout.addSpacing(24)
        
        # Section label
        section = QLabel("MENU")
        section.setStyleSheet("color: #475569; font-size: 10px; font-weight: 600; margin-left: 16px;")
        layout.addWidget(section)
        layout.addSpacing(8)
        
        # Nav items
        self._items = []
        nav_data = [
            ('aim', 'Aim'),
            ('flick', 'Flick & Trigger'),
            ('humanizer', 'Humanizer'),
            ('mouse', 'Mouse'),
            ('settings', 'Settings'),
        ]
        
        for i, (icon, text) in enumerate(nav_data):
            item = NavItem(icon, text)
            item.clicked.connect(lambda idx=i: self._on_click(idx))
            self._items.append(item)
            layout.addWidget(item)
        
        self._items[0].setActive(True)
        self._current = 0
        
        layout.addStretch()
        
        # Clear button
        clear_btn = QPushButton("🧹 Clear")
        clear_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        clear_btn.setToolTip("Kill zombie processes & clear UDP sockets")
        clear_btn.setStyleSheet("""
            QPushButton {
                background-color: rgba(59, 130, 246, 0.12);
                border: 1px solid rgba(59, 130, 246, 0.3);
                border-radius: 4px;
                color: #60a5fa;
                font-size: 11px;
                font-weight: 600;
                padding: 6px 10px;
                margin: 0 16px;
            }
            QPushButton:hover {
                background-color: rgba(59, 130, 246, 0.2);
                border-color: rgba(59, 130, 246, 0.45);
            }
        """)
        clear_btn.clicked.connect(self.clearRequested.emit)
        layout.addWidget(clear_btn)
        layout.addSpacing(4)
        
        # Exit button
        exit_btn = QPushButton("Exit")
        exit_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        exit_btn.setStyleSheet("""
            QPushButton {
                background-color: rgba(239, 68, 68, 0.12);
                border: 1px solid rgba(239, 68, 68, 0.3);
                border-radius: 4px;
                color: #f87171;
                font-size: 11px;
                font-weight: 600;
                padding: 6px 10px;
                margin: 0 16px;
            }
            QPushButton:hover {
                background-color: rgba(239, 68, 68, 0.2);
                border-color: rgba(239, 68, 68, 0.45);
            }
        """)
        exit_btn.clicked.connect(self.exitRequested.emit)
        layout.addWidget(exit_btn)
        layout.addSpacing(8)
        
        # Footer
        footer = QLabel("v1.0.0")
        footer.setAlignment(Qt.AlignmentFlag.AlignCenter)
        footer.setStyleSheet("color: #374151; font-size: 10px;")
        layout.addWidget(footer)
    
    def _on_click(self, index: int):
        if index == self._current:
            return
        
        self._items[self._current].setActive(False)
        self._items[index].setActive(True)
        self._current = index
        
        self.pageChanged.emit(index)
    
    def setCurrentIndex(self, index: int):
        if 0 <= index < len(self._items):
            self._on_click(index)
