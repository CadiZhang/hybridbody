"""
Directional Pulse Visualization

This module provides a conical pulsing visualization that indicates
direction and proximity to objects detected by depth estimation.
"""
import cv2
import numpy as np
import math
from typing import Tuple, Optional

class DirectionalPulse:
    """
    Creates a conical visualization that pulses based on proximity.
    
    The visualization shows a conical shape pointing North (or another
    specified direction) that pulses faster as objects get closer.
    """
    
    def __init__(self, 
                width: int = 200, 
                height: int = 150,
                min_distance: float = 0.5,
                max_distance: float = 5.0):
        """
        Initialize the directional pulse visualization.
        
        Args:
            width (int): Width of the visualization in pixels
            height (int): Height of the visualization in pixels
            min_distance (float): Minimum distance in meters (closest objects)
            max_distance (float): Maximum distance in meters (furthest objects)
        """
        self.width = width
        self.height = height
        self.min_distance = min_distance
        self.max_distance = max_distance
        
        # Current distance value
        self.current_distance = max_distance
        
        # Pulse animation properties
        self.pulse_phase = 0
        self.pulse_speed = 0.1  # Base speed of pulse animation
        
        # Dark mode colors
        self.bg_color = (18, 18, 18)  # Dark background
        self.grid_color = (40, 40, 40)  # Slightly lighter grid lines
        self.text_color = (200, 200, 200)  # Light gray text
        
        # Direction indicators
        self.directions = ["N", "NE", "E", "SE", "S", "SW", "W", "NW"]
        self.current_direction = "N"  # Default to North
        
        # Create empty image
        self.pulse_image = np.ones((height, width, 3), dtype=np.uint8)
        self.pulse_image[:] = self.bg_color
    
    def update(self, distance: float, direction: str = "N") -> None:
        """
        Update the visualization with a new distance measurement.
        
        Args:
            distance (float): Current distance to nearest object in meters
            direction (str): Cardinal direction (N, NE, E, SE, S, SW, W, NW)
        """
        # Clamp distance to valid range
        distance = max(self.min_distance, min(self.max_distance, distance))
        self.current_distance = distance
        
        # Update direction if valid
        if direction in self.directions:
            self.current_direction = direction
        
        # Update pulse phase and speed based on distance
        # Closer objects = faster pulse
        distance_ratio = (self.current_distance - self.min_distance) / (self.max_distance - self.min_distance)
        self.pulse_speed = 0.3 - (distance_ratio * 0.25)  # 0.05 to 0.3
        self.pulse_phase = (self.pulse_phase + self.pulse_speed) % (2 * math.pi)
    
    def render(self) -> np.ndarray:
        """
        Render the directional pulse visualization.
        
        Returns:
            np.ndarray: Image of the directional pulse
        """
        # Reset the image
        self.pulse_image = np.ones((self.height, self.width, 3), dtype=np.uint8)
        self.pulse_image[:] = self.bg_color
        
        # Calculate pulse intensity (0-1 range)
        pulse_intensity = (math.sin(self.pulse_phase) + 1) / 2.0
        
        # Calculate distance-based color (green to red gradient)
        distance_ratio = (self.current_distance - self.min_distance) / (self.max_distance - self.min_distance)
        distance_ratio = max(0, min(1, distance_ratio))
        
        # Create a color gradient: red (close) -> yellow -> green (far)
        if distance_ratio < 0.5:  # Red to yellow
            red = 255
            green = int(255 * (distance_ratio * 2))
            blue = 0
        else:  # Yellow to green
            red = int(255 * (1 - (distance_ratio - 0.5) * 2))
            green = 255
            blue = 0
        
        base_color = (blue, green, red)  # BGR format for OpenCV
        
        # Draw radar-like circular grid
        center_x = self.width // 2
        center_y = self.height // 2
        max_radius = min(center_x, center_y) - 10
        
        # Draw concentric circles
        for i in range(1, 4):
            radius = max_radius * (i / 3)
            cv2.circle(self.pulse_image, (center_x, center_y), int(radius), self.grid_color, 1)
        
        # Draw cardinal direction indicators
        for i, direction in enumerate(["N", "E", "S", "W"]):
            angle = math.pi/2 * i
            offset_x = int(max_radius * 1.1 * math.sin(angle))
            offset_y = int(-max_radius * 1.1 * math.cos(angle))
            pos_x = center_x + offset_x
            pos_y = center_y + offset_y
            
            # Highlight the current direction
            text_color = self.text_color
            if direction == self.current_direction:
                text_color = (base_color[0], base_color[1], base_color[2])
                
            cv2.putText(self.pulse_image, direction, (pos_x-5, pos_y+5), 
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, text_color, 1)
        
        # Draw the conical visualization for the current direction
        angle_map = {
            "N": 0, "NE": math.pi/4, "E": math.pi/2, "SE": 3*math.pi/4,
            "S": math.pi, "SW": 5*math.pi/4, "W": 3*math.pi/2, "NW": 7*math.pi/4
        }
        
        base_angle = angle_map.get(self.current_direction, 0)
        cone_width = math.pi / 3  # 60 degrees wide cone
        
        # Adjust color intensity based on pulse
        color_intensity = int(150 + 105 * pulse_intensity)  # 150-255 range
        pulse_color = (
            int(base_color[0] * color_intensity / 255),
            int(base_color[1] * color_intensity / 255),
            int(base_color[2] * color_intensity / 255)
        )
        
        # Draw the cone
        segments = 40
        for i in range(segments):
            segment_angle = base_angle + (cone_width * (i / segments - 0.5))
            
            # Calculate start point (center)
            start_x = center_x
            start_y = center_y
            
            # Calculate end point on circumference
            end_radius = max_radius * pulse_intensity
            end_x = int(center_x + math.sin(segment_angle) * end_radius)
            end_y = int(center_y - math.cos(segment_angle) * end_radius)
            
            # Draw line segment
            cv2.line(self.pulse_image, (start_x, start_y), (end_x, end_y), pulse_color, 2)
        
        # Fill the cone area
        points = np.array([
            [center_x, center_y], 
            [int(center_x + math.sin(base_angle - cone_width/2) * max_radius * pulse_intensity), 
             int(center_y - math.cos(base_angle - cone_width/2) * max_radius * pulse_intensity)],
            [int(center_x + math.sin(base_angle + cone_width/2) * max_radius * pulse_intensity), 
             int(center_y - math.cos(base_angle + cone_width/2) * max_radius * pulse_intensity)]
        ], np.int32)
        
        points = points.reshape((-1, 1, 2))
        
        # Use a semi-transparent fill
        overlay = self.pulse_image.copy()
        cv2.fillPoly(overlay, [points], pulse_color)
        cv2.addWeighted(overlay, 0.5, self.pulse_image, 0.5, 0, self.pulse_image)
        
        # Add distance text
        distance_text = f"{self.current_distance:.2f}m"
        cv2.putText(self.pulse_image, distance_text, 
                    (5, self.height - 10),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, self.text_color, 1)
        
        return self.pulse_image 