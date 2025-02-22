import numpy as np
import utils.config as config

def estimate_ground_plane(depth_map):
    """Create a mask identifying ground pixels based on height."""
    height, width = depth_map.shape
    u, v = np.meshgrid(np.arange(width), np.arange(height))
    # Assume depth_map is in relative units; scale to meters later if needed*
    z = depth_map  # Placeholder; actual depth scaling requires calibration
    x = (u - width / 2) * z / config.FOCAL_LENGTH
    y = (v - height / 2) * z / config.FOCAL_LENGTH
    
    # Heights relative to camera (camera at y = 0, ground at y = -GROUND_HEIGHT_THRESHOLD)*
    heights = -y - config.GROUND_HEIGHT_THRESHOLD
    # Ground is where height is near zero*
    ground_mask = np.abs(heights) < 0.1  # 10 cm tolerance*
    return ground_mask