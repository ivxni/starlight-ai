# Moonlight AI Settings Overview

***

#### Aim Page Overview

The Aim page is the primary interface for configuring the assistive pointing behavior. It is structured into three main vertical sections: Global Settings, Targeting & Position, and a dynamic Aim Controls panel that changes based on the selected algorithm.

***

#### 1. Global Aim Settings

Located at the top of the page, these settings apply universally to the aim function, regardless of the

* Activation Controls:
  * Aim Key: A multi-select dropdown that lets you bind one or more keys (e.g., Left Click, Right Click, Side Buttons) to activate the aim function.
  * Aim Enable: The master toggle switch for the entire aim system.
* Timing & Limitations:
  * Reaction Time: A slider that introduces an artificial delay (in milliseconds) between the key press and the start of the aim movement, simulating human reaction speed.
  * Max Aim Time: A checkbox and slider combo. When enabled, it sets a hard time limit (in seconds) for how long the aim assist remains active per press, preventing it from "sticking" to a target for suspicious durations.

***

#### 2. Targeting & Position

Group: "Targeting & Position"

This section defines the visual field in which the system searches for targets and applies fixed offsets to the final aim point.

* Field of View (FOV):
  * Aim FOV: Controls the radius of the search circle around the crosshair.
  * FOV Scale: Adjusts the FOV size relative to the screen resolution/reference size.
* Dynamic FOV:
  * Enable Switch: Toggles the dynamic resizing behavior.
  * Min / Max FOV: Defines the lower and upper bounds for the FOV. The system dynamically resizes the search area between these values based on tracking conditions or target distance.
* Offsets:
  * X Offset: Applies a fixed horizontal pixel adjustment to the aim point (left/right).
  * Y Offset: Applies a fixed vertical pixel adjustment (up/down), often used for manual recoil compensation or aiming at a specific body part height.

***

#### 3. Aim Controls

Group: "Aim Controls"

This is a dynamic panel that changes its available sliders and options based on the Aim Type selected in the header.

**A. Header Selection**

* Aim Type: Determines the underlying movement algorithm.
  * Legacy: Uses linear speed and acceleration curves.
  * Aim V2: Uses advanced smoothing algorithms with distance scaling.
  * GAN: Uses a neural network to generate human-like movement patterns.
* Aim Mode: Determines how the activation key behaves (e.g., Hold to aim vs. Toggle on/off).

**B. Mode-Specific Controls**

The sliders below appear only when their respective Aim Type is selected:

1\. Legacy Mode (AIM)

* X / Y Speed: Sets the base horizontal and vertical tracking speeds.
* Speed Modifiers (1 & 2): Secondary speed sliders for fine-tuning acceleration curves or specific zone behaviors.

2\. Aim V2 Mode

* Smooth X / Y: Primary smoothing values for horizontal and vertical movement. Higher values result in slower, smoother tracking; lower values result in snappier movement.
* Distance Scale Factor: Adjusts how smoothing scales with target distance.
  * *Lower values* make the aim faster up close and slower at range.
  * *Higher values* keep the speed more consistent regardless of distance.
  * Distance Scale Factor only functions when (Legacy Distance Smoothing (Old Behavior)) is selected in the Mouse/HID settings page sub tab.
* Smooth Modifiers: A specialized list allowing you to define custom zones. You can add specific smoothing values that trigger only within certain FOV ranges.

3\. GAN Mode

* GAN Speed: Controls the overall speed of the neural network's path generation.
* GAN Humanization: Adjusts the amount of "noise" or imperfection added to the path to mimic human error.
* GAN Smoothness: Defines the curvature of the generated trajectory.
* GAN Overshoot %: Sets the probability that the aim will intentionally overshoot the target before correcting back.
* GAN Model: A dropdown to select which specific trained neural network model (`.pth` or `.onnx`) to use for movement generation.

***

***

#### Flick & Trigger Page Overview

The Flick + Trigger page combines configuration for two distinct assistive behaviors: Flick (rapid target acquisition) and Trigger (automated firing). The page is organized vertically into three main sections: Global Presets, Flick Settings, and Trigger Settings.

***

#### 1. Flick Settings

This section controls the "Flick" behavior, which is designed for faster, snap-like movements compared to the smoother tracking of the Aim tab.

**Targeting & Position**

Group: "Targeting & Position"

Defines the search area and static offsets for the flick behavior.

* Flick FOV: Sets the radius of the search circle. This is typically larger than the Aim FOV to allow acquiring targets further from the crosshair.
* X Offset: Horizontal pixel adjustment for the final flick point.
* Y Offset: Vertical pixel adjustment for the final flick point (e.g., aiming slightly higher for headshots).

**Flick Controls**

Group: "Flick Controls"

Controls the activation and motion characteristics of the flick.

* Activation:
  * Flick Enable: Master toggle for the flick system.
  * Flick Key: Dropdown to select the activation key (e.g., Right Click, Side Buttons).
* Motion Settings:
  * Reaction Time: Adds a delay (in milliseconds) before the flick movement begins.
  * Distance Scale Factor: Adjusts smoothing based on target distance. Lower values make flicks faster up close and slower at range; higher values maintain consistent speed.
  * Smooth X / Y: Independent smoothing values for horizontal and vertical movement. Lower values create faster, snappier flicks; higher values create slower, more controlled movements.
  * Smooth Modifiers: A specialized list allowing you to define custom smoothing zones based on FOV ranges (e.g., faster smoothing when the target is far, precise smoothing when close).

***

#### 2. Trigger Settings

This section configures the Triggerbot, which automatically fires when a target enters the crosshair or defined region.

