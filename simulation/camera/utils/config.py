# Camera settings
CAMERA_INDEX = 0  # Default camera (e.g., webcam)
FRAME_WIDTH = 640
FRAME_HEIGHT = 480
FOCAL_LENGTH = 525.0  # Approximate focal length in pixels (adjust per camera)# Depth estimation
DEPTH_MODEL = "MiDaS_small"  # Lightweight MiDaS model# Obstacle detection
GROUND_HEIGHT_THRESHOLD = 1.2  # Camera height in meters
WARNING_DISTANCE = 2.0  # Distance in meters to trigger haptic feedback
SECTORS = ["N", "NE", "NW"]  # Directional sectors for feedback# Haptic feedback
# SERIAL_PORT = "COM3"  # Adjust based on your OS and hardware
BAUD_RATE = 9600

# Simulation
SIMULATION_ENABLED = True  # Toggle 3D visualization