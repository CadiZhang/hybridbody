"""
Depth Normalization Utilities

This module provides functions for normalizing and processing depth maps,
including:
1. Converting relative depth to metric depth
2. Normalizing depth maps for visualization
3. Filtering and smoothing depth data
"""
import numpy as np
import cv2
from typing import Tuple

def normalize_depth(depth_map: np.ndarray) -> np.ndarray:
    """
    Normalize a depth map to 0-1 range.
    
    Args:
        depth_map (np.ndarray): Input depth map
        
    Returns:
        np.ndarray: Normalized depth map (0-1 range)
    """
    depth_min = depth_map.min()
    depth_max = depth_map.max()
    
    # Avoid division by zero
    if depth_max - depth_min > 0:
        normalized = (depth_map - depth_min) / (depth_max - depth_min)
    else:
        normalized = np.zeros_like(depth_map)
    
    return normalized

def apply_depth_colormap(depth_map: np.ndarray, colormap: int = cv2.COLORMAP_TURBO) -> np.ndarray:
    """
    Apply a colormap to a depth map for visualization.
    
    Args:
        depth_map (np.ndarray): Normalized depth map (0-1 range)
        colormap (int): OpenCV colormap to apply
        
    Returns:
        np.ndarray: Colorized depth map
    """
    # Convert to 8-bit for colormap application
    depth_8bit = (depth_map * 255).astype(np.uint8)
    
    # Apply colormap
    colored_depth = cv2.applyColorMap(depth_8bit, colormap)
    
    return colored_depth

def filter_depth_map(depth_map: np.ndarray, kernel_size: int = 5) -> np.ndarray:
    """
    Apply median filtering to reduce noise in depth map.
    
    Args:
        depth_map (np.ndarray): Input depth map
        kernel_size (int): Size of median filter kernel
        
    Returns:
        np.ndarray: Filtered depth map
    """
    return cv2.medianBlur(depth_map.astype(np.float32), kernel_size)

def create_depth_overlay(frame: np.ndarray, depth_colored: np.ndarray, 
                         alpha: float = 0.6) -> np.ndarray:
    """
    Create an overlay of the depth map on the original frame.
    
    Args:
        frame (np.ndarray): Original RGB frame
        depth_colored (np.ndarray): Colorized depth map
        alpha (float): Transparency factor (0-1)
        
    Returns:
        np.ndarray: Frame with depth overlay
    """
    # Ensure both images have the same size
    if frame.shape != depth_colored.shape:
        depth_colored = cv2.resize(depth_colored, (frame.shape[1], frame.shape[0]))
    
    # Create overlay
    overlay = cv2.addWeighted(frame, 1-alpha, depth_colored, alpha, 0)
    
    return overlay

def depth_to_distance(depth_map: np.ndarray, scale_factor: float = 3.0,
                      min_depth: float = 0.1, max_depth: float = 10.0) -> np.ndarray:
    """
    Convert normalized depth values to approximate metric distances.
    
    Args:
        depth_map (np.ndarray): Normalized depth map (0-1 range)
        scale_factor (float): Calibration factor to convert to meters
        min_depth (float): Minimum depth in meters
        max_depth (float): Maximum depth in meters
        
    Returns:
        np.ndarray: Depth map in approximate meters
    """
    # Convert normalized depth to metric range
    metric_depth = min_depth + depth_map * (max_depth - min_depth)
    
    # Apply calibration factor
    metric_depth = metric_depth * scale_factor
    
    return metric_depth 