**Global Trigger Settings**

* Trigger Preset System: Similar to other tabs, allows loading pre-made profiles for different weapon types (e.g., "Instant," "Safe & Legit").

**Trigger Controls**

Group: "Trigger Controls"

* Activation:
  * Trigger Enable: Master toggle for the auto-fire system.
  * Trigger Key: Dropdown to select the key that must be held for the triggerbot to be active.
* Detection & Timing:
  * Trigger Scale: Adjusts the effective FOV or "tightness" of the trigger detection zone.
  * 1st Shot Delay: Adds a delay before the *first* shot is fired after a target is detected. Useful for simulating human reaction time.
  * Multi-Shot Delay: Adds a delay between subsequent shots (for semi-automatic weapons or tapping control).

***

***

#### Recoil Control System (RCS) Page Overview

The Recoil Control page manages weapon recoil mitigation features. Unlike other pages, it does not use a global preset system at the top; instead, it provides direct access to control logic and specialized modes for handling complex recoil patterns. The page is divided into four main sections: RCS Controls, Mode Settings, Pattern Settings, and Pattern Visualization.

***

#### 1. RCS Controls

Group: "RCS Controls"

This section manages the core activation and timing of the generic pull-down system.

* RCS Enable:
  * Widget: Checkbox
  * Function: The master switch to turn the recoil control system on or off.
* RCS Strength:
  * Widget: Slider
  * Function: Controls the vertical pull-down force applied to counteract muzzle rise. Higher values result in a stronger downward movement to fight high-recoil weapons.
* RCS Activation Delay:
  * Widget: Slider
  * Function: Introduces a pause (in milliseconds) after firing before the recoil control kicks in. This is useful for weapons that have a stable initial shot before the recoil pattern begins.
* Max Time:
  * Widget: Slider
  * Function: Sets a maximum duration limit (in milliseconds) for the RCS to remain active during a continuous spray. This prevents the mouse from being pulled down indefinitely if the fire button is held for too long.

***

#### 2. RCS Mode Settings

Group: "RCS Mode Settings"

This section determines when and how the recoil control is applied relative to game conditions.

* RCS Activation Mode:
  * Widget: Dropdown
  * Options:
    1. Always Active: RCS runs continuously whenever the fire key is held, regardless of whether a target is present.
    2. Enemy Detected: RCS activates *only* when a valid enemy target is identified by the AI.
    3. Within FOV: RCS activates *only* when an enemy is located within the defined Field of View radius.
    4. Pattern Based: Disables the generic vertical pull-down and instead uses a specific CSV recoil pattern file (this enables the Pattern Settings section below).
* Enemy Detection Threshold (Dynamic Visibility):
  * Widget: Slider
  * Visibility: Appears only when Enemy Detected mode is selected.
  * Function: Defines how centered the crosshair must be on the target's bounding box (0-100%) for RCS to engage. Lower values are stricter (must be dead center), while higher values are more lenient.

***

#### 3. Pattern Settings

Group: "Pattern Settings"

Visible only when RCS Activation Mode is set to "Pattern Based".

This section configures precise, file-based recoil compensation that mimics specific weapon spray patterns rather than just pulling down.

* RCS Pattern File:
  * Widget: Text Field & Browse Button
  * Function: Allows you to select a `.csv` file containing relative x/y coordinates and timing data representing a specific weapon's recoil pattern.
* Pattern Randomness:
  * Widget: Slider
  * Function: Injects random pixel noise into the pattern execution to simulate human imperfection and prevent the movement from looking completely static or robotic.
* Pattern Interpolation:
  * Widget: Slider
  * Function: A multiplier that adds intermediate smoothing points between the defined steps in the pattern file, creating a fluid motion rather than "jumping" between coordinates.
* Pattern Sensitivity:
  * Widget: Slider
  * Function: Scales the magnitude of the entire pattern. This allows you to adjust a single pattern file to work correctly with different in-game sensitivities or FOV settings.
* Require Enemy Visible:
  * Widget: Checkbox
  * Function: If enabled, the pattern execution will pause or stop if no enemy is currently detected, preventing the cursor from moving wildly when firing at walls or empty space.

***

#### 4. Pattern Visualization

Group: "Pattern Visualization"

Visible only when RCS Activation Mode is set to "Pattern Based".

This panel provides real-time visual feedback on the loaded recoil pattern.

* Full Pattern View: A graph displaying the entire static path of the loaded CSV pattern .
* Live Pattern View: A dynamic graph showing the active cursor position along the pattern path in real-time while firing .
* Status Indicators:
  * Bullets: Displays the total number of steps in the loaded pattern.
  * Current: Shows the current step index being executed.
  * Active: Indicates whether the RCS system is currently engaging ("Yes/No").
* Reload Pattern Button: Forces a reload of the CSV file from the disk, useful if edits have been made to the file externally while the program is running.

***

***

#### Humanizer Page Overview

The Humanizer page is dedicated to masking robotic movement patterns to make aiming behaviors indistinguishable from natural human input. This page is critical for security and evasion. It is structured with a Global Preset system at the top, followed by a Tab System that allows you to configure distinct humanization profiles for "Aim" and "Flick" behaviors separately.

***

#### 2. Humanizer Tabs

The page is divided into two identical tabs to allow for independent tuning:

* Aim Humanizer: Controls humanization for standard tracking/smoothing (Aim V2/Legacy).
* Flick Humanizer: Controls humanization for rapid target acquisition (Flick/Trigger).

*Each tab contains the same sets of controls described below.*

***

#### 3. Humanization Mode

Group: "Humanization Mode"

