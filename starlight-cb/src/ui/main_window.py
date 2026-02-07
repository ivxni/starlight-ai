"""
Starlight Main Window - Minimal Design
"""

from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QStackedWidget, QPushButton
)
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QColor

from .styles import GLASSMORPHISM_STYLESHEET, COLORS
from .widgets.sidebar import Sidebar
from .widgets.debug_view import DebugView
from .widgets.log_console import LogConsole
from .tabs.aim_tab import AimTab
from .tabs.flick_trigger_tab import FlickTriggerTab
from .tabs.humanizer_tab import HumanizerTab
from .tabs.mouse_tab import MouseDeviceTab
from .tabs.settings_tab import SettingsTab
from ..core.config import Config, save_config
from ..core.assistant import Assistant
from ..core.cleanup import full_cleanup


class MainWindow(QMainWindow):
    """Main window - minimal design"""
    
    TITLES = ["Aim", "Flick & Trigger", "Humanizer", "Mouse", "Settings"]
    
    def __init__(self, config: Config, parent=None):
        super().__init__(parent)
        self.config = config
        self.assistant = None
        self._last_detections = []
        
        self._setup_window()
        self._setup_ui()
        
        self._save_timer = QTimer()
        self._save_timer.timeout.connect(lambda: save_config())
        self._save_timer.start(30000)
    
    def _setup_window(self):
        self.setWindowTitle("Starlight")
        self.setMinimumSize(1000, 650)
        self.resize(1100, 700)
        
        self.setStyleSheet(GLASSMORPHISM_STYLESHEET)
        
        palette = self.palette()
        palette.setColor(self.backgroundRole(), QColor(COLORS['bg_primary']))
        self.setPalette(palette)
    
    def _setup_ui(self):
        central = QWidget()
        central.setStyleSheet(f"background-color: {COLORS['bg_primary']};")
        self.setCentralWidget(central)
        
        main_layout = QHBoxLayout(central)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        
        # Sidebar
        self.sidebar = Sidebar()
        self.sidebar.pageChanged.connect(self._on_page_change)
        self.sidebar.exitRequested.connect(self.close)
        self.sidebar.clearRequested.connect(self._on_clear_processes)
        main_layout.addWidget(self.sidebar)
        
        # Content
        content = QWidget()
        content.setStyleSheet("background-color: transparent;")
        content_layout = QVBoxLayout(content)
        content_layout.setContentsMargins(16, 14, 16, 14)
        content_layout.setSpacing(12)
        
        # Header
        header = self._create_header()
        content_layout.addWidget(header)
        
        # Body
        body = QHBoxLayout()
        body.setSpacing(12)
        
        # Pages
        self.pages = QStackedWidget()
        self.pages.setStyleSheet("background-color: transparent;")
        
        self.pages.addWidget(AimTab(self.config))
        self.pages.addWidget(FlickTriggerTab(self.config))
        self.pages.addWidget(HumanizerTab(self.config))
        self.pages.addWidget(MouseDeviceTab(self.config))
        self.settings_tab = SettingsTab(self.config)
        self.pages.addWidget(self.settings_tab)
        
        body.addWidget(self.pages, stretch=1)
        
        # Debug
        self.debug_view = DebugView()
        
        # Connect debug toggles from settings tab
        self.settings_tab.dbg_bones.toggled.connect(
            lambda v: setattr(self.debug_view, '_debug_bones', v)
        )
        self.settings_tab.dbg_trigger_zone.toggled.connect(
            lambda v: setattr(self.debug_view, '_debug_trigger_zone', v)
        )
        self.debug_view.setFixedWidth(260)
        body.addWidget(self.debug_view)
        
        content_layout.addLayout(body)
        
        # Log console (collapsible, hidden by default)
        self.log_console = LogConsole()
        content_layout.addWidget(self.log_console)
        
        main_layout.addWidget(content, stretch=1)
    
    def _create_header(self) -> QWidget:
        header = QWidget()
        header.setFixedHeight(40)
        layout = QHBoxLayout(header)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(12)
        
        # Title
        self.title = QLabel("Aim")
        self.title.setStyleSheet("color: #e2e8f0; font-size: 16px; font-weight: 600;")
        layout.addWidget(self.title)
        
        layout.addStretch()
        
        # Status
        self.status_dot = QLabel()
        self.status_dot.setFixedSize(6, 6)
        self.status_dot.setStyleSheet("background-color: #475569; border-radius: 3px;")
        layout.addWidget(self.status_dot)
        
        self.status_text = QLabel("Idle")
        self.status_text.setStyleSheet("color: #475569; font-size: 11px;")
        layout.addWidget(self.status_text)
        
        layout.addSpacing(8)
        
        # Console toggle button
        self.console_btn = QPushButton("Console")
        self.console_btn.setFixedSize(70, 28)
        self.console_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.console_btn.setStyleSheet("""
            QPushButton {
                background-color: #1e1e2e;
                border: 1px solid #334155;
                border-radius: 4px;
                color: #64748b;
                font-size: 10px;
                font-weight: 500;
            }
            QPushButton:hover {
                color: #e2e8f0;
                border-color: #475569;
            }
        """)
        self.console_btn.clicked.connect(self._toggle_console)
        layout.addWidget(self.console_btn)
        
        layout.addSpacing(4)
        
        # Save button
        self.save_btn = QPushButton("Save")
        self.save_btn.setFixedSize(60, 28)
        self.save_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.save_btn.setStyleSheet("""
            QPushButton {
                background-color: #334155;
                border: 1px solid #475569;
                border-radius: 4px;
                color: #e2e8f0;
                font-size: 11px;
                font-weight: 500;
            }
            QPushButton:hover {
                background-color: #3f4f63;
                border-color: #64748b;
            }
        """)
        self.save_btn.clicked.connect(self._save_config)
        layout.addWidget(self.save_btn)
        
        layout.addSpacing(4)
        
        # Start button
        self.start_btn = QPushButton("Start")
        self.start_btn.setFixedSize(70, 28)
        self.start_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.start_btn.setStyleSheet("""
            QPushButton {
                background-color: #8b5cf6;
                border: none;
                border-radius: 4px;
                color: white;
                font-size: 11px;
                font-weight: 600;
            }
            QPushButton:hover {
                background-color: #9d6ff8;
            }
        """)
        self.start_btn.clicked.connect(self._toggle_assistant)
        layout.addWidget(self.start_btn)
        
        return header
    
    def _on_page_change(self, index: int):
        self.pages.setCurrentIndex(index)
        self.title.setText(self.TITLES[index])
    
    def _save_config(self):
        """Save config to file and show feedback"""
        save_config()
        
        # Visual feedback - briefly change button style
        self.save_btn.setText("Saved!")
        self.save_btn.setStyleSheet("""
            QPushButton {
                background-color: #22c55e;
                border: none;
                border-radius: 4px;
                color: white;
                font-size: 11px;
                font-weight: 500;
            }
        """)
        
        # Reset after 1.5 seconds
        QTimer.singleShot(1500, self._reset_save_btn)
    
    def _reset_save_btn(self):
        """Reset save button to normal state"""
        self.save_btn.setText("Save")
        self.save_btn.setStyleSheet("""
            QPushButton {
                background-color: #334155;
                border: 1px solid #475569;
                border-radius: 4px;
                color: #e2e8f0;
                font-size: 11px;
                font-weight: 500;
            }
            QPushButton:hover {
                background-color: #3f4f63;
                border-color: #64748b;
            }
        """)
    
    def _toggle_console(self):
        """Toggle dev console visibility"""
        self.log_console.toggle()
        if self.log_console.is_expanded:
            self.console_btn.setStyleSheet("""
                QPushButton {
                    background-color: rgba(139, 92, 246, 0.15);
                    border: 1px solid #8b5cf6;
                    border-radius: 4px;
                    color: #8b5cf6;
                    font-size: 10px;
                    font-weight: 500;
                }
                QPushButton:hover {
                    color: #9d6ff8;
                    border-color: #9d6ff8;
                }
            """)
        else:
            self.console_btn.setStyleSheet("""
                QPushButton {
                    background-color: #1e1e2e;
                    border: 1px solid #334155;
                    border-radius: 4px;
                    color: #64748b;
                    font-size: 10px;
                    font-weight: 500;
                }
                QPushButton:hover {
                    color: #e2e8f0;
                    border-color: #475569;
                }
            """)
    
    def _toggle_assistant(self):
        if self.assistant is None or not self.assistant.is_running:
            self._start_assistant()
        else:
            self._stop_assistant()
    
    def _start_assistant(self):
        self.assistant = Assistant(self.config)
        self.assistant.on_state_change = self._on_state_change
        self.assistant.on_detection = self._on_detection
        
        try:
            init_ok = self.assistant.initialize()
        except Exception as e:
            self.log_console.log(f"Initialize failed: {e}", "error")
            self.status_text.setText(f"Error: {e}")
            self.status_text.setStyleSheet("color: #f87171; font-size: 11px;")
            self.status_dot.setStyleSheet("background-color: #f87171; border-radius: 3px;")
            # Auto-open console on error
            if not self.log_console.is_expanded:
                self._toggle_console()
            return
        
        if not init_ok:
            self.log_console.log("Failed to initialize assistant (check logs above)", "error")
            self.status_text.setText("Init Failed")
            self.status_text.setStyleSheet("color: #f87171; font-size: 11px;")
            self.status_dot.setStyleSheet("background-color: #f87171; border-radius: 3px;")
            if not self.log_console.is_expanded:
                self._toggle_console()
            return
        
        if not self.assistant.start():
            self.log_console.log("Failed to start assistant (capture error?)", "error")
            self.status_text.setText("Start Failed")
            self.status_text.setStyleSheet("color: #f87171; font-size: 11px;")
            self.status_dot.setStyleSheet("background-color: #f87171; border-radius: 3px;")
            if not self.log_console.is_expanded:
                self._toggle_console()
            return
        
        if True:
            self.start_btn.setText("Stop")
            self.start_btn.setStyleSheet("""
                QPushButton {
                    background-color: #ef4444;
                    border: none;
                    border-radius: 4px;
                    color: white;
                    font-size: 11px;
                    font-weight: 600;
                }
                QPushButton:hover {
                    background-color: #f87171;
                }
            """)
            
            self.status_dot.setStyleSheet("background-color: #22c55e; border-radius: 3px;")
            self.status_text.setText("Running")
            self.status_text.setStyleSheet("color: #22c55e; font-size: 11px;")
            
            self.debug_view.start()
            
            self._frame_timer = QTimer()
            self._frame_timer.timeout.connect(self._update_frame)
            self._frame_timer.start(16)  # ~60fps debug view (GUI thread budget)
    
    def _stop_assistant(self):
        if hasattr(self, '_frame_timer') and self._frame_timer:
            self._frame_timer.stop()
            self._frame_timer = None
        
        self.debug_view.stop()
        
        if self.assistant:
            self.assistant.stop()
        
        self.start_btn.setText("Start")
        self.start_btn.setStyleSheet("""
            QPushButton {
                background-color: #8b5cf6;
                border: none;
                border-radius: 4px;
                color: white;
                font-size: 11px;
                font-weight: 600;
            }
            QPushButton:hover {
                background-color: #9d6ff8;
            }
        """)
        
        self.status_dot.setStyleSheet("background-color: #475569; border-radius: 3px;")
        self.status_text.setText("Idle")
        self.status_text.setStyleSheet("color: #475569; font-size: 11px;")
        
        self.debug_view.update_metrics(0, 0, 0, 0)
    
    def _on_state_change(self, state):
        # Called from BACKGROUND thread - only store data, NEVER touch Qt widgets
        self._pending_state = state
        self._pending_inf_ms = (
            self.assistant.detector.inference_time
            if self.assistant and self.assistant.detector else 0
        )
    
    def _on_detection(self, detections):
        # Called from BACKGROUND thread - only store data, NEVER touch Qt widgets
        self._last_detections = detections
    
    def _update_frame(self):
        """GUI-thread timer callback - safe to update all Qt widgets here"""
        if not self.assistant:
            return
        
        # Apply pending frame
        if self.assistant.capture:
            try:
                frame = self.assistant.capture.get_frame()
                if frame is not None:
                    self.debug_view.update_frame(frame.copy())
            except Exception:
                pass
        
        # Apply pending state (written by background thread, read here on GUI thread)
        state = getattr(self, '_pending_state', None)
        if state is not None:
            inf_ms = getattr(self, '_pending_inf_ms', 0)
            self.debug_view.update_metrics(
                state.capture_fps, state.detection_fps,
                inf_ms, state.latency_ms,
                state.frame_age_ms, state.lifecycle_state,
                state.detector_device
            )
            self.debug_view.update_detections(self._last_detections, state.current_target)
            self.debug_view.update_targets(state.current_target, state.flick_target)
            self.debug_view.set_aim_fov(self.config.aim.aim_fov)
            self.debug_view.set_flick_fov(self.config.flick.flick_fov)
            self.debug_view.set_feature_enabled(
                self.config.aim.enabled, self.config.flick.enabled, self.config.trigger.enabled
            )
            self.debug_view.update_key_states(
                state.aim_key_down, state.flick_key_down, state.trigger_key_down
            )
            # Pass actual active bone (from checkboxes, not stale aim_bone string)
            self.debug_view.update_bone_settings(
                getattr(state, 'active_bone', 'upper_head'),
                getattr(state, 'bone_scale', 1.0),
                getattr(self.config.trigger, 'trigger_scale', 50)
            )
            # Always On FOV + active status
            self.debug_view._always_on_enabled = self.config.always_on.enabled
            self.debug_view._always_on_fov = self.config.always_on.fov
            self.debug_view._always_on_active = getattr(state, 'always_on_active', False)
    
    def _on_clear_processes(self):
        """Clear zombie processes and restart detection"""
        print("Clearing processes...")
        
        # Stop assistant if running
        was_running = self.assistant and self.assistant.is_running
        if was_running:
            self.assistant.stop()
        
        # Run full cleanup
        cleared = full_cleanup()
        
        # Restart if was running
        if was_running and self.assistant:
            import time
            time.sleep(0.5)  # Brief pause
            self.assistant.start()
            print("Detection restarted")
        
        print(f"Clear complete: {cleared} items")
    
    def closeEvent(self, event):
        """Clean shutdown - release all resources"""
        print("Shutting down...")
        
        # Stop assistant (includes capture, detector, input blocker)
        if self.assistant:
            try:
                if self.assistant.is_running:
                    self.assistant.stop()
                # Explicitly stop capture to release UDP socket
                if self.assistant.capture:
                    self.assistant.capture.stop()
                # Stop input blocker
                if self.assistant.input_blocker:
                    self.assistant.input_blocker.stop()
            except Exception as e:
                print(f"Cleanup error: {e}")
        
        # Save config
        save_config()
        
        # Restore stdout/stderr before exit
        if hasattr(self, 'log_console'):
            self.log_console.uninstall_redirects()
        
        # Force garbage collection to release FFmpeg/CUDA resources
        import gc
        gc.collect()
        
        print("Shutdown complete")
        event.accept()
