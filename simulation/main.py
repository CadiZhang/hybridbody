"""
Blind Navigation Assistance System - Main Module

This is the main entry point for the blind navigation system. It:
1. Initializes the camera
2. Processes frames in real-time
3. Performs depth estimation using MiDaS
4. (Future) Performs obstacle detection
5. (Future) Provides directional feedback

Usage:
    python main.py --display --view overlay --debug # Run with visual display and promximity bar
"""
# run "python main.py --display" to see the camera feed

import argparse  # For parsing command-line arguments
import cv2       # OpenCV for computer vision functions
import time      # For timing and FPS control
import os        # For directory operations
import numpy as np  # For numerical operations
from utils.depth_analysis import find_nearest_point, find_nearest_clusters, mark_nearest_point
from utils.config import (PROXIMITY_BAR_WIDTH, PROXIMITY_BAR_HEIGHT, 
                         PROXIMITY_MIN_DISTANCE, PROXIMITY_MAX_DISTANCE,
                         PROXIMITY_SEGMENTS, PROXIMITY_HAPTIC_MIN, PROXIMITY_HAPTIC_MAX)
from visualization.advanced_visualization import AdvancedVisualization
import pygame
# Create necessary directories if they don't exist
os.makedirs("camera", exist_ok=True)
os.makedirs("utils", exist_ok=True)
os.makedirs("depth_estimation", exist_ok=True)
os.makedirs("visualization", exist_ok=True)

