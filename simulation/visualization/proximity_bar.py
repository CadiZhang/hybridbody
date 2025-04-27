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
                 segments: int = 10,
                 dark_mode: bool = True):
        """
        Initialize the proximity bar with specified dimensions and thresholds.
        
        Args:
            width (int): Width of the bar in pixels
            height (int): Height of the bar in pixels
            min_distance (float): Minimum distance in meters (closest objects)
            max_distance (float): Maximum distance in meters (furthest objects)
            segments (int): Number of segments to divide the bar into
            dark_mode (bool): Whether to use dark mode styling
        """
        self.width = width
        self.height = height
        self.min_distance = min_distance
        self.max_distance = max_distance
        self.segments = segments
        self.segment_height = height // segments
        self.dark_mode = dark_mode
        
        # Current distance value
        self.current_distance = max_distance
        
        # Thresholds for haptic feedback
        self.haptic_min = 0.5
        self.haptic_max = 1.5
        
        # Define color scheme based on mode
        self.setup_colors()
        
        # Create empty bar image - fix this initialization
        self.bar_image = np.ones((height, width, 3), dtype=np.uint8)
        self.bar_image[:] = self.bg_color
    
    def setup_colors(self):
        """Set up color scheme based on dark/light mode preference"""
        if self.dark_mode:
            self.bg_color = (18, 18, 18)  # Dark background
            self.text_color = (200, 200, 200)  # Light gray text
            self.border_color = (70, 70, 70)  # Medium gray border
        else:
            self.bg_color = (240, 240, 240)  # Light background
            self.text_color = (50, 50, 50)  # Dark gray text
            self.border_color = (180, 180, 180)  # Medium gray border
        
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
        # Reset the bar image - this is the problematic line
        # The multiplication might be creating an array with a non-standard format
        # Let's create the array more explicitly:
        self.bar_image = np.ones((self.height, self.width, 3), dtype=np.uint8)
        self.bar_image[:] = self.bg_color  # Fill with background color
        
        # Calculate how many segments to fill based on current distance
        if self.current_distance >= self.max_distance:
            fill_segments = 0
        else:
            # Convert distance to fill ratio (inverse relationship)
            fill_ratio = 1.0 - ((self.current_distance - self.min_distance) / 
                               (self.max_distance - self.min_distance))
            fill_segments = int(fill_ratio * self.segments)
            fill_segments = min(self.segments, max(0, fill_segments))
        
        # Add curved top to the bar
        radius = int(self.width // 2)
        center_x = int(self.width // 2)
        center_y = int(radius)
        
        # Draw the circle with proper integer coordinates
        cv2.circle(self.bar_image, (center_x, center_y), radius, self.border_color, 2)
        
        # Draw outer border for the entire bar
        cv2.rectangle(self.bar_image, 
                     (0, radius), 
                     (self.width, self.height), 
                     self.border_color, 2)
        
        # Draw distance scale markers
        scale_steps = 5
        for i in range(scale_steps + 1):
            y_pos = int(radius + (self.height - radius) * i / scale_steps)
            # Draw tick mark
            cv2.line(self.bar_image, 
                    (0, y_pos), 
                    (5, y_pos), 
                    self.text_color, 1)
            # Draw scale value
            distance_value = self.max_distance - (i / scale_steps * (self.max_distance - self.min_distance))
            if i % 2 == 0:  # Only show every other marker to avoid crowding
                cv2.putText(self.bar_image, 
                          f"{distance_value:.1f}", 
                          (8, y_pos + 4), 
                          cv2.FONT_HERSHEY_SIMPLEX, 
                          0.3, self.text_color, 1)
        
        # Draw segment fill with gradient
        if fill_segments > 0:
            # Calculate fill height
            fill_height = fill_segments * self.segment_height
            
            # Create gradient based on fill ratio
            for y in range(radius, min(radius + fill_height, self.height)):
                # Normalize position within the filled area
                rel_pos = (y - radius) / (self.height - radius)
                
                # Calculate color based on position (green->yellow->red)
                # Color transitions at 1/3 and 2/3 of the way up
                if rel_pos < 0.33:  # Green zone (far)
                    color = (0, 255, 0)  # BGR: Green
                elif rel_pos < 0.66:  # Yellow zone (medium)
                    # Blend from green to yellow
                    blend = (rel_pos - 0.33) / 0.33
                    green = 255
                    red = int(255 * blend)
                    color = (0, green, red)  # BGR: Blend green to yellow
                else:  # Red zone (close)
                    # Blend from yellow to red
                    blend = (rel_pos - 0.66) / 0.34
                    green = int(255 * (1 - blend))
                    red = 255
                    color = (0, green, red)  # BGR: Blend yellow to red
                
                # Fill this horizontal line with calculated color
                cv2.line(self.bar_image, 
                        (2, y), 
                        (self.width - 3, y), 
                        color, 1)
            
            # Fill the curved top if we're in the first segment
            if fill_segments > 0:
                # Calculate the appropriate color for the top (green/yellow/red)
                if fill_segments < self.segments // 3:
                    top_color = (0, 255, 0)  # Green
                elif fill_segments < 2 * self.segments // 3:
                    top_color = (0, 255, 255)  # Yellow
                else:
                    top_color = (0, 0, 255)  # Red
                
                # Create a mask for the curved top
                mask = np.zeros((radius * 2, self.width), dtype=np.uint8)
                cv2.circle(mask, (self.width // 2, radius), radius - 2, 255, -1)
                
                # Apply the mask to fill only inside the curved top
                top_section = self.bar_image[0:radius*2, 0:self.width].copy()
                top_section[mask > 0] = top_color
                self.bar_image[0:radius*2, 0:self.width] = top_section
        
        # Add current distance text at the bottom
        cv2.putText(self.bar_image, 
                  f"{self.current_distance:.2f}m", 
                  (5, self.height - 10),
                  cv2.FONT_HERSHEY_SIMPLEX, 0.4, self.text_color, 1)
        
        # Add "PROXIMITY" label at the top
        cv2.putText(self.bar_image, 
                  "PROXIMITY", 
                  (5, 15), 
                  cv2.FONT_HERSHEY_SIMPLEX, 0.4, self.text_color, 1)
        
        return self.bar_image
    
    def is_in_haptic_range(self) -> bool:
        """
        Check if current distance is in haptic feedback range.
        
        Returns:
            bool: True if current distance is in haptic feedback range
        """
        return self.haptic_min <= self.current_distance <= self.haptic_max 