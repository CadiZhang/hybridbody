from sklearn.cluster import DBSCAN
import numpy as np

def segment_obstacles(depth_map, ground_mask):
    """Cluster non-ground points into obstacles."""
    # Identify non-ground points
    non_ground = ~ground_mask
    v, u = np.where(non_ground)
    z = depth_map[non_ground]
    # Create 3D point cloud (u, v, z)
    points = np.vstack((u, v, z)).T
    # Cluster with DBSCAN
    db = DBSCAN(eps=10, min_samples=20).fit(points)  # Tune eps and min_samples
    labels = db.labels_
    # Extract obstacles (exclude noise labeled as -1)
    unique_labels = set(labels) - {-1}
    obstacles = []
    for label in unique_labels:
        cluster_points = points[labels == label]
        centroid = np.mean(cluster_points, axis=0)  # [u, v, z]
        obstacles.append({"centroid": centroid, "points": cluster_points})
    return obstacles