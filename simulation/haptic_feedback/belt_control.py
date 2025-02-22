import serial
import utils.config as config

# Initialize serial connection
ser = serial.Serial(config.SERIAL_PORT, config.BAUD_RATE)
def trigger_haptic_feedback(sectors):
    """Activate haptic motors based on obstacle distances."""
    motor_map = {"N": 0, "NE": 1, "NW": 2}  # Motor IDs
    for sector, distance in sectors.items():
        if distance and distance < config.WARNING_DISTANCE:
            motor_id = motor_map[sector]
            # Intensity increases as distance decreases
            intensity = int(255 * (1 - distance / config.WARNING_DISTANCE))
            intensity = max(0, min(255, intensity))  # Clamp to 0-255
            ser.write(f"{motor_id},{intensity}\n".encode())