Defines the core algorithm used to generate the humanized path.

* Enable Switch: Master toggle for humanization on this specific tab (Aim or Flick).
* Mode Selection:
  * Traditional Humanization: Uses software-based algorithms (WindMouse, Momentum, Entropy) to modify the mouse path.
  * MAKU Hardware Humanization: Offloads humanization logic to specialized hardware emulation (if supported), using geometric curves.

***

#### 4. MAKU Controls (Not Available Until Future MAKCU FW Update

Visible only when "MAKU Hardware Humanization" is selected.

This mode uses geometric curves to create fluid, non-linear paths.

* Movement Type:
  * Straight (2-param): Simple direct movement.
  * Segmented (3-param): Breaks movement into multiple distinct linear segments.
  * Quadratic Bézier (5-param): Uses one control point for a smooth, simple curve.
  * Cubic Bézier (7-param): Uses two control points for complex "S" curves or complex arcs.
* Segments: Determines the resolution or "smoothness" of the curve.
* Control Points (CX/CY):
  * CX1 / CY1: Coordinates for the first curve control point.
  * CX2 / CY2: Coordinates for the second control point (Cubic mode only).

***

#### 5. Traditional Controls

Visible only when "Traditional Humanization" is selected.

This is the standard software-based humanizer, divided into several specialized sub-systems.

**A. WindMouse Algorithm**

Group: "WindMouse Algorithm"

Simulates mouse movement as a physical object affected by environmental forces to create natural variability.

* Enable WindMouse: Toggles this specific algorithm.
* Gravity (Min/Max): The force pulling the cursor toward the target. Lower values create wider, arcing paths; higher values create snappier, straighter lines.
* Wind (Min/Max): A chaotic side-to-side force that adds "wobble" or imperfection to the path.
* Speed (Min/Max): The velocity range of the movement steps.
* Damp (Min/Max): A braking force that reduces wind/chaos as the cursor gets closer to the target, ensuring it "sticks" the landing.

**B. Advanced Humanization**

Group: "Advanced Humanization (Always-On Features)"

* Momentum Tracking: Simulates the physical weight of the mouse, adding acceleration and deceleration phases so movement doesn't start/stop instantly.
* Movement Clamping: Limits the maximum pixels moved in a single frame (typically ±14px) to prevent superhuman instantaneous snaps.

**C. Stop/Pause & Patterns**

Group: "Stop/Pause System" & "Pattern Masking"

* Stop/Pause System: Randomly introduces micro-pauses in movement to simulate a user repositioning their mouse or hesitating.
  * Chance: Probability of a pause occurring.
  * Min/Max Pause: Duration of the pause in milliseconds.
* Pattern Masking: Adds tiny, imperceptible jitter to small movements to break up mathematical linearity.
  * Intensity: Strength of the micro-adjustments.
  * Scale: Global multiplier for all humanization variance.

**D. Sub-Movement & Proximity**

Group: "Sub-Movement Decomposition" & "Proximity Pause"

* Sub-Movements: Breaks long flicks into smaller "chunks" separated by micro-delays, rather than one continuous slide.
* Proximity Pause: Triggers a hesitation when the crosshair gets very close to the target, simulating a user confirming their aim before firing.
  * Threshold: Distance (pixels) to trigger the pause.
  * Cooldown: Time before this can trigger again.

**E. Easing System**

Group: "Easing System"

Controls the acceleration curves for starting and stopping movements.

* Ease-Out: Deceleration duration before a pause.
* Ease-In: Acceleration duration after a pause.
* Curve: The power of the curve (1.0 = Linear, 2.0 = Quadratic, 3.0 = Cubic).

**F. Momentum Tracking System**

Group: "Momentum Tracking System (Physics-Based)"

Fine-tuning for the momentum physics.

* Decay: How fast momentum bleeds off (friction).
* Lead Bias: Forward prediction multiplier.
* Deadzone: Minimum error required to apply momentum corrections.
* Correction Strength: How hard the system tries to fix overshoot/undershoot errors.

**G. Entropy-Aware Humanization**

Group: "Entropy-Aware Humanization"

Advanced features specifically designed to defeat statistical analysis (entropy) detection.

* Speed Variance: Modulates movement speed with smooth noise to increase the "Speed CV" (Coefficient of Variation) metric, making speed less constant.
* Path Curvature: Adds sinusoidal waviness perpendicular to the movement path, preventing perfectly straight lines.
* Endpoint Settling: Instead of stopping instantly at the target (robotic "snap"), this adds micro-oscillations or "settling" movements as if the user is stabilizing their hand.

***

#### Settings Page: Capture Tab Overview

The Capture tab is the first sub-section of the Settings page. It handles all configurations related to video input, image acquisition, and hardware acceleration. This page is dynamic; certain controls will appear or disappear depending on which Capture Mode you select.

***

#### 1. Core Capture Settings

These are the primary settings for defining how the software "sees" the game.

* Capture Mode:
  * Widget: Dropdown
  * Options:
    1. Capture Card: Uses a physical hardware capture card (e.g., Elgato, generic USB). Enables the "Hardware Source Settings" section below.
    2. NDI / NDI-V2: Uses Network Device Interface to receive video over the local network (useful for dual-PC setups without capture cards).
    3. Screenshot: Uses standard Windows API calls to grab the screen (slower, typically for testing).
    4. UDP: Receives a video stream via a custom UDP network socket. Enables the "UDP Configuration" section. This mode is currently not functioning.&#x20;
* Enable Crop:
  * Widget: Checkbox
  * Function: Toggles cropping of the input frame. When enabled, the software processes only a center portion of the screen rather than the full resolution, significantly improving performance.
