"""
Input Blocker Module
Intercepts and blocks specific mouse/keyboard inputs from reaching the game
Uses Windows Low-Level Hooks
"""

import ctypes
from ctypes import wintypes, CFUNCTYPE, POINTER, c_int, c_void_p, byref
import threading
from typing import Set, Callable, Optional

# Windows API (use_last_error is important for reliable error codes)
user32 = ctypes.WinDLL("user32", use_last_error=True)
kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)

# Hook types
WH_MOUSE_LL = 14
WH_KEYBOARD_LL = 13

# Mouse messages
WM_LBUTTONDOWN = 0x0201
WM_LBUTTONUP = 0x0202
WM_RBUTTONDOWN = 0x0204
WM_RBUTTONUP = 0x0205
WM_MBUTTONDOWN = 0x0207
WM_MBUTTONUP = 0x0208
WM_XBUTTONDOWN = 0x020B
WM_XBUTTONUP = 0x020C

# XBUTTON values (in high word of mouseData)
XBUTTON1 = 0x0001  # Back button
XBUTTON2 = 0x0002  # Forward button

# Keyboard message
WM_KEYDOWN = 0x0100
WM_KEYUP = 0x0101
WM_SYSKEYDOWN = 0x0104
WM_SYSKEYUP = 0x0105


class MSLLHOOKSTRUCT(ctypes.Structure):
    """Mouse low-level hook structure"""
    _fields_ = [
        ("pt", wintypes.POINT),
        ("mouseData", wintypes.DWORD),
        ("flags", wintypes.DWORD),
        ("time", wintypes.DWORD),
        ("dwExtraInfo", ctypes.POINTER(ctypes.c_ulong))
    ]


class KBDLLHOOKSTRUCT(ctypes.Structure):
    """Keyboard low-level hook structure"""
    _fields_ = [
        ("vkCode", wintypes.DWORD),
        ("scanCode", wintypes.DWORD),
        ("flags", wintypes.DWORD),
        ("time", wintypes.DWORD),
        ("dwExtraInfo", ctypes.POINTER(ctypes.c_ulong))
    ]

# Hook procedure type
# Must use WINAPI calling convention (stdcall) on Windows, otherwise hook install/callback can fail.
_LRESULT = ctypes.c_longlong if ctypes.sizeof(ctypes.c_void_p) == 8 else ctypes.c_long
_HHOOK = wintypes.HANDLE
HOOKPROC = ctypes.WINFUNCTYPE(_LRESULT, c_int, wintypes.WPARAM, wintypes.LPARAM)

# Function prototypes (avoid 64-bit truncation / wrong defaults)
user32.SetWindowsHookExW.argtypes = [c_int, HOOKPROC, wintypes.HINSTANCE, wintypes.DWORD]
user32.SetWindowsHookExW.restype = _HHOOK
user32.UnhookWindowsHookEx.argtypes = [_HHOOK]
user32.UnhookWindowsHookEx.restype = wintypes.BOOL
user32.CallNextHookEx.argtypes = [_HHOOK, c_int, wintypes.WPARAM, wintypes.LPARAM]
user32.CallNextHookEx.restype = _LRESULT
user32.PeekMessageW.argtypes = [POINTER(wintypes.MSG), wintypes.HWND, wintypes.UINT, wintypes.UINT, wintypes.UINT]
user32.PeekMessageW.restype = wintypes.BOOL
user32.TranslateMessage.argtypes = [POINTER(wintypes.MSG)]
user32.TranslateMessage.restype = wintypes.BOOL
user32.DispatchMessageW.argtypes = [POINTER(wintypes.MSG)]
user32.DispatchMessageW.restype = _LRESULT

kernel32.GetModuleHandleW.argtypes = [wintypes.LPCWSTR]
kernel32.GetModuleHandleW.restype = wintypes.HMODULE


