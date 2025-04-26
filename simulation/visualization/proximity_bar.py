"""
Proximity Bar Visualization

This module provides a visual representation of proximity to objects
detected by depth estimation. It displays a vertical bar that fills
from top to bottom as objects get closer to the user.
"""
import cv2
import numpy as np
from typing import Tuple, Optional

class ProximityBar:
    """
    Creates a vertical bar visualization that indicates proximity to objects.
    
    The bar fills from top to bottom as objects get closer, with color
    changes to indicate urgency (green for far, yellow for medium, red for close).
    """
    
    def __init__(self, 
                 width: int = 60, 
                 height: int = 300,
                 min_distance: float = 0.5,
                 max_distance: float = 5.0,
                 segments: int = 10):
        """
        Initialize the proximity bar with specified dimensions and thresholds.
        
        Args:
            width (int): Width of the bar in pixels
            height (int): Height of the bar in pixels
            min_distance (float): Minimum distance in meters (closest objects)
            max_distance (float): Maximum distance in meters (furthest objects)
            segments (int): Number of segments to divide the bar into
        """
        self.width = width
        self.height = height
        self.min_distance = min_distance
        self.max_distance = max_distance
        self.segments = segments
        self.segment_height = height // segments
        
        # Current distance value
        self.current_distance = max_distance
        
        # Thresholds for haptic feedback
        self.haptic_min = 0.5
        self.haptic_max = 1.5
        
        # Create empty bar image
        self.bar_image = np.ones((height, width, 3), dtype=np.uint8) * 50  # Dark gray background
        
    def update(self, distance: float) -> bool:
        """
        Update the bar with a new distance measurement.
        
        Args:
            distance (float): Current distance to nearest object in meters
            
        Returns:
            bool: True if haptic feedback should be triggered
        """
        # Clamp distance to valid range
        distance = max(self.min_distance, min(self.max_distance, distance))
        self.current_distance = distance
        
        # Determine if haptic feedback should be triggered
        haptic_feedback = self.haptic_min <= distance <= self.haptic_max
        
        return haptic_feedback
    
    def render(self) -> np.ndarray:
        """
        Render the proximity bar visualization.
        
        Returns:
            np.ndarray: Image of the proximity bar
        """
        # Reset the bar image
        self.bar_image = np.ones((self.height, self.width, 3), dtype=np.uint8) * 50
        
        # Calculate how many segments to fill based on current distance
        if self.current_distance >= self.max_distance:
            fill_segments = 0
        else:
            # Convert distance to fill ratio (inverse relationship)
            fill_ratio = 1.0 - ((self.current_distance - self.min_distance) / 
                               (self.max_distance - self.min_distance))
            fill_segments = int(fill_ratio * self.segments)
            fill_segments = min(self.segments, max(0, fill_segments))
        
        # Draw segments
        for i in range(self.segments):
            y1 = i * self.segment_height
            y2 = y1 + self.segment_height
            
            # Determine if this segment should be filled
            if i < fill_segments:
                # Calculate color based on segment position
                # Colors in BGR format (OpenCV default)
                if i < self.segments // 3:  # Top third - Green (far)
                    color = (0, 255, 0)  # BGR: Green
                elif i < 2 * self.segments // 3:  # Middle third - Yellow (medium)
                    color = (0, 255, 255)  # BGR: Yellow (Green + Red)
                else:  # Bottom third - Red (close)
                    color = (0, 0, 255)  # BGR: Red
                
                # Fill the segment
                cv2.rectangle(self.bar_image, (0, y1), (self.width, y2), color, -1)
            
            # Draw segment outline
            cv2.rectangle(self.bar_image, (0, y1), (self.width, y2), (255, 255, 255), 1)
        
        # Add distance text
        cv2.putText(self.bar_image, 
                  f"{self.current_distance:.2f}m", 
                  (5, self.height - 10),
                  cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
        
        return self.bar_image
    
    def is_in_haptic_range(self) -> bool:
        """
        Check if current distance is in haptic feedback range.
        
        Returns:
            bool: True if current distance is in haptic feedback range
        """
        return self.haptic_min <= self.current_distance <= self.haptic_max 