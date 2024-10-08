# Copyright (c) 2022-2023, NVIDIA CORPORATION. All rights reserved.
#
# NVIDIA CORPORATION and its licensors retain all intellectual property
# and proprietary rights in and to this software, related documentation
# and any modifications thereto. Any use, reproduction, disclosure or
# distribution of this software and related documentation without an express
# license agreement from NVIDIA CORPORATION is strictly prohibited.
#

import numpy as np
import omni.timeline
import omni.ui as ui
from omni.isaac.core.articulations import Articulation
from omni.isaac.core.utils.prims import get_prim_object_type
from omni.isaac.core.utils.types import ArticulationAction
from omni.isaac.ui.element_wrappers import CollapsableFrame, DropDown, FloatField, TextBlock
from omni.isaac.ui.ui_utils import get_style
from omni.isaac.core.prims import XFormPrim
from asyncua.sync import Client, ua
import omni.graph.core as og
from omni.isaac.core import World
from omni.isaac.core.objects import DynamicCuboid
from omni.isaac.core.materials import OmniPBR
import omni.kit.raycast.query
from datetime import datetime
import random
from scipy.spatial.transform import Rotation as R

class Photoeye():
    # The photoeye logic that binds to a physical prim in the scene. 
    # For simplicity it's assumed that the photoeyes are all pointing in the +Y direction.
    def __init__(self, prim_path, opc_ua_node, range_min=0.0, range_max=0.8):
        self._range_min = range_min
        self._range_max = range_max
        self._prim = XFormPrim(f"{prim_path}/Geometry/H30_DIF_1500X_XM_0")
        self._position, self._rotation = self._prim.get_world_pose()
        self._direction = [0, 1, 0]
        self._position = self._position.astype(float)
        self._position[1] = self._position[1] + 0.1
        self._ray = omni.kit.raycast.query.Ray(self._position, self._direction)
        self._raycast_interface = omni.kit.raycast.query.acquire_raycast_query_interface()
        self._led_prim = XFormPrim(f"{prim_path}/LED")
        self._led_prim.set_visibility(visible=False)
        self._opc_ua_node = opc_ua_node
        self.triggered = True

    def _status_callback(self, ray, result):
        if result.valid:
            # Calculate the distance to the intersection point.
            distance = result.hit_position[1] - self._position[1]
            if distance >= self._range_min and distance <= self._range_max:
                self.triggered = True
            else:
                self.triggered = False
        else:
            self.triggered = False 
        self._led_prim.set_visibility(visible=self.triggered)
        # Lastly, write to the OPC UA node.
        data_value = ua.DataValue(ua.Variant(self.triggered, ua.VariantType.Boolean))
        self._opc_ua_node.write_value(data_value)

    def update(self):
        self._raycast_interface.submit_raycast_query(self._ray, self._status_callback)


class Conveyor():
    def __init__(self, prim_path, opc_ua_node):
        self._opc_ua_node = opc_ua_node
        graph = og.get_graph_by_path(f"{prim_path}/ConveyorBeltGraph")
        node = graph.get_node(f"{prim_path}/ConveyorBeltGraph/ConveyorNode")
        self._velocity_attribute = node.get_attribute("inputs:velocity")

    def update(self):
        # Read conveyor speed from PLC, and assign to conveyors. 
        speed = self._opc_ua_node.read_value()
        self._velocity_attribute.set(speed)


