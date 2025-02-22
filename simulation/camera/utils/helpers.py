import numpy as np
import utils.config as config

def map_obstacles_to_sectors(obstacles):
    """Map obstacles to directional sectors and find closest in each."""
    sectors = {"N": [], "NE": [], "NW": []}
    for obs in obstacles:
        u, _, z = obs["centroid"]
        # Calculate horizontal angle from image center
        angle = np.arctan2(u - config.FRAME_WIDTH / 2, config.FOCAL_LENGTH) * 180 / np.pi
        if -15 <= angle <= 15:
            sectors["N"].append(z)
        elif 15 < angle <= 45:
            sectors["NE"].append(z)
        elif -45 <= angle < -15:
            sectors["NW"].append(z)
    
    # Find closest obstacle per sector
    closest = {sector: min(distances) if distances else None for sector, distances in sectors.items()}
    return closest