# Starlight - AI Assistive Input Tool

A private assistive input tool designed to help users with physical or mental disabilities in applications requiring precise mouse control.

## Features

- **AI-Powered Detection**: TensorRT/ONNX object detection for target identification
- **Humanized Movement**: WindMouse algorithm and other humanization techniques for natural mouse movement
- **Configurable Controls**: Aim assist, flick assist, and trigger functionality with extensive customization
- **Clean UI**: Modern dark-themed PyQt6 interface similar to professional tools

## Requirements

- Windows 10/11
- Python 3.10+
- NVIDIA GPU (for TensorRT acceleration, optional)
- CUDA Toolkit (if using TensorRT)

## Installation

1. Clone or download this repository
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

3. (Optional) For TensorRT support:
   ```bash
   pip install tensorrt --extra-index-url https://pypi.nvidia.com
   ```

4. Place your AI model file in the `models/` folder

## Usage

Run the application:
```bash
python main.py
```

### Configuration

The application saves configuration to `config.json`. Settings can be adjusted through the UI:

- **Aim Tab**: Configure aim assist FOV, smoothing, and controls
- **Flick & Trigger Tab**: Configure flick assist and triggerbot settings
- **Humanizer Tab**: Configure movement humanization algorithms
- **Settings Tab**: Configure capture, detection, mouse, and tracking settings

### Controls

Default key bindings:
- **Forward Mouse Button**: Activate aim assist
- **Back Mouse Button**: Activate flick assist / trigger

## Project Structure

```
starlight/
├── main.py                 # Entry point
├── config.json             # User configuration
├── requirements.txt        # Dependencies
├── models/                 # AI model files
└── src/
    ├── capture/            # Screen capture
    ├── detection/          # AI detection engine
    ├── movement/           # Mouse control & humanization
    ├── core/               # Config & main logic
    └── ui/                 # PyQt6 interface
```

## Disclaimer

This software is designed exclusively as an assistive input tool for individuals with disabilities. It is intended to provide accessibility assistance and ensure compliance with disability rights laws such as the ADA.

Any use outside of this scope is not endorsed.

## License

Private use only. Not for distribution.
