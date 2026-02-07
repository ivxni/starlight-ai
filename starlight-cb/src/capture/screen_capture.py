"""
Screen Capture Module
Supports: Screen capture, Window capture, OBS Virtual Camera
"""

import numpy as np
import cv2
import time
from typing import Optional, Tuple, List
from collections import deque
from dataclasses import dataclass
from threading import Thread, Lock
import ctypes
from ctypes import wintypes

try:
    import bettercam as dxcam  # Maintained fork with stability fixes
    DXCAM_AVAILABLE = True
    print("Using bettercam (stable)")
except ImportError:
    try:
        import dxcam  # Fallback to original dxcam
        DXCAM_AVAILABLE = True
        print("Using dxcam (original)")
    except ImportError:
        DXCAM_AVAILABLE = False
        print("Warning: bettercam/dxcam not available, falling back to mss")

try:
    import mss
    MSS_AVAILABLE = True
except ImportError:
    MSS_AVAILABLE = False

# Windows API for window capture
user32 = ctypes.windll.user32
gdi32 = ctypes.windll.gdi32

# Window capture constants
SRCCOPY = 0x00CC0020
DIB_RGB_COLORS = 0


class BITMAPINFOHEADER(ctypes.Structure):
    _fields_ = [
        ('biSize', wintypes.DWORD),
        ('biWidth', wintypes.LONG),
        ('biHeight', wintypes.LONG),
        ('biPlanes', wintypes.WORD),
        ('biBitCount', wintypes.WORD),
        ('biCompression', wintypes.DWORD),
        ('biSizeImage', wintypes.DWORD),
        ('biXPelsPerMeter', wintypes.LONG),
        ('biYPelsPerMeter', wintypes.LONG),
        ('biClrUsed', wintypes.DWORD),
        ('biClrImportant', wintypes.DWORD),
    ]


class BITMAPINFO(ctypes.Structure):
    _fields_ = [
        ('bmiHeader', BITMAPINFOHEADER),
        ('bmiColors', wintypes.DWORD * 3),
    ]


def get_window_list() -> List[Tuple[int, str]]:
    """Get list of visible windows with titles"""
    windows = []
    
    def enum_callback(hwnd, _):
        if user32.IsWindowVisible(hwnd):
            length = user32.GetWindowTextLengthW(hwnd)
            if length > 0:
                buff = ctypes.create_unicode_buffer(length + 1)
                user32.GetWindowTextW(hwnd, buff, length + 1)
                windows.append((hwnd, buff.value))
        return True
    
    WNDENUMPROC = ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.POINTER(ctypes.c_int), ctypes.POINTER(ctypes.c_int))
    user32.EnumWindows(WNDENUMPROC(enum_callback), 0)
    return windows


def find_window_by_name(name: str) -> Optional[int]:
    """Find window handle by partial name match"""
    name_lower = name.lower()
    for hwnd, title in get_window_list():
        if name_lower in title.lower():
            return hwnd
    return None


