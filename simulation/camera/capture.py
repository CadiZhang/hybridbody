import cv2
import utils.config as config

def capture_frame():
    """Capture a single frame from the camera."""
    cap = cv2.VideoCapture(config.CAMERA_INDEX)
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, config.FRAME_WIDTH)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, config.FRAME_HEIGHT)
    ret, frame = cap.read()
    cap.release()
    if not ret:
        raise Exception("Failed to capture frame from camera")
    return frame