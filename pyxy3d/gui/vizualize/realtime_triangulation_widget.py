#%%

import pyxy3d.logger

logger = pyxy3d.logger.get(__name__)

import sys
from pathlib import Path
import numpy as np
import pandas as pd
from queue import Queue
from threading import Thread
import pyqtgraph.opengl as gl

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QApplication,
    QSlider,
    QVBoxLayout,
    QWidget,
)
from pyxy3d.session.session import Session
from pyxy3d.gui.vizualize.camera_mesh import CameraMesh, mesh_from_camera
from pyxy3d.interface import XYZPacket
from pyxy3d.cameras.camera_array import CameraArray

class RealTimeTriangulationWidget(QWidget):
    def __init__(self, camera_array:CameraArray, xyz_packet_q:Queue):
        super(RealTimeTriangulationWidget, self).__init__()

        self.camera_array = camera_array
        self.xyz_packet_q = xyz_packet_q #place to receive xyz_packets from Triangulator or similar...

        self.visualizer = TriangulationVisualizer(self.camera_array)

        self.setMinimumSize(500, 500)

        self.place_widgets()
        self.connect_widgets()

        self.thread = Thread(target=self.process_incoming,args=[],daemon=True)
        self.thread.start()

    def place_widgets(self):
        self.setLayout(QVBoxLayout())
        self.layout().addWidget(self.visualizer.scene)

    def connect_widgets(self):
        pass
        # self.slider.valueChanged.connect(self.visualizer.display_points)

    def process_incoming(self):
        
        while True:
            xyz_packet = self.xyz_packet_q.get()
            self.visualizer.display_points(xyz_packet)
            

class TriangulationVisualizer:
    """
    Can except either a single camera array or a capture volume that includes
    point_estimates. If a capture volume is supplied, point positions can
    be played back.
    """

    def __init__(
        self, camera_array: CameraArray
    ):

        self.camera_array = camera_array

        # self.min_sync_index = np.min(self.sync_indices)
        # self.max_sync_index = np.max(self.sync_indices)
        # self.sync_index = self.min_sync_index

        # x_coord = self.xyz_history["x_coord"]
        # y_coord = self.xyz_history["y_coord"]
        # z_coord = self.xyz_history["z_coord"]
        # self.xyz_coord = np.vstack([x_coord,y_coord,z_coord]).T
        
        # constuct a scene
        self.scene = gl.GLViewWidget()
        self.scene.setCameraPosition(distance=4)  # the scene camera, not a real Camera

        axis = gl.GLAxisItem()
        self.scene.addItem(axis)

        # build meshes for all cameras
        self.meshes = {}
        for port, cam in self.camera_array.cameras.items():
            print(port)
            print(cam)
            mesh:CameraMesh = mesh_from_camera(cam)
            self.meshes[port] = mesh
            self.scene.addItem(mesh)

        self.scatter = gl.GLScatterPlotItem(
            pos=np.array([0, 0, 0]),
            color=[1, 1, 1, 1],
            size=0.01,
            pxMode=False,
        )
        self.scene.addItem(self.scatter)

        # self.display_points(self.sync_index)
                 
    def display_points(self, xyz_packet:XYZPacket):
        # self.sync_index = sync_index
        # current_sync_index_flag = self.sync_indices == self.sync_index
        # self.single_board_points = self.xyz_coord[current_sync_index_flag]
        # logger.info(f"Displaying xyz points for sync index {sync_index}")
        self.scatter.setData(pos=xyz_packet.point_xyz)

if __name__ == "__main__":

    from PySide6.QtWidgets import QApplication
    import time
    from pyxy3d import __root__
    from pyxy3d.calibration.capture_volume.helper_functions.get_point_estimates import (
        get_point_estimates,
    )

    from pyxy3d.calibration.capture_volume.capture_volume import CaptureVolume
    
    test_sessions = [
        # Path(__root__, "dev", "sample_sessions", "post_triangulation"),
        Path(__root__, "dev", "sample_sessions", "triangulated_hands", )
    ]

    test_session_index = 0
    session_path = test_sessions[test_session_index]
    logger.info(f"Loading session {session_path}")
    session = Session(session_path)

    session.load_estimated_capture_volume()

    app = QApplication(sys.argv)
    
    xyz_queue = Queue()
    
    vizr_dialog = RealTimeTriangulationWidget(session.capture_volume.camera_array, xyz_queue)

#%%   
    def send_packets_from_history():
        xyz_history_path = Path(session_path,"xyz_history.csv")
        
        xyz_data = pd.read_csv(xyz_history_path)
        sync_indices = np.unique(xyz_data["sync_index"])
        sync_indices.sort()
        
        for sync_index in sync_indices:
            current_xyz = xyz_data[xyz_data["sync_index"]==sync_index] 
            points = current_xyz["point_id"].to_numpy()
            xyz = current_xyz[["x_coord", "y_coord", "z_coord"]].to_numpy()
            
            xyz_packet = XYZPacket(sync_index,points,xyz )
            xyz_queue.put(xyz_packet)
            time.sleep(.01)  
        logger.info("attempting to quit application")
        # vizr_dialog.close()
        # app.quit()
        # sys.exit()
         
    thread = Thread(target=send_packets_from_history,args=[],daemon=True)
    thread.start()        

    vizr_dialog.show()

    sys.exit(app.exec())
