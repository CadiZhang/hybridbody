from inference_sdk import InferenceHTTPClient
import cv2
import numpy as np
import os

# Initialize the client
CLIENT = InferenceHTTPClient(
    api_url="https://serverless.roboflow.com",
    api_key="332esun3nfjDfFcA8sNp"
)

def detect_objects(image_path, model_id="chair-detection-y06j5/1", confidence_threshold=0.65):
    """
    Detect objects in an image using the Roboflow model
    
    Args:
        image_path: Path to the image file
        model_id: Roboflow model ID in format "project/version"
        confidence_threshold: Minimum confidence score to display a detection (0.0-1.0)
        
    Returns:
        image: The image with bounding boxes drawn
        predictions: The raw prediction data
    """
    # Run inference
    result = CLIENT.infer(image_path, model_id=model_id)
    
    # Load image for visualization
    image = cv2.imread(image_path)
    
    # Draw bounding boxes
    for prediction in result.get("predictions", []):
        confidence = prediction["confidence"]
        
        # Only process detections above the confidence threshold
        if confidence >= confidence_threshold:
            x, y, width, height = prediction["x"], prediction["y"], prediction["width"], prediction["height"]
            class_name = prediction["class"]
            
            # Convert coordinates to int (top-left and bottom-right points)
            x1 = int(x - width/2)
            y1 = int(y - height/2)
            x2 = int(x + width/2)
            y2 = int(y + height/2)
            
            # Draw rectangle
            cv2.rectangle(image, (x1, y1), (x2, y2), (0, 255, 0), 2)
            
            # Add label
            label = f"{class_name}: {confidence:.2f}"
            cv2.putText(image, label, (x1, y1-10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)
    
    return image, result

def display_detection(image_path, model_id="chair-detection-y06j5/1", save_output=True):
    """
    Display detection results from the Roboflow model
    
    Args:
        image_path: Path to the image
        model_id: Roboflow model ID
        save_output: Whether to save the output image
    """
    image, predictions = detect_objects(image_path, model_id)
    
    # Display
    cv2.imshow("Object Detection", image)
    cv2.waitKey(0)
    cv2.destroyAllWindows()
    
    # Save output if needed
    if save_output:
        output_dir = "detection_results"
        os.makedirs(output_dir, exist_ok=True)
        base_name = os.path.basename(image_path)
        output_path = os.path.join(output_dir, f"detected_{base_name}")
        cv2.imwrite(output_path, image)
        print(f"Results saved to {output_path}")
    
    return predictions

def process_camera_feed(model_id="chair-detection-y06j5/1", camera_id=0, save_frames=False, confidence_threshold=0.65):
    """
    Process live camera feed with Roboflow object detection
    
    Args:
        model_id: Roboflow model ID
        camera_id: Camera device ID (usually 0 for default webcam)
        save_frames: Whether to save detection frames
        confidence_threshold: Minimum confidence score to display a detection (0.0-1.0)
    """
    # Initialize webcam
    cap = cv2.VideoCapture(camera_id)
    
    if not cap.isOpened():
        print("Error: Could not open camera.")
        return
    
    output_dir = "detection_results"
    if save_frames:
        os.makedirs(output_dir, exist_ok=True)
    
    frame_count = 0
    
    print(f"Press 'q' to quit. Showing detections with confidence >= {confidence_threshold}")
    
    while True:
        # Read frame
        ret, frame = cap.read()
        if not ret:
            print("Error: Failed to capture frame.")
            break
        
        # Save frame temporarily
        temp_frame_path = "temp_frame.jpg"
        cv2.imwrite(temp_frame_path, frame)
        
        try:
            # Run inference
            result = CLIENT.infer(temp_frame_path, model_id=model_id)
            
            # Draw bounding boxes for high-confidence detections
            for prediction in result.get("predictions", []):
                confidence = prediction["confidence"]
                
                # Only process detections above the confidence threshold
                if confidence >= confidence_threshold:
                    x, y, width, height = prediction["x"], prediction["y"], prediction["width"], prediction["height"]
                    class_name = prediction["class"]
                    
                    # Convert coordinates to int
                    x1 = int(x - width/2)
                    y1 = int(y - height/2)
                    x2 = int(x + width/2)
                    y2 = int(y + height/2)
                    
                    # Draw rectangle
                    cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 2)
                    
                    # Add label
                    label = f"{class_name}: {confidence:.2f}"
                    cv2.putText(frame, label, (x1, y1-10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)
            
            # Display frame
            cv2.imshow("Object Detection - Camera Feed", frame)
            
            # Save frame if needed
            has_high_confidence_detections = any(p["confidence"] >= confidence_threshold for p in result.get("predictions", []))
            if save_frames and has_high_confidence_detections:
                output_path = os.path.join(output_dir, f"detected_frame_{frame_count}.jpg")
                cv2.imwrite(output_path, frame)
                frame_count += 1
                
        except Exception as e:
            print(f"Error during inference: {e}")
        
        # Break loop on 'q' press
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break
    
    # Clean up
    if os.path.exists(temp_frame_path):
        os.remove(temp_frame_path)
    
    cap.release()
    cv2.destroyAllWindows()

def detect_objects_in_frame(frame, model_id="chair-detection-y06j5/1", confidence_threshold=0.65):
    """
    Detect objects in a frame using the Roboflow model
    
    Args:
        frame: OpenCV image frame
        model_id: Roboflow model ID in format "project/version"
        confidence_threshold: Minimum confidence score to display a detection (0.0-1.0)
        
    Returns:
        processed_frame: The frame with bounding boxes drawn
        predictions: The raw prediction data
    """
    # Create a copy of the frame
    processed_frame = frame.copy()
    
    try:
        # Save frame temporarily
        temp_frame_path = "temp_frame.jpg"
        cv2.imwrite(temp_frame_path, frame)
        
        # Run inference using the file path
        result = CLIENT.infer(temp_frame_path, model_id=model_id)
        
        # Draw bounding boxes
        for prediction in result.get("predictions", []):
            confidence = prediction["confidence"]
            
            # Only process detections above the confidence threshold
            if confidence >= confidence_threshold:
                x, y, width, height = prediction["x"], prediction["y"], prediction["width"], prediction["height"]
                class_name = prediction["class"]
                
                # Convert coordinates to int
                x1 = int(x - width/2)
                y1 = int(y - height/2)
                x2 = int(x + width/2)
                y2 = int(y + height/2)
                
                # Draw rectangle
                cv2.rectangle(processed_frame, (x1, y1), (x2, y2), (0, 255, 0), 2)
                
                # Add label
                label = f"{class_name}: {confidence:.2f}"
                cv2.putText(processed_frame, label, (x1, y1-10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)
        
        # Remove the temporary file
        if os.path.exists(temp_frame_path):
            os.remove(temp_frame_path)
            
        return processed_frame, result
    
    except Exception as e:
        print(f"Error during object detection: {e}")
        # Try to remove temp file if it exists
        if 'temp_frame_path' in locals() and os.path.exists(temp_frame_path):
            os.remove(temp_frame_path)
        return processed_frame, {"predictions": []}

if __name__ == "__main__":
    # For camera feed:
    process_camera_feed(model_id="chair-detection-y06j5/1", confidence_threshold=0.65)
    
    # For single image (original code):
    # image_path = "path/to/your/image.jpg"
    # model_id = "chair-detection-y06j5/1"
    # predictions = display_detection(image_path, model_id)
    # print("Predictions:", predictions) 