# VENV

terminal
python -m venv venv
source venv/bin/activate
conda deactivate #deactive base

# Run Code

python main.py --display --view overlay --debug
python main.py --display --view overlay --debug --detect-objects

# Blind Navigation Assistance System

A real-time navigation assistance system for visually impaired users that converts camera input into directional obstacle warnings using monocular depth estimation.

# Project Overview

This system uses a chest-mounted webcam (angled at ~45° downward) to detect obstacles in the user's path and provides directional feedback (N, NE, NW, E, W) to help with navigation. The core technology is monocular depth estimation using MiDaS, which allows depth perception from a single camera without specialized depth sensors.

# System Architecture

blind_navigation_assist/
├── main.py # Main script to orchestrate the pipeline
├── camera/
│ └── capture.py # Video capture functionality
├── depth_estimation/
│ ├── midas.py # MiDaS depth estimation models
│ └── normalize.py # Depth normalization utilities
├── obstacle_detection/
│ ├── ground_plane.py # Ground plane estimation logic
│ └── grid_segmentation.py # Grid-based obstacle detection
├── feedback/
│ └── output.py # Directional output (console/visual for prototype)
├── simulation/
│ ├── visualizer.py # Optional 3D visualization with Panda3D
│ └── performance.py # Performance monitoring
├── utils/
│ ├── config.py # Configuration settings
│ ├── calibration.py # Depth calibration utilities
│ └── helpers.py # Utility functions
└── requirements.txt # Python dependencies

# Pipeline Flow

1. Capture Frame:
   - Camera captures a frame (640×480 RGB image)
   - Webcam mounted at chest height, angled ~45° downward
2. Estimate Depth:
   - MiDaS model processes the frame to generate a depth map
   - Using lightweight models optimized for embedded devices
3. Detect Obstacles:
   - Ground plane estimation identifies the floor
   - Grid-based segmentation separates obstacles from ground
   - Obstacles represented as 3D boxes with position data
4. Map to Sectors:
   - Obstacles mapped to 5 directional sectors (N, NE, NW, E, W)
   - Each sector tracks the closest obstacle within detection range
5. Generate Feedback:
   - Console/visual output shows which sectors contain obstacles
   - Distance-based intensity (closer obstacles = stronger feedback)
6. Update Simulation (optional):
   - 3D visualization renders the detected obstacles
   - Useful for development and debugging

# Visualization System

## Views

- **Top-Down View**: Bird's-eye perspective showing obstacles around user
- **First-Person View**: Camera perspective with obstacle overlays
- **Depth Map View**: Colorized visualization of the depth map
- **Sector Map**: Visual representation of the 5 directional sectors

## Interactive Elements

- **Parameter Adjustment**: Sliders for thresholds and detection ranges
- **Recording**: Capture and replay scenarios for testing
- **Ground Truth Marking**: Manually mark obstacles for evaluation

# Data Flow

[Camera] → [Frame Buffer] → [MiDaS Model] → [Depth Map] → [Ground Plane Estimation]
↓
[Feedback Output] ← [Sector Mapping] ← [Obstacle Detection] ← [Non-Ground Mask]
↓
[Console/Visual Display]

# Implementation Details

## Depth Estimation

- Model Options:
  - dpt_levit_224: Fastest option, suitable for Raspberry Pi 4
  - dpt_swin2_tiny_256: Better quality, recommended for Raspberry Pi 5/Jetson Nano
  - midas_v21_small: Legacy option with OpenVINO support
- Processing Resolution: 224×224 or 256×256 (model dependent)
- Optimization: Model quantization and/or ONNX conversion for performance

## Ground Plane & Obstacle Detection

- Ground Plane Approach: Fixed-angle assumption with height threshold
- Detection Range: 0-2.5 meters (configurable)
- Distance Categories:
  - Close: 0-1m
  - Medium: 1-2m
  - Far: 2-2.5m

### Grid-Based Obstacle Segmentation

1. **Grid Creation**:

   - Divide depth map into cells (e.g., 16×12 grid)
   - Each cell represents approximately 20×20cm in physical space

2. **Cell Classification**:

   - Calculate average depth and height for each cell
   - Classify as ground/obstacle based on height threshold
   - Apply median filtering to reduce noise

3. **Obstacle Grouping**:
   - Use connected components algorithm to group adjacent obstacle cells
   - Calculate centroid and minimum distance for each obstacle group
   - Filter small groups (< 3 cells) to reduce false positives

## Directional Mapping

- Sectors:
  - North (N): Straight ahead (-15° to 15°)
  - Northeast (NE): Front-right (15° to 45°)
  - Northwest (NW): Front-left (-45° to -15°)
  - East (E): Right (45° to 90°)
  - West (W): Left (-90° to -45°)

## Calibration Procedure

1. **Camera Intrinsics**:

   - Use OpenCV's calibration tools with a checkerboard pattern
   - Store camera matrix and distortion coefficients in a configuration file

