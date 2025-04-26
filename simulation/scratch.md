# Plan for Depth-Based Proximity Bar Implementation

## Background and Motivation

The goal is to create a low-latency proximity detection system using monocular depth estimation that provides a simple but effective visualization of obstacles in front of the user. The system will use a vertical proximity bar that fills from top to bottom as objects get closer to the user, with corresponding color changes to indicate urgency.

## Key Challenges and Analysis

1. Latency reduction in the depth estimation pipeline
2. Creating an intuitive proximity bar visualization
3. Ensuring stable detection without excessive temporal smoothing
4. Properly mapping depth values to the proximity bar

## High-level Task Breakdown

### Task 1: Optimize MiDaS for Lower Latency

- Update `midas.py` to reduce input resolution (160x120 or similar)
- Adjust EMA filter alpha value for less smoothing but still prevent flickering
- Ensure depth values are properly clamped between 0.5m and 5.0m
- Success criteria: Depth estimation should run at >15 FPS with stable output

### Task 2: Create ProximityBar Class

- Create new file `simulation/visualization/proximity_bar.py`
- Implement ProximityBar class with the following features:
  - Vertical bar visualization (user at bottom, 5m range at top)
  - Fill from top to bottom as objects approach
  - Color gradient (green→yellow→red) based on distance
  - Configurable dimensions and thresholds
- Success criteria: Bar should display and update correctly with test values

### Task 3: Integrate Proximity Bar into Main Loop

- Modify `main.py` to create and display the proximity bar
- Extract nearest object information from depth map
- Update proximity bar based on nearest point
- Add console output of "haptic feedback invoked" when objects are within 0.5-1.5m
- Success criteria: System should display camera feed, depth map, and proximity bar simultaneously

### Task 4: Testing and Refinement

- Test system with various objects at different distances
- Adjust thresholds and visualization parameters as needed
- Optimize performance if still experiencing latency issues
- Success criteria: System reliably detects objects and provides stable visualization

## Project Status Board

- [x] Task 1: Optimize MiDaS for Lower Latency
- [x] Task 2: Create ProximityBar Class
- [x] Task 3: Integrate Proximity Bar into Main Loop
- [x] Task 4: Testing and Refinement (Initial improvements completed)

## Executor's Feedback or Assistance Requests

The implementation has been completed with the following optimizations:

1. Added performance metrics using an exponential moving average for depth estimation
2. Improved first frame handling to ensure smoother startup
3. Added a debug flag to control verbose output
4. Implemented frame skipping to reduce CPU load

To run the system with these improvements:
