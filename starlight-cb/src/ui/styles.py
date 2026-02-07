"""
Starlight UI Styles - Minimal Dark Theme 2026
Clean, simple, compact design
"""

# ============================================
# COLOR PALETTE
# ============================================

COLORS = {
    # Backgrounds
    'bg_primary': '#0d0d12',
    'bg_secondary': '#12121a',
    'bg_tertiary': '#18182a',
    
    # Glass/Panel
    'panel_bg': 'rgba(255, 255, 255, 0.03)',
    'panel_border': 'rgba(255, 255, 255, 0.06)',
    
    # Purple accent (flat, no gradient)
    'accent': '#8b5cf6',
    'accent_hover': '#9d6ff8',
    'accent_muted': 'rgba(139, 92, 246, 0.15)',
    
    # Text
    'text_primary': '#e2e8f0',
    'text_secondary': '#94a3b8',
    'text_muted': '#64748b',
    
    # Status
    'success': '#22c55e',
    'warning': '#eab308',
    'error': '#ef4444',
    
    # Input
    'input_bg': 'rgba(0, 0, 0, 0.25)',
    'input_border': 'rgba(255, 255, 255, 0.08)',
}

# ============================================
# MINIMAL STYLESHEET
# ============================================

GLASSMORPHISM_STYLESHEET = """
/* ============================================
   GLOBAL
   ============================================ */

QWidget {
    font-family: 'Segoe UI', sans-serif;
    font-size: 12px;
    background-color: transparent;
    color: #e2e8f0;
}

QMainWindow {
    background-color: #0d0d12;
}

/* ============================================
   PANELS / GROUP BOXES
   ============================================ */

QGroupBox {
    background-color: rgba(255, 255, 255, 0.02);
    border: 1px solid rgba(255, 255, 255, 0.06);
    border-radius: 8px;
    margin-top: 16px;
    padding: 12px;
    padding-top: 24px;
}

QGroupBox::title {
    subcontrol-origin: margin;
    subcontrol-position: top left;
    left: 12px;
    padding: 4px 8px;
    color: #64748b;
    font-size: 10px;
    font-weight: 600;
}

/* ============================================
   LABELS
   ============================================ */

QLabel {
    background: transparent;
    background-color: transparent;
    border: 0px;
    border-radius: 0px;
    color: #94a3b8;
    font-size: 11px;
    padding: 0px;
    margin: 0px;
}

QLabel:!active {
    background: transparent;
}

/* ============================================
   BUTTONS
   ============================================ */

QPushButton {
    background-color: rgba(255, 255, 255, 0.04);
    border: 1px solid rgba(255, 255, 255, 0.08);
    border-radius: 6px;
    padding: 6px 14px;
    color: #e2e8f0;
    font-size: 11px;
    font-weight: 500;
}

QPushButton:hover {
    background-color: rgba(255, 255, 255, 0.06);
    border-color: rgba(139, 92, 246, 0.4);
}

QPushButton:pressed {
    background-color: rgba(139, 92, 246, 0.15);
}

QPushButton:disabled {
    background-color: rgba(255, 255, 255, 0.02);
    color: #475569;
}

/* Primary Button */
QPushButton[class="primary"] {
    background-color: #8b5cf6;
    border: none;
    color: white;
    font-weight: 600;
}

QPushButton[class="primary"]:hover {
    background-color: #9d6ff8;
}

/* ============================================
   INPUT FIELDS
   ============================================ */

QLineEdit {
    background-color: rgba(0, 0, 0, 0.25);
    border: 1px solid rgba(255, 255, 255, 0.08);
    border-radius: 4px;
    padding: 5px 8px;
    color: #e2e8f0;
    font-size: 11px;
    selection-background-color: rgba(139, 92, 246, 0.4);
}

QLineEdit:focus {
    border-color: rgba(139, 92, 246, 0.5);
}

/* ============================================
   SPIN BOXES
   ============================================ */

QSpinBox, QDoubleSpinBox {
    background-color: rgba(0, 0, 0, 0.2);
    border: 1px solid rgba(255, 255, 255, 0.08);
    border-radius: 3px;
    padding: 3px 6px;
    color: #e2e8f0;
    font-size: 11px;
    min-height: 18px;
}

QSpinBox:focus, QDoubleSpinBox:focus {
    border-color: rgba(139, 92, 246, 0.5);
}

QSpinBox::up-button, QDoubleSpinBox::up-button,
QSpinBox::down-button, QDoubleSpinBox::down-button {
    width: 0px;
    height: 0px;
    border: none;
    background: none;
}

QSpinBox::up-arrow, QDoubleSpinBox::up-arrow,
QSpinBox::down-arrow, QDoubleSpinBox::down-arrow {
    width: 0px;
    height: 0px;
    image: none;
}

/* ============================================
   COMBO BOXES
   ============================================ */

QComboBox {
    background-color: rgba(0, 0, 0, 0.25);
    border: 1px solid rgba(255, 255, 255, 0.08);
    border-radius: 4px;
    padding: 5px 8px;
    padding-right: 24px;
    color: #e2e8f0;
    font-size: 11px;
    min-height: 20px;
}

QComboBox:hover {
    border-color: rgba(139, 92, 246, 0.4);
}

QComboBox::drop-down {
    border: none;
    width: 20px;
}

QComboBox::down-arrow {
    image: none;
    border-left: 4px solid transparent;
    border-right: 4px solid transparent;
    border-top: 5px solid #64748b;
}

QComboBox QAbstractItemView {
    background-color: #18182a;
    border: 1px solid rgba(255, 255, 255, 0.1);
    border-radius: 4px;
    padding: 4px;
    selection-background-color: rgba(139, 92, 246, 0.25);
    outline: none;
}

QComboBox QAbstractItemView::item {
    padding: 5px 8px;
    border-radius: 3px;
}

/* ============================================
   SLIDERS
   ============================================ */

QSlider::groove:horizontal {
    background-color: rgba(255, 255, 255, 0.06);
    height: 3px;
    border-radius: 1px;
}

QSlider::handle:horizontal {
    background-color: #8b5cf6;
    width: 12px;
    height: 12px;
    margin: -5px 0;
    border-radius: 6px;
}

QSlider::handle:horizontal:hover {
    background-color: #9d6ff8;
}

QSlider::sub-page:horizontal {
    background-color: #8b5cf6;
    border-radius: 1px;
}

/* ============================================
   TAB WIDGET
   ============================================ */

QTabWidget::pane {
    border: none;
    background-color: transparent;
}

QTabBar::tab {
    background-color: transparent;
    border: none;
    border-radius: 3px;
    padding: 5px 10px;
    margin-right: 4px;
    color: #64748b;
    font-size: 11px;
    font-weight: 500;
}

QTabBar::tab:hover {
    background-color: rgba(255, 255, 255, 0.04);
    color: #94a3b8;
}

QTabBar::tab:selected {
    background-color: #8b5cf6;
    color: white;
}

/* ============================================
   SCROLL AREAS
   ============================================ */

QScrollArea {
    border: none;
    background-color: transparent;
}

QScrollBar:vertical {
    background-color: transparent;
    width: 6px;
    margin: 2px;
}

QScrollBar::handle:vertical {
    background-color: rgba(255, 255, 255, 0.1);
    border-radius: 3px;
    min-height: 30px;
}

QScrollBar::handle:vertical:hover {
    background-color: rgba(139, 92, 246, 0.4);
}

QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical,
QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {
    background: transparent;
    height: 0px;
}

QScrollBar:horizontal {
    background-color: transparent;
    height: 6px;
    margin: 2px;
}

QScrollBar::handle:horizontal {
    background-color: rgba(255, 255, 255, 0.1);
    border-radius: 3px;
    min-width: 30px;
}

/* ============================================
   TOOLTIPS
   ============================================ */

QToolTip {
    background-color: #1e1e2e;
    border: 1px solid rgba(255, 255, 255, 0.1);
    border-radius: 4px;
    padding: 4px 8px;
    color: #e2e8f0;
    font-size: 11px;
}

/* ============================================
   FRAMES
   ============================================ */

QFrame[class="panel"] {
    background-color: rgba(255, 255, 255, 0.02);
    border: 1px solid rgba(255, 255, 255, 0.06);
    border-radius: 8px;
}
"""

# Alias
DARK_STYLESHEET = GLASSMORPHISM_STYLESHEET