@dataclass
class CaptureRegion:
    """Defines the capture region (cropped area)"""
    left: int
    top: int
    width: int
    height: int
    
    @property
    def right(self) -> int:
        return self.left + self.width
    
    @property
    def bottom(self) -> int:
        return self.top + self.height
    
    @property
    def center(self) -> Tuple[int, int]:
        return (self.left + self.width // 2, self.top + self.height // 2)
    
    def to_tuple(self) -> Tuple[int, int, int, int]:
        """Returns (left, top, right, bottom)"""
        return (self.left, self.top, self.right, self.bottom)


class ScreenCapture:
    """
    Multi-mode screen capture supporting:
    - Screen: DXGI/MSS capture of screen region
    - Window: Capture specific window
    - OBS: Capture from OBS Virtual Camera
    """
    
    def __init__(self, capture_width: int = 640, capture_height: int = 640, 
                 target_fps: int = 240, monitor: int = 0,
                 mode: str = "screen", window_name: str = "", obs_stream_url: str = "",
                 capture_buffer_size: int = 1, max_frame_age_ms: int = 0,
                 force_mss: bool = False):
        """
        Initialize screen capture
        
        Args:
            capture_width: Width of capture region (centered)
            capture_height: Height of capture region (centered)
            target_fps: Target capture framerate
            monitor: Monitor index to capture
            mode: "screen", "window", or "obs"
            window_name: Window title for window capture mode
            force_mss: Skip BetterCam/DXCam and use MSS directly (needed when DirectML is active)
        """
        self.force_mss = force_mss
        self.capture_width = capture_width
        self.capture_height = capture_height
        self.target_fps = target_fps
        self.monitor_idx = monitor
        self.mode = mode
        self.window_name = window_name
        self.obs_stream_url = obs_stream_url
        self.capture_buffer_size = max(1, int(capture_buffer_size))
        self.max_frame_age_ms = max(0, int(max_frame_age_ms))
        
        # Get screen dimensions
        self.screen_width = user32.GetSystemMetrics(0)
        self.screen_height = user32.GetSystemMetrics(1)
        
        # Calculate center crop region
        self.region = self._calculate_center_region()
        
        # Capture backend
        self.camera = None
        self._backend = None
        self._mss = None
        self._window_hwnd = None
        self._obs_capture = None
        
        # Hybrid capture system - MSS always ready as fallback
        self._mss_fallback_active: bool = False
        self._mss_fallback_mss = None  # Dedicated MSS instance for fallback
        self._dxcam_restarting: bool = False
        
        # Frame buffer
        self._frame: Optional[np.ndarray] = None
        self._frame_lock = Lock()
        self._frame_time: float = 0
        self._frame_buffer = deque(maxlen=self.capture_buffer_size) if self.capture_buffer_size > 1 else None
        
        # Performance tracking
        self._capture_count: int = 0
        self._capture_fps: float = 0
        self._last_fps_time: float = 0
        
        # Threading
        self._running: bool = False
        self._capture_thread: Optional[Thread] = None
        self._restart_thread: Optional[Thread] = None
        
    def _calculate_center_region(self) -> CaptureRegion:
        """Calculate the center crop region"""
        left = (self.screen_width - self.capture_width) // 2
        top = (self.screen_height - self.capture_height) // 2
        return CaptureRegion(left, top, self.capture_width, self.capture_height)
    
    def start(self) -> bool:
        """Start screen capture based on mode"""
        if self._running:
            return True
        
        if self.mode == "window":
            return self._start_window_capture()
        elif self.mode == "obs":
            return self._start_obs_capture()
        elif self.mode == "obs_stream":
            return self._start_obs_stream_capture()
        else:
            return self._start_screen_capture()
    
    def _start_screen_capture(self) -> bool:
        """Start screen region capture"""
        # Skip DXCam when DirectML is active (D3D11 conflict)
        if self.force_mss:
            print("Using MSS capture (DirectML mode - BetterCam D3D conflict avoided)")
            return self._start_mss_capture()
        
        # Try dxcam first (fastest)
        if DXCAM_AVAILABLE:
            try:
                self.camera = dxcam.create(
                    device_idx=0,
                    output_idx=self.monitor_idx,
                    output_color="BGR"
                )
                # Use region-based capture for better performance
                # This captures only the center region instead of full screen
                region = (self.region.left, self.region.top, self.region.right, self.region.bottom)
                
                # video_mode=False = on-demand capture (less CPU)
                # video_mode=True = continuous capture (more CPU, lower latency)
                # Use False for better game performance
                self.camera.start(target_fps=self.target_fps, video_mode=False, region=region)
                self._backend = "dxcam"
                self._running = True
                
                # Start capture thread
                self._capture_thread = Thread(target=self._capture_loop_dxcam_efficient, daemon=True)
                self._capture_thread.start()
                
                print(f"Screen capture started (dxcam efficient) - Region: {self.capture_width}x{self.capture_height}")
                return True
            except Exception as e:
                print(f"dxcam region capture failed: {e}, trying full capture...")
                # Fallback to full capture with crop
                try:
                    if self.camera:
                        try:
                            self.camera.stop()
                        except:
                            pass
                    self.camera = dxcam.create(
                        device_idx=0,
                        output_idx=self.monitor_idx,
                        output_color="BGR"
                    )
                    self.camera.start(target_fps=self.target_fps, video_mode=False)
                    self._backend = "dxcam"
                    self._running = True
                    
                    self._capture_thread = Thread(target=self._capture_loop_dxcam, daemon=True)
                    self._capture_thread.start()
                    
                    print(f"Screen capture started (dxcam full+crop) - Crop: {self.capture_width}x{self.capture_height}")
                    return True
                except Exception as e2:
                    print(f"dxcam failed completely: {e2}")
                    self.camera = None
        
        # Fallback to mss
        return self._start_mss_capture()
    
    def _start_mss_capture(self) -> bool:
        """Start MSS-based screen capture (GDI, no D3D conflict)"""
        if MSS_AVAILABLE:
            try:
                self._mss = mss.mss()
                self._backend = "mss"
                self._running = True
                
                # Start capture thread
                self._capture_thread = Thread(target=self._capture_loop_mss, daemon=True)
                self._capture_thread.start()
                
                print(f"Screen capture started (mss) - Region: {self.capture_width}x{self.capture_height}")
                return True
            except Exception as e:
                print(f"mss failed: {e}")
                
        print("No capture backend available!")
        return False
    
    def _start_window_capture(self) -> bool:
        """Start window capture mode"""
        if not self.window_name:
            print("Window capture: No window name specified")
            return False
        
        self._window_hwnd = find_window_by_name(self.window_name)
        if not self._window_hwnd:
            print(f"Window capture: Window '{self.window_name}' not found")
            return False
        
        self._backend = "window"
        self._running = True
        self._capture_thread = Thread(target=self._capture_loop_window, daemon=True)
        self._capture_thread.start()
        
        print(f"Window capture started - '{self.window_name}'")
        return True
    
    def _start_obs_capture(self) -> bool:
        """Start OBS Virtual Camera capture"""
        try:
            # Try to open OBS Virtual Camera
            # Common device indices for OBS Virtual Camera: 0, 1, 2
            for idx in range(5):
                cap = cv2.VideoCapture(idx, cv2.CAP_DSHOW)
                if cap.isOpened():
                    # Check if this is OBS by reading a frame
                    ret, frame = cap.read()
                    if ret and frame is not None:
                        self._obs_capture = cap
                        self._backend = "obs"
                        self._running = True
                        self._capture_thread = Thread(target=self._capture_loop_obs, daemon=True)
                        self._capture_thread.start()
                        print(f"OBS Virtual Camera started (device {idx})")
                        return True
                cap.release()
            
            print("OBS Virtual Camera not found. Make sure OBS is running and Virtual Camera is started.")
            return False
        except Exception as e:
            print(f"OBS capture failed: {e}")
            return False

    def _start_obs_stream_capture(self) -> bool:
        """Start capture from an OBS local stream URL (UDP/RTMP/etc)."""
        if not self.obs_stream_url:
            print("OBS stream: No URL set")
            return False
        
        url = self.obs_stream_url
        print(f"OBS stream: Connecting to {url}")
        print("OBS settings: Container=mpegts, Encoder=mjpeg, Keyframe=0")
        
        # Try to open with retry
        cap = None
        for attempt in range(3):
            try:
                cap = cv2.VideoCapture(url, cv2.CAP_FFMPEG)
                if cap.isOpened():
                    # Test read a frame
                    ret, _ = cap.read()
                    if ret:
                        break
                    cap.release()
                    cap = None
            except Exception as e:
                print(f"OBS stream: Attempt {attempt+1} failed: {e}")
            
            if attempt < 2:
                print(f"OBS stream: Retrying in 1s...")
                time.sleep(1)

        if cap is None or not cap.isOpened():
            print(f"OBS stream: Could not connect to {url}")
            print("Make sure OBS Recording is started BEFORE clicking Start!")
            if cap:
                try:
                    cap.release()
                except:
                    pass
            return False

        # Minimal buffer for lowest latency (MJPEG doesn't need large buffers)
        cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
        cap.set(cv2.CAP_PROP_OPEN_TIMEOUT_MSEC, 5000)
        cap.set(cv2.CAP_PROP_READ_TIMEOUT_MSEC, 500)

        self._obs_capture = cap
        self._backend = "obs_stream"
        self._running = True
        self._capture_thread = Thread(target=self._capture_loop_obs_stream, daemon=True)
        self._capture_thread.start()
        print(f"OBS stream: Connected successfully")
        return True
    
    def stop(self):
        """Stop screen capture"""
        self._running = False
        
        if self._capture_thread:
            self._capture_thread.join(timeout=2.0)
            self._capture_thread = None
            
        if self.camera:
            try:
                self.camera.stop()
            except:
                pass
            self.camera = None
            
        if self._mss:
            try:
                self._mss.close()
            except:
                pass
            self._mss = None
        
        if self._obs_capture:
            try:
                # Release multiple times to ensure cleanup
                self._obs_capture.release()
                self._obs_capture.release()
            except:
                pass
            self._obs_capture = None
            # Force garbage collection to release FFmpeg resources
            import gc
            gc.collect()
        
        self._window_hwnd = None
        with self._frame_lock:
            self._frame = None
            self._frame_time = 0
            if self._frame_buffer is not None:
                self._frame_buffer.clear()
            
        print("Screen capture stopped")
    
    def __del__(self):
        """Destructor - ensure cleanup"""
        try:
            self.stop()
        except:
            pass
    
    def set_mode(self, mode: str, window_name: str = ""):
        """Change capture mode"""
        was_running = self._running
        if was_running:
            self.stop()
        
        self.mode = mode
        self.window_name = window_name
        
        if was_running:
            self.start()
    
    @staticmethod
    def get_available_windows() -> List[str]:
        """Get list of window titles for capture"""
        return [title for _, title in get_window_list() if len(title) > 3]
    
    def _capture_loop_dxcam_efficient(self):
        """
        Efficient DXCam capture loop - minimal CPU usage.
        Uses video_mode=False (on-demand capture) for better game performance.
        """
        target_interval = 1.0 / self.target_fps
        last_good_frame = time.perf_counter()
        
        while self._running:
            start = time.perf_counter()
            
            try:
                if self.camera is None:
                    break
                
                # Grab frame on-demand (not continuous)
                frame = self.camera.grab()
                
                if frame is not None:
                    last_good_frame = time.perf_counter()
                    
                    # Frame is already cropped to region, no need to crop again
                    with self._frame_lock:
                        self._frame = frame
                        self._frame_time = time.perf_counter()
                        if self._frame_buffer is not None:
                            self._frame_buffer.append((frame, self._frame_time))
                    self._update_fps()
                else:
                    # No frame - check for stall
                    if time.perf_counter() - last_good_frame > 1.0:
                        print("DXCam stall detected, restarting...")
                        break
                        
            except Exception as e:
                print(f"DXCam error: {e}")
                break
            
            # Rate limiting - don't capture faster than needed
            elapsed = time.perf_counter() - start
            sleep_time = target_interval - elapsed
            if sleep_time > 0:
                time.sleep(sleep_time)
        
        # Fallback to full capture mode
        if self._running:
            print("Falling back to full capture mode...")
            self._cleanup_dxcam()
            try:
                self.camera = dxcam.create(
                    device_idx=0,
                    output_idx=self.monitor_idx,
                    output_color="BGR"
                )
                self.camera.start(target_fps=self.target_fps, video_mode=False)
                self._capture_loop_dxcam()
            except Exception:
                print("DXCam failed, switching to MSS...")
                self._capture_loop_mss()
    
    def _capture_loop_dxcam(self):
        """
        DXCam capture loop with full screen + crop.
        Used as fallback when region capture fails.
        """
        target_interval = 1.0 / self.target_fps
        last_good_frame = time.perf_counter()
        restart_count = 0
        
        while self._running:
            start = time.perf_counter()
            
            try:
                if self.camera is None:
                    # Try to recreate camera
                    self.camera = dxcam.create(
                        device_idx=0,
                        output_idx=self.monitor_idx,
                        output_color="BGR"
                    )
                    self.camera.start(target_fps=self.target_fps, video_mode=False)
                    restart_count += 1
                    if restart_count >= 5:
                        print("DXCam unstable, switching to MSS...")
                        self._capture_loop_mss()
                        return
                
                # Grab frame on-demand
                frame = self.camera.grab()
                
                if frame is not None:
                    last_good_frame = time.perf_counter()
                    
                    # Crop to center region
                    frame = self._crop_center(frame)
                    
                    with self._frame_lock:
                        self._frame = frame
                        self._frame_time = time.perf_counter()
                        if self._frame_buffer is not None:
                            self._frame_buffer.append((frame, self._frame_time))
                    self._update_fps()
                else:
                    # Check for stall
                    if time.perf_counter() - last_good_frame > 1.0:
                        print("DXCam stall, restarting...")
                        self._cleanup_dxcam()
                        continue
                        
            except Exception as e:
                print(f"DXCam error: {e}")
                self._cleanup_dxcam()
                time.sleep(0.1)
                continue
            
            # Rate limiting
            elapsed = time.perf_counter() - start
            sleep_time = target_interval - elapsed
            if sleep_time > 0:
                time.sleep(sleep_time)
    
    def _trigger_background_restart(self):
        """Trigger non-blocking DXCam restart while MSS provides frames."""
        if self._dxcam_restarting:
            return  # Already restarting
        
        self._mss_fallback_active = True
        self._dxcam_restarting = True
        
        # Start background restart thread
        self._restart_thread = Thread(target=self._restart_dxcam_background, daemon=True)
        self._restart_thread.start()
    
    def _restart_dxcam_background(self):
        """Restart DXCam in background while MSS handles capture."""
        import gc
        
        try:
            # Cleanup old camera
            self._cleanup_dxcam()
            gc.collect()
            
            time.sleep(0.1)  # Brief pause for DirectX to stabilize
            
            # Recreate camera with video_mode=False for efficiency
            self.camera = dxcam.create(
                device_idx=0,
                output_idx=self.monitor_idx,
                output_color="BGR"
            )
            self.camera.start(target_fps=self.target_fps, video_mode=False)
            
            time.sleep(0.03)  # Brief warmup
            
        except Exception as e:
            print(f"Background restart failed: {e}")
            self.camera = None
        finally:
            self._dxcam_restarting = False
    
    def _grab_mss_fallback_frame(self):
        """Grab a frame using MSS fallback (used while DXCam is restarting)."""
        if not self._mss_fallback_mss:
            return
        
        try:
            # Capture full screen and crop (like DXCam does)
            monitor = self._mss_fallback_mss.monitors[self.monitor_idx + 1]  # mss uses 1-indexed
            screenshot = self._mss_fallback_mss.grab(monitor)
            frame = np.array(screenshot)
            frame = cv2.cvtColor(frame, cv2.COLOR_BGRA2BGR)
            
            # Crop to center
            frame = self._crop_center(frame)
            
            with self._frame_lock:
                self._frame = frame
                self._frame_time = time.perf_counter()
                if self._frame_buffer is not None:
                    self._frame_buffer.append((frame, self._frame_time))
            self._update_fps()
            
        except Exception as e:
            pass  # MSS errors are non-fatal
    
    def _cleanup_dxcam(self):
        """Safely cleanup dxcam camera instance."""
        try:
            if hasattr(self, 'camera') and self.camera:
                try:
                    self.camera.stop()
                except:
                    pass
                try:
                    del self.camera
                except:
                    pass
        except:
            pass
        self.camera = None
    
    def _capture_loop_mss(self):
        """Capture loop using mss"""
        monitor = {
            "left": self.region.left,
            "top": self.region.top,
            "width": self.region.width,
            "height": self.region.height
        }
        
        target_interval = 1.0 / self.target_fps
        frame_count = 0
        error_count = 0
        
        # MSS instances are NOT thread-safe - create a new one for this thread
        try:
            import mss as _mss
            thread_mss = _mss.mss()
        except Exception as e:
            print(f"MSS thread init failed: {e}")
            return
        
        print(f"MSS capture thread started - monitor region: {monitor}")
        
        while self._running:
            start = time.perf_counter()
            try:
                screenshot = thread_mss.grab(monitor)
                frame = np.array(screenshot)
                # Convert BGRA to BGR
                frame = cv2.cvtColor(frame, cv2.COLOR_BGRA2BGR)
                
                with self._frame_lock:
                    self._frame = frame
                    self._frame_time = time.perf_counter()
                    if self._frame_buffer is not None:
                        self._frame_buffer.append((frame, self._frame_time))
                self._update_fps()
                
                frame_count += 1
                if frame_count == 1:
                    print(f"MSS first frame captured: {frame.shape[1]}x{frame.shape[0]}")
                    
            except Exception as e:
                error_count += 1
                if error_count <= 5:
                    print(f"MSS capture error ({error_count}): {e}")
                if error_count > 100:
                    print("MSS too many errors, stopping capture thread")
                    break
                
            # Rate limiting
            elapsed = time.perf_counter() - start
            if elapsed < target_interval:
                time.sleep(target_interval - elapsed)
        
        try:
            thread_mss.close()
        except:
            pass
    
    def _capture_loop_window(self):
        """Capture loop for window capture"""
        target_interval = 1.0 / self.target_fps
        
        while self._running:
            start = time.perf_counter()
            try:
                frame = self._capture_window()
                if frame is not None:
                    # Crop to center region
                    frame = self._crop_center(frame)
                    
                    with self._frame_lock:
                        self._frame = frame
                        self._frame_time = time.perf_counter()
                        if self._frame_buffer is not None:
                            self._frame_buffer.append((frame, self._frame_time))
                    self._update_fps()
            except Exception as e:
                pass
            
            elapsed = time.perf_counter() - start
            if elapsed < target_interval:
                time.sleep(target_interval - elapsed)
    
    def _capture_window(self) -> Optional[np.ndarray]:
        """Capture window content using Windows GDI"""
        if not self._window_hwnd:
            return None
        
        try:
            # Get window dimensions
            rect = wintypes.RECT()
            user32.GetClientRect(self._window_hwnd, ctypes.byref(rect))
            width = rect.right - rect.left
            height = rect.bottom - rect.top
            
            if width <= 0 or height <= 0:
                return None
            
            # Get device contexts
            hwnd_dc = user32.GetDC(self._window_hwnd)
            mfc_dc = gdi32.CreateCompatibleDC(hwnd_dc)
            bitmap = gdi32.CreateCompatibleBitmap(hwnd_dc, width, height)
            gdi32.SelectObject(mfc_dc, bitmap)
            
            # Capture
            result = ctypes.windll.user32.PrintWindow(self._window_hwnd, mfc_dc, 2)
            
            if result:
                # Get bitmap data
                bmi = BITMAPINFO()
                bmi.bmiHeader.biSize = ctypes.sizeof(BITMAPINFOHEADER)
                bmi.bmiHeader.biWidth = width
                bmi.bmiHeader.biHeight = -height  # Top-down
                bmi.bmiHeader.biPlanes = 1
                bmi.bmiHeader.biBitCount = 32
                bmi.bmiHeader.biCompression = 0
                
                buffer = (ctypes.c_char * (width * height * 4))()
                gdi32.GetDIBits(mfc_dc, bitmap, 0, height, buffer, ctypes.byref(bmi), DIB_RGB_COLORS)
                
                # Convert to numpy array
                img = np.frombuffer(buffer, dtype=np.uint8).reshape((height, width, 4))
                frame = cv2.cvtColor(img, cv2.COLOR_BGRA2BGR)
            else:
                frame = None
            
            # Cleanup
            gdi32.DeleteObject(bitmap)
            gdi32.DeleteDC(mfc_dc)
            user32.ReleaseDC(self._window_hwnd, hwnd_dc)
            
            return frame
        except Exception as e:
            return None
    
    def _capture_loop_obs(self):
        """Capture loop for OBS Virtual Camera"""
        frame_count = 0
        while self._running:
            try:
                ret, frame = self._obs_capture.read()
                if ret and frame is not None:
                    # Debug: print original size once
                    if frame_count == 0:
                        print(f"OBS frame size: {frame.shape[1]}x{frame.shape[0]}")
                    
                    # Crop to center region - no stretching
                    cropped = self._crop_center(frame)
                    
                    # Debug: print cropped size once
                    if frame_count == 0:
                        print(f"Cropped size: {cropped.shape[1]}x{cropped.shape[0]}")
                        frame_count = 1
                    
                    with self._frame_lock:
                        self._frame = cropped
                        self._frame_time = time.perf_counter()
                        if self._frame_buffer is not None:
                            self._frame_buffer.append((cropped, self._frame_time))
                    self._update_fps()
            except Exception as e:
                pass
            time.sleep(0.001)

    def _capture_loop_obs_stream(self):
        """Capture loop for OBS stream URL (UDP/RTMP/etc) - optimized for MJPEG."""
        frame_count = 0
        consecutive_fails = 0
        last_frame_time = time.perf_counter()
        
        while self._running:
            try:
                # For MJPEG: use direct read() - each frame is independent
                ret, frame = self._obs_capture.read()
                
                if not ret or frame is None:
                    consecutive_fails += 1
                    
                    # After many fails, try to reconnect
                    if consecutive_fails > 500:
                        print("OBS stream: Too many failed reads, attempting reconnect...")
                        try:
                            self._obs_capture.release()
                            time.sleep(0.5)
                            self._obs_capture = cv2.VideoCapture(self.obs_stream_url, cv2.CAP_FFMPEG)
                            self._obs_capture.set(cv2.CAP_PROP_BUFFERSIZE, 1)
                            consecutive_fails = 0
                            print("OBS stream: Reconnected")
                        except Exception as e:
                            print(f"OBS stream: Reconnect failed: {e}")
                    
                    # Adaptive sleep based on failure count
                    if consecutive_fails > 100:
                        time.sleep(0.01)
                    elif consecutive_fails > 10:
                        time.sleep(0.002)
                    continue
                
                consecutive_fails = 0
                now = time.perf_counter()
                
                # Log first frame and periodic health
                if frame_count == 0:
                    print(f"OBS stream: First frame received - {frame.shape[1]}x{frame.shape[0]}")
                elif frame_count == 100:
                    fps = 100 / (now - last_frame_time) if (now - last_frame_time) > 0 else 0
                    print(f"OBS stream: Healthy - ~{fps:.0f} FPS")
                
                # Crop to center region
                cropped = self._crop_center(frame)
                
                if frame_count == 0:
                    print(f"OBS stream: Crop size - {cropped.shape[1]}x{cropped.shape[0]}")
                
                frame_count += 1
                if frame_count == 1:
                    last_frame_time = now
                
                with self._frame_lock:
                    self._frame = cropped
                    self._frame_time = now
                    if self._frame_buffer is not None:
                        self._frame_buffer.append((cropped, now))
                
                self._update_fps()
                
            except Exception as e:
                if frame_count == 0:
                    print(f"OBS stream error: {e}")
                time.sleep(0.001)
    
    def _crop_center(self, frame: np.ndarray) -> np.ndarray:
        """Crop frame to center region of specified size - NO resizing/stretching"""
        h, w = frame.shape[:2]
        
        # If frame is smaller than crop size, just return it as-is
        if w <= self.capture_width and h <= self.capture_height:
            return frame
        
        # Calculate center crop coordinates
        left = max(0, (w - self.capture_width) // 2)
        top = max(0, (h - self.capture_height) // 2)
        right = left + self.capture_width
        bottom = top + self.capture_height
        
        # Ensure we don't go out of bounds
        right = min(right, w)
        bottom = min(bottom, h)
        
        # Crop without any resizing
        cropped = frame[top:bottom, left:right]
        
        return cropped
    
    def _update_fps(self):
        """Update FPS counter"""
        self._capture_count += 1
        now = time.perf_counter()
        
        if now - self._last_fps_time >= 1.0:
            self._capture_fps = self._capture_count / (now - self._last_fps_time)
            self._capture_count = 0
            self._last_fps_time = now
    
    def get_frame(self) -> Optional[np.ndarray]:
        """
        Get the latest captured frame
        
        Returns:
            BGR numpy array of shape (height, width, 3) or None
        """
        with self._frame_lock:
            frame = self._frame
            ts = self._frame_time
            if self._frame_buffer is not None and self._frame_buffer:
                frame, ts = self._frame_buffer[-1]
            if frame is not None:
                if self.max_frame_age_ms:
                    age_ms = (time.perf_counter() - ts) * 1000
                    if age_ms > self.max_frame_age_ms:
                        return None
                return frame.copy()
        return None
    
    def get_frame_with_timestamp(self) -> Tuple[Optional[np.ndarray], float]:
        """
        Get the latest frame with its timestamp
        
        Returns:
            Tuple of (frame, timestamp)
        """
        with self._frame_lock:
            frame = self._frame
            ts = self._frame_time
            if self._frame_buffer is not None and self._frame_buffer:
                frame, ts = self._frame_buffer[-1]
            if frame is not None:
                if self.max_frame_age_ms:
                    age_ms = (time.perf_counter() - ts) * 1000
                    if age_ms > self.max_frame_age_ms:
                        return None, 0
                return frame.copy(), ts
        return None, 0
    
    @property
    def fps(self) -> float:
        """Get current capture FPS"""
        return self._capture_fps
    
    @property
    def backend(self) -> str:
        """Get current capture backend name"""
        return self._backend or "none"
    
    @property
    def is_running(self) -> bool:
        """Check if capture is running"""
        return self._running
    
    def update_region(self, width: int, height: int):
        """Update capture region size"""
        self.capture_width = width
        self.capture_height = height
        self.region = self._calculate_center_region()
        
        # Restart capture with new region if running
        if self._running:
            was_running = True
            self.stop()
            self.start()
    
    @property
    def screen_center(self) -> Tuple[int, int]:
        """Get screen center coordinates"""
        return (self.screen_width // 2, self.screen_height // 2)
    
    def frame_to_screen_coords(self, frame_x: int, frame_y: int) -> Tuple[int, int]:
        """Convert frame coordinates to screen coordinates"""
        screen_x = self.region.left + frame_x
        screen_y = self.region.top + frame_y
        return (screen_x, screen_y)
    
    def screen_to_frame_coords(self, screen_x: int, screen_y: int) -> Tuple[int, int]:
        """Convert screen coordinates to frame coordinates"""
        frame_x = screen_x - self.region.left
        frame_y = screen_y - self.region.top
        return (frame_x, frame_y)