* Debug Size:
  * Widget: Text Field & Apply Button
  * Function: Sets the size of the debug overlay/window. Typically used to control the visual feedback area.
* Select Visual Type:
  * Widget: Dropdown
  * Options:
    * Debug - Crop Only: Shows only the cropped processing region.
    * Debug - Full Screen: Shows the entire captured frame.
    * Debug - Weapon Detection ROI: specialized view for the OCR system.
    * None: Disables visual feedback for maximum performance.

***

#### 2. Debug Performance

* Display Scale:
  * Widget: Slider/Input (0.25 - 1.0)
  * Function: Downscales the debug window resolution.
  * *Example*: 0.5 renders the debug view at 50% resolution, reducing rendering overhead.
* Max FPS:
  * Widget: Slider/Input (15 - 240)
  * Function: Limits the refresh rate of the debug window.
  * *Recommendation*: Set to 30 or 60 to save resources; this does *not* limit the detection FPS, only the viewer.

***

#### 3. UDP Configuration (UDP IS CURRENTLY NOT WORKING)

Visible only when Capture Mode is set to "UDP".

Advanced settings for network-based streaming setups.

* UDP URL:
  * Widget: Text Field
  * Function: The network address to listen on (e.g., `udp://127.0.0.1:1234?...`).
* Use MJPEG UDP:
  * Widget: Checkbox
  * Function: Switches the stream decoding format from H.264 to MJPEG. Useful if H.264 has high latency or artifacts.
* H.264 Decode Method:
  * Widget: Dropdown
  * Options: Auto, NVDEC (NVIDIA), QSV (Intel), AMF (AMD), CPU.
  * Function: Selects the hardware decoder to use for the video stream. Matching this to your GPU can drastically reduce latency.
* Frame Dropping:
  * Widget: Dropdown
  * Options: Disabled (Smooth), Balanced, Aggressive (Low Latency).
  * Function: Determines how the decoder handles buffered frames. "Aggressive" drops old frames to ensure the newest data is processed immediately.
* Debug Capture:
  * Widget: Checkbox
  * Function: Enables verbose logging for the capture backend to diagnose stream issues.

***

#### 4. Hardware Source Settings

*Visible only when Capture Mode is set to "Capture Card".*

* Select Codec:
  * Widget: Dropdown
  * Options: Direct Show, MSMF.
  * Function: The Windows API used to interface with the camera/capture card. Direct Show is generally more compatible; MSMF is newer and also worse.
* Capture Source:
  * Widget: Dropdown
  * Function: Lists all available video input devices connected to the PC (e.g., "Capture Device 0", "Cam Link 4K").
* Capture Format:
  * Widget: Dropdown
  * Options: YUY2, NV12, MJPG, etc.
  * Function: The raw data format provided by the capture card. &#x20;
* Capture Resolution:
  * Widget: Two Text Fields (Width x Height)
  * Function: Manually forces the capture resolution (e.g., 1920 x 1080).
* Max Capture FPS:
  * Widget: Text Field
  * Function: Sets the target framerate for the capture loop (e.g., 240). Used to prevent the capture thread from consuming 100% of a core if the camera provides frames faster than needed.

***

#### 5. Performance & Acceleration

Group: "OpenCL GPU Acceleration"

Settings for hardware-accelerated image processing (color conversion).

* Enable OpenCL:
  * Widget: Checkbox
  * Function: Offloads color space conversion (e.g., YUV to RGB) from the CPU to the GPU.
* Performance Mode:
  * Widget: Dropdown
  * Options:
    * Force CPU: Maximum raw inference speed (avoids PCIe transfer overhead).
    * Auto: Uses GPU if efficient, falls back to CPU.
    * Force GPU: Strictly uses GPU acceleration.
* Early Initialization:
  * Widget: Checkbox
  * Function: Pre-loads OpenCL contexts at application startup. Increases launch time but prevents lag spikes when detection first starts.
* Status:
  * Widget: Label
  * Function: Displays the current acceleration state (e.g., "GPU Acceleration Active", "CPU Mode").

***

#### Settings Page: Detection/Model Tab Overview

The Detection/Model tab within the Settings page is the central hub for configuring the neural network and inference engine that powers the object detection capabilities. This tab handles model selection, hardware acceleration backends, and detection parameters.

***

#### 1. Backend & Model Configuration

Group: "Backend & Model"

This section defines the core inference engine used to run the AI models.

* Backend:
  * Widget: Dropdown
  * Function: Selects the inference framework. Currently defaults to ONNX (Open Neural Network Exchange), which offers broad compatibility and performance.
* ONNX Provider:
  * Widget: Dropdown
  * Options:
    * gpu: Uses DirectML (Windows)
    * openvino: Uses Intel's OpenVINO toolkit, optimized for Intel CPUs and integrated graphics (iGPUs). Also works for AMD CPUs
* OpenVINO Device:
  * Widget: Dropdown
  * Visibility: Only appears when ONNX Provider is set to "openvino".
  * Function: Allows specific hardware selection for OpenVINO (e.g., AUTO, CPU, GPU, NPU).
* ONNX Threads:
  * Widget: Dropdown
  * Function: Sets the number of CPU threads dedicated to the ONNX runtime. Tuning this can help balance CPU load versus detection speed.
* Model File:
  * Widget: Dropdown
  * Function: Selects the specific AI model file to load (e.g., `.onnx`, `.enc`, or `.xml` files located in the `models/` directory). This determines *what* the system detects.
