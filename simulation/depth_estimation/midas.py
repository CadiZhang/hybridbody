"""
MiDaS Depth Estimation Module

This module handles monocular depth estimation using the MiDaS model.
It provides functionality to:
1. Load and initialize the MiDaS model
2. Process frames to generate depth maps
3. Convert relative depth to metric depth estimates

MiDaS models estimate depth from a single RGB image without requiring
specialized depth sensors or stereo cameras.
"""

#Code for midas swin Model
import os
import torch
import cv2
import numpy as np
from typing import Tuple
from pathlib import Path

class DepthEstimator:
    def __init__(self, model_type: str = "dpt_swin2_tiny_256", device: str = "cuda" if torch.cuda.is_available() else "cpu"):
        self.model_type = model_type
        self.device = device

        # Paths
        self.model_path = "models/dpt_swin2_tiny_256.pt"
        self.midas_dir = Path("MiDaS")  # Path to your cloned MiDaS repo

        # Load model
        print(f"Loading DPT model: {self.model_type}")
        self.model, self.transform, self.net_w, self.net_h = self._load_model()

        self.model.eval().to(self.device)

        # Depth scaling & filtering
        self.depth_scale_factor = 3.0
        self.depth_min = 0.5
        self.depth_max = 10.0

        from .normalize import EMADepthFilter
        self.depth_filter = EMADepthFilter(alpha=0.2)

        self.calibration_file = "calibration.json"
        self.load_calibration()
        print("Depth estimator initialized.")

    def _load_model(self):
        import sys
        from pathlib import Path

        sys.path.append(str(self.midas_dir.resolve()))
        sys.path.append(str(Path("models").resolve()))

        from midas.load_model import load_model

        model, transform, net_w, net_h = load_model(
            model_path=self.model_path,
            model_type=self.model_type,
            optimize=False,
            device=self.device,
        )
        return model, transform, net_w, net_h


    def load_calibration(self):
        try:
            import json
            if os.path.exists(self.calibration_file):
                with open(self.calibration_file, 'r') as f:
                    data = json.load(f)
                    self.depth_scale_factor = data['scale_factor']
                    print(f"Loaded calibration: scale_factor = {self.depth_scale_factor}")
        except Exception as e:
            print(f"Could not load calibration: {e}")

    def save_calibration(self):
        try:
            import json
            with open(self.calibration_file, 'w') as f:
                json.dump({'scale_factor': self.depth_scale_factor}, f)
                print(f"Saved calibration: scale_factor = {self.depth_scale_factor}")
        except Exception as e:
            print(f"Could not save calibration: {e}")

    def calibrate(self, known_distance: float, depth_value: float):
        self.depth_scale_factor = known_distance / depth_value
        print(f"Calibrated scale factor: {self.depth_scale_factor:.3f}")
        self.save_calibration()

    def estimate_depth(self, frame: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
        original_size = frame.shape[:2]
        try:
            img_input = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB) / 255.0
            sample = {"image": img_input}
            sample = self.transform(sample)
            image = sample["image"].unsqueeze(0).to(self.device)

            with torch.no_grad():
                prediction = self.model(image)

            prediction = prediction.squeeze().cpu().numpy()
            depth_map = cv2.resize(prediction, (original_size[1], original_size[0]))
            depth_map = (depth_map - depth_map.min()) / (depth_map.max() - depth_map.min() + 1e-6)
            depth_map = 1.0 - depth_map  # Invert for closer = brighter

            # Apply EMA and scale
            depth_map = self.depth_filter.filter(depth_map)
            metric_depth = depth_map * self.depth_scale_factor
            metric_depth = np.clip(metric_depth, self.depth_min, self.depth_max)

        except Exception as e:
            print(f"Error during depth estimation: {e}")
            h, w = original_size
            depth_map = np.zeros((h, w), dtype=np.float32)
            metric_depth = np.zeros_like(depth_map)

        return depth_map, metric_depth

    def visualize_depth(self, depth_map: np.ndarray) -> np.ndarray:
        return cv2.applyColorMap((depth_map * 255).astype(np.uint8), cv2.COLORMAP_TURBO)

    def compute_confidence(self, depth_map: np.ndarray, window_size: int = 5) -> np.ndarray:
        local_var = cv2.blur(depth_map**2, (window_size, window_size)) - \
                    cv2.blur(depth_map, (window_size, window_size))**2
        confidence = 1 / (1 + local_var)
        confidence = (confidence - confidence.min()) / (confidence.max() - confidence.min() + 1e-6)
        return confidence

    def apply_confidence_filter(self, depth_map: np.ndarray, confidence: np.ndarray, threshold: float = 0.5) -> np.ndarray:
        mask = confidence > threshold
        filtered_depth = depth_map.copy()
        filtered_depth[~mask] = cv2.blur(depth_map, (5, 5))[~mask]
        return filtered_depth