# Define the adjust_parameters function outside the main loop
def adjust_parameters(estimator, alpha_delta=0, beta_delta=0, gamma_delta=0, offset_delta=0, 
                     slope_delta=0, intercept_delta=0):
    """Manually adjust calibration parameters"""
    if estimator.use_linear_mapping:
        estimator.slope = max(0.1, estimator.slope + slope_delta)
        estimator.intercept = estimator.intercept + intercept_delta
        print(f"Adjusted linear parameters: slope={estimator.slope:.2f}, intercept={estimator.intercept:.2f}")
        
        # Show predicted distances at key depths
        print("Predicted distances:")
        for d in [0.1, 0.3, 0.5, 0.7, 0.9]:
            dist = estimator.slope * d + estimator.intercept
            print(f"  depth={d:.1f} → distance={dist:.2f}m")
    else:
        estimator.alpha = max(0.1, estimator.alpha + alpha_delta)
        estimator.beta = max(0.1, estimator.beta + beta_delta)
        estimator.gamma = max(0.01, estimator.gamma + gamma_delta)
        estimator.offset = estimator.offset + offset_delta
        print(f"Adjusted inverse parameters: alpha={estimator.alpha:.2f}, beta={estimator.beta:.2f}, gamma={estimator.gamma:.2f}, offset={estimator.offset:.2f}")
        
        # Show predicted distances at key depths
        print("Predicted distances:")
        for d in [0.1, 0.3, 0.5, 0.7, 0.9]:
            dist = estimator.alpha / (estimator.beta * (1.0 - d) + estimator.gamma) + estimator.offset
            print(f"  depth={d:.1f} → distance={dist:.2f}m")
    
    estimator.save_calibration()

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
    parser.add_argument("--debug", action="store_true",
                        help="Enable debug output")
    parser.add_argument("--detect-objects", action="store_true", 
                      help="Enable object detection using Roboflow")
    parser.add_argument("--detection-confidence", type=float, default=0.65,
                      help="Confidence threshold for object detection (0.0-1.0)")
    parser.add_argument("--detection-model", type=str, default="chair-detection-y06j5/1",
                      help="Roboflow model ID to use for detection")
    parser.add_argument("--detection-frequency", type=int, default=3,
                      help="Process detection every N frames (higher values improve performance)")
    
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
    
    # Initialize the advanced visualization (replacing proximity_bar and directional_pulse)
    advanced_vis = AdvancedVisualization(
        width=800,
        height=500,
        min_distance=PROXIMITY_MIN_DISTANCE,
        max_distance=PROXIMITY_MAX_DISTANCE
    )
    advanced_vis.start()  # Start the visualization thread
    
    # Initialize tracking variables
    last_haptic_time = 0
    haptic_cooldown = 1.0
    
    # Add tracking for depth values at center point
    depth_values = []  # Store recent depth values for plotting
    max_tracked_frames = 30  # Track last 30 frames
    
    # Initialize frame counter and performance metrics
    frame_count = 0
    avg_depth_time = 0.0
    alpha = 0.1  # Smoothing factor for moving average
    
    # Initialize object detection if enabled
    if args.detect_objects:
        from camera.roboflow_inference import detect_objects_in_frame, CLIENT
        print(f"Object detection enabled with model: {args.detection_model}")
        print(f"Detection confidence threshold: {args.detection_confidence}")
    
    try:
        calibration_mode = False
        # Track which frames to process for depth
        last_depth_map = None
        last_metric_depth = None
        
        # Track object detection results
        detection_results = {"predictions": []}
        original_frame = None  # Store an unmodified frame copy
        
        while True:
            # Record the start time for FPS calculation
            start_time = time.time()
            
            # Capture a frame from the camera
            frame = camera.capture_frame()
            if frame is None:
                print("Failed to capture frame. Retrying...")
                continue
            
            # Always keep an unmodified copy of the frame
            original_frame = frame.copy()
            
            # Run object detection if enabled (every N frames for performance)
            if args.detect_objects and frame_count % args.detection_frequency == 0:
                detection_start = time.time()
                # Use detect_objects_in_frame but don't modify the original frame
                _, new_detection_results = detect_objects_in_frame(
                    original_frame.copy(),  # Use a copy to avoid modifying our frame
                    model_id=args.detection_model,
                    confidence_threshold=args.detection_confidence
                )
                detection_end = time.time()
                
                # Update detection results if we got predictions
                if new_detection_results.get("predictions"):
                    detection_results = new_detection_results
                    
                    # Debug info for detections
                    if args.debug:
                        detection_time = detection_end - detection_start
                        num_detections = len(detection_results.get("predictions", []))
                        print(f"Object detection: {num_detections} objects found in {detection_time:.3f}s")
            
            # Increment frame counter
            frame_count += 1
            
            # Perform depth estimation
            # Process either when we don't have a previous frame or on every other frame
            if last_depth_map is None or frame_count % 2 == 0:
                depth_start = time.time()
                depth_map, metric_depth = depth_estimator.estimate_depth(frame)
                depth_end = time.time()
                
                # Update performance metrics with moving average
                elapsed = depth_end - depth_start
                avg_depth_time = alpha * elapsed + (1.0 - alpha) * avg_depth_time
                
                # Periodically show depth estimation performance
                if frame_count % 60 == 0 and avg_depth_time > 0:
                    depth_fps = 1.0 / avg_depth_time
                    print(f"Depth estimation: {depth_fps:.1f} FPS")
                
                # Save this frame's depth for reuse in skipped frames
                last_depth_map = depth_map
                last_metric_depth = metric_depth
            else:
                # Reuse the previous depth map for skipped frames
                depth_map = last_depth_map
                metric_depth = last_metric_depth
            
            # Skip processing if no depth map is available (shouldn't happen with improved handling)
            if depth_map is None or metric_depth is None:
                continue
                
            # Find the nearest point
            nearest_point = find_nearest_point(depth_map, 
                                              min_region_size=50,
                                              ignore_margin_percent=0.1,
                                              use_region_averaging=True)
            
            # Get metric distance from nearest point
            x, y = nearest_point['position']
            distance = metric_depth[y, x] if metric_depth is not None else None
            nearest_point['distance'] = distance  # Update in case it's used elsewhere
            
            # Update the advanced visualization with the current distance
            if distance is not None:
                advanced_vis.update(distance, direction="N")
                
                # Check for haptic feedback conditions
                haptic_triggered = (PROXIMITY_HAPTIC_MIN <= distance <= PROXIMITY_HAPTIC_MAX)
                
                # Print haptic feedback message with cooldown
                current_time = time.time()
                if haptic_triggered and (current_time - last_haptic_time) > haptic_cooldown:
                    print("haptic feedback invoked")
                    last_haptic_time = current_time
            
            # Only print debug information if debug flag is set
            if args.debug and metric_depth is not None:
                print(f"[DEBUG] Nearest normalized value: {nearest_point['value']:.3f}")
                print(f"[DEBUG] Nearest metric value (meters): {metric_depth[y, x]:.3f}")
                
                # Print nearest point info every 30 frames
                if frame_count % 30 == 0:
                    print(f"Nearest point: {nearest_point['distance']:.2f}m at position {x}, {y}")
            
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
                    display_frame = original_frame.copy()  # Use the unmodified frame
                elif args.view == "depth":
                    display_frame = depth_colored.copy()
                elif args.view == "overlay":
                    # Create overlay of depth on RGB
                    from depth_estimation.normalize import create_depth_overlay
                    display_frame = create_depth_overlay(original_frame.copy(), depth_colored, alpha=0.6)
                elif args.view == "side-by-side":
                    # Create side-by-side view
                    display_frame = np.hstack((original_frame.copy(), depth_colored))
                
                # Mark the nearest point on the display frame
                display_frame = mark_nearest_point(display_frame, nearest_point)
                
                # Draw the most recent detection boxes on every frame if object detection is enabled
                if args.detect_objects and detection_results.get("predictions"):
                    for prediction in detection_results.get("predictions", []):
                        confidence = prediction["confidence"]
                        
                        # Only draw detections above threshold
                        if confidence >= args.detection_confidence:
                            x, y, width, height = prediction["x"], prediction["y"], prediction["width"], prediction["height"]
                            class_name = prediction["class"]
                            
                            # Convert coordinates to int
                            x1 = int(x - width/2)
                            y1 = int(y - height/2)
                            x2 = int(x + width/2)
                            y2 = int(y + height/2)
                            
                            # Draw rectangle with more prominent colors
                            cv2.rectangle(display_frame, (x1, y1), (x2, y2), (0, 255, 0), 2)
                            
                            # Add label
                            label = f"{class_name}: {confidence:.2f}"
                            # Create background for label text for better visibility
                            text_size = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.5, 2)[0]
                            cv2.rectangle(display_frame, (x1, y1-text_size[1]-5), (x1+text_size[0], y1), (0, 0, 0), -1)
                            cv2.putText(display_frame, label, (x1, y1-5), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 2)
                
                # Add detected object count to title
                if args.detect_objects and detection_results:
                    num_objects = len(detection_results.get("predictions", []))
                    if distance is not None:
                        title = f"Blind Navigation - Distance: {distance:.2f}m - Objects: {num_objects}"
                    else:
                        title = f"Blind Navigation - Objects: {num_objects}"
                    cv2.putText(display_frame, title, (10, 25), 
                              cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
                
                # Show the visualization
                cv2.imshow("Blind Navigation System", display_frame)
                
                # Get key press and add debug print
                key = cv2.waitKey(1) & 0xFF
                if key != 255 and args.debug:  # If any key was pressed and debug is enabled
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
                elif key == ord('r'):
                    print("Resetting calibration to defaults...")
                    if depth_estimator.use_linear_mapping:
                        depth_estimator.slope = 4.0
                        depth_estimator.intercept = 0.5
                        print(f"Reset to linear defaults: slope={depth_estimator.slope}, intercept={depth_estimator.intercept}")
                    else:
                        depth_estimator.alpha = 4.5
                        depth_estimator.beta = 1.8
                        depth_estimator.gamma = 0.05
                        depth_estimator.offset = -0.7
                        print(f"Reset to inverse defaults: alpha={depth_estimator.alpha}, beta={depth_estimator.beta}, gamma={depth_estimator.gamma}, offset={depth_estimator.offset}")
                    
                    depth_estimator.calibration_points = []
                    depth_estimator.save_calibration()
                    print("Calibration reset complete.")
                elif key == ord('p'):  # 'p' for plot
                    print("Generating calibration visualization...")
                    depth_estimator.visualize_calibration()
                    print("Calibration visualization saved.")
                elif key == ord('a'):  # Increase alpha
                    adjust_parameters(depth_estimator, alpha_delta=0.1)
                elif key == ord('z'):  # Decrease alpha
                    adjust_parameters(depth_estimator, alpha_delta=-0.1)
                elif key == ord('s'):  # Increase beta
                    adjust_parameters(depth_estimator, beta_delta=0.1)
                elif key == ord('x'):  # Decrease beta
                    adjust_parameters(depth_estimator, beta_delta=-0.1)
                elif key == ord('d'):  # Increase gamma
                    adjust_parameters(depth_estimator, gamma_delta=0.01)
                elif key == ord('f'):  # Decrease gamma (changed from 'c' to avoid conflict)
                    adjust_parameters(depth_estimator, gamma_delta=-0.01)
                elif key == ord('g'):  # Increase offset (move curve up)
                    adjust_parameters(depth_estimator, offset_delta=0.1)
                elif key == ord('b'):  # Decrease offset (move curve down)
                    adjust_parameters(depth_estimator, offset_delta=-0.1)
                
                # Handle calibration number input
                if calibration_mode and ord('0') <= key <= ord('9'):
                    distance = float(chr(key))
                    print(f"Calibrating for distance: {distance}m")
                    h, w = depth_map.shape
                    center_depth = depth_map[h//2, w//2]
                    
                    # Use new multi-point calibration
                    depth_estimator.add_calibration_point(known_distance=distance, depth_value=center_depth)
                    
                    # Check if we need more calibration points
                    if len(depth_estimator.calibration_points) < 3:
                        print(f"Added calibration point at {distance}m. Need {3 - len(depth_estimator.calibration_points)} more points.")
                    else:
                        print("Calibration complete with multiple points.")
                        calibration_mode = False
                
                # Add a key handler for toggling between linear and inverse mapping
                elif key == ord('l'):  # 'l' for linear toggle
                    depth_estimator.use_linear_mapping = not depth_estimator.use_linear_mapping
                    mapping_type = "linear" if depth_estimator.use_linear_mapping else "inverse"
                    print(f"Switched to {mapping_type} depth mapping")
                    depth_estimator.save_calibration()
                
                # Linear parameter adjustment keys
                elif key == ord('u'):  # Increase slope
                    adjust_parameters(depth_estimator, slope_delta=0.1)
                elif key == ord('j'):  # Decrease slope
                    adjust_parameters(depth_estimator, slope_delta=-0.1)
                elif key == ord('i'):  # Increase intercept
                    adjust_parameters(depth_estimator, intercept_delta=0.1)
                elif key == ord('k'):  # Decrease intercept
                    adjust_parameters(depth_estimator, intercept_delta=-0.1)
                elif key == ord('o'):  # Toggle object detection
                    args.detect_objects = not args.detect_objects
                    status = "enabled" if args.detect_objects else "disabled"
                    print(f"Object detection {status}")
                elif key == ord('+'):  # Increase confidence threshold
                    args.detection_confidence = min(0.95, args.detection_confidence + 0.05)
                    print(f"Detection confidence threshold: {args.detection_confidence:.2f}")
                elif key == ord('-'):  # Decrease confidence threshold
                    args.detection_confidence = max(0.05, args.detection_confidence - 0.05)
                    print(f"Detection confidence threshold: {args.detection_confidence:.2f}")
            
            # Control the frame rate
            elapsed = time.time() - start_time
            sleep_time = max(0, 1.0/args.fps - elapsed)
            if sleep_time > 0:
                time.sleep(sleep_time)
            
            # Calculate and occasionally display the actual FPS
            actual_fps = 1.0 / (time.time() - start_time)
            if args.display and frame_count % 150 == 0:  # Every ~5 seconds at 30fps
                print(f"FPS: {actual_fps:.2f}")
    
    except KeyboardInterrupt:
        # Handle Ctrl+C gracefully
        print("Exiting...")
    finally:
        # Clean up resources
        advanced_vis.stop()  # Stop the visualization thread
        camera.release()
        cv2.destroyAllWindows()
        pygame.quit()

# This is the entry point when the script is run directly
if __name__ == "__main__":
    main()
