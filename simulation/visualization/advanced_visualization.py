"""
Advanced Proximity Visualization with Pygame

This module provides an enhanced visualization of proximity and directional data
using Pygame for smoother animations and better visual effects.
"""
import pygame
import numpy as np
import math
import threading
import time
from typing import Dict, Tuple, Optional

class AdvancedVisualization:
    """
    Creates an enhanced visualization with a conical directional display
    and proximity bar using Pygame.
    """
    
    def __init__(self, 
                width: int = 800, 
                height: int = 500,
                min_distance: float = 0.5,
                max_distance: float = 5.0):
        """
        Initialize the advanced visualization.
        
        Args:
            width (int): Width of the visualization window
            height (int): Height of the visualization window
            min_distance (float): Minimum distance in meters (closest objects)
            max_distance (float): Maximum distance in meters (furthest objects)
        """
        self.width = width
        self.height = height
        self.min_distance = min_distance
        self.max_distance = max_distance
        
        # Current distance and direction values
        self.current_distance = max_distance
        self.current_direction = "N"
        
        # Directions and their angles (in degrees)
        self.directions = ["N", "NE", "E", "SE", "S", "SW", "W", "NW"]
        self.angle_lookup = {
            "N": -90, "NE": -45, "E": 0, "SE": 45,
            "S": 90, "SW": 135, "W": 180, "NW": -135
        }
        
        # Sensor states for each direction
        self.sensor_states = {dir: {"length": 0, "color": (0, 255, 0)} for dir in self.directions}
        
        # Animation variables
        self.pulse_timers = {dir: 0 for dir in self.directions}
        self.bg_angle = 0
        
        # Initialize Pygame
        pygame.init()
        self.screen = pygame.display.set_mode((width, height))
        pygame.display.set_caption("Blind Navigation Visualization")
        self.clock = pygame.time.Clock()
        self.font = pygame.font.SysFont("Arial", 18)
        
        # Layout dimensions
        # Left side: Conical visualization
        self.radar_width = width * 2 // 3
        self.radar_height = height
        
        # Right side: Proximity bar
        self.bar_width = 80
        self.bar_height = height - 100
        self.bar_x = self.radar_width + (width - self.radar_width - self.bar_width) // 2
        self.bar_y = 50
        self.bar_segments = 10
        self.segment_height = self.bar_height // self.bar_segments
        
        # Center coordinates for radar
        self.cx = self.radar_width // 2
        self.cy = self.radar_height // 2
        
        # Start visualization thread
        self.running = False
        self.thread = None
    
    def start(self):
        """Start the visualization in a separate thread."""
        if not self.running:
            self.running = True
            self.thread = threading.Thread(target=self.run)
            self.thread.daemon = True
            self.thread.start()
    
    def stop(self):
        """Stop the visualization thread."""
        self.running = False
        if self.thread:
            self.thread.join(timeout=1.0)
    
    def update(self, distance: float, direction: str = "N") -> None:
        """
        Update the visualization with new distance and direction data.
        
        Args:
            distance (float): Current distance to nearest object in meters
            direction (str): Cardinal direction (N, NE, E, SE, S, SW, W, NW)
        """
        # Clamp distance to valid range
        self.current_distance = max(self.min_distance, min(self.max_distance, distance))
        
        # Update direction if valid
        if direction in self.directions:
            self.current_direction = direction
    
    def lerp(self, a, b, t):
        """Linear interpolation between a and b by factor t."""
        return a + (b - a) * t
    
    def distance_to_color(self, distance):
        """Convert distance to color (green->yellow->orange->red)."""
        # Normalize distance to 0-1 range (inverted)
        norm_dist = 1.0 - min(1.0, max(0.0, (distance - self.min_distance) / 
                                       (self.max_distance - self.min_distance)))
        
        if norm_dist < 0.3:  # Far (green)
            return (0, 255, 0)
        elif norm_dist < 0.6:  # Medium (yellow)
            ratio = (norm_dist - 0.3) / 0.3
            r = int(ratio * 255)
            return (r, 255, 0)
        else:  # Close (orange to red)
            ratio = (norm_dist - 0.6) / 0.4
            g = int(255 * (1 - ratio))
            return (255, g, 0)
    
    def distance_to_length(self, distance):
        """Convert distance to cone length (closer = longer)."""
        norm_dist = 1.0 - min(1.0, max(0.0, (distance - self.min_distance) / 
                                     (self.max_distance - self.min_distance)))
        return int(120 * norm_dist)
    
    def get_offset(self, angle_deg, dist):
        """Calculate offset position based on angle and distance."""
        angle_rad = math.radians(angle_deg)
        return (int(self.cx + dist * math.cos(angle_rad)), 
                int(self.cy + dist * math.sin(angle_rad)))
    
    def draw_background(self):
        """Draw the radar background with rotating grid."""
        # Draw title for conical radar section
        title = self.font.render("DIRECTIONAL RADAR", True, (200, 200, 200))
        self.screen.blit(title, (self.cx - title.get_width() // 2, 15))
        
        # Draw direction indicator text
        direction_text = f"DIRECTION: {self.current_direction}"
        direction_label = self.font.render(direction_text, True, (200, 200, 200))
        self.screen.blit(direction_label, (self.cx - direction_label.get_width() // 2, 40))
        
        # Draw concentric circles
        radar_radius = min(self.cx, self.cy) - 60
        for i, r in enumerate(range(radar_radius // 3, radar_radius + 1, radar_radius // 3)):
            # Draw circle with grey color
            pygame.draw.circle(self.screen, (50, 50, 50), (self.cx, self.cy), r, 1)
            
            # Add distance labels at each circle
            if i < 3:
                distance_value = self.min_distance + (i+1) * ((self.max_distance - self.min_distance) / 3)
                dist_text = f"{distance_value:.1f}m"
                dist_label = self.font.render(dist_text, True, (150, 150, 150))
                # Position at bottom of circle
                self.screen.blit(dist_label, (self.cx - dist_label.get_width() // 2, 
                                            self.cy + r - dist_label.get_height() // 2))
        
        # Draw radial lines
        for i in range(0, 360, 30):
            angle = i + self.bg_angle
            x, y = self.get_offset(angle, radar_radius)
            pygame.draw.line(self.screen, (50, 50, 50), (self.cx, self.cy), (x, y), 1)
        
        # Rotate background slightly each frame
        self.bg_angle = (self.bg_angle + 0.1) % 360
    
    def draw_center(self):
        """Draw pulsing center point."""
        pulse = 5 * math.sin(pygame.time.get_ticks() * 0.005) + 15
        pygame.draw.circle(self.screen, (100, 100, 100), (self.cx, self.cy), int(pulse))
    
    def draw_directional_cones(self, dt):
        """Draw conical visualizations for each direction."""
        radar_radius = min(self.cx, self.cy) - 60
        
        # We'll draw all cones but highlight the current direction
        for direction in self.directions:
            # Use current distance for all directions, but could be modified to have different
            # distances per direction if sensor data was available
            dist = self.current_distance
            
            # Update state with smooth transitions
            state = self.sensor_states[direction]
            target_length = self.distance_to_length(dist)
            state["length"] = self.lerp(state["length"], target_length, 0.2)
            
            target_color = self.distance_to_color(dist)
            state["color"] = tuple(int(self.lerp(c1, c2, 0.2)) for c1, c2 in zip(state["color"], target_color))
            
            # Update pulse animation
            self.pulse_timers[direction] += dt * 2
            
            # Adjust length with pulsing effect
            pulse_factor = 1.0
            if direction == self.current_direction:
                # Only active direction should pulse
                pulse_factor = 1 + 0.3 * math.sin(self.pulse_timers[direction] * math.pi)
            
            final_length = int(state["length"] * pulse_factor)
            
            # Calculate cone vertices
            inner_offset = 50
            outer_offset = inner_offset + final_length
            half_angle = 20
            inner_left = self.get_offset(self.angle_lookup[direction] - half_angle, inner_offset)
            inner_right = self.get_offset(self.angle_lookup[direction] + half_angle, inner_offset)
            outer_left = self.get_offset(self.angle_lookup[direction] - half_angle, outer_offset)
            outer_right = self.get_offset(self.angle_lookup[direction] + half_angle, outer_offset)
            vertices = [inner_left, outer_left, outer_right, inner_right]
            
            # Draw cone with glow effect for active direction
            if direction == self.current_direction:
                # Create glow surface
                glow_surface = pygame.Surface((self.radar_width, self.radar_height), pygame.SRCALPHA)
                glow_color = state["color"] + (100,)  # Add alpha
                glow_vertices = [(int(self.cx + (vx - self.cx) * 1.1), int(self.cy + (vy - self.cy) * 1.1)) 
                                for vx, vy in vertices]
                pygame.draw.polygon(glow_surface, glow_color, glow_vertices)
                self.screen.blit(glow_surface, (0, 0))
                
                # Draw solid cone
                pygame.draw.polygon(self.screen, state["color"], vertices)
                
                # Add distance label
                label_text = f"{direction}: {dist:.2f}m"
                label = self.font.render(label_text, True, (255, 255, 255))
                self.screen.blit(label, label.get_rect(center=self.get_offset(
                    self.angle_lookup[direction], outer_offset + 20)))
            else:
                # Draw inactive directions with reduced opacity
                pygame.draw.polygon(self.screen, tuple(int(c * 0.3) for c in state["color"]), vertices)
        
        # Draw cardinal direction indicators
        for i, direction in enumerate(["N", "E", "S", "W"]):
            angle = i * 90 - 90  # Convert to proper angle (N = -90, E = 0, etc.)
            offset_x = int(radar_radius * 1.1 * math.cos(math.radians(angle)))
            offset_y = int(radar_radius * 1.1 * math.sin(math.radians(angle)))
            pos_x = self.cx + offset_x
            pos_y = self.cy + offset_y
            
            # Highlight current direction
            text_color = (255, 255, 255) if direction == self.current_direction else (150, 150, 150)
            label = self.font.render(direction, True, text_color)
            self.screen.blit(label, (pos_x - label.get_width() // 2, pos_y - label.get_height() // 2))
    
    def draw_proximity_bar(self):
        """Draw the proximity bar visualization on the right side."""
        # Draw bar title
        title = self.font.render("PROXIMITY", True, (200, 200, 200))
        self.screen.blit(title, (self.bar_x + self.bar_width // 2 - title.get_width() // 2, 15))
        
        # Draw outer border with curved top
        pygame.draw.rect(self.screen, (70, 70, 70), 
                        (self.bar_x, self.bar_y, self.bar_width, self.bar_height), 2)
        
        # Draw curved top
        radius = self.bar_width // 2
        pygame.draw.circle(self.screen, (70, 70, 70), 
                          (self.bar_x + radius, self.bar_y), radius, 2)
        
        # Draw bar background
        pygame.draw.rect(self.screen, (30, 30, 30), 
                        (self.bar_x + 2, self.bar_y + 2, self.bar_width - 4, self.bar_height - 4))
        
        # Calculate fill level based on current distance
        if self.current_distance >= self.max_distance:
            fill_segments = 0
        else:
            # Convert distance to fill ratio (inverse relationship)
            fill_ratio = 1.0 - ((self.current_distance - self.min_distance) / 
                               (self.max_distance - self.min_distance))
            fill_segments = int(fill_ratio * self.bar_segments)
            fill_segments = min(self.bar_segments, max(0, fill_segments))
        
        # Draw segments with gradient
        for i in range(fill_segments):
            y_pos = self.bar_y + (self.bar_segments - i - 1) * self.segment_height
            
            # Calculate color based on segment position
            rel_pos = i / self.bar_segments
            if rel_pos < 0.33:  # Green zone (far)
                color = (0, 255, 0)
            elif rel_pos < 0.66:  # Yellow zone (medium)
                blend = (rel_pos - 0.33) / 0.33
                green = 255
                red = int(255 * blend)
                color = (red, green, 0)
            else:  # Red zone (close)
                blend = (rel_pos - 0.66) / 0.34
                green = int(255 * (1 - blend))
                red = 255
                color = (red, green, 0)
            
            # Draw the segment
            pygame.draw.rect(self.screen, color, 
                            (self.bar_x + 4, y_pos, self.bar_width - 8, self.segment_height))
            
            # Add segment divider line
            pygame.draw.line(self.screen, (40, 40, 40), 
                            (self.bar_x, y_pos), 
                            (self.bar_x + self.bar_width, y_pos), 1)
        
        # Fill curved top if any segments are filled
        if fill_segments > 0:
            # Determine color for the top segment
            if fill_segments < self.bar_segments // 3:
                top_color = (0, 255, 0)  # Green
            elif fill_segments < 2 * self.bar_segments // 3:
                top_color = (255, 255, 0)  # Yellow
            else:
                top_color = (255, 0, 0)  # Red
                
            # Draw filled circle for the top
            pygame.draw.circle(self.screen, top_color, 
                             (self.bar_x + radius, self.bar_y), radius - 4)
        
        # Draw distance scale markers
        for i in range(6):
            y_pos = self.bar_y + i * (self.bar_height / 5)
            distance_value = self.max_distance - i * (self.max_distance - self.min_distance) / 5
            
            # Draw tick mark
            pygame.draw.line(self.screen, (150, 150, 150), 
                            (self.bar_x - 5, y_pos), 
                            (self.bar_x, y_pos), 1)
            
            # Add distance label
            if i % 2 == 0:  # Only show every other label to avoid crowding
                label = self.font.render(f"{distance_value:.1f}m", True, (150, 150, 150))
                self.screen.blit(label, (self.bar_x - label.get_width() - 10, y_pos - label.get_height() // 2))
        
        # Add current distance text
        dist_text = self.font.render(f"{self.current_distance:.2f}m", True, (255, 255, 255))
        self.screen.blit(dist_text, (self.bar_x + self.bar_width // 2 - dist_text.get_width() // 2, 
                                   self.bar_y + self.bar_height + 15))
    
    def render_to_image(self) -> np.ndarray:
        """
        Render the visualization to a NumPy array suitable for OpenCV display.
        
        Returns:
            np.ndarray: Image of the visualization
        """
        # Convert Pygame surface to numpy array
        pygame_surface = pygame.display.get_surface()
        raw_buffer = pygame.image.tostring(pygame_surface, "RGB")
        image = np.frombuffer(raw_buffer, dtype=np.uint8).reshape(
            (self.height, self.width, 3))
        
        # OpenCV uses BGR, but Pygame uses RGB
        image = image[:, :, ::-1].copy()  # Convert RGB to BGR and create a copy
        
        return image
    
    def run(self):
        """Main visualization loop."""
        while self.running:
            dt = self.clock.tick(60) / 1000.0
            
            # Handle Pygame events
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self.running = False
            
            # Clear screen
            self.screen.fill((18, 18, 18))
            
            # Draw visualization elements
            self.draw_background()
            self.draw_center()
            self.draw_directional_cones(dt)
            self.draw_proximity_bar()
            
            # Update display
            pygame.display.flip() 