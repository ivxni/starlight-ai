"""
AI Detection Engine
Supports multiple inference backends:
- TensorRT (NVIDIA GPUs, fastest)
- ONNX Runtime with DirectML (AMD/Intel/NVIDIA GPUs)
- OpenVINO (Intel CPUs/iGPUs/NPU)
"""

import numpy as np
import cv2
import os
import time
from typing import List, Optional, Tuple, Dict, Any
from pathlib import Path

from .detection import Detection

# Backend availability flags
TENSORRT_AVAILABLE = False
ONNX_AVAILABLE = False
OPENVINO_AVAILABLE = False

# Try to import TensorRT
try:
    import tensorrt as trt
    import pycuda.driver as cuda
    import pycuda.autoinit
    TENSORRT_AVAILABLE = True
    print("TensorRT backend available")
except ImportError as e:
    print(f"TensorRT not installed: {e}")
except Exception as e:
    import traceback
    print(f"TensorRT import failed: {e}")
    traceback.print_exc()

# Try to import ONNX Runtime
try:
    import onnxruntime as ort
    ONNX_AVAILABLE = True
    print(f"ONNX Runtime available (providers: {ort.get_available_providers()})")
except ImportError as e:
    print(f"ONNX Runtime not installed: {e}")
except Exception as e:
    import traceback
    print(f"ONNX Runtime import failed: {e}")
    traceback.print_exc()

# Try to import OpenVINO
try:
    from openvino.runtime import Core as OVCore
    OPENVINO_AVAILABLE = True
    print("OpenVINO backend available")
except ImportError as e:
    print(f"OpenVINO not installed: {e}")
except Exception as e:
    import traceback
    print(f"OpenVINO import failed: {e}")
    traceback.print_exc()


def get_available_backends() -> List[str]:
    """Get list of available inference backends"""
    backends = []
    if ONNX_AVAILABLE:
        backends.append("onnx")
    if TENSORRT_AVAILABLE:
        backends.append("tensorrt")
    if OPENVINO_AVAILABLE:
        backends.append("openvino")
    return backends


def nms(boxes: np.ndarray, scores: np.ndarray, iou_threshold: float = 0.45) -> List[int]:
    """
    Non-Maximum Suppression
    
    Args:
        boxes: Array of boxes [N, 4] in format [x1, y1, x2, y2]
        scores: Array of confidence scores [N]
        iou_threshold: IoU threshold for suppression
        
    Returns:
        List of indices to keep
    """
    if len(boxes) == 0:
        return []
    
    x1 = boxes[:, 0]
    y1 = boxes[:, 1]
    x2 = boxes[:, 2]
    y2 = boxes[:, 3]
    
    areas = (x2 - x1) * (y2 - y1)
    order = scores.argsort()[::-1]
    
    keep = []
    while order.size > 0:
        i = order[0]
        keep.append(i)
        
        if order.size == 1:
            break
            
        xx1 = np.maximum(x1[i], x1[order[1:]])
        yy1 = np.maximum(y1[i], y1[order[1:]])
        xx2 = np.minimum(x2[i], x2[order[1:]])
        yy2 = np.minimum(y2[i], y2[order[1:]])
        
        w = np.maximum(0, xx2 - xx1)
        h = np.maximum(0, yy2 - yy1)
        
        inter = w * h
        iou = inter / (areas[i] + areas[order[1:]] - inter)
        
        inds = np.where(iou <= iou_threshold)[0]
        order = order[inds + 1]
    
    return keep


