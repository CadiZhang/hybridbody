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
import os
import torch
import cv2
import numpy as np
import time
from typing import Tuple

class DepthEstimator:
    """
    Handles depth estimation using MiDaS models.
    
    This class provides a simple interface to the MiDaS depth estimation models,
    handling model loading, input preprocessing, and output postprocessing.
    """
    
    def __init__(self, model_type: str = "MiDaS_small", device: str = "cpu"):
        """
        Initialize the depth estimator with the specified model.
        
        Args:
            model_type (str): Which MiDaS model to use. Default is "MiDaS_small"
                which is the most compatible with torch.hub.
            device (str): Device to run inference on ("cpu" or "cuda")
        
        Raises:
            RuntimeError: If model loading fails
        """
        self.model_type = model_type
        self.device = device
        
        # Create models directory if it doesn't exist
        os.makedirs("models", exist_ok=True)
        
        # Load the model
        print(f"Loading MiDaS model: {model_type}")
        self.model = self._load_model()
        
        # Set input size based on model
        self.input_width = 256
        self.input_height = 256
        
        # Initialize depth scaling parameters (to be calibrated)
        self.depth_scale_factor = 3.0
        self.depth_min = 0.1
        self.depth_max = 10.0
        
        print(f"Depth estimator initialized with model: {model_type}")
    
    def _load_model(self) -> torch.nn.Module:
        """
        Load the MiDaS model from torch hub.
        
        Returns:
            torch.nn.Module: The loaded MiDaS model
            
        Raises:
            RuntimeError: If model loading fails
        """
        try:
            # Load MiDaS model from torch hub
            model = torch.hub.load("intel-isl/MiDaS", self.model_type)
            model.to(self.device)
            model.eval()
            return model
        except Exception as e:
            raise RuntimeError(f"Failed to load MiDaS model: {e}")
    
    def preprocess(self, frame: np.ndarray) -> torch.Tensor:
        """
        Preprocess an image for input to the MiDaS model.
        
        Args:
            frame (np.ndarray): Input RGB image (HxWx3)
            
        Returns:
            torch.Tensor: Preprocessed tensor ready for model input
        """
        # Resize to input dimensions
        img = cv2.resize(frame, (self.input_width, self.input_height))
        
        # Convert from BGR (OpenCV) to RGB
        img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB) / 255.0
        
        # Normalize using ImageNet mean and std
        mean = np.array([0.485, 0.456, 0.406])
        std = np.array([0.229, 0.224, 0.225])
        img = (img - mean) / std
        
        # Convert to tensor and add batch dimension
        img = torch.from_numpy(img).float().permute(2, 0, 1).unsqueeze(0)
        
        return img.to(self.device)
    
    def postprocess(self, depth: torch.Tensor, original_size: Tuple[int, int]) -> np.ndarray:
        """
        Postprocess the model output to a usable depth map.
        
        Args:
            depth (torch.Tensor): Raw depth output from the model
            original_size (Tuple[int, int]): Original image size (height, width)
            
        Returns:
            np.ndarray: Processed depth map resized to original image dimensions
        """
        # Convert to numpy and reshape
        depth = depth.squeeze().cpu().numpy()
        
        # Resize to original resolution
        depth = cv2.resize(depth, (original_size[1], original_size[0]))
        
        # Normalize depth values to 0-1 range
        depth_min = depth.min()
        depth_max = depth.max()
        if depth_max > depth_min:
            depth = (depth - depth_min) / (depth_max - depth_min)
        else:
            depth = np.zeros_like(depth)
        
        # Invert the depth map so that smaller values represent closer objects
        depth = 1.0 - depth
        
        return depth
    
    def estimate_depth(self, frame: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
        """
        Estimate depth from a single RGB image.
        
        Args:
            frame (np.ndarray): Input RGB image
            
        Returns:
            Tuple[np.ndarray, np.ndarray]: 
                - Normalized depth map (0-1 range)
                - Metric depth map (in approximate meters)
        """
        # Record original size
        original_size = frame.shape[:2]  # (height, width)
        
        # Start timing
        start_time = time.time()
        
        try:
            # Preprocess the image
            input_tensor = self.preprocess(frame)
            
            # Run inference
            with torch.no_grad():
                prediction = self.model(input_tensor)
            
            # Postprocess the depth map
            depth_map = self.postprocess(prediction, original_size)
            
        except Exception as e:
            print(f"Error during depth estimation: {e}")
            # Create a fallback depth map (gradient from top to bottom)
            h, w = original_size
            depth_map = np.zeros((h, w), dtype=np.float32)
            for y in range(h):
                depth_map[y, :] = y / h  # Simple gradient
        
        # Convert to metric depth (approximate)
        metric_depth = self.depth_min + depth_map * (self.depth_max - self.depth_min)
        metric_depth = metric_depth * self.depth_scale_factor
        
        # Calculate and print inference time occasionally
        inference_time = time.time() - start_time
        if int(time.time()) % 10 == 0:  # Every 10 seconds
            print(f"Depth inference time: {inference_time*1000:.1f}ms")
        
        return depth_map, metric_depth
    
    def visualize_depth(self, depth_map: np.ndarray) -> np.ndarray:
        """
        Create a colored visualization of the depth map.
        
        Args:
            depth_map (np.ndarray): Normalized depth map (0-1 range)
            
        Returns:
            np.ndarray: Colorized depth map for visualization
        """
        # Apply colormap for visualization (TURBO gives good depth perception)
        colored_depth = cv2.applyColorMap(
            (depth_map * 255).astype(np.uint8), 
            cv2.COLORMAP_TURBO
        )
        
        return colored_depth
    
    def calibrate(self, known_distance: float, depth_value: float):
        """
        Calibrate the depth scale factor using a known distance.
        
        Args:
            known_distance (float): Actual distance to an object in meters
            depth_value (float): Measured depth value from the model
        """
        # Update the scale factor based on the calibration
        self.depth_scale_factor = known_distance / depth_value
        print(f"Depth scale factor calibrated to: {self.depth_scale_factor:.3f}") 