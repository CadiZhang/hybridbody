"""
Configuration Settings for Blind Navigation Assistance System

This file contains all the adjustable parameters that control how the system works.
Think of it as a central control panel where you can tweak various aspects of the
system without having to modify the actual code.
"""

# ===== CAMERA SETTINGS =====
# These control how the camera captures images

# Which camera to use (0 is usually the built-in camera, 1+ for external cameras)
CAMERA_INDEX = 0

# The resolution at which to capture video (higher = more detail but slower)
FRAME_WIDTH = 640   # Width in pixels
FRAME_HEIGHT = 480  # Height in pixels

# The angle at which the camera is tilted downward (in degrees)
# This helps the system understand the ground plane
CAMERA_ANGLE = 45

# ===== PROCESSING SETTINGS =====
# These control how the system processes the camera feed

# Target frames per second (higher = more responsive but more CPU usage)
TARGET_FPS = 30

# Whether to show visual output by default
DISPLAY_OUTPUT = True

# ===== DEPTH ESTIMATION SETTINGS =====
# These control how the system calculates depth from the camera image

# Which depth estimation model to use
# Options:
#   "dpt_levit_224" - Fastest, good for Raspberry Pi 4
#   "dpt_swin2_tiny_256" - Better quality, for Raspberry Pi 5/Jetson Nano
#   "midas_v21_small" - Legacy model with OpenVINO support
DEPTH_MODEL = "dpt_levit_224"

# Resolution for depth processing (lower = faster)
PROCESSING_WIDTH = 224
PROCESSING_HEIGHT = 224

# Factor to convert depth values to approximate meters
# This will be calibrated during setup
DEPTH_SCALE_FACTOR = 3.0

# Add new depth stabilization settings
DEPTH_SMOOTHING_FRAMES = 3        # Number of frames for temporal smoothing
DEPTH_CONFIDENCE_THRESHOLD = 0.5   # Minimum confidence for direct depth use
DEPTH_MIN_RANGE = 0.5             # Minimum depth in meters
DEPTH_MAX_RANGE = 3.0             # Maximum depth in meters

# ===== OBSTACLE DETECTION SETTINGS =====
# These control how the system identifies obstacles

# How high above the ground plane something must be to count as an obstacle (in meters)
GROUND_HEIGHT_THRESHOLD = 0.1

# Minimum height for something to be considered an obstacle (in meters)
MIN_OBSTACLE_HEIGHT = 0.05

# How many cells to divide the depth map into for grid-based detection
GRID_CELLS_X = 16  # Horizontal divisions
GRID_CELLS_Y = 12  # Vertical divisions

# ===== FEEDBACK SETTINGS =====
# These control how the system provides warnings about obstacles

# Distance thresholds for different warning levels (in meters)
WARNING_DISTANCE_CLOSE = 1.0    # Strong warning (very close)
WARNING_DISTANCE_MEDIUM = 2.0   # Medium warning
WARNING_DISTANCE_FAR = 2.5      # Mild warning (farther away)

# ===== DIRECTIONAL SECTORS =====
# The directions in which the system can detect obstacles
SECTORS = ["N", "NE", "NW", "E", "W"]  # North, Northeast, Northwest, East, West 

# ===== PROXIMITY BAR SETTINGS =====
PROXIMITY_BAR_WIDTH = 60
PROXIMITY_BAR_HEIGHT = 300
PROXIMITY_MIN_DISTANCE = 0.5  # Minimum distance in meters
PROXIMITY_MAX_DISTANCE = 5.0  # Maximum distance in meters
PROXIMITY_SEGMENTS = 10       # Number of segments in the bar
PROXIMITY_HAPTIC_MIN = 0.5    # Minimum distance for haptic feedback
PROXIMITY_HAPTIC_MAX = 1.5    # Maximum distance for haptic feedback 