"""
Settings Tab - Minimal Design
"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QComboBox, QScrollArea, QFrame, QTabWidget,
    QSpinBox, QDoubleSpinBox, QAbstractSpinBox, QLineEdit, QPushButton,
    QFileDialog
)
from PyQt6.QtCore import Qt

from ..widgets.section_widget import SectionWidget
from ..widgets.slider_widget import SliderWidget
from ..widgets.toggle_switch import LabeledToggle, ToggleWithStatus
from ...core.config import Config


class CaptureSettings(QWidget):
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
        
        # Capture Source
        cap = SectionWidget("Capture Source")
        
        source_row = QHBoxLayout()
        source_row.addWidget(QLabel("Source"))
        source_row.addStretch()
        self.source_mode = QComboBox()
        self.source_mode.addItems(["Screen"])
        self.source_mode.setFixedWidth(140)
        self.source_mode.currentTextChanged.connect(self._on_source_change)
        source_row.addWidget(self.source_mode)
        cap.addLayout(source_row)
        
        layout.addWidget(cap)
        
        # Resolution
        res = SectionWidget("Resolution")
        
        res_row = QHBoxLayout()
        res_row.addWidget(QLabel("Width"))
        self.width = QSpinBox()
        # allow small crop sizes like 120x120
        self.width.setRange(32, 3840)
        self.width.setValue(640)
        self.width.setButtonSymbols(QSpinBox.ButtonSymbols.NoButtons)
        # If user types out-of-range, clamp instead of reverting to previous value
        self.width.setCorrectionMode(QAbstractSpinBox.CorrectionMode.CorrectToNearestValue)
        # Don't emit intermediate value changes while typing
        self.width.setKeyboardTracking(False)
        self.width.setFixedWidth(70)
        self.width.editingFinished.connect(self._on_width_changed)
        res_row.addWidget(self.width)
        
        res_row.addSpacing(10)
        res_row.addWidget(QLabel("Height"))
        self.height = QSpinBox()
        self.height.setRange(32, 2160)
        self.height.setValue(640)
        self.height.setButtonSymbols(QSpinBox.ButtonSymbols.NoButtons)
        self.height.setCorrectionMode(QAbstractSpinBox.CorrectionMode.CorrectToNearestValue)
        self.height.setKeyboardTracking(False)
        self.height.setFixedWidth(70)
        self.height.editingFinished.connect(self._on_height_changed)
        res_row.addWidget(self.height)
        res_row.addStretch()
        res.addLayout(res_row)
        
        self.max_fps = SliderWidget("Max FPS", 30, 360, 240)
        self.max_fps.valueChanged.connect(lambda v: setattr(self.config.capture, 'max_fps', int(v)))
        res.addWidget(self.max_fps)
        
        layout.addWidget(res)
        
        # Debug
        dbg = SectionWidget("Debug Display")
        
        self.dbg_scale = SliderWidget("Scale", 0.25, 2.0, 1.0, decimals=2)
        self.dbg_scale.valueChanged.connect(lambda v: setattr(self.config.capture, 'debug_scale', v))
        dbg.addWidget(self.dbg_scale)
        
        self.dbg_fps = SliderWidget("Max FPS", 15, 120, 60)
        self.dbg_fps.valueChanged.connect(lambda v: setattr(self.config.capture, 'debug_max_fps', int(v)))
        dbg.addWidget(self.dbg_fps)
        
        self.dbg_bones = ToggleWithStatus("Show Bone Skeleton")
        self.dbg_bones.setChecked(False)
        dbg.addWidget(self.dbg_bones)
        
        self.dbg_trigger_zone = ToggleWithStatus("Show Trigger Zone")
        self.dbg_trigger_zone.setChecked(True)
        dbg.addWidget(self.dbg_trigger_zone)
        
        layout.addWidget(dbg)
        layout.addStretch()
        
        scroll.setWidget(content)
        main = QVBoxLayout(self)
        main.setContentsMargins(0, 0, 0, 0)
        main.addWidget(scroll)
    
    def _load_config(self):
        # Block signals to prevent feedback loops while populating UI
        self.source_mode.blockSignals(True)
        self.width.blockSignals(True)
        self.height.blockSignals(True)
        self.max_fps.blockSignals(True)
        self.dbg_scale.blockSignals(True)
        self.dbg_fps.blockSignals(True)
        
        c = self.config.capture
        
        mode_map = {"screen": "Screen"}
        self.source_mode.setCurrentText(mode_map.get(c.capture_mode, "Screen"))
        
        self.width.setValue(int(c.capture_width))
        self.height.setValue(int(c.capture_height))
        self.max_fps.setValue(int(c.max_fps))
        self.dbg_scale.setValue(float(c.debug_scale))
        self.dbg_fps.setValue(int(c.debug_max_fps))
        
        # Re-enable signals
        self.source_mode.blockSignals(False)
        self.width.blockSignals(False)
        self.height.blockSignals(False)
        self.max_fps.blockSignals(False)
        self.dbg_scale.blockSignals(False)
        self.dbg_fps.blockSignals(False)
    
    def _on_source_change(self, text: str):
        mode_map = {"Screen": "screen", "OBS Virtual Camera": "obs"}
        self.config.capture.capture_mode = mode_map.get(text, "screen")

    def _on_width_changed(self):
        self.config.capture.capture_width = int(self.width.value())

    def _on_height_changed(self):
        self.config.capture.capture_height = int(self.height.value())


class DetectionSettings(QWidget):
    """AI Detection Settings - Backend, Model, Bones, Class Filter"""
    
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
        
        # ============ Backend & Model Section ============
        backend_section = SectionWidget("Backend & Model")
        
        # GPU Provider Selection
        provider_row = QHBoxLayout()
        provider_row.addWidget(QLabel("GPU Provider"))
        provider_row.addStretch()
        self.gpu_provider = QComboBox()
        self.gpu_provider.addItems(["TensorRT", "CUDA", "DirectML", "CPU"])
        self.gpu_provider.setFixedWidth(120)
        self.gpu_provider.setToolTip("TensorRT: NVIDIA GPUs (fastest, FP16)\nCUDA: NVIDIA GPUs (fast)\nDirectML: All GPUs (needs onnxruntime-directml)\nCPU: Fallback")
        self.gpu_provider.currentTextChanged.connect(self._on_provider_change)
        provider_row.addWidget(self.gpu_provider)
        backend_section.addLayout(provider_row)
        
        # Model File Selection
        model_row = QHBoxLayout()
        model_row.addWidget(QLabel("Model File"))
        model_row.addStretch()
        self.model_file = QComboBox()
        self.model_file.setFixedWidth(200)
        self.model_file.setToolTip("Select ONNX or TensorRT engine file")
        self.model_file.currentTextChanged.connect(self._on_model_change)
        model_row.addWidget(self.model_file)
        backend_section.addLayout(model_row)
        
        # Refresh Models Button
        refresh_row = QHBoxLayout()
        refresh_row.addStretch()
        self.refresh_btn = QPushButton("Refresh Models")
        self.refresh_btn.setFixedWidth(100)
        self.refresh_btn.clicked.connect(self._refresh_models)
        refresh_row.addWidget(self.refresh_btn)
        backend_section.addLayout(refresh_row)
        
        # Confidence
        conf_row = QHBoxLayout()
        conf_row.addWidget(QLabel("Confidence"))
        conf_row.addStretch()
        self.confidence = QComboBox()
        self.confidence.addItems([str(i) for i in range(10, 100, 5)])
        self.confidence.setFixedWidth(80)
        self.confidence.setToolTip("Minimum confidence threshold (1-99%)")
        self.confidence.currentTextChanged.connect(self._on_confidence_change)
        conf_row.addWidget(self.confidence)
        backend_section.addLayout(conf_row)
        
        layout.addWidget(backend_section)
        
        # ============ Model Settings Section ============
        model_section = SectionWidget("Model Settings")
        
        # Model Type
        type_row = QHBoxLayout()
        type_row.addWidget(QLabel("Model Type"))
        type_row.addStretch()
        self.model_type = QComboBox()
        self.model_type.addItems(["Object Detection", "Pose Estimation"])
        self.model_type.setFixedWidth(140)
        self.model_type.currentTextChanged.connect(self._on_model_type_change)
        type_row.addWidget(self.model_type)
        model_section.addLayout(type_row)
        
        # TRT Optimization Level
        trt_row = QHBoxLayout()
        trt_row.addWidget(QLabel("TRT Optimization"))
        trt_row.addStretch()
        self.trt_level = QComboBox()
        self.trt_level.addItems(["Level " + str(i) for i in range(6)])
        self.trt_level.setFixedWidth(100)
        self.trt_level.setToolTip("TensorRT optimization level (higher = faster but longer build)")
        self.trt_level.currentIndexChanged.connect(lambda i: setattr(self.config.detection, 'trt_optimization', i))
        trt_row.addWidget(self.trt_level)
        model_section.addLayout(trt_row)
        
        # Async Inference Toggle
        self.async_inference = LabeledToggle("Async Inference Disabled (Lower Latency)")
        self.async_inference.setToolTip("Async: Higher FPS but more latency\nSync: Lower latency, frame-by-frame")
        self.async_inference.toggled.connect(lambda v: setattr(self.config.detection, 'async_inference', v))
        model_section.addWidget(self.async_inference)
        
        layout.addWidget(model_section)
        
        # ============ Detector Process Mode ============
        process_section = SectionWidget("Detector Process Mode")
        
        self.use_subprocess = LabeledToggle("Use Subprocess")
        self.use_subprocess.setToolTip("Run detection in separate process\nRequires restart to take effect")
        self.use_subprocess.toggled.connect(lambda v: setattr(self.config.detection, 'use_subprocess', v))
        process_section.addWidget(self.use_subprocess)
        
        subprocess_note = QLabel("Requires restart to take effect")
        subprocess_note.setStyleSheet("color: #64748b; font-size: 9px;")
        process_section.addWidget(subprocess_note)
        
        layout.addWidget(process_section)
        
        # ============ Aim Bones Section ============
        bones_section = SectionWidget("Aim Bones")
        
        # Head bones row
        head_label = QLabel("Head:")
        head_label.setStyleSheet("color: #94a3b8; font-size: 10px;")
        bones_section.addWidget(head_label)
        
        head_row = QHBoxLayout()
        self.bone_top_head = LabeledToggle("Top Head")
        self.bone_top_head.toggled.connect(lambda v: setattr(self.config.detection, 'bone_top_head', v))
        head_row.addWidget(self.bone_top_head)
        
        self.bone_upper_head = LabeledToggle("Upper Head")
        self.bone_upper_head.toggled.connect(lambda v: setattr(self.config.detection, 'bone_upper_head', v))
        head_row.addWidget(self.bone_upper_head)
        
        self.bone_head = LabeledToggle("Head")
        self.bone_head.toggled.connect(lambda v: setattr(self.config.detection, 'bone_head', v))
        head_row.addWidget(self.bone_head)
        
        self.bone_neck = LabeledToggle("Neck")
        self.bone_neck.toggled.connect(lambda v: setattr(self.config.detection, 'bone_neck', v))
        head_row.addWidget(self.bone_neck)
        
        head_row.addStretch()
        bones_section.addLayout(head_row)
        
        # Torso bones row
        torso_label = QLabel("Torso:")
        torso_label.setStyleSheet("color: #94a3b8; font-size: 10px; margin-top: 6px;")
        bones_section.addWidget(torso_label)
        
        torso_row1 = QHBoxLayout()
        self.bone_upper_chest = LabeledToggle("Upper Chest")
        self.bone_upper_chest.toggled.connect(lambda v: setattr(self.config.detection, 'bone_upper_chest', v))
        torso_row1.addWidget(self.bone_upper_chest)
        
        self.bone_chest = LabeledToggle("Chest")
        self.bone_chest.toggled.connect(lambda v: setattr(self.config.detection, 'bone_chest', v))
        torso_row1.addWidget(self.bone_chest)
        
        self.bone_lower_chest = LabeledToggle("Lower Chest")
        self.bone_lower_chest.toggled.connect(lambda v: setattr(self.config.detection, 'bone_lower_chest', v))
        torso_row1.addWidget(self.bone_lower_chest)
        
        torso_row1.addStretch()
        bones_section.addLayout(torso_row1)
        
        torso_row2 = QHBoxLayout()
        self.bone_upper_stomach = LabeledToggle("Upper Stomach")
        self.bone_upper_stomach.toggled.connect(lambda v: setattr(self.config.detection, 'bone_upper_stomach', v))
        torso_row2.addWidget(self.bone_upper_stomach)
        
        self.bone_stomach = LabeledToggle("Stomach")
        self.bone_stomach.toggled.connect(lambda v: setattr(self.config.detection, 'bone_stomach', v))
        torso_row2.addWidget(self.bone_stomach)
        
        self.bone_lower_stomach = LabeledToggle("Lower Stomach")
        self.bone_lower_stomach.toggled.connect(lambda v: setattr(self.config.detection, 'bone_lower_stomach', v))
        torso_row2.addWidget(self.bone_lower_stomach)
        
        self.bone_pelvis = LabeledToggle("Pelvis")
        self.bone_pelvis.toggled.connect(lambda v: setattr(self.config.detection, 'bone_pelvis', v))
        torso_row2.addWidget(self.bone_pelvis)
        
        torso_row2.addStretch()
        bones_section.addLayout(torso_row2)
        
        # Bone Scale
        self.bone_scale = SliderWidget("Bone Scale", 0.5, 2.0, 1.0, decimals=2)
        self.bone_scale.setToolTip("Scale factor for bone position within bounding box")
        self.bone_scale.valueChanged.connect(lambda v: setattr(self.config.detection, 'bone_scale', v))
        bones_section.addWidget(self.bone_scale)
        
        layout.addWidget(bones_section)
        
        # ============ Class Filter Section ============
        class_section = SectionWidget("Class Filter")
        
        filter_label = QLabel("Prioritize classes (checked = higher priority):")
        filter_label.setStyleSheet("color: #94a3b8; font-size: 10px;")
        class_section.addWidget(filter_label)
        
        filter_row = QHBoxLayout()
        self.class_filter_0 = LabeledToggle("Class Filter 0")
        self.class_filter_0.toggled.connect(lambda v: setattr(self.config.detection, 'class_filter_0', v))
        filter_row.addWidget(self.class_filter_0)
        
        self.class_filter_1 = LabeledToggle("Class Filter 1")
        self.class_filter_1.toggled.connect(lambda v: setattr(self.config.detection, 'class_filter_1', v))
        filter_row.addWidget(self.class_filter_1)
        
        self.class_filter_2 = LabeledToggle("Class Filter 2")
        self.class_filter_2.toggled.connect(lambda v: setattr(self.config.detection, 'class_filter_2', v))
        filter_row.addWidget(self.class_filter_2)
        
        self.class_filter_3 = LabeledToggle("Class Filter 3")
        self.class_filter_3.toggled.connect(lambda v: setattr(self.config.detection, 'class_filter_3', v))
        filter_row.addWidget(self.class_filter_3)
        
        filter_row.addStretch()
        class_section.addLayout(filter_row)
        
        layout.addWidget(class_section)
        
        # ============ Disable Classes Section ============
        disable_section = SectionWidget("Disable Classes")
        
        disable_label = QLabel("Completely ignore these classes:")
        disable_label.setStyleSheet("color: #94a3b8; font-size: 10px;")
        disable_section.addWidget(disable_label)
        
        disable_row = QHBoxLayout()
        self.class_disable_0 = LabeledToggle("Disable Class 0")
        self.class_disable_0.toggled.connect(lambda v: setattr(self.config.detection, 'class_disable_0', v))
        disable_row.addWidget(self.class_disable_0)
        
        self.class_disable_1 = LabeledToggle("Disable Class 1")
        self.class_disable_1.toggled.connect(lambda v: setattr(self.config.detection, 'class_disable_1', v))
        disable_row.addWidget(self.class_disable_1)
        
        self.class_disable_2 = LabeledToggle("Disable Class 2")
        self.class_disable_2.toggled.connect(lambda v: setattr(self.config.detection, 'class_disable_2', v))
        disable_row.addWidget(self.class_disable_2)
        
        self.class_disable_3 = LabeledToggle("Disable Class 3")
        self.class_disable_3.toggled.connect(lambda v: setattr(self.config.detection, 'class_disable_3', v))
        disable_row.addWidget(self.class_disable_3)
        
        disable_row.addStretch()
        disable_section.addLayout(disable_row)
        
        layout.addWidget(disable_section)
        
        # ============ Enemy Color Filter Section ============
        filter_section = SectionWidget("Enemy Color Filter")
        
        self.enemy_color_enabled = LabeledToggle("Enable Color Filter")
        self.enemy_color_enabled.setToolTip("Filter detections by enemy outline color\nUsed to exclude teammates")
        self.enemy_color_enabled.toggled.connect(lambda v: setattr(self.config.filtering, 'enemy_color_enabled', v))
        filter_section.addWidget(self.enemy_color_enabled)
        
        color_row = QHBoxLayout()
        color_row.addWidget(QLabel("Enemy Color"))
        color_row.addStretch()
        self.enemy_color = QComboBox()
        self.enemy_color.addItems(["purple", "purple_tight", "pink", "yellow", "red"])
        self.enemy_color.setFixedWidth(120)
        self.enemy_color.currentTextChanged.connect(lambda t: setattr(self.config.filtering, 'enemy_color', t))
        color_row.addWidget(self.enemy_color)
        filter_section.addLayout(color_row)
        
        layout.addWidget(filter_section)
        
        layout.addStretch()
        
        scroll.setWidget(content)
        main = QVBoxLayout(self)
        main.setContentsMargins(0, 0, 0, 0)
        main.addWidget(scroll)
        
        # Initial model scan
        self._refresh_models()
    
    def _load_config(self):
        """Load configuration values into UI"""
        d = self.config.detection
        f = self.config.filtering
        
        # Block all signals during load
        widgets = [
            self.gpu_provider, self.model_file, self.confidence, self.model_type,
            self.trt_level, self.async_inference, self.use_subprocess,
            self.bone_top_head, self.bone_upper_head, self.bone_head, self.bone_neck,
            self.bone_upper_chest, self.bone_chest, self.bone_lower_chest,
            self.bone_upper_stomach, self.bone_stomach, self.bone_lower_stomach, self.bone_pelvis,
            self.bone_scale,
            self.class_filter_0, self.class_filter_1, self.class_filter_2, self.class_filter_3,
            self.class_disable_0, self.class_disable_1, self.class_disable_2, self.class_disable_3,
            self.enemy_color_enabled, self.enemy_color
        ]
        for w in widgets:
            w.blockSignals(True)
        
        # GPU Provider
        provider_map = {"tensorrt": "TensorRT", "cuda": "CUDA", "directml": "DirectML", "cpu": "CPU"}
        self.gpu_provider.setCurrentText(provider_map.get(d.onnx_provider, "CUDA"))
        
        # Find model file in dropdown
        model_name = d.model_file.split("/")[-1].split("\\")[-1] if d.model_file else ""
        idx = self.model_file.findText(model_name)
        if idx >= 0:
            self.model_file.setCurrentIndex(idx)
        
        # Confidence
        conf_str = str(d.confidence)
        idx = self.confidence.findText(conf_str)
        if idx >= 0:
            self.confidence.setCurrentIndex(idx)
        else:
            self.confidence.setCurrentText(conf_str)
        
        # Model Settings
        type_map = {"object_detection": "Object Detection", "pose_estimation": "Pose Estimation"}
        self.model_type.setCurrentText(type_map.get(d.model_type, "Object Detection"))
        self.trt_level.setCurrentIndex(d.trt_optimization)
        self.async_inference.setChecked(d.async_inference)
        self.use_subprocess.setChecked(d.use_subprocess)
        
        # Aim Bones
        self.bone_top_head.setChecked(d.bone_top_head)
        self.bone_upper_head.setChecked(d.bone_upper_head)
        self.bone_head.setChecked(d.bone_head)
        self.bone_neck.setChecked(d.bone_neck)
        self.bone_upper_chest.setChecked(d.bone_upper_chest)
        self.bone_chest.setChecked(d.bone_chest)
        self.bone_lower_chest.setChecked(d.bone_lower_chest)
        self.bone_upper_stomach.setChecked(d.bone_upper_stomach)
        self.bone_stomach.setChecked(d.bone_stomach)
        self.bone_lower_stomach.setChecked(d.bone_lower_stomach)
        self.bone_pelvis.setChecked(d.bone_pelvis)
        self.bone_scale.setValue(d.bone_scale)
        
        # Class Filter
        self.class_filter_0.setChecked(d.class_filter_0)
        self.class_filter_1.setChecked(d.class_filter_1)
        self.class_filter_2.setChecked(d.class_filter_2)
        self.class_filter_3.setChecked(d.class_filter_3)
        
        # Disable Classes
        self.class_disable_0.setChecked(d.class_disable_0)
        self.class_disable_1.setChecked(d.class_disable_1)
        self.class_disable_2.setChecked(d.class_disable_2)
        self.class_disable_3.setChecked(d.class_disable_3)
        
        # Enemy Color Filter
        self.enemy_color_enabled.setChecked(f.enemy_color_enabled)
        self.enemy_color.setCurrentText(f.enemy_color)
        
        # Unblock all signals
        for w in widgets:
            w.blockSignals(False)
        
        # ALWAYS force backend = "onnx" (all providers go through ONNX Runtime)
        # This prevents stale "tensorrt" backend value from config.json
        self.config.detection.backend = "onnx"
    
    def _refresh_models(self):
        """Scan models folder and populate dropdown"""
        import os
        models_dir = "models"
        self.model_file.clear()
        self.model_file.addItem("")  # Empty option
        
        if os.path.exists(models_dir):
            for f in sorted(os.listdir(models_dir)):
                ext = f.split(".")[-1].lower()
                if ext in ["onnx", "engine", "enc", "xml"]:
                    self.model_file.addItem(f)
    
    def _on_provider_change(self, text: str):
        """Handle GPU provider selection change"""
        provider_map = {"TensorRT": "tensorrt", "CUDA": "cuda", "DirectML": "directml", "CPU": "cpu"}
        self.config.detection.onnx_provider = provider_map.get(text, "cuda")
        # All providers go through ONNX Runtime - keep backend as "onnx"
        self.config.detection.backend = "onnx"
    
    def _on_model_change(self, text: str):
        """Handle model file selection change"""
        if text:
            self.config.detection.model_file = f"models/{text}"
        else:
            self.config.detection.model_file = ""
    
    def _on_confidence_change(self, text: str):
        """Handle confidence threshold change"""
        try:
            self.config.detection.confidence = int(text)
        except ValueError:
            pass
    
    def _on_model_type_change(self, text: str):
        """Handle model type change"""
        type_map = {"Object Detection": "object_detection", "Pose Estimation": "pose_estimation"}
        self.config.detection.model_type = type_map.get(text, "object_detection")


class MouseSettings(QWidget):
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
        
        # Sensitivity
        sens = SectionWidget("Sensitivity")
        
        self.sens_enabled = ToggleWithStatus("Normalization", True, "On", "Off")
        self.sens_enabled.toggled.connect(lambda v: setattr(self.config.mouse, 'sens_normalization_enabled', v))
        sens.addWidget(self.sens_enabled)
        
        dpi_row = QHBoxLayout()
        dpi_row.addWidget(QLabel("DPI"))
        dpi_row.addStretch()
        self.dpi = QSpinBox()
        self.dpi.setRange(100, 16000)
        self.dpi.setValue(800)
        self.dpi.setButtonSymbols(QSpinBox.ButtonSymbols.NoButtons)
        self.dpi.setFixedWidth(70)
        self.dpi.editingFinished.connect(self._on_sens)
        dpi_row.addWidget(self.dpi)
        sens.addLayout(dpi_row)
        
        ig_row = QHBoxLayout()
        ig_row.addWidget(QLabel("In-Game Sens"))
        ig_row.addStretch()
        self.ig_sens = QDoubleSpinBox()
        self.ig_sens.setRange(0.01, 10.0)
        self.ig_sens.setDecimals(2)
        self.ig_sens.setValue(0.41)
        self.ig_sens.setButtonSymbols(QDoubleSpinBox.ButtonSymbols.NoButtons)
        self.ig_sens.setFixedWidth(70)
        self.ig_sens.editingFinished.connect(self._on_sens)
        ig_row.addWidget(self.ig_sens)
        sens.addLayout(ig_row)
        
        ref_row = QHBoxLayout()
        ref_row.addWidget(QLabel("Reference Sens"))
        ref_row.addStretch()
        self.ref_sens = QDoubleSpinBox()
        self.ref_sens.setRange(0.01, 10.0)
        self.ref_sens.setDecimals(2)
        self.ref_sens.setValue(0.70)
        self.ref_sens.setButtonSymbols(QDoubleSpinBox.ButtonSymbols.NoButtons)
        self.ref_sens.setFixedWidth(70)
        self.ref_sens.editingFinished.connect(self._on_sens)
        ref_row.addWidget(self.ref_sens)
        sens.addLayout(ref_row)
        
        self.edpi = QLabel("eDPI: 328.0")
        self.edpi.setStyleSheet("color: #64748b; font-size: 10px;")
        sens.addWidget(self.edpi)
        
        layout.addWidget(sens)
        
        # Delays
        delays = SectionWidget("Delays")
        
        self.aim_delay = SliderWidget("Aim", 0, 20, 3, suffix="ms")
        self.aim_delay.valueChanged.connect(lambda v: setattr(self.config.mouse, 'aim_delay', int(v)))
        delays.addWidget(self.aim_delay)
        
        self.flick_delay = SliderWidget("Flick", 0, 20, 3, suffix="ms")
        self.flick_delay.valueChanged.connect(lambda v: setattr(self.config.mouse, 'flick_delay', int(v)))
        delays.addWidget(self.flick_delay)
        
        self.sens_mult = SliderWidget("Sens Mult", 0.1, 3.0, 1.0, decimals=2)
        self.sens_mult.valueChanged.connect(lambda v: setattr(self.config.mouse, 'sens_multiplier', v))
        delays.addWidget(self.sens_mult)
        
        layout.addWidget(delays)
        layout.addStretch()
        
        scroll.setWidget(content)
        main = QVBoxLayout(self)
        main.setContentsMargins(0, 0, 0, 0)
        main.addWidget(scroll)
    
    def _load_config(self):
        # Block signals
        self.sens_enabled.blockSignals(True)
        self.dpi.blockSignals(True)
        self.ig_sens.blockSignals(True)
        self.ref_sens.blockSignals(True)
        self.aim_delay.blockSignals(True)
        self.flick_delay.blockSignals(True)
        self.sens_mult.blockSignals(True)
        
        m = self.config.mouse
        self.sens_enabled.setChecked(m.sens_normalization_enabled)
        self.dpi.setValue(m.dpi_value)
        self.ig_sens.setValue(m.in_game_sens)
        self.ref_sens.setValue(m.reference_sens)
        self.aim_delay.setValue(m.aim_delay)
        self.flick_delay.setValue(m.flick_delay)
        self.sens_mult.setValue(m.sens_multiplier)
        self._update_edpi()
        
        # Unblock signals
        self.sens_enabled.blockSignals(False)
        self.dpi.blockSignals(False)
        self.ig_sens.blockSignals(False)
        self.ref_sens.blockSignals(False)
        self.aim_delay.blockSignals(False)
        self.flick_delay.blockSignals(False)
        self.sens_mult.blockSignals(False)
    
    def _on_sens(self):
        self.config.mouse.dpi_value = self.dpi.value()
        self.config.mouse.in_game_sens = self.ig_sens.value()
        self.config.mouse.reference_sens = self.ref_sens.value()
        self._update_edpi()
    
    def _update_edpi(self):
        edpi = self.dpi.value() * self.ig_sens.value()
        self.edpi.setText(f"eDPI: {edpi:.1f}")


class TrackingSettings(QWidget):
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
        
        # Basic
        basic = SectionWidget("Basic")
        
        self.min_smooth = SliderWidget("Min Smooth", 0, 20, 2, decimals=1)
        self.min_smooth.valueChanged.connect(lambda v: setattr(self.config.tracking, 'min_smoothing', v))
        basic.addWidget(self.min_smooth)
        
        self.deadzone = SliderWidget("Deadzone", 0, 20, 1)
        self.deadzone.valueChanged.connect(lambda v: setattr(self.config.tracking, 'tracking_deadzone', int(v)))
        basic.addWidget(self.deadzone)
        
        self.extra = SliderWidget("Extra Smooth", 0, 20, 1, decimals=1)
        self.extra.valueChanged.connect(lambda v: setattr(self.config.tracking, 'extra_smoothing', v))
        basic.addWidget(self.extra)
        
        layout.addWidget(basic)
        
        # Clamping
        clamp = SectionWidget("Movement Clamping")
        
        self.clamp_enabled = LabeledToggle("Enable")
        self.clamp_enabled.toggled.connect(lambda v: setattr(self.config.tracking, 'movement_clamping_enabled', v))
        clamp.addWidget(self.clamp_enabled)
        
        self.clamp_fov = SliderWidget("Clamp FOV", 10, 200, 50, suffix="px")
        self.clamp_fov.valueChanged.connect(lambda v: setattr(self.config.tracking, 'clamp_fov', int(v)))
        clamp.addWidget(self.clamp_fov)
        
        self.clamp_max = SliderWidget("Clamp Max", 1, 50, 14, suffix="px")
        self.clamp_max.valueChanged.connect(lambda v: setattr(self.config.tracking, 'clamp_max', int(v)))
        clamp.addWidget(self.clamp_max)
        
        layout.addWidget(clamp)
        layout.addStretch()
        
        scroll.setWidget(content)
        main = QVBoxLayout(self)
        main.setContentsMargins(0, 0, 0, 0)
        main.addWidget(scroll)
    
    def _load_config(self):
        # Block signals
        self.min_smooth.blockSignals(True)
        self.deadzone.blockSignals(True)
        self.extra.blockSignals(True)
        self.clamp_enabled.blockSignals(True)
        self.clamp_fov.blockSignals(True)
        self.clamp_max.blockSignals(True)
        
        t = self.config.tracking
        self.min_smooth.setValue(t.min_smoothing)
        self.deadzone.setValue(t.tracking_deadzone)
        self.extra.setValue(t.extra_smoothing)
        self.clamp_enabled.setChecked(t.movement_clamping_enabled)
        self.clamp_fov.setValue(t.clamp_fov)
        self.clamp_max.setValue(t.clamp_max)
        
        # Unblock signals
        self.min_smooth.blockSignals(False)
        self.deadzone.blockSignals(False)
        self.extra.blockSignals(False)
        self.clamp_enabled.blockSignals(False)
        self.clamp_fov.blockSignals(False)
        self.clamp_max.blockSignals(False)


class SettingsTab(QWidget):
    def __init__(self, config: Config, parent=None):
        super().__init__(parent)
        self.config = config
        self._setup_ui()
    
    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        
        self.tabs = QTabWidget()
        self.tabs.setStyleSheet("""
            QTabWidget::pane { border: none; background: transparent; }
            QTabBar::tab {
                background: transparent;
                border: none;
                border-radius: 4px;
                padding: 5px 10px;
                margin-right: 4px;
                color: #64748b;
                font-size: 11px;
            }
            QTabBar::tab:hover { background: rgba(255,255,255,0.04); color: #94a3b8; }
            QTabBar::tab:selected { background: #8b5cf6; color: white; }
        """)
        
        self.capture_settings = CaptureSettings(self.config)
        self.tabs.addTab(self.capture_settings, "Capture")
        self.tabs.addTab(DetectionSettings(self.config), "Detection/Model")
        self.tabs.addTab(MouseSettings(self.config), "Mouse")
        self.tabs.addTab(TrackingSettings(self.config), "Tracking")
        
        # Expose debug toggles for main_window
        self.dbg_bones = self.capture_settings.dbg_bones
        self.dbg_trigger_zone = self.capture_settings.dbg_trigger_zone
        
        layout.addWidget(self.tabs)