class TensorRTEngine:
    """TensorRT inference engine"""
    
    def __init__(self, engine_path: str, optimization_level: int = 3):
        if not TENSORRT_AVAILABLE:
            raise RuntimeError("TensorRT is not available")
        
        self.logger = trt.Logger(trt.Logger.WARNING)
        self.runtime = trt.Runtime(self.logger)
        
        # Load engine
        with open(engine_path, 'rb') as f:
            self.engine = self.runtime.deserialize_cuda_engine(f.read())
        
        self.context = self.engine.create_execution_context()
        
        # Allocate buffers
        self.inputs = []
        self.outputs = []
        self.bindings = []
        self.stream = cuda.Stream()
        
        for i in range(self.engine.num_io_tensors):
            name = self.engine.get_tensor_name(i)
            dtype = trt.nptype(self.engine.get_tensor_dtype(name))
            shape = self.engine.get_tensor_shape(name)
            size = trt.volume(shape)
            
            # Allocate host and device buffers
            host_mem = cuda.pagelocked_empty(size, dtype)
            device_mem = cuda.mem_alloc(host_mem.nbytes)
            
            self.bindings.append(int(device_mem))
            
            if self.engine.get_tensor_mode(name) == trt.TensorIOMode.INPUT:
                self.inputs.append({'host': host_mem, 'device': device_mem, 'shape': shape})
            else:
                self.outputs.append({'host': host_mem, 'device': device_mem, 'shape': shape})
        
        # Get input shape
        self.input_shape = self.inputs[0]['shape']
        self.input_size = (self.input_shape[2], self.input_shape[3])  # (H, W)
    
    def infer(self, input_data: np.ndarray) -> np.ndarray:
        """Run inference"""
        # Copy input to device
        np.copyto(self.inputs[0]['host'], input_data.ravel())
        cuda.memcpy_htod_async(self.inputs[0]['device'], self.inputs[0]['host'], self.stream)
        
        # Run inference
        self.context.execute_async_v2(bindings=self.bindings, stream_handle=self.stream.handle)
        
        # Copy output to host
        cuda.memcpy_dtoh_async(self.outputs[0]['host'], self.outputs[0]['device'], self.stream)
        self.stream.synchronize()
        
        return self.outputs[0]['host'].reshape(self.outputs[0]['shape'])
    
    def __del__(self):
        """Cleanup"""
        pass  # CUDA context handles cleanup