* Confidence:
  * Widget: Dropdown
  * Function: Sets the minimum confidence threshold (1-99%) required for a detection to be considered valid. Higher values reduce false positives but may miss harder-to-see targets; lower values catch more targets but risk false detections.

***

#### 2. Model Settings

Group: "Model Settings"

This section configures how the loaded model's output is interpreted and processed.

* Model Type:
  * Widget: Dropdown
  * Options:
    1. Object Detection: Standard bounding box detection (e.g., detecting "Enemy" boxes).
    2. Pose Estimation: Advanced keypoint detection (e.g., detecting specific joints/bones like Head, Neck, Shoulders). You must have a pose model selected for this to work correctly.
* Async Inference Enable:
  * Widget: Checkbox
  * Function: Toggles asynchronous inference mode.
    * Enabled: Runs inference in parallel with capture, potentially increasing FPS but introducing slightly more latency (frames are buffered).
    * Disabled: Runs synchronously, prioritizing lowest possible latency (frame-by-frame).
* Target Keypoints:
  * Widget: Dropdown
  * Visibility: Only visible when Model Type is set to "Pose Estimation".
  * Function: Selects the specific body part to target from the pose model (e.g., Head, Neck, Chest, or All Keypoints).

***

#### 3. Detection Filtering

This section provides tools to refine *what* is targeted among the detected objects.

* Bone Selection:
  * Widget: Dropdown
  * Options:
    * Nearest Bone (SIMPLE/ADVANCED): Automatically selects the closest bone to the crosshair.
    * Head/Chest: Forces targeting to a specific area.
    * Pose Estimation: Uses the detailed keypoint data if the model supports it.
* Class Filtering:
  * Widgets: Series of Checkboxes (Class Filter 0-3)
  * Function: Allows enabling specific class IDs defined in the model. This is used to prioritize classes over another.&#x20;
* Disable Classes:
  * Widgets: Series of Checkboxes (Disable Class 0-3)
  * Function: Explicitly ignores specific class IDs, preventing the system from locking onto them even if detected.

***

#### Settings Page: Filtering Tab Overview

The Filtering tab allows you to configure advanced logic to ignore specific targets or false positives. Unlike the basic Class/Bone filtering on the Detection tab, these filters use computer vision techniques (color, shape, and image matching) to analyze detected objects and decide whether they should be targeted or ignored.

***

#### 1. Enemy Color Filter

Group: "Enemy Color Filter"

This is a high-level filter often used in games with character outlines or specific team colors.

* Enemy Color Filter Enable:
  * Widget: Checkbox
  * Function: Toggles the color-based validation logic.
* Color Selection:
  * Widget: Dropdown
  * Options: Purple, Pink, Yellow, Red (with variants).
  * Function: Defines the specific color range the system looks for on a target. If the detected object does not contain this color, it is ignored.

***

#### 2. Color+Shape Ignore Filter

Group: "Color+Shape Ignore Filter"

This system allows you to define complex rules to ignore specific detections based on their geometric properties or internal colors. This is useful for filtering out teammates, dead bodies, or map objects that the AI model might mistakenly identify as enemies.

* Enable Switch:
  * Widget: Checkbox
  * Function: Master toggle for the shape filtering logic.
* Show Debug Overlay:
  * Widget: Checkbox
  * Function: Draws visualization lines on the debug screen, showing the search regions and detected shapes in real-time to help you tune the filter.
* Decay:
  * Widget: Spinbox (ms)
  * Function: Sets a persistence time for the filter. If a target is flagged as "ignore," it remains ignored for this duration, preventing flickering between valid/invalid states.
* Filter Rules List:
  * Widget: List & Control Buttons (Add/Edit/Remove)
  * Function: Displays defined rules. Each rule can combine multiple criteria:
    * Color: Specific RGB values and tolerance.
    * Shape: Geometric shape classification (e.g., Triangle, Circle, Diamond, Arrow).
    * Rotation: Lock to specific angles (useful for directional markers).
    * Dimensions: Minimum/Maximum area and Aspect Ratio constraints.
    * Region: Where to search for this feature relative to the target (Inside, Above, Below, or Custom Offset).

***

#### 3. Template Matching Ignore Filter

Group: "Template Matching Ignore Filter"

This is an advanced visual filter that ignores targets if a specific image (template) is found on or near them. It is highly effective for filtering out UI elements (like "Revive" icons, nameplates, or specific status markers).

* Enable Switch:
  * Widget: Checkbox
  * Function: Master toggle for the template matching system.
* Template Rules List:
  * Widget: List & Control Buttons (Add/Edit/Remove)
  * Function: Manages the list of image templates. Each rule includes:
    * Template Image: The specific `.png` or `.jpg` icon to search for.
    * Preprocessing Pipeline: A powerful suite of image adjustments to ensure reliable matching regardless of lighting or background noise:
      * Basic: Grayscale, Invert, Crop.
      * Enhancement: CLAHE (Contrast), Sharpen, Bilateral Filter.
      * Noise Removal: Gaussian Blur, Morphology (Erode/Dilate), Small Blob removal.
      * Edge Detection: Canny edge extraction for matching shapes/outlines rather than pixels.
    * Matching Settings:
      * Threshold: How close the match must be (0-100%).
      * Method: The mathematical algorithm used (Correlation, Squared Difference, etc.).
      * Multi-scale: Checks multiple sizes of the template to handle distance scaling.
    * Search Region: Defines where relative to the detection box the system should look for the icon (e.g., "Above BBox" for a health bar icon).
    * Live Preview: A split-screen view showing the original image and the processed result to verify your settings work against a live screen capture.

***

#### Settings Page: Tracking Tab Overview

