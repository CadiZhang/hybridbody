"""
Depth Analysis Utilities

This module provides diagnostic tools for analyzing depth maps,
including finding the nearest points and visualizing depth information.
These are primarily for testing and debugging purposes.
"""
import numpy as np
import cv2
from typing import Tuple, Dict, Any

def find_nearest_point(depth_map: np.ndarray, 
                       min_region_size: int = 50,
                       ignore_margin_percent: float = 0.1,
                       noise_threshold: float = 0.05,
                       use_region_averaging: bool = True) -> Dict[str, Any]:
    """
    Find the nearest point (smallest depth value) in the depth map with improved reliability.
    
    Args:
        depth_map: Normalized depth map (0-1 range)
        min_region_size: Minimum size of region to consider (filters noise)
        ignore_margin_percent: Percentage of frame edges to ignore
        noise_threshold: Threshold for considering a point as noise
        use_region_averaging: Whether to average depth in a region around the minimum
        
    Returns:
        Dictionary containing:
            - 'value': The depth value (0-1)
            - 'position': (x, y) coordinates
            - 'distance': Approximate distance in meters (if available)
    """
    # Create a copy to avoid modifying the original
    depth_copy = depth_map.copy()
    
    # Get dimensions
    h, w = depth_copy.shape
    
    # Calculate margins to ignore (helps avoid edge artifacts)
    margin_h = int(h * ignore_margin_percent)
    margin_w = int(w * ignore_margin_percent)
    
    # Create a mask for the valid region (excluding margins)
    mask = np.ones_like(depth_copy, dtype=bool)
    mask[:margin_h, :] = False
    mask[h-margin_h:, :] = False
    mask[:, :margin_w] = False
    mask[:, w-margin_w:] = False
    
    # Apply median blur to reduce noise
    smoothed_depth = cv2.medianBlur(depth_copy.astype(np.float32), 5)
    
    # Apply mask
    masked_depth = np.where(mask, smoothed_depth, 1.0)
    
    # Find the minimum value and its position
    min_val = np.min(masked_depth)
    min_pos = np.unravel_index(np.argmin(masked_depth), masked_depth.shape)
    
    # Convert to (x, y) format
    y, x = min_pos  # min_pos is (row, col) which is (y, x)
    
    # If using region averaging, compute the average depth in a region around the minimum
    if use_region_averaging:
        # Define region size
        region_size = 10
        
        # Calculate region boundaries with bounds checking
        y_start = max(0, y - region_size // 2)
        y_end = min(h, y + region_size // 2)
        x_start = max(0, x - region_size // 2)
        x_end = min(w, x + region_size // 2)
        
        # Extract the region
        region = depth_copy[y_start:y_end, x_start:x_end]
        
        # Calculate the average depth in the region
        region_avg = np.mean(region)
        
        # Use the region average as the depth value
        min_val = region_avg
    
    # Create result dictionary
    result = {
        'value': min_val,
        'position': (x, y),  # (x, y) format
        'distance': None  # Will be filled in by the caller if metric depth is available
    }
    
    return result

def mark_nearest_point(frame: np.ndarray, 
                       point: Dict[str, Any], 
                       color: Tuple[int, int, int] = (0, 0, 255),
                       radius: int = 10) -> np.ndarray:
    """
    Mark the nearest point on the frame with a circle and distance text.
    
    Args:
        frame: RGB frame to mark
        point: Point dictionary from find_nearest_point
        color: BGR color tuple for the marker
        radius: Radius of the circle marker
        
    Returns:
        Frame with the marked point
    """
    # Create a copy to avoid modifying the original
    marked_frame = frame.copy()
    
    # Extract position
    x, y = point['position']
    
    # Draw circle at the nearest point
    cv2.circle(marked_frame, (x, y), radius, color, 2)
    
    # Add crosshair
    cv2.line(marked_frame, (x-radius, y), (x+radius, y), color, 1)
    cv2.line(marked_frame, (x, y-radius), (x, y+radius), color, 1)
    
    # Add distance text if available
    if point['distance'] is not None:
        distance_text = f"{point['distance']:.2f}m"
        cv2.putText(marked_frame, distance_text, (x+15, y), 
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2)
    
    return marked_frame 

def find_nearest_clusters(depth_map: np.ndarray, 
                          num_clusters: int = 3,
                          min_distance: float = 0.2,
                          ignore_margin_percent: float = 0.1) -> list:
    """
    Find multiple nearest points by clustering regions of similar depth.
    
    Args:
        depth_map: Normalized depth map (0-1 range)
        num_clusters: Number of nearest clusters to find
        min_distance: Minimum normalized distance between clusters
        ignore_margin_percent: Percentage of frame edges to ignore
        
    Returns:
        List of dictionaries, each containing:
            - 'value': The depth value (0-1)
            - 'position': (x, y) coordinates
            - 'distance': Approximate distance in meters (if available)
            - 'size': Size of the cluster in pixels
    """
    # Create a copy to avoid modifying the original
    depth_copy = depth_map.copy()
    
    # Get dimensions
    h, w = depth_copy.shape
    
    # Calculate margins to ignore
    margin_h = int(h * ignore_margin_percent)
    margin_w = int(w * ignore_margin_percent)
    
    # Create a mask for the valid region
    mask = np.ones_like(depth_copy, dtype=bool)
    mask[:margin_h, :] = False
    mask[h-margin_h:, :] = False
    mask[:, :margin_w] = False
    mask[:, w-margin_w:] = False
    
    # Apply median blur to reduce noise
    smoothed_depth = cv2.medianBlur(depth_copy.astype(np.float32), 5)
    
    # Apply mask
    masked_depth = np.where(mask, smoothed_depth, 1.0)
    
    # Threshold the depth map to find close objects
    # Convert to 8-bit for contour finding
    close_threshold = np.min(masked_depth) + min_distance
    binary = (masked_depth < close_threshold).astype(np.uint8) * 255
    
    # Find contours in the binary image
    contours, _ = cv2.findContours(binary, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    
    # Sort contours by average depth
    clusters = []
    for contour in contours:
        # Create a mask for this contour
        contour_mask = np.zeros_like(binary)
        cv2.drawContours(contour_mask, [contour], 0, 255, -1)
        contour_mask = contour_mask > 0
        
        # Skip small contours
        if np.sum(contour_mask) < 50:
            continue
        
        # Calculate average depth in the contour
        avg_depth = np.mean(depth_copy[contour_mask])
        
        # Find the centroid of the contour
        M = cv2.moments(contour)
        if M["m00"] > 0:
            cx = int(M["m10"] / M["m00"])
            cy = int(M["m01"] / M["m00"])
        else:
            # Fallback to bounding box center
            x, y, w, h = cv2.boundingRect(contour)
            cx, cy = x + w // 2, y + h // 2
        
        clusters.append({
            'value': avg_depth,
            'position': (cx, cy),
            'distance': None,
            'size': np.sum(contour_mask)
        })
    
    # Sort clusters by depth (closest first)
    clusters.sort(key=lambda x: x['value'])
    
    # Return the specified number of clusters (or fewer if not enough found)
    return clusters[:num_clusters] 