class ONNXEngine:
    """ONNX Runtime inference engine"""
    
    # Provider priority: try best GPU first, fall back gracefully
    _PROVIDER_MAP = {
        "cuda": ["CUDAExecutionProvider", "DmlExecutionProvider", "CPUExecutionProvider"],
        "directml": ["DmlExecutionProvider", "CUDAExecutionProvider", "CPUExecutionProvider"],
        "tensorrt": ["TensorrtExecutionProvider", "CUDAExecutionProvider", "CPUExecutionProvider"],
        "cpu": ["CPUExecutionProvider"],
    }
    
    def __init__(self, model_path: str, provider: str = "directml"):
        if not ONNX_AVAILABLE:
            raise RuntimeError("ONNX Runtime is not available")
        
        # Ensure NVIDIA DLLs are in PATH for GPU providers
        if provider in ("cuda", "tensorrt"):
            self._setup_cuda_paths()
            self._setup_tensorrt_paths()
        
        # Smart provider selection with automatic fallback
        available = ort.get_available_providers()
        wanted = self._PROVIDER_MAP.get(provider, ["CPUExecutionProvider"])
        providers = [p for p in wanted if p in available]
        if not providers:
            providers = ["CPUExecutionProvider"]
        
        print(f"Provider: requested={provider}, available={available}")
        print(f"Provider: will use chain {providers}")
        
        # Build optimized provider options
        has_trt = any(
            ("Tensorrt" in p) if isinstance(p, str) else ("Tensorrt" in p[0])
            for p in providers
        )
        has_cuda = any(
            ("CUDA" in p) if isinstance(p, str) else ("CUDA" in p[0])
            for p in providers
        )
        
        if has_trt:
            # TensorRT: FP16 + engine caching for fast restarts
            cache_dir = os.path.join(os.path.dirname(model_path) or ".", "trt_cache")
            os.makedirs(cache_dir, exist_ok=True)
            trt_opts = {
                'device_id': '0',
                'trt_fp16_enable': True,
                'trt_max_workspace_size': str(2 * 1024 * 1024 * 1024),
                'trt_builder_optimization_level': '3',
                'trt_engine_cache_enable': True,
                'trt_engine_cache_path': cache_dir,
            }
            providers = [
                ('TensorrtExecutionProvider', trt_opts) if (isinstance(p, str) and p == 'TensorrtExecutionProvider') else p
                for p in providers
            ]
            print(f"TensorRT options: FP16=ON, cache={cache_dir}")
        
        if has_cuda:
            cuda_opts = {
                'device_id': '0',
                'arena_extend_strategy': 'kSameAsRequested',
                'cudnn_conv_algo_search': 'EXHAUSTIVE',
                'do_copy_in_default_stream': 'True',
            }
            providers = [
                ('CUDAExecutionProvider', cuda_opts) if (isinstance(p, str) and p == 'CUDAExecutionProvider') else p
                for p in providers
            ]
            print("CUDA options: cuDNN=EXHAUSTIVE")
        
        # Session options
        sess_options = ort.SessionOptions()
        sess_options.graph_optimization_level = ort.GraphOptimizationLevel.ORT_ENABLE_ALL
        sess_options.enable_mem_pattern = True
        sess_options.enable_cpu_mem_arena = True
        
        self.session = ort.InferenceSession(model_path, sess_options, providers=providers)
        
        # Verify which provider is actually active
        self.active_provider = self.session.get_providers()[0]
        is_gpu = self.active_provider != "CPUExecutionProvider"
        
        if provider != "cpu" and not is_gpu:
            print(f"WARNING: GPU requested ({provider}) but fell back to CPU!")
            print(f"  Installed: onnxruntime-gpu provides {available}")
            print(f"  Tip: 'cuda' needs onnxruntime-gpu, 'directml' needs onnxruntime-directml")
        
        # Get input/output info
        self.input_name = self.session.get_inputs()[0].name
        self.input_shape = self.session.get_inputs()[0].shape
        
        # Handle dynamic shapes
        if isinstance(self.input_shape[2], str) or self.input_shape[2] is None:
            self.input_size = (640, 640)  # Default
        else:
            self.input_size = (self.input_shape[2], self.input_shape[3])
        
        self.output_names = [o.name for o in self.session.get_outputs()]
        
        # Read model metadata for class names
        output_shape = self.session.get_outputs()[0].shape
        self.class_names = {}
        try:
            meta = self.session.get_modelmeta()
            if meta.custom_metadata_map:
                import json
                names_str = meta.custom_metadata_map.get("names", "")
                if names_str:
                    self.class_names = json.loads(names_str)
                    # Convert string keys to int
                    self.class_names = {int(k): v for k, v in self.class_names.items()}
        except Exception:
            pass
        
        num_classes = output_shape[1] - 4 if len(output_shape) >= 2 and isinstance(output_shape[1], int) else "?"
        print(f"ONNX model loaded: input={self.input_name}, size={self.input_size}")
        print(f"  Output shape: {output_shape}, classes: {num_classes}")
        if self.class_names:
            print(f"  Class names: {self.class_names}")
        print(f"Active provider: {self.active_provider}")
        
        # Extended warmup (EXHAUSTIVE cuDNN search needs more iterations to find optimal algo)
        if is_gpu:
            try:
                dummy = np.zeros((1, 3, self.input_size[0], self.input_size[1]), dtype=np.float32)
                for _ in range(15):
                    self.session.run(self.output_names, {self.input_name: dummy})
                print("GPU warmup complete (15 iterations, cuDNN algo search done)")
            except Exception as e:
                print(f"GPU warmup failed: {e}")
    
    @staticmethod
    def _setup_cuda_paths():
        """Add NVIDIA pip package DLLs so CUDA/cuDNN can be found"""
        import importlib.util
        added = []
        for pkg in ["nvidia.cudnn", "nvidia.cublas", "nvidia.cuda_runtime"]:
            try:
                spec = importlib.util.find_spec(pkg)
                if spec and spec.submodule_search_locations:
                    bin_path = os.path.join(spec.submodule_search_locations[0], "bin")
                    if os.path.isdir(bin_path):
                        try:
                            os.add_dll_directory(bin_path)
                        except (OSError, AttributeError):
                            pass
                        if bin_path not in os.environ.get("PATH", ""):
                            os.environ["PATH"] = bin_path + os.pathsep + os.environ.get("PATH", "")
                        added.append(pkg)
            except Exception:
                pass
        if added:
            print(f"Added NVIDIA DLL paths for: {', '.join(added)}")
    
    @staticmethod
    def _setup_tensorrt_paths():
        """Add TensorRT pip package DLLs (nvinfer etc.)"""
        import importlib.util
        try:
            spec = importlib.util.find_spec("tensorrt_libs")
            if spec and spec.submodule_search_locations:
                trt_path = spec.submodule_search_locations[0]
                if os.path.isdir(trt_path):
                    try:
                        os.add_dll_directory(trt_path)
                    except (OSError, AttributeError):
                        pass
                    if trt_path not in os.environ.get("PATH", ""):
                        os.environ["PATH"] = trt_path + os.pathsep + os.environ.get("PATH", "")
                    print(f"Added TensorRT DLL path: {trt_path}")
        except Exception:
            pass
    
    def infer(self, input_data: np.ndarray) -> np.ndarray:
        """Run inference"""
        outputs = self.session.run(self.output_names, {self.input_name: input_data})
        return outputs[0]


