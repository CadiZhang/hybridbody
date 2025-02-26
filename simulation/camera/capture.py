"""
Camera Capture Module

This module handles all camera-related functionality, including:
1. Camera initialization and configuration
2. Frame capture with error handling
3. Resource management

It provides a simple, reliable interface for accessing camera frames
that automatically handles common errors and recovery.
"""
import cv2  # OpenCV library for camera access
import time  # For timing and delays

class CameraCapture:
    """
    Handles camera initialization and frame capture with error handling and retry logic.
    
    This class provides a robust wrapper around OpenCV's camera functionality,
    with automatic error recovery and resource management.
    """
    def __init__(self, camera_index=0, frame_width=640, frame_height=480):
        """
        Initialize the camera capture system.
        
        Args:
            camera_index (int): Which camera to use (0 for built-in, 1+ for external)
            frame_width (int): Desired width of captured frames in pixels
            frame_height (int): Desired height of captured frames in pixels
        
        Note:
            The actual resolution may differ from requested if the camera
            doesn't support the exact dimensions.
        """
        # Store the configuration
        self.camera_index = camera_index
        self.frame_width = frame_width
        self.frame_height = frame_height
        
        # Initialize camera object to None (will be created in initialize_camera)
        self.cap = None
        
        # Start the camera
        self.initialize_camera()
    
    def initialize_camera(self):
        """
        Set up the camera with the specified parameters.
        
        This method:
        1. Releases any existing camera connection
        2. Opens the specified camera
        3. Sets the requested resolution
        4. Verifies the camera is working
        5. Allows a warm-up period for auto-exposure to stabilize
        
        Raises:
            RuntimeError: If the camera cannot be opened
        """
        # Clean up any existing camera connection
        if self.cap is not None:
            self.cap.release()
        
        # Create a new camera capture object
        self.cap = cv2.VideoCapture(self.camera_index)
        
        # Configure the camera resolution
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, self.frame_width)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self.frame_height)
        
        # Check if the camera opened successfully
        if not self.cap.isOpened():
            raise RuntimeError(f"Failed to open camera {self.camera_index}")
        
        # Allow camera to warm up (important for auto-exposure to stabilize)
        time.sleep(0.5)
    
    def capture_frame(self):
        """
        Capture a single frame from the camera with error handling.
        
        This method:
        1. Checks if the camera is still open
        2. Attempts to read a frame
        3. Handles errors by trying to reinitialize the camera
        
        Returns:
            numpy.ndarray: The captured image frame, or None if capture failed
            
        Note:
            The returned frame is in BGR color format (OpenCV default)
        """
        # Check if camera is still open, reinitialize if needed
        if not self.cap.isOpened():
            self.initialize_camera()
        
        # Attempt to read a frame from the camera
        ret, frame = self.cap.read()
        
        # Handle failed frame capture
        if not ret or frame is None:
            print("Warning: Failed to capture frame")
            
            # Try to recover by reinitializing the camera
            try:
                self.initialize_camera()
                ret, frame = self.cap.read()
                if not ret:
                    return None  # Still failed after reinitialization
            except Exception as e:
                print(f"Error reinitializing camera: {e}")
                return None
        
        return frame
    
    def release(self):
        """
        Release camera resources.
        
        This method should be called when done with the camera to properly
        free system resources. It's automatically called in the destructor,
        but explicit calling is recommended.
        """
        if self.cap is not None:
            self.cap.release()
            self.cap = None