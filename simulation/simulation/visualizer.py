from direct.showbase.ShowBase import ShowBase
from panda3d.core import GeomNode
from panda3d.core import Geom, GeomVertexFormat, GeomVertexData, GeomVertexWriter, GeomTriangles
import numpy as np
import utils.config as config

class Visualizer(ShowBase):
    def __init__(self):
        ShowBase.__init__(self)
        self.obstacle_node = self.render.attachNewNode("obstacles")
        self.setBackgroundColor(0, 0, 0, 1)  # Black background
    
    def update_simulation(self, obstacles):
        """Update the 3D scene with obstacle positions."""
        self.obstacle_node.removeNode()
        self.obstacle_node = self.render.attachNewNode("obstacles")
        
        for obs in obstacles:
            centroid = obs["centroid"]
            u, v, z = centroid
            # Convert to 3D space
            x = (u - config.FRAME_WIDTH / 2) * z / config.FOCAL_LENGTH
            y = (v - config.FRAME_HEIGHT / 2) * z / config.FOCAL_LENGTH
            # Use a simple box model
            box = self.loader.loadModel("models/box")
            box.setScale(0.1, 0.1, 0.1)  # Small scale for visibility
            box.setPos(x, z, -y)  # Panda3D: z forward, y up
            box.reparentTo(self.obstacle_node)
visualizer = Visualizer() if config.SIMULATION_ENABLED else None

def update_simulation(obstacles):
    """Update the simulation if enabled."""
    if visualizer:
        visualizer.update_simulation(obstacles)
        visualizer.taskMgr.step()  # Render one frame