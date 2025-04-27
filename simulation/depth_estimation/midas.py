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
        
        # Reduce input size for better performance
        self.input_width = 256  # Keep dimensions as multiples of 32 for deep learning models
        self.input_height = 192  # Keep dimensions as multiples of 32 for deep learning models
        
        # Initialize linear depth model parameters
        self.use_linear_mapping = True  # Use linear mapping by default
        self.slope = 4.0     # Initial slope for linear mapping
        self.intercept = 0.5 # Initial intercept for linear mapping
        
        # Keep inverse model parameters for backward compatibility
        self.alpha = 4.5
        self.beta = 1.8
        self.gamma = 0.05
        self.offset = -0.7
        
        # Initialize depth scaling parameters with safer thresholds
        self.depth_scale_factor = 3.0  # Keep for backward compatibility
        self.depth_min = 0.5  # Minimum depth 0.5m
        self.depth_max = 5.0  # Maximum depth 5.0m
        
        # Add EMA filter with reduced smoothing for lower latency
        from .normalize import EMADepthFilter
        self.depth_filter = EMADepthFilter(alpha=0.4)  # Increased alpha for less smoothing
        
        # Calibration data
        self.calibration_points = []  # List of (depth_value, actual_distance) tuples
        
        # Load calibration if exists
        self.calibration_file = "calibration.json"
        self.load_calibration()
        
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
    
    def load_calibration(self):
        """Load calibration from file"""
        try:
            import json
            if os.path.exists(self.calibration_file):
                with open(self.calibration_file, 'r') as f:
                    data = json.load(f)
                    
                    # Load legacy scale_factor if present
                    if 'scale_factor' in data:
                        self.depth_scale_factor = data['scale_factor']
                        print(f"Loaded legacy calibration: scale_factor = {self.depth_scale_factor}")
                    
                    # Load mapping type
                    if 'use_linear_mapping' in data:
                        self.use_linear_mapping = data['use_linear_mapping']
                    
                    # Load linear parameters if present
                    if 'slope' in data and 'intercept' in data:
                        self.slope = data['slope']
                        self.intercept = data['intercept']
                        if self.use_linear_mapping:
                            print(f"Loaded linear calibration parameters: slope={self.slope}, intercept={self.intercept}")
                    
                    # Load inverse model parameters if present
                    if all(key in data for key in ['alpha', 'beta', 'gamma']):
                        self.alpha = data['alpha']
                        self.beta = data['beta']
                        self.gamma = data['gamma']
                        self.offset = data.get('offset', -0.3)
                        if not self.use_linear_mapping:
                            print(f"Loaded inverse calibration parameters: alpha={self.alpha}, beta={self.beta}, gamma={self.gamma}, offset={self.offset}")
                    
                    # Load calibration points if present
                    if 'calibration_points' in data:
                        self.calibration_points = data['calibration_points']
                        print(f"Loaded {len(self.calibration_points)} calibration points")
        except Exception as e:
            print(f"Could not load calibration: {e}")

    def save_calibration(self):
        """Save calibration to file"""
        try:
            import json
            with open(self.calibration_file, 'w') as f:
                data = {
                    'scale_factor': self.depth_scale_factor,  # Keep for backward compatibility
                    'alpha': self.alpha,
                    'beta': self.beta,
                    'gamma': self.gamma,
                    'offset': self.offset,
                    'use_linear_mapping': self.use_linear_mapping,
                    'slope': self.slope,
                    'intercept': self.intercept,
                    'calibration_points': self.calibration_points
                }
                json.dump(data, f)
                if self.use_linear_mapping:
                    print(f"Saved linear calibration parameters: slope={self.slope:.2f}, intercept={self.intercept:.2f}")
                else:
                    print(f"Saved inverse calibration parameters: alpha={self.alpha:.2f}, beta={self.beta:.2f}, gamma={self.gamma:.2f}, offset={self.offset:.2f}")
        except Exception as e:
            print(f"Could not save calibration: {e}")

    def add_calibration_point(self, known_distance: float, depth_value: float):
        """Add a calibration point and update parameters if enough points are available"""
        self.calibration_points.append((depth_value, known_distance))
        print(f"Added calibration point: depth={depth_value:.3f}, distance={known_distance}m")
        
        # Update parameters if we have enough points
        if len(self.calibration_points) >= 3:
            self.update_calibration_parameters()
        
        # Save calibration data
        self.save_calibration()

    def update_calibration_parameters(self):
        """Update calibration parameters using collected calibration points"""
        if len(self.calibration_points) < 2:
            print("Need at least 2 calibration points to fit parameters")
            return
        
        # Extract depth values and actual distances
        depth_values = np.array([point[0] for point in self.calibration_points])
        actual_distances = np.array([point[1] for point in self.calibration_points])
        
        # Print calibration points for debugging
        print("Calibration points:")
        for i, (depth, dist) in enumerate(zip(depth_values, actual_distances)):
            print(f"  Point {i+1}: depth={depth:.3f}, distance={dist}m")
        
        if self.use_linear_mapping:
            try:
                # Simple linear regression
                A = np.vstack([depth_values, np.ones_like(depth_values)]).T
                self.slope, self.intercept = np.linalg.lstsq(A, actual_distances, rcond=None)[0]
                print(f"Updated linear parameters: slope={self.slope:.3f}, intercept={self.intercept:.3f}")
                
                # Compute and print mean absolute error
                predicted = self.slope * depth_values + self.intercept
                mean_abs_error = np.mean(np.abs(predicted - actual_distances))
                print(f"Mean absolute error after calibration: {mean_abs_error:.3f}m")
                
                # Print test values for important ranges
                test_depths = [0.1, 0.3, 0.5, 0.7, 0.9]
                print("Predicted distances at test depths:")
                for d in test_depths:
                    pred = self.slope * d + self.intercept
                    print(f"  depth={d:.1f} → distance={pred:.2f}m")
                    
            except Exception as e:
                print(f"Error updating linear parameters: {e}")
                # Reset to sensible defaults
                self.slope = 4.0
                self.intercept = 0.5
        else:
            # Existing inverse function fitting code
            try:
                import scipy.optimize as optimize
                
                # Define the inverse function to fit
                def inverse_func(x, a, b, c):
                    return a / (b * (1.0 - x) + c)
                
                # Initial parameter guess (current values)
                initial_guess = [self.alpha, self.beta, self.gamma]
                
                # Find optimal parameters with tighter bounds
                params, _ = optimize.curve_fit(
                    inverse_func, depth_values, actual_distances,
                    p0=initial_guess,
                    bounds=([0.5, 0.5, 0.01], [10.0, 10.0, 0.5])
                )
                
                # Update parameters
                self.alpha, self.beta, self.gamma = params
                print(f"Updated inverse parameters: alpha={self.alpha:.3f}, beta={self.beta:.3f}, gamma={self.gamma:.3f}")
                
                # Compute and print mean absolute error
                predicted = inverse_func(depth_values, *params)
                mean_abs_error = np.mean(np.abs(predicted - actual_distances))
                print(f"Mean absolute error after calibration: {mean_abs_error:.3f}m")
                
                # Print test values for important ranges
                test_depths = [0.1, 0.3, 0.5, 0.7, 0.9]
                print("Predicted distances at test depths:")
                for d in test_depths:
                    pred = inverse_func(d, *params)
                    print(f"  depth={d:.1f} → distance={pred:.2f}m")
                
            except Exception as e:
                print(f"Error updating inverse parameters: {e}")
                print("Falling back to default parameters")
                # Reset to sensible defaults
                self.alpha = 4.5
                self.beta = 1.8
                self.gamma = 0.05

    def calibrate(self, known_distance: float, depth_value: float):
        """
        Legacy calibration method - redirects to add_calibration_point
        """
        # Store the legacy scale factor for backward compatibility
        self.depth_scale_factor = known_distance / depth_value
        print(f"Legacy depth scale factor: {self.depth_scale_factor:.3f}")
        
        # Add as a calibration point for the inverse model
        self.add_calibration_point(known_distance, depth_value)

    def estimate_depth(self, frame: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
        """
        Estimate depth with EMA stabilization and metric conversion
        """
        # Record original size
        original_size = frame.shape[:2]
        
        try:
            # Preprocess the image
            input_tensor = self.preprocess(frame)
            
            # Run inference
            with torch.no_grad():
                prediction = self.model(input_tensor)
            
            # Initial postprocessing
            depth_map = self.postprocess(prediction, original_size)
            
            # Apply EMA filtering for stability
            depth_map = self.depth_filter.filter(depth_map)
            
            # Import required functions here to avoid circular import
            if self.use_linear_mapping:
                from .normalize import depth_to_metric_linear
                
                # Use calibrated linear parameters or defaults
                slope = getattr(self, 'slope', 4.0)
                intercept = getattr(self, 'intercept', 0.5)
                
                metric_depth = depth_to_metric_linear(
                    depth_map,
                    slope=slope,
                    intercept=intercept,
                    min_depth=self.depth_min,
                    max_depth=self.depth_max
                )
            else:
                from .normalize import depth_to_metric_inverse
                
                # Use calibrated inverse parameters or defaults
                alpha = getattr(self, 'alpha', 4.5)
                beta = getattr(self, 'beta', 1.8)
                gamma = getattr(self, 'gamma', 0.05)
                offset = getattr(self, 'offset', -0.7)
                
                metric_depth = depth_to_metric_inverse(
                    depth_map,
                    alpha=alpha,
                    beta=beta,
                    gamma=gamma,
                    offset=offset,
                    min_depth=self.depth_min,
                    max_depth=self.depth_max
                )
            
        except Exception as e:
            print(f"Error during depth estimation: {e}")
            # Create fallback depth map
            h, w = original_size
            depth_map = np.zeros((h, w), dtype=np.float32)
            metric_depth = np.zeros_like(depth_map)
        
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
    
    def compute_confidence(self, depth_map: np.ndarray, window_size: int = 5) -> np.ndarray:
        """
        Compute confidence map based on local depth consistency.
        Lower variance = higher confidence.
        """
        # Calculate local variance using a sliding window
        local_var = cv2.blur(depth_map**2, (window_size, window_size)) - \
                    cv2.blur(depth_map, (window_size, window_size))**2
        
        # Convert variance to confidence (inverse relationship)
        confidence = 1 / (1 + local_var)
        
        # Normalize confidence to 0-1
        confidence = (confidence - confidence.min()) / \
                    (confidence.max() - confidence.min() + 1e-6)
        
        return confidence

    def apply_confidence_filter(self, depth_map: np.ndarray, 
                              confidence: np.ndarray,
                              threshold: float = 0.5) -> np.ndarray:
        """
        Filter depth values based on confidence scores.
        """
        # Create mask for high-confidence regions
        mask = confidence > threshold
        
        # For low-confidence regions, use neighborhood average
        filtered_depth = depth_map.copy()
        filtered_depth[~mask] = cv2.blur(depth_map, (5, 5))[~mask]
        
        return filtered_depth

    def visualize_calibration(self):
        """Create a visualization of the current depth-to-distance mapping"""
        try:
            import matplotlib.pyplot as plt
            import numpy as np
            
            # Create a range of depth values from 0 to 1
            depth_values = np.linspace(0, 1, 100)
            
            # Calculate corresponding distances using current parameters
            if self.use_linear_mapping:
                distances = self.slope * depth_values + self.intercept
                formula = f"distance = {self.slope:.2f} * depth + {self.intercept:.2f}"
            else:
                distances = self.alpha / (self.beta * (1.0 - depth_values) + self.gamma) + self.offset
                formula = f"distance = {self.alpha:.2f} / ({self.beta:.2f} * (1 - depth) + {self.gamma:.2f}) + {self.offset:.2f}"
            
            # Create the plot
            plt.figure(figsize=(10, 6))
            plt.plot(depth_values, distances, 'b-', linewidth=2)
            
            # Plot the calibration points if available
            if len(self.calibration_points) > 0:
                calib_depths = [p[0] for p in self.calibration_points]
                calib_dists = [p[1] for p in self.calibration_points]
                plt.plot(calib_depths, calib_dists, 'ro', markersize=8, label='Calibration Points')
            
            # Mark key depths with vertical lines
            for d in [0.1, 0.3, 0.5, 0.7, 0.9]:
                if self.use_linear_mapping:
                    dist = self.slope * d + self.intercept
                else:
                    dist = self.alpha / (self.beta * (1.0 - d) + self.gamma) + self.offset
                    
                plt.axvline(x=d, color='gray', linestyle='--', alpha=0.5)
                plt.text(d+0.01, 0.5, f"{d:.1f} → {dist:.2f}m", rotation=90, verticalalignment='center')
            
            # Add labels and title
            plt.xlabel('Normalized Depth')
            plt.ylabel('Distance (meters)')
            title = "Linear Depth Mapping" if self.use_linear_mapping else "Inverse Depth Mapping"
            plt.title(title)
            plt.grid(True)
            plt.ylim(0, 6)
            
            # Add formula and parameters
            plt.figtext(0.5, 0.01, formula, ha='center', fontsize=12)
            
            # Show the plot
            plt.tight_layout()
            plt.savefig('calibration_curve.png')
            print(f"Calibration visualization saved to 'calibration_curve.png'")
            
        except ImportError:
            print("Matplotlib is required for visualization") 