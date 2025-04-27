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
from collections import deque

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

def clamp_depth_range(depth_map: np.ndarray, 
                     min_depth: float = 0.5,
                     max_depth: float = 3.0) -> np.ndarray:
    """
    Clamp depth values to a realistic range based on physical constraints.
    """
    return np.clip(depth_map, min_depth, max_depth)

def depth_to_metric_inverse(depth_map: np.ndarray, 
                           alpha: float = 3.5, 
                           beta: float = 2.5, 
                           gamma: float = 0.05,
                           offset: float = -0.3,  # Add offset parameter
                           min_depth: float = 0.5,
                           max_depth: float = 5.0) -> np.ndarray:
    """
    Convert normalized depth to metric using inverse relationship with offset.
    
    metric_depth = alpha / (beta * (1 - depth_map) + gamma) + offset
    
    Args:
        depth_map: Normalized depth map (0-1 range, 1=closest)
        alpha, beta, gamma: Parameters determined by calibration
        offset: Vertical shift (negative values lower the curve)
        min_depth: Minimum depth in meters
        max_depth: Maximum depth in meters
        
    Returns:
        Depth map in metric units (meters)
    """
    # Ensure depth is properly normalized
    depth_map = np.clip(depth_map, 0.0, 1.0)
    
    # Apply inverse transformation with offset
    metric_depth = alpha / (beta * (1.0 - depth_map) + gamma) + offset
    
    # Clamp to min/max range for safety
    metric_depth = np.clip(metric_depth, min_depth, max_depth)
    
    return metric_depth

def depth_to_metric_linear(depth_map: np.ndarray,
                          slope: float = 4.0,
                          intercept: float = 0.5,
                          min_depth: float = 0.5,
                          max_depth: float = 5.0) -> np.ndarray:
    """
    Convert normalized depth to metric using simple linear relationship.
    
    metric_depth = slope * depth_map + intercept
    
    Args:
        depth_map: Normalized depth map (0-1 range, 1=closest)
        slope: Scaling factor for converting depth to distance
        intercept: Vertical offset (y-intercept) for the linear function
        min_depth: Minimum depth in meters
        max_depth: Maximum depth in meters
        
    Returns:
        Depth map in metric units (meters)
    """
    # Ensure depth is properly normalized
    depth_map = np.clip(depth_map, 0.0, 1.0)
    
    # Apply linear transformation
    metric_depth = slope * depth_map + intercept
    
    # Clamp to min/max range for safety
    metric_depth = np.clip(metric_depth, min_depth, max_depth)
    
    return metric_depth

class DepthCalibrator:
    """
    Handles depth calibration using known reference distances.
    """
    def __init__(self):
        self.calibration_points = []  # [(measured_depth, actual_depth), ...]
        self.scale_factor = None
        self.offset = None
    
    def add_calibration_point(self, measured_depth: float, actual_depth: float):
        """
        Add a calibration point with known actual distance.
        """
        self.calibration_points.append((measured_depth, actual_depth))
        self._update_calibration()
    
    def _update_calibration(self):
        """
        Update calibration parameters using linear regression.
        """
        if len(self.calibration_points) < 2:
            return
            
        measured = np.array([p[0] for p in self.calibration_points])
        actual = np.array([p[1] for p in self.calibration_points])
        
        # Simple linear regression
        A = np.vstack([measured, np.ones_like(measured)]).T
        self.scale_factor, self.offset = np.linalg.lstsq(A, actual, rcond=None)[0]
    
    def calibrate_depth(self, depth_map: np.ndarray) -> np.ndarray:
        """
        Apply calibration to depth map.
        """
        if self.scale_factor is None:
            return depth_map
            
        return depth_map * self.scale_factor + self.offset

class DepthSmoother:
    """
    Handles temporal smoothing of depth maps using a weighted moving average.
    More recent frames have higher weight in the average.
    """
    def __init__(self, buffer_size=3):
        self.buffer = deque(maxlen=buffer_size)
        # Weights give more importance to recent frames
        self.weights = np.array([0.5, 0.3, 0.2])  # Must sum to 1.0
    
    def update(self, depth_map: np.ndarray) -> np.ndarray:
        """
        Update buffer with new depth map and return smoothed result.
        """
        self.buffer.append(depth_map.copy())
        
        if len(self.buffer) < self.buffer.maxlen:
            return depth_map
        
        # Apply weighted average to available frames
        smoothed = np.zeros_like(depth_map)
        weights = self.weights[-len(self.buffer):]
        weights = weights / weights.sum()  # Normalize weights
        
        for i, frame in enumerate(self.buffer):
            smoothed += frame * weights[i]
            
        return smoothed 

class DepthStabilizer:
    """
    Combines EMA filtering with confidence-based stabilization
    """
    def __init__(self, alpha=0.2, confidence_threshold=0.5):
        self.alpha = alpha
        self.previous_depth = None
        self.confidence_threshold = confidence_threshold
    
    def apply_ema_filter(self, current_depth):
        """
        Apply Exponential Moving Average filter
        """
        if self.previous_depth is None:
            self.previous_depth = current_depth
            return current_depth
            
        filtered_depth = self.alpha * current_depth + \
                        (1 - self.alpha) * self.previous_depth
        self.previous_depth = filtered_depth
        return filtered_depth
    
    def compute_confidence(self, depth_map: np.ndarray, window_size: int = 5) -> np.ndarray:
        """
        Compute confidence map based on local depth consistency
        """
        local_var = cv2.blur(depth_map**2, (window_size, window_size)) - \
                    cv2.blur(depth_map, (window_size, window_size))**2
        
        confidence = 1 / (1 + local_var)
        confidence = (confidence - confidence.min()) / \
                    (confidence.max() - confidence.min() + 1e-6)
        
        return confidence
    
    def stabilize(self, depth_map: np.ndarray) -> np.ndarray:
        """
        Apply hybrid stabilization:
        - Use EMA for all pixels
        - Apply additional filtering for low-confidence regions
        """
        # Apply EMA filter first
        filtered_depth = self.apply_ema_filter(depth_map)
        
        # Compute confidence map
        confidence = self.compute_confidence(filtered_depth)
        
        # For low-confidence regions, apply additional spatial filtering
        low_confidence_mask = confidence < self.confidence_threshold
        if np.any(low_confidence_mask):
            filtered_depth[low_confidence_mask] = cv2.medianBlur(
                filtered_depth.astype(np.float32), 5
            )[low_confidence_mask]
        
        return filtered_depth 

class EMADepthFilter:
    """
    Exponential Moving Average filter for depth map stabilization.
    Provides temporal smoothing with minimal latency.
    """
    def __init__(self, alpha: float = 0.2):
        """
        Initialize EMA filter.
        
        Args:
            alpha (float): Smoothing factor (0-1). Lower values mean more smoothing.
                0.2 gives 20% weight to new values, 80% to history.
        """
        self.alpha = alpha
        self.previous_depth = None
    
    def filter(self, depth_map: np.ndarray) -> np.ndarray:
        """
        Apply EMA filtering to depth map.
        
        Args:
            depth_map (np.ndarray): Current depth map
            
        Returns:
            np.ndarray: Filtered depth map
        """
        # Initialize on first frame
        if self.previous_depth is None:
            self.previous_depth = depth_map.copy()
            return depth_map
        
        # Apply EMA formula: y(t) = α * x(t) + (1-α) * y(t-1)
        filtered_depth = (self.alpha * depth_map + 
                        (1 - self.alpha) * self.previous_depth)
        
        # Update previous depth
        self.previous_depth = filtered_depth.copy()
        
        return filtered_depth 