The Tracking tab provides detailed controls for how the aim assist interprets target movement and stabilizes aiming. This page combines basic smoothing adjustments with advanced predictive algorithms designed to compensate for system latency and target velocity.

***

#### 1. Basic Tracking

Group: "Basic Tracking"

This section handles fundamental stabilization of the cursor movement.

* Min Smoothing Clamp:
  * Widget: Slider
  * Function: Sets a hard lower limit on smoothing values. This prevents the aim from becoming uncontrollably fast (wild flicks) if dynamic algorithms try to reduce smoothing to near zero. Higher values ensure a baseline level of control.
* Tracking Deadzone:
  * Widget: Slider
  * Function: Defines a small radius (in pixels) around the center of the target where no aim adjustments are made. This prevents "jitter" or constant micro-corrections when the crosshair is already on target.
* Extra Smoothing:
  * Widget: Slider
  * Function: Applies an additional layer of uniform smoothing on top of the base calculation. Useful for games with erratic mouse input or very high sensitivity.

***

#### 2. Kalman Prediction

Group: "Kalman Prediction"

This section configures the primary predictive aiming system, which uses a Kalman filter to estimate where a moving target will be in the future to compensate for latency.

* Kalman Filter Tuning:
  * Process Noise (Q): Controls how much the system expects the target's velocity to change (acceleration).
    * *Lower values* assume constant velocity (smoother tracking).
    * *Higher values* adapt quickly to erratic direction changes (more responsive).
  * Measurement Noise (R): Controls how much the system trusts the raw AI detection data versus its own prediction.
    * *Lower values* trust the raw detection (faster reaction but jittery).
    * *Higher values* trust the prediction (smoother but potential lag).
  * Prediction Responsiveness: Controls how fast the crosshair moves toward the predicted point. Higher values result in an instant snap; lower values create a smoother, lag-like transition.
  * Direction Change Speed: Determines how quickly the prediction resets when the target reverses direction.
  * Velocity Ramp / Curve: Defines the relationship between target speed and prediction strength.
    * *Velocity Ramp*: The speed (px/ms) at which prediction reaches 100% strength.
    * *Velocity Ramp Curve*: The shape of the ramp (Linear, Quadratic, etc.).
  * Low Speed Dampener: Reduces prediction strength for slow-moving targets to prevent over-correction on small movements.
  * Velocity Smoothing: Applies an Exponential Moving Average (EMA) to the velocity measurement itself to filter out noise.

***

#### 3. Alpha-Beta Filter Tuning

Group: "Alpha-Beta Filter Tuning (Advanced)"

Secondary filtering parameters for specialized velocity handling.

* Beta (Velocity Rate): Controls how quickly the velocity estimate updates.
* Direction Threshold: The number of pixels a target must move in the opposite direction before the system registers a true direction change.
* Direction Change Caution: A multiplier that reduces the "Beta" value during direction changes to prevent overshooting.
* Stationary Threshold: The velocity floor below which a target is considered "stopped."
* Aim Ahead (ms): Additional time offset added to the prediction to compensate specifically for USB/hardware latency.

***

#### 4. Stationary Target Response

Group: "Stationary Target Response"

This system adjusts aiming behavior based on whether the target is moving or standing still, helping to eliminate the "mushy" or "floaty" feeling on static targets.

* Detection Smoothing: Smoothing factor applied to the bounding box position itself.
* Stationary Velocity: The velocity threshold (px/sec) that defines a "stationary" target.
* Stationary Response: Kalman alpha value used when the target is stationary (typically higher for sticky/instant response).
* Moving Response: Kalman alpha value used when the target is moving (typically lower for smoother tracking).
* Velocity Decay (Stationary): How fast the stored velocity value drops to zero when the target stops.

***

#### 5. Latency & Prediction Debug Info

Group: "Latency & Prediction Debug Info"

A real-time readout panel that displays critical performance metrics:

* Capture Latency: Time taken for the image to reach the software.
* Processing Latency: Time taken for AI inference and logic.
* Total Latency: Sum of all delays.
* Velocity: Current calculated target velocity (X/Y).
* Prediction Status: Whether the prediction system is currently active or warming up.
* Samples: Number of valid data points collected for the current track.

***

#### Settings Page: Mouse/HID Tab Overview

The Mouse/HID tab is the hardware configuration center of the software. It handles how the software communicates with your mouse (via software emulation or hardware spoofing), manages input blocking, and normalizes sensitivity across different games and setups.

***

#### 1. Device Selection

Group: "Device Selection"

This section defines the method used to move the mouse cursor.

* Device:
  * Widget: Dropdown
  * Options:
    * Moonlink: Standard software-based mouse simulation. No external hardware required.
    * KMBox: Hardware mouse spoofing devices. Requires a physical KMBox device.
    * MAKCU / Ferrum: Advanced hardware spoofing devices.
  * Function: Selects the driver or hardware interface used to execute aim movements. Hardware devices are generally considered safer for evasion.
* COM Port:
  * Widget: Dropdown (Visible only for hardware devices like KMBox/Ferrum)
  * Function: Selects the specific USB communication port the hardware device is plugged into.

***

#### 2. Input Masking

Group: "Input Masking"

This feature allows the software to intercept or block physical mouse clicks to prevent conflict between your hand and the AI.