class OpenVINOEngine:
    """OpenVINO inference engine"""
    
    def __init__(self, model_path: str, device: str = "AUTO"):
        if not OPENVINO_AVAILABLE:
            raise RuntimeError("OpenVINO is not available")
        
        self.core = OVCore()
        
        # Load model
        self.model = self.core.read_model(model_path)
        self.compiled_model = self.core.compile_model(self.model, device)
        
        # Get input/output info
        self.input_layer = self.compiled_model.input(0)
        self.output_layer = self.compiled_model.output(0)
        
        self.input_shape = self.input_layer.shape
        self.input_size = (self.input_shape[2], self.input_shape[3])
        
        # Create infer request
        self.infer_request = self.compiled_model.create_infer_request()
        
        print(f"OpenVINO model loaded on {device}: size={self.input_size}")
    
    def infer(self, input_data: np.ndarray) -> np.ndarray:
        """Run inference"""
        self.infer_request.infer({self.input_layer: input_data})
        return self.infer_request.get_output_tensor().data


class AIEngine:
    """
    Main AI inference engine
    Abstracts different backends (TensorRT, ONNX, OpenVINO)
    """
    
    def __init__(self, config=None):
        """
        Initialize AI engine
        
        Args:
            config: DetectionConfig object
        """
        self.config = config
        self.engine = None
        self.backend = "onnx"
        self.model_path = ""
        self.input_size = (640, 640)
        self.confidence_threshold = 0.60
        self.iou_threshold = 0.45
        
        # Performance tracking
        self._inference_times = []
        self._last_inference_time = 0.0
        
        if config:
            self.load_from_config(config)
    
    def load_from_config(self, config):
        """Load settings from config (does not raise on failure)"""
        self.backend = getattr(config, 'backend', 'onnx')
        self.model_path = getattr(config, 'model_file', '')
        self.confidence_threshold = getattr(config, 'confidence', 60) / 100.0
        
        onnx_provider = getattr(config, 'onnx_provider', 'directml')
        openvino_device = getattr(config, 'openvino_device', 'AUTO')
        trt_optimization = getattr(config, 'trt_optimization', 3)
        
        if self.model_path and os.path.exists(self.model_path):
            try:
                self.load_model(self.model_path, onnx_provider, openvino_device, trt_optimization)
            except Exception as e:
                print(f"Warning: Could not load model '{self.model_path}': {e}")
                print("The assistant will start without a model. Select a valid model in Settings.")
                self.engine = None
    
    def load_model(self, model_path: str, onnx_provider: str = "directml",
                   openvino_device: str = "AUTO", trt_optimization: int = 3):
        """
        Load model from file
        
        Args:
            model_path: Path to model file (.onnx or .engine)
            onnx_provider: ONNX provider (directml, cuda, cpu)
            openvino_device: OpenVINO device (AUTO, CPU, GPU, NPU)
            trt_optimization: TensorRT optimization level
        """
        self.model_path = model_path
        ext = Path(model_path).suffix.lower()
        
        try:
            # Print current backend availability
            print(f"Backend availability - ONNX: {ONNX_AVAILABLE}, TensorRT: {TENSORRT_AVAILABLE}, OpenVINO: {OPENVINO_AVAILABLE}")
            
            if ext == ".engine":
                if TENSORRT_AVAILABLE:
                    self.backend = "tensorrt"
                    self.engine = TensorRTEngine(model_path, trt_optimization)
                else:
                    raise RuntimeError("TensorRT is not available for .engine model")
            elif ext in [".onnx", ".enc"]:
                # Use ONNX Runtime by default for .onnx/.enc files
                if ONNX_AVAILABLE:
                    self.backend = "onnx"
                    self.engine = ONNXEngine(model_path, onnx_provider)
                elif OPENVINO_AVAILABLE:
                    self.backend = "openvino"
                    self.engine = OpenVINOEngine(model_path, openvino_device)
                else:
                    raise RuntimeError(f"No inference backend available for ONNX model. ONNX_AVAILABLE={ONNX_AVAILABLE}")
            elif ext == ".xml":
                if OPENVINO_AVAILABLE:
                    self.backend = "openvino"
                    self.engine = OpenVINOEngine(model_path, openvino_device)
                else:
                    raise RuntimeError("OpenVINO is not available for .xml model")
            else:
                raise ValueError(f"Unsupported model format: {ext}")
            
            self.input_size = self.engine.input_size
            print(f"Model loaded: {model_path} (backend={self.backend}, size={self.input_size})")
            
        except Exception as e:
            print(f"Error loading model: {e}")
            self.engine = None
            raise
    
    def preprocess(self, frame: np.ndarray) -> Tuple[np.ndarray, float, float]:
        """
        Preprocess frame for inference (optimized)
        Split resize (INTER_NEAREST for speed) + blobFromImage (no resize needed)
        """
        h, w = frame.shape[:2]
        target_h, target_w = self.input_size
        scale_x = w / target_w
        scale_y = h / target_h
        
        # If frame is not model input size, resize with INTER_NEAREST (fastest)
        # INTER_NEAREST is fine here - AI model doesn't need smooth interpolation
        if h != target_h or w != target_w:
            frame = cv2.resize(frame, (target_w, target_h), interpolation=cv2.INTER_NEAREST)
        
        # blobFromImage on already-resized frame: only normalize+swap+transpose (no resize)
        blob = cv2.dnn.blobFromImage(frame, 1.0 / 255.0, swapRB=True, crop=False)
        
        # Ensure contiguous for fast CUDA memcpy
        if not blob.flags['C_CONTIGUOUS']:
            blob = np.ascontiguousarray(blob)
        return blob, scale_x, scale_y
    
    def postprocess(self, output: np.ndarray, scale_x: float, scale_y: float,
                    frame_width: int, frame_height: int) -> List[Detection]:
        """
        Postprocess model output to detections (vectorized - no Python for-loops)
        """
        # Handle batch dimension
        if len(output.shape) == 3:
            output = output[0]
            # YOLOv8 format: [5+classes, 8400] → transpose to [8400, 5+classes]
            if output.shape[0] < output.shape[1] and output.shape[0] <= 20:
                output = output.T
        
        num_cols = output.shape[1]
        if num_cols < 5:
            return []
        
        # Split into boxes and class scores (fully vectorized)
        boxes_xywh = output[:, :4]
        
        if num_cols > 5:
            # Multi-class: class scores start at index 4
            scores_matrix = output[:, 4:]
            class_ids = np.argmax(scores_matrix, axis=1)
            confidences = scores_matrix[np.arange(len(scores_matrix)), class_ids]
        else:
            # Single class: confidence at index 4
            confidences = output[:, 4]
            class_ids = np.zeros(len(output), dtype=np.int32)
        
        # Filter by confidence (vectorized)
        mask = confidences >= self.confidence_threshold
        if not np.any(mask):
            return []
        
        boxes_xywh = boxes_xywh[mask]
        confidences = confidences[mask]
        class_ids = class_ids[mask]
        
        # Convert xywh → xyxy and scale to original frame coords (vectorized)
        half_w = boxes_xywh[:, 2] * 0.5
        half_h = boxes_xywh[:, 3] * 0.5
        x1 = np.clip((boxes_xywh[:, 0] - half_w) * scale_x, 0, frame_width)
        y1 = np.clip((boxes_xywh[:, 1] - half_h) * scale_y, 0, frame_height)
        x2 = np.clip((boxes_xywh[:, 0] + half_w) * scale_x, 0, frame_width)
        y2 = np.clip((boxes_xywh[:, 1] + half_h) * scale_y, 0, frame_height)
        
        # NMS using OpenCV's optimized C++ implementation
        # cv2.dnn.NMSBoxes expects list of [x, y, w, h] rects
        widths = x2 - x1
        heights = y2 - y1
        rects = np.stack([x1, y1, widths, heights], axis=1).tolist()
        conf_list = confidences.astype(float).tolist()
        
        indices = cv2.dnn.NMSBoxes(rects, conf_list,
                                   self.confidence_threshold, self.iou_threshold)
        
        if len(indices) == 0:
            return []
        
        # Build detections (only for kept indices - typically <10)
        indices = indices.flatten()
        detections = []
        for i in indices:
            detections.append(Detection(
                x1=float(x1[i]), y1=float(y1[i]),
                x2=float(x2[i]), y2=float(y2[i]),
                confidence=float(confidences[i]),
                class_id=int(class_ids[i])
            ))
        
        return detections
    
    def detect(self, frame: np.ndarray) -> List[Detection]:
        """
        Run detection on frame
        
        Args:
            frame: Input frame (BGR, any size)
            
        Returns:
            List of Detection objects
        """
        if self.engine is None:
            return []
        
        try:
            h, w = frame.shape[:2]
            
            # Preprocess
            t0 = time.perf_counter()
            input_tensor, scale_x, scale_y = self.preprocess(frame)
            
            # Inference
            t1 = time.perf_counter()
            output = self.engine.infer(input_tensor)
            
            # Postprocess
            t2 = time.perf_counter()
            detections = self.postprocess(output, scale_x, scale_y, w, h)
            t3 = time.perf_counter()
            
            # Track timing (total = pre + infer + post)
            self._last_inference_time = (t3 - t0) * 1000
            self._inference_times.append(self._last_inference_time)
            if len(self._inference_times) > 100:
                self._inference_times.pop(0)
            
            # Detailed timing log every 200 frames
            self._detect_count = getattr(self, '_detect_count', 0) + 1
            if self._detect_count % 200 == 1:
                pre_ms = (t1 - t0) * 1000
                inf_ms = (t2 - t1) * 1000
                post_ms = (t3 - t2) * 1000
                provider = getattr(self.engine, 'active_provider', '?')
                print(f"[perf] pre={pre_ms:.1f}ms infer={inf_ms:.1f}ms post={post_ms:.1f}ms "
                      f"total={self._last_inference_time:.1f}ms provider={provider} "
                      f"frame={w}x{h} dets={len(detections)}")
            
            return detections
            
        except Exception as e:
            print(f"Detection error: {e}")
            return []
    
    def set_confidence(self, confidence: float):
        """Set confidence threshold (0-1)"""
        self.confidence_threshold = max(0.01, min(0.99, confidence))
    
    def set_iou_threshold(self, iou: float):
        """Set IoU threshold for NMS"""
        self.iou_threshold = max(0.1, min(0.9, iou))
    
    @property
    def inference_time(self) -> float:
        """Get last inference time in ms"""
        return self._last_inference_time
    
    @property
    def avg_inference_time(self) -> float:
        """Get average inference time in ms"""
        if self._inference_times:
            return sum(self._inference_times) / len(self._inference_times)
        return 0.0
    
    @property
    def is_loaded(self) -> bool:
        """Check if model is loaded"""
        return self.engine is not None
    
    def get_info(self) -> Dict[str, Any]:
        """Get engine info"""
        return {
            "backend": self.backend,
            "model_path": self.model_path,
            "input_size": self.input_size,
            "confidence": self.confidence_threshold,
            "loaded": self.is_loaded,
            "avg_inference_ms": self.avg_inference_time
        }
    
    def reset(self):
        """Reset engine state"""
        self._inference_times.clear()
        self._last_inference_time = 0.0


def scan_models_folder(folder: str = "models") -> List[str]:
    """
    Scan folder for model files
    
    Args:
        folder: Path to models folder
        
    Returns:
        List of model file paths
    """
    models = []
    if os.path.exists(folder):
        for f in os.listdir(folder):
            ext = Path(f).suffix.lower()
            if ext in [".onnx", ".engine", ".xml", ".enc"]:
                models.append(os.path.join(folder, f))
    return sorted(models)
