import cv2
from camera.capture import capture_frame
from depth_estimation.midas import estimate_depth
from obstacle_detection.ground_plane import estimate_ground_plane
from obstacle_detection.segmentation import segment_obstacles
from utils.helpers import map_obstacles_to_sectors
from haptic_feedback.belt_control import trigger_haptic_feedback
from simulation.visualizer import update_simulation
import utils.config as config

def main():
    while True:
        # Capture and process frame
        frame = capture_frame()
        depth_map = estimate_depth(frame)
        ground_mask = estimate_ground_plane(depth_map)
        obstacles = segment_obstacles(depth_map, ground_mask)
        # Map obstacles to sectors and trigger feedback
        sectors = map_obstacles_to_sectors(obstacles)
        trigger_haptic_feedback(sectors)
        # Update simulation if enabled
        if config.SIMULATION_ENABLED:
            update_simulation(obstacles)
        # Allow exit with 'q' and handle rendering
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("Shutting down...")
    except Exception as e:
        print(f"Error: {e}")