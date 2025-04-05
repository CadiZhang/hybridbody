"""
Blind Navigation Assistance System - Main Module

This is the main entry point for the blind navigation system. It:
1. Initializes the camera
2. Processes frames in real-time
3. Performs depth estimation using MiDaS
4. (Future) Performs obstacle detection
5. (Future) Provides directional feedback

Usage:
    python main.py --display  # Run with visual display
    python main.py --camera 1 --width 1280 --height 720  # Use external camera at HD resolution
"""
# run "python main.py --display" to see the camera feed

import argparse  # For parsing command-line arguments
import cv2       # OpenCV for computer vision functions
import time      # For timing and FPS control
import os        # For directory operations
import numpy as np  # For numerical operations
from utils.depth_analysis import find_nearest_point, find_nearest_clusters, mark_nearest_point

# Create necessary directories if they don't exist
os.makedirs("camera", exist_ok=True)
os.makedirs("utils", exist_ok=True)
os.makedirs("depth_estimation", exist_ok=True)

def main():
    """
    Main function that runs the blind navigation system.
    
    This function:
    1. Parses command-line arguments
    2. Sets up the camera and depth estimator
    3. Runs the main processing loop
    4. Handles cleanup when the program exits
    """
    # Set up command-line argument parsing
    parser = argparse.ArgumentParser(description="Blind Navigation Assistance System")
    parser.add_argument("--camera", type=int, default=0, 
                        help="Camera index (0 for built-in, 1+ for external)")
    parser.add_argument("--width", type=int, default=640, 
                        help="Camera capture width in pixels")
    parser.add_argument("--height", type=int, default=480, 
                        help="Camera capture height in pixels")
    parser.add_argument("--fps", type=int, default=30, 
                        help="Target frames per second")
    parser.add_argument("--display", action="store_true", 
                        help="Display camera feed in a window")
    parser.add_argument("--view", type=str, default="rgb",
                        choices=["rgb", "depth", "overlay", "side-by-side"],
                        help="Visualization mode when --display is used")
    parser.add_argument("--calibrate", action="store_true", 
                        help="Enter calibration mode")
    
    # Parse the arguments
    args = parser.parse_args()
    
    # Initialize the camera system
    from camera.capture import CameraCapture
    camera = CameraCapture(
        camera_index=args.camera,
        frame_width=args.width,
        frame_height=args.height
    )
    
    # Confirm camera initialization
    print(f"Camera initialized: Using camera index {args.camera} at {args.width}x{args.height}")
    
    # Initialize the depth estimator
    from depth_estimation import DepthEstimator
    depth_estimator = DepthEstimator()
    
    # Add tracking for depth values at center point
    depth_values = []  # Store recent depth values for plotting
    max_tracked_frames = 30  # Track last 30 frames
    
    # Initialize frame counter
    frame_count = 0
    
    try:
        calibration_mode = False
        while True:
            # Record the start time for FPS calculation
            start_time = time.time()
            
            # Capture a frame from the camera
            frame = camera.capture_frame()
            if frame is None:
                print("Failed to capture frame. Retrying...")
                continue
            
            # Increment frame counter
            frame_count += 1
            
            # Perform depth estimation
            depth_map, metric_depth = depth_estimator.estimate_depth(frame)
            
            # Find the nearest point (for diagnostic purposes)
            nearest_point = find_nearest_point(depth_map, 
                                              min_region_size=50,
                                              ignore_margin_percent=0.1,
                                              use_region_averaging=True)
            
            # Optionally, find multiple nearest clusters
            # nearest_clusters = find_nearest_clusters(depth_map, num_clusters=3)
            
            # Add metric distance information if available
            if metric_depth is not None and 'position' in nearest_point:
                pos = nearest_point['position']
            if isinstance(pos, (tuple, list)) and len(pos) == 2:
                x, y = pos
                nearest_point['distance'] = metric_depth[y, x]

                # Print nearest point info every 30 frames (adjust as needed)
            if frame_count % 30 == 0:
                print(f"Nearest point: {nearest_point['distance']:.2f}m at position {x}, {y}")
            else:
                print(f"[Warning] nearest_point['position'] is invalid: {pos}")

            # if metric_depth is not None:
            #     x, y = nearest_point['position']
            #     nearest_point['distance'] = metric_depth[y, x]
                
            #     # Print nearest point info every 30 frames (adjust as needed)
            #     if frame_count % 30 == 0:
            #         print(f"Nearest point: {nearest_point['distance']:.2f}m at position {x}, {y}")
            
            # Get depth at center point for tracking
            h, w = depth_map.shape
            center_depth = metric_depth[h//2, w//2]
            depth_values.append(center_depth)
            if len(depth_values) > max_tracked_frames:
                depth_values.pop(0)
            
            # Create visualization if display is enabled
            if args.display:
                # Create colored depth map for visualization
                depth_colored = depth_estimator.visualize_depth(depth_map)
                
                # Prepare display based on view mode
                if args.view == "rgb":
                    display_frame = frame.copy()
                elif args.view == "depth":
                    display_frame = depth_colored.copy()
                elif args.view == "overlay":
                    # Create overlay of depth on RGB
                    from depth_estimation.normalize import create_depth_overlay
                    display_frame = create_depth_overlay(frame, depth_colored, alpha=0.6)
                elif args.view == "side-by-side":
                    # Create side-by-side view
                    display_frame = np.hstack((frame, depth_colored))
                
                # Mark the nearest point on the display frame
                display_frame = mark_nearest_point(display_frame, nearest_point)
                
                # Draw depth value graph
                if len(depth_values) > 1:
                    graph_h = 100  # Graph height
                    graph_w = 200  # Graph width
                    graph = np.ones((graph_h, graph_w, 3), dtype=np.uint8) * 255
                    
                    # Scale values to fit graph
                    min_d = min(depth_values)
                    max_d = max(depth_values)
                    if max_d > min_d:
                        scaled_values = [int(graph_h - (d - min_d) * graph_h / (max_d - min_d)) 
                                      for d in depth_values]
                        
                        # Draw lines connecting points
                        for i in range(len(scaled_values)-1):
                            pt1 = (i * graph_w // max_tracked_frames, scaled_values[i])
                            pt2 = ((i+1) * graph_w // max_tracked_frames, scaled_values[i+1])
                            cv2.line(graph, pt1, pt2, (0, 0, 255), 2)
                    
                    # Add graph to corner of display
                    display_frame[20:20+graph_h, 20:20+graph_w] = graph
                
                # Add current depth value text
                cv2.putText(display_frame, 
                          f"Center Depth: {center_depth:.2f}m",
                          (20, 150), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)
                
                # Handle calibration mode
                if calibration_mode:
                    cv2.putText(display_frame, 
                              "CALIBRATION MODE - Enter distance in meters (0-9):",
                              (20, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
                    cv2.putText(display_frame, 
                              f"Current center depth: {center_depth:.3f}",
                              (20, 60), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
                else:
                    cv2.putText(display_frame, 
                              f"Depth: {metric_depth[h//2, w//2]:.2f}m (press 'c' for calibration)",
                              (20, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
                
                # Show the visualization
                cv2.imshow("Blind Navigation System", display_frame)
                
                # Get key press and add debug print
                key = cv2.waitKey(1) & 0xFF
                if key != 255:  # If any key was pressed
                    print(f"Key pressed: {chr(key) if key < 128 else key}")
                
                # Handle key presses
                if key == ord('q'):
                    print("Quitting...")
                    break
                elif key == ord('c'):
                    print("Entering calibration mode...")
                    calibration_mode = True
                elif key == ord('v'):
                    views = ["rgb", "depth", "overlay", "side-by-side"]
                    current_idx = views.index(args.view)
                    args.view = views[(current_idx + 1) % len(views)]
                    print(f"View mode changed to: {args.view}")
                
                # Handle calibration number input
                if calibration_mode and ord('0') <= key <= ord('9'):
                    distance = float(chr(key))
                    print(f"Calibrating for distance: {distance}m")
                    h, w = depth_map.shape
                    center_depth = depth_map[h//2, w//2]
                    depth_estimator.calibrate(known_distance=distance, depth_value=center_depth)
                    print(f"Calibrated with distance {distance}m")
                    calibration_mode = False
            
            # === Future: Add obstacle detection here ===
            # obstacles = obstacle_detector.detect(metric_depth)
            
            # === Future: Add directional mapping here ===
            # directions = mapper.map_to_sectors(obstacles)
            
            # === Future: Add feedback generation here ===
            # feedback.generate(directions)
            
            # Control the frame rate
            elapsed = time.time() - start_time
            sleep_time = max(0, 1.0/args.fps - elapsed)
            if sleep_time > 0:
                time.sleep(sleep_time)
            
            # Calculate and occasionally display the actual FPS
            actual_fps = 1.0 / (time.time() - start_time)
            if args.display and int(time.time()) % 5 == 0:  # Every 5 seconds
                print(f"FPS: {actual_fps:.2f}")
    
    except KeyboardInterrupt:
        # Handle Ctrl+C gracefully
        print("Exiting...")
    finally:
        # Clean up resources
        camera.release()
        cv2.destroyAllWindows()

# This is the entry point when the script is run directly
if __name__ == "__main__":
    main()