* Mouse Buttons:
  * Widgets: Checkboxes (Mouse 1, Mouse 2, Mouse 4, Mouse 5)
  * Function: If checked, the software will "mask" or block the physical input of that button while the AI is active. This prevents "fighting" the aimbot (e.g., stopping you from clicking manually if the bot determines it shouldn't fire).
* M1 Block Threshold:
  * Widget: Slider (Visible only when Mouse 1 is checked)
  * Function: Defines a safety zone for firing.
    * It represents a percentage of the target's bounding box width.
    * Lower values: Stricter. The aiming line must be very close to the center of the target before your physical Left Click is allowed to register.
    * Higher values: More lenient. Allows you to fire even if your aim is near the edge of the target.

***

#### 3. Debug & Analysis

Group: "Debug & Analysis"

Tools for monitoring the safety and logic of the mouse output.

* Show Button States Debug:
  * Widget: Checkbox (Visible only for MAKCU/Ferrum devices)
  * Function: Displays the internal state of hardware buttons to verify that input masking is working correctly on the physical device.
* Enable Entropy Analyzer:
  * Widget: Checkbox
  * Function: Opens the Entropy Analyzer panel on the right side of the screen. This tool visualizes your mouse path complexity (entropy) in real-time to help you tune Humanizer settings for maximum safety.

***

#### 4. Sensitivity Normalization

Group: "Sensitivity Normalization"

This system ensures that your aim settings feel consistent regardless of your mouse DPI or in-game sensitivity.

* Enable Sensitivity Normalization:
  * Widget: Checkbox
  * Function: Toggles the normalization logic. When enabled, it scales aim speed so that `Speed 10` feels the same at 800 DPI as it does at 1600 DPI.
* DPI Value:
  * Widget: Input Field
  * Function: Enter your physical mouse DPI (e.g., 800, 1600).
* In-Game Sens:
  * Widget: Input Field
  * Function: Enter your actual in-game sensitivity value.
* Reference Sens:
  * Widget: Input Field
  * Function: A baseline value used by config creators. It allows different users to share configs; the software automatically calculates a multiplier to match the creator's "feel" on your specific sensitivity.
* Legacy Distance Smoothing:
  * Widget: Checkbox
  * Function: Toggles between the old and new distance scaling algorithms.
    * Disabled (Recommended): Newer logic where aim is slower/precise at close range and faster at long range.
    * Enabled: Old behavior (slower at range, faster up close) Can flag easier for advanced anti-cheats.

***

#### 5. Delays & Sensitivity

Group: "Delays & Sensitivity"

Fine-tuning for hardware communication and global speed.

* Device Delay:
  * Widget: Slider
  * Function: Adds a delay (in ms) to commands sent to hardware devices (KMBox/MAKCU). Increasing this can fix connection instability or "ghosty" aim movement.
* Aim / Flick / RCS Delay:
  * Widgets: Sliders
  * Function: Adds specific artificial latency to Aim, Flick, or Recoil commands respectively. Useful for smoothing out robotic "instant" reactions. Increasing this can fix connection instability or "ghosty" aim movement.
* Sens Multiplier:
  * Widget: Slider
  * Function: A global multiplier for all mouse movement output.
    * 1.0: Standard 1:1 output.
    * < 1.0: Reduces overall speed (fine control).
    * \> 1.0: Amplifies overall speed.

***

#### Settings Page: Config Tab Overview

The Config page is the administrative hub of the software. It handles file management, profile switching, and the automated systems that detect your weapon to switch settings for you. It is divided into three sub-tabs: Settings, OCR, and Template Matching.

***

#### 1. Settings Tab (Main Config)

This tab manages your configuration files and the manual aspects of the Weapon Class system.

**Profile Management**

Group: "Profile Management"

* Config File:
  * Dropdown: Selects the active JSON configuration file to load.
  * Refresh List: Reloads the list of files from the config folder.
* Import Config: Opens a dialog to download configurations directly from a linked Discord channel.
* Export Config: Uploads your current configuration and AI model to Discord to share with others.
* Duplicate Config: Creates a copy of the current settings file with a new name (useful for backups).
* Delete Config: Permanently removes the selected file.

**Weapon Class Management**

Group: "Weapon Class"

This system allows you to create separate profiles (e.g., "Rifles," "Shotguns," "Snipers") within a single config file.

* Weapon Class Dropdown: Manually switches the active profile. All settings on the Aim, Flick, and RCS pages will instantly update to match this class.
* Manage: Opens a dedicated window to create, rename, or delete weapon classes.
* Hotkey:
  * Input Field: Displays the current keybind for cycling through classes.
  * Set: Records a new keystroke (e.g., `F3`) to cycle to the next available class in-game.
  * Clear: Removes the hotkey binding.

***

#### 2. OCR Tab (Text Recognition)

This system uses Optical Character Recognition to read text on your screen (like a weapon name in the HUD) and automatically switch your Weapon Class.

**OCR Engine**

Group: "OCR Weapon Detection"

* Enable Auto Weapon Detection: Master switch for the text recognition system.
* OCR Engine: Selects the recognition library (Default: `EasyOCR`).

**ROI Configuration (Region of Interest)**

Group: "ROI Configuration"

Defines where on the screen the system looks for text.

* ROI Position (X / Y): Sets the top-left corner coordinates of the search box.
* ROI Size (W / H): Sets the width and height of the search box.
* Sliders: Drag these to adjust the region visually in real-time.

**Live Preview**

Group: "Live ROI Preview"

* Start/Stop Preview: Shows a real-time feed of the capture area.
* Visuals:
  * Green Box: Indicates the current scan region.
  * Zoom: Allows zooming into specific corners or the center to help you place the ROI precisely over your game's weapon name.
* Refresh/Scale: Adjusts the preview framerate and quality to save performance while tuning.

**Preprocessing & Detection**

Groups: "Preprocessing" & "Detection Settings"

* Grayscale / Threshold: Filters applied to the image to make text stand out against the game background.
* Contrast: Increases the separation between text and background.
* Detection Interval: How often (in milliseconds) the system scans for text. Higher values = less CPU usage.
* Similarity Threshold: How close the detected text must match your keyword (0-100%). Lower values allow for fuzzy matching (e.g., reading "Vanda1" as "Vandal").
* OCR Languages: Selects which language packs to use for reading text.

**Weapon Text Mappings**

Group: "Weapon Text Mappings"

This table links the text seen on screen to your profiles.

* Keyword: The text to look for (e.g., "AK-47", "Operator").
* Target Class: The profile to switch to when that text is found (e.g., "Rifles", "Snipers").
* Test OCR Mapping: Allows you to type a phrase to see if it triggers a match against your current rules.

***

#### 3. Template Matching Tab (Icon Recognition)

This system is an alternative to OCR. Instead of reading text, it looks for specific images (like weapon icons in the killfeed or HUD) to trigger a profile switch.

**Template Settings**

Group: "Weapon Class Template Matching"

* Enable Template Matching: Master switch for icon recognition.
* Check Interval: How frequently the system scans for the image.
* Switch Cooldown: Minimum time to wait before switching classes again (prevents rapid flickering).

**Live Debug Status**

Group: "Live Debug Status"

Provides real-time feedback on the system's performance.

* Status: Shows if the system is active and how many rules are loaded.
* Last Match: Displays the name of the last icon detected and the confidence score.
* Checks/Matches: Counters showing total activity.

**Template Rules**

Group: "Template Rules"

The list of images to search for.

* Add Rule: Opens a dialog to create a new match rule:
  * Template Image: Browse for the `.png` or `.jpg` of the weapon icon.
  * Target Weapon Class: The profile to activate when this icon is seen.
  * Search Region: Limits the scan to a specific area (e.g., "Bottom Right") to save performance.
  * Match Threshold: How strict the image match must be (0.80+ recommended).
  * Preprocessing: Advanced options (Blur, Edges, Invert) to help the system see the icon clearly even if the game background changes.
* Edit/Remove: Modify or delete existing rules.
* Test Selected: Verifies if the selected rule matches the current screen content.

***

#### Settings Page: ML Mouse Model Tab Overview

The ML Mouse Model tab allows you to train a custom Neural Network that mimics your *specific* mouse movement style. Instead of using generic humanization algorithms, this system learns from your actual hand movements to create an Aim Assist that is mathematically indistinguishable from your natural playstyle.

***

#### 1. Training Data Collection

Group: "Training Data Collection"

This section is used to record your natural mouse movements to build a dataset for the AI.

* Status:
  * Widget: Label
  * Function: Displays the current recording state (e.g., "Not Recording", "Recording - Move your mouse naturally!").
* Sensitivity:
  * Widget: Slider
  * Function: Matches the recording engine to your in-game sensitivity. Set this to match your feeling so the AI learns the correct speed/distance relationship.
* Recording Controls:
  * Start Recording: Begins capturing mouse data. While recording, move your mouse naturally as if aiming at targets (flicking, tracking, stopping).
  * Stop Recording: Saves the captured movement session to the database.
* Live Stats:
  * Widget: Label
  * Function: Shows real-time feedback during recording, including the number of movements captured, current speed, and movement classification.

***

#### 2. Training Data Summary

Group: "Training Data Summary"

This panel reviews the quality and quantity of the data you have collected.

* Summary Display:
  * Widget: Info Panel
  * Function: detailed breakdown of your dataset:
    * Total Sessions: How many recording sessions you have saved.
    * Recent Sessions: Details on the last few recordings.
    * Metrics: Path efficiency (how straight your lines are), Jitter (how shaky your hand is), and Overshoots.
* Refresh Summary:
  * Widget: Button
  * Function: Updates the stats display with the latest data.

***

#### 3. Model Training

Group: "Model Training"

This is where you convert your recorded data into a functioning AI Brain.

* Model Architecture:
  * Widget: Dropdown
  * Options:
    * VAE (Original): Good balance of quality and performance.
    * GRU (Fast): Faster processing, ideal for older PCs.
    * Transformer (Best): Highest quality, captures complex human patterns best (recommended for high-end PCs).
* Training Epochs:
  * Widget: Spinbox
  * Function: Determines how long the AI studies your data. Higher values (e.g., 200-500) result in a more accurate model but take longer to train.
* Actions:
  * Train Model from Data: Starts the training process. The AI will analyze your recorded movements and generate a `.pth` or `.onnx` model file.
  * Load Existing Model: Manually re-loads the last used model into memory.
* Model Info:
  * Widget: Status Label
  * Function: Displays technical details about the currently active model, such as its architecture type and "Validation Loss" (a score indicating how accurately it mimics you—lower is better).

***

#### 4. Model Management

Group: "Model Management"

Tools to organize and select different trained profiles.

* Available Models:
  * Widget: Dropdown
  * Function: Lists all trained models found in the system. Shows the model name, type, and accuracy score.
* Management Actions:
  * Load Selected: Activates the chosen model for use in the Aim/Flick tabs.
  * Save As...: Creates a copy of the current model with a new name.
  * Rename: Changes the name of the selected file.
  * Delete: Permanently removes a model file.

***

#### 5. Data Management

Group: "Data Management"

Options for handling the raw recording data.

* Export Training Data:
  * Widget: Button
  * Function: Saves your raw movement dataset to a file, allowing you to back it up or share it with developers for analysis.
* Clear All Data:
  * Widget: Button
  * Function: Wipes all recorded sessions. Use this if you want to start fresh with a completely different aiming style.