class InputBlocker:
    """
    Blocks specific mouse/keyboard inputs from reaching applications
    while still allowing the software to detect them
    """
    
    # Button name to block info mapping
    BUTTON_MAP = {
        "forward_button": ("mouse", XBUTTON2),  # Mouse X2 (Forward)
        "back_button": ("mouse", XBUTTON1),     # Mouse X1 (Back)
        "middle_button": ("mouse", "middle"),    # Middle mouse button
        "left_button": ("mouse", "left"),        # Left mouse (usually not blocked)
        "right_button": ("mouse", "right"),      # Right mouse (usually not blocked)
    }
    
    def __init__(self):
        self._mouse_hook = None
        self._keyboard_hook = None
        self._hook_thread: Optional[threading.Thread] = None
        self._running = False
        
        # Buttons to block (set of button names)
        self._blocked_buttons: Set[str] = set()
        
        # Callbacks when blocked button is pressed/released
        self.on_blocked_press: Optional[Callable[[str], None]] = None
        self.on_blocked_release: Optional[Callable[[str], None]] = None
        
        # Current state of blocked buttons
        self._button_states: dict = {}
        
        # Store hook procedures to prevent garbage collection
        self._mouse_proc = None
        self._keyboard_proc = None
    
    def add_blocked_button(self, button_name: str):
        """Add a button to the block list"""
        if button_name in self.BUTTON_MAP:
            self._blocked_buttons.add(button_name)
            print(f"InputBlocker: Added '{button_name}' to block list")
    
    def remove_blocked_button(self, button_name: str):
        """Remove a button from the block list"""
        self._blocked_buttons.discard(button_name)
    
    def clear_blocked_buttons(self):
        """Clear all blocked buttons"""
        self._blocked_buttons.clear()
    
    def is_button_pressed(self, button_name: str) -> bool:
        """Check if a blocked button is currently pressed"""
        return self._button_states.get(button_name, False)

    def has_state(self, button_name: str) -> bool:
        """Check if we have observed a state for this button."""
        return button_name in self._button_states

    @property
    def is_running(self) -> bool:
        """Check if hook thread is running."""
        return self._running
    
    def start(self) -> bool:
        """Start the input blocker hooks"""
        if self._running:
            return True
        
        self._running = True
        self._hook_thread = threading.Thread(target=self._hook_loop, daemon=True)
        self._hook_thread.start()
        
        print("InputBlocker: Started")
        return True
    
    def stop(self):
        """Stop the input blocker hooks"""
        self._running = False
        
        # Post quit message to hook thread
        if self._hook_thread and self._hook_thread.is_alive():
            # We need to unhook from the same thread that created the hook
            # Send a message to exit the message loop
            pass
        
        self._hook_thread = None
        print("InputBlocker: Stopped")
    
    def _hook_loop(self):
        """Main hook loop running in separate thread"""
        # Create hook procedures
        self._mouse_proc = HOOKPROC(self._mouse_hook_proc)
        
        # Install mouse hook
        hmod = kernel32.GetModuleHandleW(None)
        self._mouse_hook = user32.SetWindowsHookExW(
            WH_MOUSE_LL,
            self._mouse_proc,
            hmod,
            0
        )
        
        if not self._mouse_hook:
            err = ctypes.get_last_error()
            print(f"InputBlocker: Failed to install mouse hook (error: {err})")
            return
        
        print("InputBlocker: Mouse hook installed")
        
        # Message loop (required for hooks to work)
        msg = wintypes.MSG()
        while self._running:
            # Use PeekMessage with a timeout to allow checking _running flag
            result = user32.PeekMessageW(byref(msg), None, 0, 0, 1)  # PM_REMOVE = 1
            if result:
                user32.TranslateMessage(byref(msg))
                user32.DispatchMessageW(byref(msg))
            else:
                # No message, sleep briefly
                ctypes.windll.kernel32.Sleep(1)
        
        # Unhook
        if self._mouse_hook:
            user32.UnhookWindowsHookEx(self._mouse_hook)
            self._mouse_hook = None
        
        print("InputBlocker: Hooks removed")
    
    def _mouse_hook_proc(self, nCode: int, wParam: int, lParam: int) -> int:
        """Low-level mouse hook procedure"""
        if nCode >= 0:
            # Get hook structure
            hook_struct = ctypes.cast(lParam, POINTER(MSLLHOOKSTRUCT)).contents
            
            # Check for left button
            if wParam in (WM_LBUTTONDOWN, WM_LBUTTONUP):
                is_down = (wParam == WM_LBUTTONDOWN)
                self._button_states["left_button"] = is_down
                if "left_button" in self._blocked_buttons:
                    if is_down and self.on_blocked_press:
                        self.on_blocked_press("left_button")
                    elif not is_down and self.on_blocked_release:
                        self.on_blocked_release("left_button")
                    
                    return 1
            
            # Check for right button
            elif wParam in (WM_RBUTTONDOWN, WM_RBUTTONUP):
                is_down = (wParam == WM_RBUTTONDOWN)
                self._button_states["right_button"] = is_down
                if "right_button" in self._blocked_buttons:
                    if is_down and self.on_blocked_press:
                        self.on_blocked_press("right_button")
                    elif not is_down and self.on_blocked_release:
                        self.on_blocked_release("right_button")
                    
                    return 1
            
            # Check for middle button
            elif wParam in (WM_MBUTTONDOWN, WM_MBUTTONUP):
                is_down = (wParam == WM_MBUTTONDOWN)
                self._button_states["middle_button"] = is_down
                if "middle_button" in self._blocked_buttons:
                    if is_down and self.on_blocked_press:
                        self.on_blocked_press("middle_button")
                    elif not is_down and self.on_blocked_release:
                        self.on_blocked_release("middle_button")
                    
                    return 1
            
            # Check for X buttons (side buttons)
            elif wParam in (WM_XBUTTONDOWN, WM_XBUTTONUP):
                # Get which X button
                x_button = (hook_struct.mouseData >> 16) & 0xFFFF
                
                button_name = None
                if x_button == XBUTTON1:
                    button_name = "back_button"
                elif x_button == XBUTTON2:
                    button_name = "forward_button"
                
                if button_name:
                    is_down = (wParam == WM_XBUTTONDOWN)
                    self._button_states[button_name] = is_down

                if button_name and button_name in self._blocked_buttons:
                    # Call callbacks
                    if is_down and self.on_blocked_press:
                        self.on_blocked_press(button_name)
                    elif not is_down and self.on_blocked_release:
                        self.on_blocked_release(button_name)
                    
                    # Block the input (return non-zero to prevent passing to next hook)
                    return 1
        
        # Call next hook
        return user32.CallNextHookEx(self._mouse_hook, nCode, wParam, lParam)


# Global singleton instance
_blocker_instance: Optional[InputBlocker] = None


def get_input_blocker() -> InputBlocker:
    """Get or create the global InputBlocker instance"""
    global _blocker_instance
    if _blocker_instance is None:
        _blocker_instance = InputBlocker()
    return _blocker_instance