# import os
# import torch
# import cv2
# import numpy as np
# import time
# from typing import Tuple

# class DepthEstimator:
#     """
#     Handles depth estimation using MiDaS models.
    
#     This class provides a simple interface to the MiDaS depth estimation models,
#     handling model loading, input preprocessing, and output postprocessing.
#     """
    
#     def __init__(self, model_type: str = "MiDaS_small", device: str = "cpu"):
#         """
#         Initialize the depth estimator with the specified model.
        
#         Args:
#             model_type (str): Which MiDaS model to use. Default is "MiDaS_small"
#                 which is the most compatible with torch.hub.
#             device (str): Device to run inference on ("cpu" or "cuda")
        
#         Raises:
#             RuntimeError: If model loading fails
#         """
#         self.model_type = model_type
#         self.device = device
        
#         # Create models directory if it doesn't exist
#         os.makedirs("models", exist_ok=True)
        
#         # Load the model
#         print(f"Loading MiDaS model: {model_type}")
#         self.model = self._load_model()
        
#         # Set input size based on model
#         self.input_width = 256
#         self.input_height = 256
        
#         # Initialize depth scaling parameters with safer thresholds
#         self.depth_scale_factor = 3.0
#         self.depth_min = 0.5  # Changed to 0.5m (50cm) for safety
#         self.depth_max = 10.0  # Keep max at 10m
        
#         # Add EMA filter
#         from .normalize import EMADepthFilter
#         self.depth_filter = EMADepthFilter(alpha=0.2)
        
#         # Load calibration if exists
#         self.calibration_file = "calibration.json"
#         self.load_calibration()
        
#         print(f"Depth estimator initialized with model: {model_type}")
    
#     def _load_model(self) -> torch.nn.Module:
#         """
#         Load the MiDaS model from torch hub.
        
#         Returns:
#             torch.nn.Module: The loaded MiDaS model
            
#         Raises:
#             RuntimeError: If model loading fails
#         """
#         try:
#             # Load MiDaS model from torch hub
#             model = torch.hub.load("intel-isl/MiDaS", self.model_type)
#             model.to(self.device)
#             model.eval()
#             return model
#         except Exception as e:
#             raise RuntimeError(f"Failed to load MiDaS model: {e}")
    
#     def preprocess(self, frame: np.ndarray) -> torch.Tensor:
#         """
#         Preprocess an image for input to the MiDaS model.
        
#         Args:
#             frame (np.ndarray): Input RGB image (HxWx3)
            
#         Returns:
#             torch.Tensor: Preprocessed tensor ready for model input
#         """
#         # Resize to input dimensions
#         img = cv2.resize(frame, (self.input_width, self.input_height))
        
#         # Convert from BGR (OpenCV) to RGB
#         img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB) / 255.0
        
#         # Normalize using ImageNet mean and std
#         mean = np.array([0.485, 0.456, 0.406])
#         std = np.array([0.229, 0.224, 0.225])
#         img = (img - mean) / std
        
#         # Convert to tensor and add batch dimension
#         img = torch.from_numpy(img).float().permute(2, 0, 1).unsqueeze(0)
        
#         return img.to(self.device)
    
#     def postprocess(self, depth: torch.Tensor, original_size: Tuple[int, int]) -> np.ndarray:
#         """
#         Postprocess the model output to a usable depth map.
        
#         Args:
#             depth (torch.Tensor): Raw depth output from the model
#             original_size (Tuple[int, int]): Original image size (height, width)
            
#         Returns:
#             np.ndarray: Processed depth map resized to original image dimensions
#         """
#         # Convert to numpy and reshape
#         depth = depth.squeeze().cpu().numpy()
        
#         # Resize to original resolution
#         depth = cv2.resize(depth, (original_size[1], original_size[0]))
        
