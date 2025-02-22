import torch
import cv2
import numpy as np
import utils.config as config

# Load MiDaS model and transform
model = torch.hub.load("intel-isl/MiDaS", config.DEPTH_MODEL)
model.eval()
transform = torch.hub.load("intel-isl/MiDaS", "transforms").small_transform

def estimate_depth(frame):
    """Estimate depth map from an RGB frame using MiDaS."""
    # Preprocess frame
    img = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    input_tensor = transform(img).unsqueeze(0)
    
    # Perform depth estimation
    with torch.no_grad():
        depth = model(input_tensor)
        depth = torch.nn.functional.interpolate(
            depth.unsqueeze(1),
            size=(config.FRAME_HEIGHT, config.FRAME_WIDTH),
            mode="bicubic",
            align_corners=False,
        ).squeeze()
    # Normalize depth for downstream use
    depth_min = depth.min()
    depth_max = depth.max()
    depth_normalized = (depth - depth_min) / (depth_max - depth_min)
    return depth_normalized.numpy()