2. **Depth Scaling**:

   - Place objects at known distances (1m, 2m) from camera
   - Record depth values and establish a scaling function
   - Create a simple UI for this calibration step

3. **Ground Plane**:
   - Capture frames in an empty area with flat ground
   - Analyze depth gradient to establish baseline ground plane
   - Save parameters to configuration file

## Performance Considerations

- Target Hardware: Raspberry Pi 4/5 or Jetson Nano
- Frame Rate: Minimum 5 FPS for prototype, 10+ FPS target
- Optimization Techniques:
  - Lower resolution processing
  - Model quantization
  - Frame skipping if necessary
- Grid-based obstacle detection instead of DBSCAN

## Performance Optimization

### Model Optimization

- **Quantization**: Convert model to INT8 precision using PyTorch quantization
- **ONNX Conversion**: Export model to ONNX format for faster inference
- **TensorRT** (for Jetson): Convert ONNX model to TensorRT engine

### Processing Optimizations

- **Resolution Scaling**: Process depth at 256×192 or lower
- **Region of Interest**: Focus processing on central 60% of image
- **Temporal Consistency**: Skip full processing every n frames
- **Multithreading**: Separate capture, processing, and visualization threads

# Configuration Parameters

## Camera Settings

- `CAMERA_INDEX`: 0 (default webcam)
- `FRAME_WIDTH`: 640 pixels
- `FRAME_HEIGHT`: 480 pixels
- `CAMERA_ANGLE`: 45° (downward tilt)

## Depth Estimation

- `DEPTH_MODEL`: "dpt_levit_224" (options: "dpt_swin2_tiny_256", "midas_v21_small")
- `PROCESSING_WIDTH`: 224 pixels
- `PROCESSING_HEIGHT`: 224 pixels
- `DEPTH_SCALE_FACTOR`: 3.0 (calibrated value to convert to meters)

## Obstacle Detection

- `GROUND_HEIGHT_THRESHOLD`: 0.1 meters (tolerance for ground plane)
- `MIN_OBSTACLE_HEIGHT`: 0.05 meters (minimum height to be considered an obstacle)
- `GRID_CELLS_X`: 16 (horizontal grid divisions)
- `GRID_CELLS_Y`: 12 (vertical grid divisions)

## Feedback Settings

- `WARNING_DISTANCE_CLOSE`: 1.0 meter
- `WARNING_DISTANCE_MEDIUM`: 2.0 meters
- `WARNING_DISTANCE_FAR`: 2.5 meters

# Development Roadmap

## Phase 1: Core Pipeline

- Camera capture setup
- MiDaS model integration and testing
- Basic ground plane estimation
- Simple obstacle detection

## Phase 2: Directional Mapping

- Implement sector-based mapping
- Create console/visual output
- Add distance-based categorization

## Phase 3: Optimization & Testing

- Performance benchmarking
- Model and parameter optimization
- Controlled environment testing

## Phase 4: Visualization & Analysis

- Implement 3D visualization
- Add performance monitoring
- Create analysis tools for recorded data

# Testing Methodology

## Quantitative Evaluation

- **Detection Rate**: % of obstacles correctly identified
- **False Positive Rate**: Incorrect obstacle detections
- **Distance Accuracy**: Error in estimated distances vs. ground truth
- **Processing Time**: Breakdown of time spent in each pipeline stage

## Test Scenarios

1. **Static Environment**: Room with furniture at known positions
2. **Dynamic Objects**: People walking in front of the camera
3. **Edge Cases**: Low light, reflective surfaces, textureless walls

## Validation Process

1. Record ground truth obstacle positions
2. Run system on test scenarios
3. Compare detected obstacles with ground truth
4. Analyze performance metrics and adjust parameters

# Limitations & Future Work

## Current Limitations

- Indoor environments only
- Flat ground surfaces
- Fixed camera position
- No haptic hardware integration yet

## Future Enhancements

- Haptic belt integration
- IMU for camera orientation tracking
- Terrain handling (stairs, slopes)
- Object classification
- Moving obstacle tracking
- Audio feedback option

## Dependencies

- OpenCV: Camera capture and image processing
- PyTorch: MiDaS depth estimation
- NumPy: Numerical operations
- Panda3D: Optional 3D visualization
- ONNX Runtime (optional): Optimized inference

# Error Handling and Edge Cases

## Depth Estimation Failures

- Low-confidence regions marked and excluded from obstacle detection
- Temporal smoothing to handle intermittent estimation errors
- Fallback to previous frame's depth map when confidence is low

## Environmental Challenges

- Brightness adjustment for varying lighting conditions
- Detection confidence thresholds adjusted based on lighting quality
- Warning indicators when operating in suboptimal conditions

## System Failures

- Watchdog timer to detect and recover from processing hangs
- Graceful degradation when processing cannot keep up with frame rate
- User notification for critical system errors

# References

- MiDaS: https://github.com/isl-org/MiDaS
- Panda3D: https://www.panda3d.org/