#         # Normalize depth values to 0-1 range
#         depth_min = depth.min()
#         depth_max = depth.max()
#         if depth_max > depth_min:
#             depth = (depth - depth_min) / (depth_max - depth_min)
#         else:
#             depth = np.zeros_like(depth)
        
#         # Invert the depth map so that smaller values represent closer objects
#         depth = 1.0 - depth
        
#         return depth
    
#     def load_calibration(self):
#         """Load calibration from file"""
#         try:
#             import json
#             if os.path.exists(self.calibration_file):
#                 with open(self.calibration_file, 'r') as f:
#                     data = json.load(f)
#                     self.depth_scale_factor = data['scale_factor']
#                     print(f"Loaded calibration: scale_factor = {self.depth_scale_factor}")
#         except Exception as e:
#             print(f"Could not load calibration: {e}")

#     def save_calibration(self):
#         """Save calibration to file"""
#         try:
#             import json
#             with open(self.calibration_file, 'w') as f:
#                 json.dump({'scale_factor': self.depth_scale_factor}, f)
#                 print(f"Saved calibration: scale_factor = {self.depth_scale_factor}")
#         except Exception as e:
#             print(f"Could not save calibration: {e}")

#     def calibrate(self, known_distance: float, depth_value: float):
#         """Calibrate depth scaling"""
#         self.depth_scale_factor = known_distance / depth_value
#         print(f"Depth scale factor calibrated to: {self.depth_scale_factor:.3f}")
#         self.save_calibration()  # Save after calibration

#     def estimate_depth(self, frame: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
#         """
#         Estimate depth with EMA stabilization
#         """
#         # Record original size
#         original_size = frame.shape[:2]
        
#         try:
#             # Preprocess the image
#             input_tensor = self.preprocess(frame)
            
#             # Run inference
#             with torch.no_grad():
#                 prediction = self.model(input_tensor)
            
#             # Initial postprocessing
#             depth_map = self.postprocess(prediction, original_size)
            
#             # Apply EMA filtering for stability
#             depth_map = self.depth_filter.filter(depth_map)
            
#             # Convert to metric depth with safety threshold
#             metric_depth = depth_map * self.depth_scale_factor
#             metric_depth = np.clip(metric_depth, self.depth_min, self.depth_max)
            
#         except Exception as e:
#             print(f"Error during depth estimation: {e}")
#             # Create fallback depth map
#             h, w = original_size
#             depth_map = np.zeros((h, w), dtype=np.float32)
#             metric_depth = np.zeros_like(depth_map)
        
#         return depth_map, metric_depth
    
#     def visualize_depth(self, depth_map: np.ndarray) -> np.ndarray:
#         """
#         Create a colored visualization of the depth map.
        
#         Args:
#             depth_map (np.ndarray): Normalized depth map (0-1 range)
            
#         Returns:
#             np.ndarray: Colorized depth map for visualization
#         """
#         # Apply colormap for visualization (TURBO gives good depth perception)
#         colored_depth = cv2.applyColorMap(
#             (depth_map * 255).astype(np.uint8), 
#             cv2.COLORMAP_TURBO
#         )
        
#         return colored_depth
    
#     def compute_confidence(self, depth_map: np.ndarray, window_size: int = 5) -> np.ndarray:
#         """
#         Compute confidence map based on local depth consistency.
#         Lower variance = higher confidence.
#         """
#         # Calculate local variance using a sliding window
#         local_var = cv2.blur(depth_map**2, (window_size, window_size)) - \
#                     cv2.blur(depth_map, (window_size, window_size))**2
        
#         # Convert variance to confidence (inverse relationship)
#         confidence = 1 / (1 + local_var)
        
#         # Normalize confidence to 0-1
#         confidence = (confidence - confidence.min()) / \
#                     (confidence.max() - confidence.min() + 1e-6)
        
#         return confidence

#     def apply_confidence_filter(self, depth_map: np.ndarray, 
#                               confidence: np.ndarray,
#                               threshold: float = 0.5) -> np.ndarray:
#         """
#         Filter depth values based on confidence scores.
#         """
#         # Create mask for high-confidence regions
#         mask = confidence > threshold
        
#         # For low-confidence regions, use neighborhood average
#         filtered_depth = depth_map.copy()
#         filtered_depth[~mask] = cv2.blur(depth_map, (5, 5))[~mask]
        
#         return filtered_depth 