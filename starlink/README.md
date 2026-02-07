# Starlink v2.0

Arduino Leonardo HID Mouse Controller with Advanced Humanization

## Features

### Device Spoofing
- Appears as **Logitech G Pro X Superlight** (or any mouse you configure)
- Custom VID/PID spoofing
- Authentic manufacturer strings

### Humanization Layers
| Layer | Description |
|-------|-------------|
| **Micro-Jitter** | Gaussian-distributed random noise, velocity-scaled |
| **Hand Tremor** | 8-12Hz oscillation simulating natural hand tremor |
| **Burst Patterns** | Micro-bursts mimicking human muscle movement |
| **Micro-Corrections** | Small adjustments after main movements |
| **Timing Variance** | Natural USB polling jitter (50-250µs) |
| **Deceleration Smoothing** | Natural slowdown at movement end |
| **Sub-Pixel Accumulation** | Preserves precision for small movements |

---

## Setup

### 1. Install Arduino IDE
Download from: https://www.arduino.cc/en/software

### 2. Spoof VID/PID (IMPORTANT)
Follow instructions in `firmware/SPOOFING_SETUP.md`

### 3. Flash Firmware
1. Connect Arduino Leonardo via USB
2. Open `firmware/starlink_mouse/starlink_mouse.ino`
3. Select **Tools → Board → Arduino Leonardo**
4. Select correct **Tools → Port**
5. Click **Upload**

### 4. Install Python Dependencies
```bash
pip install pyserial
```

---

## Usage

### Python API
```python
from starlink.src.controller import ArduinoMouseController, find_arduino_port

# Connect
mouse = ArduinoMouseController()
mouse.connect()

# Move mouse (supports float for precision)
mouse.move(10.5, -5.2)

# Smooth movement over multiple steps
mouse.move_smooth(100, 50, steps=10, interval_ms=2)

# Click
mouse.click("L")  # Left click
mouse.click("R")  # Right click

# Press and hold
mouse.press("L")
# ... do something ...
mouse.release("L")

# Configure humanization
mouse.set_humanization(enabled=True, jitter=50, tremor=50)

# Disconnect
mouse.disconnect()
```

### Integration with Starlight-CB
```python
# In your aimbot code:
from starlink.src.controller import ArduinoMouseController

# Initialize once
arduino_mouse = ArduinoMouseController()
arduino_mouse.connect()

# Instead of SendInput:
def move_mouse(dx, dy):
    arduino_mouse.move(dx, dy)
```

---

## Serial Protocol

| Command | Description | Example |
|---------|-------------|---------|
| `M,dx,dy` | Move mouse | `M,10.5,-3.2` |
| `C,btn` | Click button | `C,L` |
| `P,btn` | Press button | `P,R` |
| `R,btn` | Release button | `R,L` |
| `J,val` | Set jitter (0-100) | `J,50` |
| `T,val` | Set tremor (0-100) | `T,50` |
| `E,0/1` | Enable humanization | `E,1` |
| `H,j,t,e` | Set all params | `H,50,50,1` |
| `X` | Reset state | `X` |
| `?` | Ping | `?` → `OK:STARLINK` |
| `V` | Version | `V` → `VER:2.0.0` |
| `S` | Status | `S` → `STATUS:j=0.30,t=0.15,h=1,v=0.0` |

---

## Humanization Parameters

### Jitter (0-100)
- **0-20**: Very subtle, almost imperceptible
- **30-50**: Natural hand shake (recommended)
- **60-80**: Noticeable tremor
- **80-100**: Exaggerated (not recommended)

### Tremor (0-100)
- **0**: Disabled
- **30-50**: Natural hand tremor (recommended)
- **70-100**: Exaggerated tremor

### Recommended Settings
```python
# For aiming (subtle)
mouse.set_humanization(enabled=True, jitter=40, tremor=35)

# For general movement
mouse.set_humanization(enabled=True, jitter=50, tremor=50)

# Disabled (raw input)
mouse.set_humanization(enabled=False)
```

---

## Troubleshooting

### Arduino not detected
```python
from starlink.src.controller import list_serial_ports
print(list_serial_ports())
```

### Upload fails after VID/PID change
1. Double-tap reset button on Leonardo
2. Quickly select new COM port in Arduino IDE
3. Upload within 8 seconds

### Movement feels laggy
- Reduce `steps` in `move_smooth()`
- Use direct `move()` for fast movements
- Check serial latency with `mouse.last_latency_ms`

---

## Security Considerations

This tool is designed for:
- Accessibility/disability assistance
- Personal testing and development
- Portfolio projects

The humanization is designed to produce natural-looking mouse movement that matches human biomechanics.

---

## License

Private use only. Not for distribution.
