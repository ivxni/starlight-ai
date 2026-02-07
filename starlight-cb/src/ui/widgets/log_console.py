"""
Dev Console - Captures stdout/stderr and displays in a collapsible panel.
Toggle with the Console button in the header.
"""

import sys
import io
from datetime import datetime

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTextEdit,
    QPushButton, QLabel
)
from PyQt6.QtCore import Qt, QObject, pyqtSignal
from PyQt6.QtGui import QTextCursor, QFont


class _StreamRedirector(QObject):
    """Redirects a text stream (stdout/stderr) to a Qt signal while keeping original output."""
    
    text_written = pyqtSignal(str)
    
    def __init__(self, original_stream, tag: str = ""):
        super().__init__()
        self._original = original_stream
        self._tag = tag
    
    def write(self, text: str):
        if text and text.strip():
            self.text_written.emit(text)
        # Always write to original stream too (so terminal still works)
        if self._original:
            self._original.write(text)
            self._original.flush()
    
    def flush(self):
        if self._original:
            self._original.flush()
    
    def fileno(self):
        if self._original:
            return self._original.fileno()
        raise io.UnsupportedOperation("fileno")
    
    @property
    def encoding(self):
        if self._original:
            return self._original.encoding
        return 'utf-8'


class LogConsole(QWidget):
    """Collapsible dev console that captures print() output."""
    
    # Max lines to keep in the console
    MAX_LINES = 500
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._is_expanded = False
        self._line_count = 0
        self._setup_ui()
        self._install_redirects()
    
    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        # Console text area
        self.console = QTextEdit()
        self.console.setReadOnly(True)
        self.console.setFont(QFont("Consolas", 9))
        self.console.setFixedHeight(180)
        self.console.setStyleSheet("""
            QTextEdit {
                background-color: #0a0a10;
                color: #a0aec0;
                border: 1px solid rgba(255, 255, 255, 0.06);
                border-radius: 4px;
                padding: 6px;
                selection-background-color: rgba(139, 92, 246, 0.3);
            }
        """)
        self.console.setVisible(False)
        layout.addWidget(self.console)
        
        # Bottom bar with buttons
        bar = QHBoxLayout()
        bar.setContentsMargins(0, 4, 0, 0)
        bar.setSpacing(6)
        
        self.clear_btn = QPushButton("Clear")
        self.clear_btn.setFixedSize(50, 22)
        self.clear_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.clear_btn.setStyleSheet("""
            QPushButton {
                background-color: #1e1e2e;
                border: 1px solid rgba(255,255,255,0.06);
                border-radius: 3px;
                color: #64748b;
                font-size: 10px;
            }
            QPushButton:hover {
                color: #e2e8f0;
                border-color: rgba(255,255,255,0.12);
            }
        """)
        self.clear_btn.clicked.connect(self._clear)
        self.clear_btn.setVisible(False)
        bar.addWidget(self.clear_btn)
        
        bar.addStretch()
        
        self.line_label = QLabel("")
        self.line_label.setStyleSheet("color: #475569; font-size: 10px;")
        self.line_label.setVisible(False)
        bar.addWidget(self.line_label)
        
        layout.addLayout(bar)
    
    def _install_redirects(self):
        """Install stdout/stderr redirectors."""
        self._stdout_redir = _StreamRedirector(sys.stdout, "stdout")
        self._stderr_redir = _StreamRedirector(sys.stderr, "stderr")
        
        self._stdout_redir.text_written.connect(self._on_stdout)
        self._stderr_redir.text_written.connect(self._on_stderr)
        
        sys.stdout = self._stdout_redir
        sys.stderr = self._stderr_redir
    
    def uninstall_redirects(self):
        """Restore original stdout/stderr."""
        sys.stdout = self._stdout_redir._original
        sys.stderr = self._stderr_redir._original
    
    def _on_stdout(self, text: str):
        self._append(text, "#a0aec0")  # light gray
    
    def _on_stderr(self, text: str):
        self._append(text, "#f87171")  # red
    
    def _append(self, text: str, color: str):
        """Append text to console."""
        timestamp = datetime.now().strftime("%H:%M:%S")
        
        # Trim if too many lines
        self._line_count += 1
        if self._line_count > self.MAX_LINES:
            cursor = self.console.textCursor()
            cursor.movePosition(QTextCursor.MoveOperation.Start)
            cursor.movePosition(QTextCursor.MoveOperation.Down, QTextCursor.MoveMode.KeepAnchor, 50)
            cursor.removeSelectedText()
            self._line_count -= 50
        
        self.console.append(
            f'<span style="color:#475569">[{timestamp}]</span> '
            f'<span style="color:{color}">{text.rstrip()}</span>'
        )
        
        # Auto-scroll to bottom
        self.console.moveCursor(QTextCursor.MoveOperation.End)
        
        # Update line count label
        self.line_label.setText(f"{self._line_count} lines")
    
    def toggle(self):
        """Toggle console visibility."""
        self._is_expanded = not self._is_expanded
        self.console.setVisible(self._is_expanded)
        self.clear_btn.setVisible(self._is_expanded)
        self.line_label.setVisible(self._is_expanded)
    
    @property
    def is_expanded(self) -> bool:
        return self._is_expanded
    
    def _clear(self):
        self.console.clear()
        self._line_count = 0
        self.line_label.setText("0 lines")
    
    def log(self, message: str, level: str = "info"):
        """Manually log a message (bypasses stdout)."""
        colors = {
            "info": "#a0aec0",
            "success": "#22c55e",
            "warning": "#f59e0b",
            "error": "#f87171",
        }
        self._append(message, colors.get(level, "#a0aec0"))
