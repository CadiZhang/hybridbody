"""
Blind Navigation Assistance System - Main Module

This is the main entry point for the blind navigation system. It:
1. Initializes the camera
2. Processes frames in real-time
3. (Future) Performs depth estimation and obstacle detection
4. (Future) Provides directional feedback

Usage:
    python main.py --display  # Run with visual display
    python main.py --camera 1 --width 1280 --height 720  # Use external camera at HD resolution
"""
# run "python main.py --display" to see the camera feed

import argparse  # For parsing command-line arguments
import cv2       # OpenCV for computer vision functions
import time      # For timing and FPS control
import os        # For directory operations

# Create necessary directories if they don't exist
os.makedirs("camera", exist_ok=True)
os.makedirs("utils", exist_ok=True)

def main():
    """
    Main function that runs the blind navigation system.
    
    This function:
    1. Parses command-line arguments
    2. Sets up the camera
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
    
    try:
        # Main processing loop - runs continuously until interrupted
        while True:
            # Record the start time for FPS calculation
            start_time = time.time()
            
            # Capture a frame from the camera
            frame = camera.capture_frame()
            if frame is None:
                print("Failed to capture frame. Retrying...")
                continue
            
            # === Future: Add depth estimation here ===
            # depth_map = depth_estimator.process(frame)
            
            # === Future: Add obstacle detection here ===
            # obstacles = obstacle_detector.detect(depth_map)
            
            # === Future: Add directional mapping here ===
            # directions = mapper.map_to_sectors(obstacles)
            
            # Display the camera feed if requested
            if args.display:
                # Show the frame in a window
                cv2.imshow("Camera Feed", frame)
                
                # Check for 'q' key press to exit
                if cv2.waitKey(1) & 0xFF == ord('q'):
                    break
            
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
