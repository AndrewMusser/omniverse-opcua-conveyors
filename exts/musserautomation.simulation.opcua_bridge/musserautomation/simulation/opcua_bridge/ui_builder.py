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

class Photoeye():
    # The photoeye logic that binds to a physical prim in the scene. 
    # For simplicity it's assumed that the photoeyes are all pointing in the -Y direction.
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
        self._led_prim = XFormPrim(f"{prim_path}/Geometry/LED")
        self._led_prim.set_visibility(visible=False)
        self._opc_ua_node = opc_ua_node
        self.triggered = True

    def _status_callback(self, ray, result):
        if result.valid:
            # Calculate the distance to the intersection point.
            distance = result.hit_position[1] - self._position[1]
            print(distance)
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

        # Run initialization for the provided example
        self._on_init()

    ###################################################################################
    #           The Functions Below Are Called Automatically By extension.py
    ###################################################################################

    def on_menu_callback(self):
        """Callback for when the UI is opened from the toolbar.
        This is called directly after build_ui().
        """
        print("Opening up the OPC UA extension...")
        # Reset internal state when UI window is closed and reopened
        self._invalidate_articulation()

        # Set up the OPC UA communication with the PLC.
        ip = "localhost"
        port = 4840
        username = "Admin"
        password = "password"
        url = f"opc.tcp://{username}:{password}@{ip}:{port}/"
        self._client = Client(url=url)
        self._client.connect()

        self._conveyors = []
        self._conveyors.append(Conveyor("/World/Conveyor1", self._client.get_node("ns=6;s=::Logic:conveyor[0].io.aoSpeed")))
        self._conveyors.append(Conveyor("/World/Conveyor2", self._client.get_node("ns=6;s=::Logic:conveyor[1].io.aoSpeed")))
        self._conveyors.append(Conveyor("/World/Conveyor3", self._client.get_node("ns=6;s=::Logic:conveyor[2].io.aoSpeed")))
        self._conveyors.append(Conveyor("/World/Conveyor4", self._client.get_node("ns=6;s=::Logic:conveyor[3].io.aoSpeed")))
        self._conveyors.append(Conveyor("/World/Conveyor5", self._client.get_node("ns=6;s=::Logic:conveyor[4].io.aoSpeed")))

        self._photoeyes = []
        self._photoeyes.append(Photoeye("/World/Photoeye1a", self._client.get_node("ns=6;s=::Logic:conveyor[0].io.diPhotoeye1")))
        self._photoeyes.append(Photoeye("/World/Photoeye1b", self._client.get_node("ns=6;s=::Logic:conveyor[0].io.diPhotoeye2")))
        self._photoeyes.append(Photoeye("/World/Photoeye2a", self._client.get_node("ns=6;s=::Logic:conveyor[1].io.diPhotoeye1")))
        self._photoeyes.append(Photoeye("/World/Photoeye2b", self._client.get_node("ns=6;s=::Logic:conveyor[1].io.diPhotoeye2")))
        self._photoeyes.append(Photoeye("/World/Photoeye3a", self._client.get_node("ns=6;s=::Logic:conveyor[2].io.diPhotoeye1")))
        self._photoeyes.append(Photoeye("/World/Photoeye3b", self._client.get_node("ns=6;s=::Logic:conveyor[2].io.diPhotoeye2")))
        self._photoeyes.append(Photoeye("/World/Photoeye4a", self._client.get_node("ns=6;s=::Logic:conveyor[3].io.diPhotoeye1")))
        self._photoeyes.append(Photoeye("/World/Photoeye4b", self._client.get_node("ns=6;s=::Logic:conveyor[3].io.diPhotoeye2")))
        self._photoeyes.append(Photoeye("/World/Photoeye5a", self._client.get_node("ns=6;s=::Logic:conveyor[4].io.diPhotoeye1")))
        self._photoeyes.append(Photoeye("/World/Photoeye5b", self._client.get_node("ns=6;s=::Logic:conveyor[4].io.diPhotoeye2")))

        self._ready_to_receive_node = self._client.get_node("ns=6;s=::Logic:conveyor[0].out.readyToReceive")

        self._spawning_new_product = False

        # Handles the case where the user loads their Articulation and
        # presses play before opening this extension
        if self._timeline.is_playing():
            self._selection_menu.repopulate()
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
        self._ready_for_new_product = self._ready_to_receive_node.read_value()
        if self._ready_for_new_product and not self._spawning_new_product:
            self._spawning_new_product = True
            self._spawn_product()
        elif not self._ready_for_new_product:
            self._spawning_new_product = False

        pass

    def on_stage_event(self, event):
        """Callback for Stage Events

        Args:
            event (omni.usd.StageEventType): Event Type
        """

        # The ASSETS_LOADED stage event is triggered on every occasion that the selection menu should be repopulated:
        #   a) The timeline is stopped or played
        #   b) An Articulation is added or removed from the stage
        #   c) The USD stage is loaded or cleared
        if event.type == int(omni.usd.StageEventType.ASSETS_LOADED):
            self._selection_menu.repopulate()
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
        selection_panel_frame = CollapsableFrame("Selection Panel", collapsed=False)

        with selection_panel_frame:
            with ui.VStack(style=get_style(), spacing=5, height=0):
                self._selection_menu = DropDown(
                    "Select Articulation",
                    tooltip="Select from Articulations found on the stage after the timeline has been played.",
                    on_selection_fn=self._on_articulation_selection,
                    keep_old_selections=True,
                    # populate_fn = self._find_all_articulations # Equivalent functionality to one-liner below
                )
                # This sets the populate_fn to find all USD objects of a certain type on the stage, overriding the populate_fn arg
                # Figure out the type of an object with get_prim_object_type(prim_path)
                self._selection_menu.set_populate_fn_to_find_all_usd_objects_of_type("articulation", repopulate=False)

        self._robot_control_frame = CollapsableFrame("Robot Control Frame", collapsed=False)

        def build_robot_control_frame_fn():
            self._joint_control_frames = []
            self._joint_position_float_fields = []
            if self.articulation is None:
                TextBlock("Status", text="There is no Articulation Selected", num_lines=2)
                return

            with ui.VStack(style=get_style(), spacing=5, height=0):
                for i in range(self.articulation.num_dof):
                    joint_frame = CollapsableFrame(f"Joint {i}", collapsed=False)
                    self._joint_control_frames.append(joint_frame)

                    # In each joint control frame, add controls to manage the robot joint
                    with joint_frame:
                        field = FloatField(label=f"Position Target", tooltip="Set joint position target")
                        field.set_on_value_changed_fn(
                            lambda value, index=i: self._on_set_joint_position_target(index, value)
                        )
                        self._joint_position_float_fields.append(field)
            self._setup_joint_control_frames()

        self._robot_control_frame.set_build_fn(build_robot_control_frame_fn)

    ######################################################################################
    # Functions Below This Point Support The Provided Example And Can Be Replaced/Deleted
    ######################################################################################

    def _on_init(self):
        self.articulation = None

    def _invalidate_articulation(self):
        """
        This function handles the event that the existing articulation becomes invalid and there is
        not a new articulation to select.  It is called explicitly in the code when the timeline is
        stopped and when the DropDown menu finds no articulations on the stage.
        """
        self.articulation = None
        self._robot_control_frame.rebuild()

    def _on_articulation_selection(self, selection: str):
        """
        This function is called whenever a new selection is made in the
        "Select Articulation" DropDown.  A new selection may also be
        made implicitly any time self._selection_menu.repopulate() is called
        since the Articulation they had selected may no longer be present on the stage.

        Args:
            selection (str): The item that is currently selected in the drop-down menu.
        """
        if selection is None:
            self._invalidate_articulation()
            return

        self.articulation = Articulation(selection)
        self.articulation.initialize()

        self._robot_control_frame.rebuild()

    def _setup_joint_control_frames(self):
        """
        Once a robot has been chosen, update the UI to match robot properties:
            Make a frame visible for each robot joint.
            Rename each frame to match the human-readable name of the joint it controls.
            Change the FloatField for each joint to match the current robot position.
            Apply the robot's joint limits to each FloatField.
        """
        num_dof = self.articulation.num_dof
        dof_names = self.articulation.dof_names
        joint_positions = self.articulation.get_joint_positions()

        lower_joint_limits = self.articulation.dof_properties["lower"]
        upper_joint_limits = self.articulation.dof_properties["upper"]

        for i in range(num_dof):
            frame = self._joint_control_frames[i]
            position_float_field = self._joint_position_float_fields[i]

            # Write the human-readable names of each joint
            frame.title = dof_names[i]
            position = joint_positions[i]

            position_float_field.set_value(position)
            position_float_field.set_upper_limit(upper_joint_limits[i])
            position_float_field.set_lower_limit(lower_joint_limits[i])

    def _on_set_joint_position_target(self, joint_index: int, position_target: float):
        """
        This function is called when the user changes one of the float fields
        to control a robot joint position target.  The index of the joint and the new
        desired value are passed in as arguments.

        This function assumes that there is a guarantee it is called safely.
        I.e. A valid Articulation has been selected and initialized
        and the timeline is playing.  These gurantees are given by careful UI
        programming.  The joint control frames are only visible to the user when
        these guarantees are met.

        Args:
            joint_index (int): Index of robot joint that was modified
            position_target (float): New position target for robot joint
        """
        robot_action = ArticulationAction(
            joint_positions=np.array([position_target]),
            joint_velocities=np.array([0]),
            joint_indices=np.array([joint_index]),
        )
        self.articulation.apply_action(robot_action)

    def _spawn_product(self):
        world = World()
        now = datetime.now()
        cube_name = f"product_{now.minute}_{now.second}_{now.microsecond}"
        print(cube_name)
        world.scene.add(
            DynamicCuboid(
                prim_path=f"/World/{cube_name}", # The prim path of the cube in the USD stage
                name=cube_name, # The unique name used to retrieve the object from the scene later on
                position=np.array([-1.64879, 0, 2.16191]), # Using the current stage units which is in meters by default.
                scale=np.array([0.53012, 0.46643, 0.5174]), # most arguments accept mainly numpy arrays.
                color=np.array([0.25, 0.25, 0.25]), # RGB channels, going from 0-1
            ))

    # def _find_all_articulations(self):
    # #    Commented code left in to help a curious user gain a thorough understanding

    #     import omni.usd
    #     from pxr import Usd
    #     items = []
    #     stage = omni.usd.get_context().get_stage()
    #     if stage:
    #         for prim in Usd.PrimRange(stage.GetPrimAtPath("/")):
    #             path = str(prim.GetPath())
    #             # Get prim type get_prim_object_type
    #             type = get_prim_object_type(path)
    #             if type == "articulation":
    #                 items.append(path)
    #     return items

    # def _photoeye_callback(self, ray, result):
    #     if result.valid:
    #         # Got the raycast result in the callback
    #         print(result.hit_position)

    # def _check_photoeye(self):
    #     ray = omni.kit.raycast.query.Ray((1000, 0, 0), (-1, 0, 0))
    #     self._raycast_interface.submit_raycast_query(ray, self._photoeye_callback)