class UIBuilder:
    def __init__(self):
        # Frames are sub-windows that can contain multiple UI elements
        self.frames = []

        # UI elements created using a UIElementWrapper from omni.isaac.ui.element_wrappers
        self.wrapped_ui_elements = []

        # Get access to the timeline to control stop/pause/play programmatically
        self._timeline = omni.timeline.get_timeline_interface()

        self._spawn_clock = 2.0


    ###################################################################################
    #           The Functions Below Are Called Automatically By extension.py
    ###################################################################################

    def on_menu_callback(self):
        """Callback for when the UI is opened from the toolbar.
        This is called directly after build_ui().
        """
        print("Opening up the OPC UA extension...")

        # Set up the OPC UA communication with the PLC.
        ip = "localhost"
        port = 4840
        username = "Admin"
        password = "password"
        url = f"opc.tcp://{username}:{password}@{ip}:{port}/"
        self._client = Client(url=url)
        self._client.connect()

        self._conveyors = []
        self._conveyors.append(Conveyor("/World/conveyors/Conveyor1", self._client.get_node("ns=6;s=::Logic:conveyor[0].io.aoSpeed")))
        self._conveyors.append(Conveyor("/World/conveyors/Conveyor2", self._client.get_node("ns=6;s=::Logic:conveyor[1].io.aoSpeed")))
        self._conveyors.append(Conveyor("/World/conveyors/Conveyor3", self._client.get_node("ns=6;s=::Logic:conveyor[2].io.aoSpeed")))
        self._conveyors.append(Conveyor("/World/conveyors/Conveyor4", self._client.get_node("ns=6;s=::Logic:conveyor[3].io.aoSpeed")))
        self._conveyors.append(Conveyor("/World/conveyors/Conveyor5", self._client.get_node("ns=6;s=::Logic:conveyor[4].io.aoSpeed")))

        self._photoeyes = []
        self._photoeyes.append(Photoeye("/World/conveyors/Photoeye1a", self._client.get_node("ns=6;s=::Logic:conveyor[0].io.diPhotoeye1")))
        self._photoeyes.append(Photoeye("/World/conveyors/Photoeye1b", self._client.get_node("ns=6;s=::Logic:conveyor[0].io.diPhotoeye2")))
        self._photoeyes.append(Photoeye("/World/conveyors/Photoeye2a", self._client.get_node("ns=6;s=::Logic:conveyor[1].io.diPhotoeye1")))
        self._photoeyes.append(Photoeye("/World/conveyors/Photoeye2b", self._client.get_node("ns=6;s=::Logic:conveyor[1].io.diPhotoeye2")))
        self._photoeyes.append(Photoeye("/World/conveyors/Photoeye3a", self._client.get_node("ns=6;s=::Logic:conveyor[2].io.diPhotoeye1")))
        self._photoeyes.append(Photoeye("/World/conveyors/Photoeye3b", self._client.get_node("ns=6;s=::Logic:conveyor[2].io.diPhotoeye2")))
        self._photoeyes.append(Photoeye("/World/conveyors/Photoeye4a", self._client.get_node("ns=6;s=::Logic:conveyor[3].io.diPhotoeye1")))
        self._photoeyes.append(Photoeye("/World/conveyors/Photoeye4b", self._client.get_node("ns=6;s=::Logic:conveyor[3].io.diPhotoeye2")))
        self._photoeyes.append(Photoeye("/World/conveyors/Photoeye5a", self._client.get_node("ns=6;s=::Logic:conveyor[4].io.diPhotoeye1")))
        self._photoeyes.append(Photoeye("/World/conveyors/Photoeye5b", self._client.get_node("ns=6;s=::Logic:conveyor[4].io.diPhotoeye2")))

        self._ready_to_receive_node = self._client.get_node("ns=6;s=::Logic:conveyor[0].out.readyToReceive")

        self._process_active_node = self._client.get_node("ns=6;s=::Logic:processActive")

        self._spawning_new_product = False
        self._process_active = False

        self._process_light_prim = XFormPrim("/World/Oven/SphereLight")
        self._process_light_prim.set_visibility(visible=False)

        self._spawn_clock = 2.0

        pass

    def on_timeline_event(self, event):
        """Callback for Timeline events (Play, Pause, Stop)

        Args:
            event (omni.timeline.TimelineEventType): Event Type
        """
        pass

    def on_physics_step(self, step):
        """Callback for Physics Step.
        Physics steps only occur when the timeline is playing

        Args:
            step (float): Size of physics step
        """
        for conveyor in self._conveyors:
            conveyor.update()

        for photoeye in self._photoeyes:
            photoeye.update()

        # Handle spawning new product.
        self._spawn_clock = self._spawn_clock + step
        if self._spawn_clock > 4:
            self._spawn_clock = 0
            self._spawning_new_product = True
            self._spawn_product()
        # elif not self._ready_for_new_product:
        #     self._spawning_new_product = False

        # Handle turning on the red light during the process step. 
        self._process_active = self._process_active_node.read_value()
        self._process_light_prim.set_visibility(visible=self._process_active)

        pass

    def on_stage_event(self, event):
        """Callback for Stage Events

        Args:
            event (omni.usd.StageEventType): Event Type
        """
        pass

    def cleanup(self):
        """
        Called when the stage is closed or the extension is hot reloaded.
        Perform any necessary cleanup such as removing active callback functions
        Buttons imported from omni.isaac.ui.element_wrappers implement a cleanup function that should be called
        """
        print("Closing the extension")
        for ui_elem in self.wrapped_ui_elements:
            ui_elem.cleanup()

        # self._client.disconnect()

    def build_ui(self):
        """
        Build a custom UI tool to run your extension.
        This function will be called any time the UI window is closed and reopened.
        """
        pass


    ######################################################################################
    # Functions Below This Point Support The Provided Example And Can Be Replaced/Deleted
    ######################################################################################

    def _spawn_product(self):
        world = World()
        now = datetime.now()
        cube_name = f"product_{now.minute}_{now.second}_{now.microsecond}"
        print(cube_name)
        random_horizontal = random.random()
        random_vertical = random.random()
        if random_vertical > 0.5:
            euler_angles = np.array([random_horizontal * 0.5, 3.14159/2, 0.0])
        else:
            euler_angles = np.array([random_horizontal * 0.5, 0.0, 0.0])
        print(euler_angles)
        world.scene.add(
            DynamicCuboid(
                prim_path=f"/World/{cube_name}", # The prim path of the cube in the USD stage
                name=cube_name, # The unique name used to retrieve the object from the scene later on
                position=np.array([-30.73771, -14.2025, 2.3]), # Using the current stage units which is in meters by default.
                orientation=R.from_euler('xyz', euler_angles).as_quat(),
                scale=np.array([0.6, 0.4, 0.4]), # most arguments accept mainly numpy arrays.
                color=np.array([0.25, 0.25, 0.25]), # RGB channels, going from 0-1
            ))


