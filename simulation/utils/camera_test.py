"""
Camera Testing Utility

This script helps users test and verify camera functionality by:
1. Listing all available cameras on the system
2. Testing specific cameras with visual feedback

Usage:
- To list all cameras: python utils/camera_test.py --list
- To test a specific camera: python utils/camera_test.py --test 0
"""
import cv2  # OpenCV library for camera access and image processing
import argparse  # For parsing command-line arguments
import time  # For timing operations

def list_available_cameras(max_cameras=10):
    """
    Scans the system for available cameras and displays their properties.
    
    This function tries to connect to cameras with indices from 0 to max_cameras-1,
    and reports which ones are available along with their default settings.
    
    Args:
        max_cameras (int): Maximum number of camera indices to check (default: 10)
        
    Returns:
        list: List of available camera indices that were found
    
    Example output:
        Camera 0 is available
          Resolution: 1280x720, FPS: 30
    """
    available_cameras = []  # Will store the list of working camera indices
    
    # Try each camera index from 0 to max_cameras-1
    for i in range(max_cameras):
        cap = cv2.VideoCapture(i)  # Attempt to open the camera
        if cap.isOpened():  # If camera opened successfully
            ret, frame = cap.read()  # Try to read a frame
            if ret:  # If frame was read successfully
                available_cameras.append(i)  # Add this index to our list
                
                # Display information about this camera
                print(f"Camera {i} is available")
                
                # Get and display camera properties
                width = cap.get(cv2.CAP_PROP_FRAME_WIDTH)  # Default width
                height = cap.get(cv2.CAP_PROP_FRAME_HEIGHT)  # Default height
                fps = cap.get(cv2.CAP_PROP_FPS)  # Default frames per second
                print(f"  Resolution: {width}x{height}, FPS: {fps}")
            
            cap.release()  # Release the camera resource
    
    return available_cameras

def test_camera(camera_index, width=640, height=480, display_time=5):
    """
    Tests a specific camera by displaying its live feed for a few seconds.
    
    This function opens the specified camera, sets the requested resolution,
    and shows a live preview with camera information overlaid on the image.
    It also measures the actual frame rate achieved.
    
    Args:
        camera_index (int): Which camera to test (0 for built-in, 1+ for external)
        width (int): Requested frame width in pixels
        height (int): Requested frame height in pixels
        display_time (int): How many seconds to display the camera feed
    
    Example:
        test_camera(0, 1280, 720, 10)  # Test camera 0 at 720p for 10 seconds
    """
    # Open the camera
    cap = cv2.VideoCapture(camera_index)
    
    # Try to set the requested resolution
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, width)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, height)
    
    # Check if camera opened successfully
    if not cap.isOpened():
        print(f"Could not open camera {camera_index}")
        return
    
    # Get the actual properties (may differ from requested)
    actual_width = cap.get(cv2.CAP_PROP_FRAME_WIDTH)
    actual_height = cap.get(cv2.CAP_PROP_FRAME_HEIGHT)
    actual_fps = cap.get(cv2.CAP_PROP_FPS)
    
    # Display camera information
    print(f"Testing Camera {camera_index}")
    print(f"Requested: {width}x{height}")
    print(f"Actual: {actual_width}x{actual_height}, FPS: {actual_fps}")
    
    # Variables for FPS calculation
    start_time = time.time()
    frames = 0
    
    # Main display loop
    while time.time() - start_time < display_time:
        # Capture a frame
        ret, frame = cap.read()
        if not ret:
            print("Failed to capture frame")
            break
        
        frames += 1  # Count frames for FPS calculation
        
        # Add text overlay with camera information
        cv2.putText(frame, f"Camera {camera_index}", (10, 30), 
                    cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
        cv2.putText(frame, f"{actual_width}x{actual_height}", (10, 70), 
                    cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
        
        # Display the frame in a window
        cv2.imshow(f"Camera {camera_index} Test", frame)
        
        # Exit if 'q' key is pressed
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break
    
    # Calculate and display the actual measured frame rate
    elapsed = time.time() - start_time
    measured_fps = frames / elapsed if elapsed > 0 else 0
    print(f"Measured FPS: {measured_fps:.2f}")
    
    # Clean up
    cap.release()
    cv2.destroyAllWindows()

# This section runs when the script is executed directly
if __name__ == "__main__":
    # Set up command-line argument parsing
    parser = argparse.ArgumentParser(description="Camera Testing Utility")
    parser.add_argument("--list", action="store_true", help="List available cameras")
    parser.add_argument("--test", type=int, default=-1, help="Test specific camera index")
    parser.add_argument("--width", type=int, default=640, help="Camera width")
    parser.add_argument("--height", type=int, default=480, help="Camera height")
    parser.add_argument("--time", type=int, default=5, help="Test duration in seconds")
    
    # Parse the arguments
    args = parser.parse_args()
    
    # If --list flag was provided, scan for available cameras
    if args.list:
        available = list_available_cameras()
        if not available:
            print("No cameras detected")
    
    # If --test flag was provided with a valid index, test that camera
    if args.test >= 0:
        test_camera(args.test, args.width, args.height, args.time) 