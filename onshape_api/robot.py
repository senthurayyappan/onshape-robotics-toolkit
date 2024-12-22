"""
This module contains classes for creating a URDF robot model

Dataclass:
    - **Robot**: Represents a robot model in URDF format, containing links and joints.

"""

import asyncio
from enum import Enum
from typing import Any, Optional

import networkx as nx
import numpy as np
from lxml import etree as ET
from scipy.spatial.transform import Rotation

from onshape_api.connect import Asset, Client
from onshape_api.graph import create_graph, plot_graph
from onshape_api.log import LOGGER
from onshape_api.models.assembly import (
    Assembly,
    MateFeatureData,
    MateRelationFeatureData,
    Part,
    RelationType,
    RootAssembly,
    SubAssembly,
)
from onshape_api.models.document import Document
from onshape_api.models.joint import (
    BaseJoint,
    ContinuousJoint,
    FixedJoint,
    FloatingJoint,
    JointMimic,
    JointType,
    PrismaticJoint,
    RevoluteJoint,
)
from onshape_api.models.link import Link
from onshape_api.models.mjcf import Actuator, Encoder, ForceSensor, Light, Sensor
from onshape_api.parse import (
    MATE_JOINER,
    RELATION_PARENT,
    get_instances,
    get_mates_and_relations,
    get_parts,
    get_subassemblies,
)
from onshape_api.urdf import get_joint_name, get_robot_joint, get_robot_link, get_topological_mates
from onshape_api.utilities.helpers import format_number

DEFAULT_COMPILER_ATTRIBUTES = {
    "angle": "radian",
    "eulerseq": "xyz",
    # "meshdir": "meshes",
}

DEFAULT_OPTION_ATTRIBUTES = {"timestep": "0.001", "gravity": "0 0 -9.81", "iterations": "50", "solver": "PGS"}

URDF_EULER_SEQ = "xyz"  # URDF uses XYZ fixed angles
MJCF_EULER_SEQ = "XYZ"  # MuJoCo uses XYZ extrinsic rotations, capitalization matters

ACTUATOR_SUFFIX = "-actuator"


class RobotType(str, Enum):
    """
    Enum for different types of robots.
    """

    URDF = "urdf"
    MJCF = "xml"

    def __str__(self):
        return self.value


def set_joint_from_xml(element: ET.Element) -> BaseJoint | None:
    """
    Set the joint type from an XML element.

    Args:
        element (ET.Element): The XML element.

    Returns:
        BaseJoint: The joint type.

    Examples:
        >>> element = ET.Element("joint", type="fixed")
        >>> set_joint_from_xml(element)
        <FixedJoint>
    """
    joint_type = element.attrib["type"]
    if joint_type == JointType.FIXED:
        return FixedJoint.from_xml(element)
    elif joint_type == JointType.REVOLUTE:
        return RevoluteJoint.from_xml(element)
    elif joint_type == JointType.CONTINUOUS:
        return ContinuousJoint.from_xml(element)
    elif joint_type == JointType.PRISMATIC:
        return PrismaticJoint.from_xml(element)
    elif joint_type == JointType.FLOATING:
        return FloatingJoint.from_xml(element)
    return None


class Robot:
    """
    Represents a robot model with a graph structure for links and joints.

    Attributes:
        name (str): The name of the robot.
        graph (nx.DiGraph): The graph structure holding links (nodes) and joints (edges).
        assets (Optional[dict[str, Asset]]): Assets associated with the robot.
        type (RobotType): The type of the robot (URDF, MJCF, etc.).

    Methods:
        add_link: Add a link to the graph.
        add_joint: Add a joint to the graph.
        to_urdf: Generate URDF XML from the graph.
        save: Save the robot model to a URDF file.
        show: Display the robot's graph as a tree.
        from_urdf: Create a robot model from a URDF file.
    """

    def __init__(self, name: str, assets: Optional[dict[str, Asset]] = None, robot_type: RobotType = RobotType.URDF):
        self.name: str = name
        self.graph: nx.DiGraph = nx.DiGraph()  # Graph to hold links and joints

        if assets is None:
            self.assets: dict[str, Asset] = {}
        else:
            self.assets: dict[str, Asset] = assets

        self.type: RobotType = robot_type

        # Onshape assembly attributes
        self.parts: dict[str, Part] = {}
        self.mates: dict[str, MateFeatureData] = {}
        self.relations: dict[str, MateRelationFeatureData] = {}

        self.subassemblies: dict[str, SubAssembly] = {}
        self.rigid_subassemblies: dict[str, RootAssembly] = {}

        self.assembly: Optional[Assembly] = None

        # MuJoCo attributes
        self.lights: dict[str, Any] = {}
        self.cameras: dict[str, Any] = {}
        self.actuators: dict[str, Any] = {}
        self.sensors: dict[str, Any] = {}

        self.position: tuple[float, float, float] = (0, 0, 0)
        self.ground_position: tuple[float, float, float] = (0, 0, 0)
        self.compiler_attributes: dict[str, str] = DEFAULT_COMPILER_ATTRIBUTES
        self.option_attributes: dict[str, str] = DEFAULT_OPTION_ATTRIBUTES

    def add_link(self, link: Link) -> None:
        """Add a link to the graph."""
        self.graph.add_node(link.name, data=link)

    def add_joint(self, joint: BaseJoint) -> None:
        """Add a joint to the graph."""
        self.graph.add_edge(joint.parent, joint.child, data=joint)

    def set_robot_position(self, pos: tuple[float, float, float]) -> None:
        self.position = pos

    def set_ground_position(self, pos: tuple[float, float, float]) -> None:
        self.ground_position = pos

    def set_compiler_attributes(self, attributes: dict[str, str]) -> None:
        self.compiler_attributes = attributes

    def set_option_attributes(self, attributes: dict[str, str]) -> None:
        self.option_attributes = attributes

    def add_light(
        self,
        name: str,
        directional: bool,
        diffuse: tuple[float, float, float],
        specular: tuple[float, float, float],
        pos: tuple[float, float, float],
        direction: tuple[float, float, float],
        castshadow: bool,
    ) -> None:
        self.lights[name] = Light(
            directional=directional,
            diffuse=diffuse,
            specular=specular,
            pos=pos,
            direction=direction,
            castshadow=castshadow,
        )

    def add_actuator(
        self,
        actuator_name: str,
        joint_name: str,
        ctrl_limited: bool,
        gear: float,
        add_encoder: bool = True,
        add_force_sensor: bool = True,
        ctrl_range: tuple[float, float] = (0, 0),
    ) -> None:

        self.actuators[actuator_name] = Actuator(
            name=actuator_name,
            joint=joint_name,
            ctrllimited=ctrl_limited,
            gear=gear,
            ctrlrange=ctrl_range,
        )

        if add_encoder:
            self.add_sensor(actuator_name + "-enc", Encoder(actuator_name, actuator_name))

        if add_force_sensor:
            self.add_sensor(actuator_name + "-frc", ForceSensor(actuator_name + "-frc", actuator_name))

    def add_sensor(self, name: str, sensor: Sensor) -> None:
        self.sensors[name] = sensor

    def add_custom_element(
        self,
        parent: ET.Element,
        tag: str,
        name: Optional[str] = None,
        attributes: Optional[dict[str, str]] = None,
    ) -> ET.Element:
        """
        Add a custom XML element to a parent element.

        Args:
            parent: The parent element to append to
            tag: The tag name for the new element
            name: Optional name attribute for the element
            attributes: Optional dictionary of attribute key-value pairs

        Returns:
            ET.Element: The newly created element

        Examples:
            >>> # Add ground plane
            >>> ground = robot.add_custom_element(
            ...     worldbody,
            ...     "geom",
            ...     name="ground",
            ...     attributes={
            ...         "type": "plane",
            ...         "pos": "0 0 0",
            ...         "size": "2 2 0.001",
            ...         "condim": "3"
            ...     }
            ... )
        """
        element = ET.Element(tag)
        if name:
            element.set("name", name)

        if attributes:
            for key, value in attributes.items():
                element.set(key, str(value))

        parent.append(element)
        return element

    def set_element_attributes(
        self,
        element: ET.Element,
        attributes: dict[str, str],
    ) -> None:
        """
        Set or update attributes of an existing XML element.

        Args:
            element: The element to modify
            attributes: Dictionary of attribute key-value pairs to set/update

        Examples:
            >>> # Update existing element attributes
            >>> robot.set_element_attributes(
            ...     ground_element,
            ...     {"size": "3 3 0.001", "friction": "1 0.5 0.5"}
            ... )
        """
        for key, value in attributes.items():
            element.set(key, str(value))

    def add_ground_plane(
        self, root: ET.Element, size: int = 2, orientation: tuple[float, float, float] = (0, 0, 0)
    ) -> ET.Element:
        """
        Add a ground plane to the root element with associated texture and material.

        Args:
            root: The root element to append the ground plane to
            size: Size of the ground plane (default: 2)
            orientation: Euler angles for orientation (default: (0, 0, 0))

        Returns:
            ET.Element: The ground plane element
        """
        # Add ground plane geom
        attributes = {
            "type": "plane",
            "pos": " ".join(map(str, self.ground_position)),
            "euler": " ".join(map(str, orientation)),
            "size": f"{size} {size} 0.001",
            "condim": "3",
            "conaffinity": "15",
            "material": "grid"
        }

        return self.add_custom_element(root, "geom", name="ground", attributes=attributes)

    def add_ground_plane_assets(self, root: ET.Element) -> None:
        # Add texture definition
        self.add_custom_element(
            root,
            "texture",
            name="checker",
            attributes={
                "type": "2d",
                "builtin": "checker",
                "rgb1": ".1 .2 .3",
                "rgb2": ".2 .3 .4",
                "width": "300",
                "height": "300"
            }
        )

        # Add material definitions
        self.add_custom_element(
            root,
            "material",
            name="grid",
            attributes={
                "texture": "checker",
                "texrepeat": "8 8",
                "reflectance": ".2"
            }
        )

    def to_urdf(self) -> str:
        """Generate URDF XML from the graph."""
        robot = ET.Element("robot", name=self.name)

        # Add links
        for link_name, link_data in self.graph.nodes(data="data"):
            if link_data is not None:
                link_data.to_xml(robot)
            else:
                LOGGER.warning(f"Link {link_name} has no data.")

        # Add joints
        for parent, child, joint_data in self.graph.edges(data="data"):
            if joint_data is not None:
                joint_data.to_xml(robot)
            else:
                LOGGER.warning(f"Joint between {parent} and {child} has no data.")

        return ET.tostring(robot, pretty_print=True, encoding="unicode")

    def to_mjcf(self) -> str:  # noqa: C901
        """Generate MJCF XML from the graph."""
        model = ET.Element("mujoco", model=self.name)

        ET.SubElement(
            model,
            "compiler",
            attrib=self.compiler_attributes,
        )

        ET.SubElement(
            model,
            "option",
            attrib=self.option_attributes,
        )

        if self.assets:
            asset_element = ET.SubElement(model, "asset")
            for asset in self.assets.values():
                asset.to_mjcf(asset_element)

            self.add_ground_plane_assets(asset_element)
        else:
            # Find or create asset element after default element
            asset = ET.SubElement(model, "asset")
            self.add_ground_plane_assets(asset)

        worldbody = ET.SubElement(model, "worldbody")

        if self.lights:
            for light in self.lights.values():
                light.to_mjcf(worldbody)

        self.add_ground_plane(worldbody)

        root_body = ET.SubElement(worldbody, "body", name=self.name, pos=" ".join(map(str, self.position)))
        ET.SubElement(root_body, "freejoint", name=f"{self.name}_freejoint")

        body_elements = {self.name: root_body}

        for link_name, link_data in self.graph.nodes(data="data"):
            if link_data is not None:
                body_elements[link_name] = link_data.to_mjcf(root_body)
            else:
                LOGGER.warning(f"Link {link_name} has no data.")

        dissolved_transforms = {}

        # First, process all fixed joints
        for parent_name, child_name, joint_data in self.graph.edges(data="data"):
            if joint_data is not None and joint_data.joint_type == "fixed":
                parent_body = body_elements.get(parent_name)
                child_body = body_elements.get(child_name)

                if parent_body is not None and child_body is not None:
                    LOGGER.debug(f"\nProcessing fixed joint from {parent_name} to {child_name}")

                    # Convert joint transform from URDF convention
                    joint_pos = np.array(joint_data.origin.xyz)
                    joint_rot = Rotation.from_euler(URDF_EULER_SEQ, joint_data.origin.rpy)

                    # If parent was dissolved, compose transformations
                    if parent_name in dissolved_transforms:
                        parent_pos, parent_rot = dissolved_transforms[parent_name]
                        # Transform position and rotation
                        joint_pos = parent_rot.apply(joint_pos) + parent_pos
                        joint_rot = parent_rot * joint_rot

                    dissolved_transforms[child_name] = (joint_pos, joint_rot)

                    # Transform geometries
                    for element in list(child_body):
                        if element.tag == "inertial":
                            continue
                        elif element.tag == "geom":
                            current_pos = np.array([float(x) for x in (element.get("pos") or "0 0 0").split()])
                            current_euler = np.array([float(x) for x in (element.get("euler") or "0 0 0").split()])

                            # Convert current rotation from MuJoCo convention
                            current_rot = Rotation.from_euler(MJCF_EULER_SEQ, current_euler, degrees=False)

                            # Apply the dissolved transformation
                            new_pos = joint_rot.apply(current_pos) + joint_pos
                            new_rot = joint_rot * current_rot  # Order matters for rotation composition

                            # Convert back to MuJoCo convention - explicitly specify intrinsic/extrinsic
                            new_euler = new_rot.as_euler(MJCF_EULER_SEQ, degrees=False)

                            element.set("pos", " ".join(format_number(v) for v in new_pos))
                            element.set("euler", " ".join(format_number(v) for v in new_euler))

                        parent_body.append(element)

                    root_body.remove(child_body)
                    body_elements[child_name] = parent_body

        # Then process revolute joints
        for parent_name, child_name, joint_data in self.graph.edges(data="data"):
            if joint_data is not None and joint_data.joint_type != "fixed":
                parent_body = body_elements.get(parent_name)
                child_body = body_elements.get(child_name)

                if parent_body is not None and child_body is not None:
                    LOGGER.debug(f"\nProcessing revolute joint from {parent_name} to {child_name}")

                    # Get dissolved parent transform
                    if parent_name in dissolved_transforms:
                        parent_pos, parent_rot = dissolved_transforms[parent_name]
                    else:
                        parent_pos = np.array([0, 0, 0])
                        parent_rot = Rotation.from_euler(URDF_EULER_SEQ, [0, 0, 0])

                    # Convert joint transform from URDF convention
                    joint_pos = np.array(joint_data.origin.xyz)
                    joint_rot = Rotation.from_euler(URDF_EULER_SEQ, joint_data.origin.rpy)

                    # Apply parent's dissolved transformation
                    final_pos = parent_rot.apply(joint_pos) + parent_pos
                    final_rot = parent_rot * joint_rot

                    # Convert to MuJoCo convention while maintaining the joint axis orientation
                    final_euler = final_rot.as_euler(MJCF_EULER_SEQ, degrees=False)

                    LOGGER.debug(f"Joint {parent_name}->{child_name}:")
                    LOGGER.debug(f"  Original: pos={joint_data.origin.xyz}, rpy={joint_data.origin.rpy}")
                    LOGGER.debug(f"  Final: pos={final_pos}, euler={final_euler}")

                    # Update child body transformation
                    child_body.set("pos", " ".join(format_number(v) for v in final_pos))
                    child_body.set("euler", " ".join(format_number(v) for v in final_euler))

                    # Create joint with zero origin
                    joint_data.origin.xyz = [0, 0, 0]
                    joint_data.origin.rpy = [0, 0, 0]
                    joint_data.to_mjcf(child_body)

                    # Move child under parent
                    parent_body.append(child_body)

        if self.actuators:
            actuator_element = ET.SubElement(model, "actuator")
            for actuator in self.actuators.values():
                actuator.to_mjcf(actuator_element)

        if self.sensors:
            sensor_element = ET.SubElement(model, "sensor")
            for sensor in self.sensors.values():
                sensor.to_mjcf(sensor_element)

        return ET.tostring(model, pretty_print=True, encoding="unicode")

    def save(self, file_path: Optional[str] = None, download_assets: bool = True) -> None:
        """Save the robot model to a URDF file."""
        if download_assets and self.assets:
            asyncio.run(self._download_assets())

        if not file_path:
            LOGGER.warning("No file path provided. Saving to current directory.")
            LOGGER.warning("Please keep in mind that the path to the assets will not be updated")
            file_path = f"{self.name}.{self.type}"

        xml_declaration = '<?xml version="1.0" ?>\n'

        if self.type == RobotType.URDF:
            urdf_str = xml_declaration + self.to_urdf()
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(urdf_str)

        elif self.type == RobotType.MJCF:
            mjcf_str = xml_declaration + self.to_mjcf()
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(mjcf_str)

        LOGGER.info(f"Robot model saved to {file_path}")

    def show_tree(self) -> None:
        """Display the robot's graph as a tree structure."""

        def print_tree(node, depth=0):
            prefix = "    " * depth
            print(f"{prefix}{node}")
            for child in self.graph.successors(node):
                print_tree(child, depth + 1)

        root_nodes = [n for n in self.graph.nodes if self.graph.in_degree(n) == 0]
        for root in root_nodes:
            print_tree(root)

    def show_graph(self, file_name: Optional[str] = None) -> None:
        """Display the robot's graph as a directed graph."""
        plot_graph(self.graph, file_name=file_name)

    async def _download_assets(self) -> None:
        """Asynchronously download the assets."""
        if not self.assets:
            LOGGER.warning("No assets found for the robot model.")
            return

        tasks = [asset.download() for asset in self.assets.values() if not asset.is_from_file]
        try:
            await asyncio.gather(*tasks)
            LOGGER.info("All assets downloaded successfully.")
        except Exception as e:
            LOGGER.error(f"Error downloading assets: {e}")

    @classmethod
    def from_urdf(cls, file_name: str, robot_type: RobotType) -> "Robot":  # noqa: C901
        """Load a robot model from a URDF file."""
        tree: ET.ElementTree = ET.parse(file_name)  # noqa: S320
        root: ET.Element = tree.getroot()

        name = root.attrib["name"]
        robot = cls(name=name, robot_type=robot_type)

        for element in root:
            if element.tag == "link":
                link = Link.from_xml(element)
                robot.add_link(link)

                # Process the visual element within the link
                visual = element.find("visual")
                if visual is not None:
                    geometry = visual.find("geometry")
                    if geometry is not None:
                        mesh = geometry.find("mesh")
                        if mesh is not None:
                            file_name = mesh.attrib.get("filename")
                            if file_name and file_name not in robot.assets:
                                robot.assets[file_name] = Asset.from_file(file_name)

                # Process the collision element within the link
                collision = element.find("collision")
                if collision is not None:
                    geometry = collision.find("geometry")
                    if geometry is not None:
                        mesh = geometry.find("mesh")
                        if mesh is not None:
                            file_name = mesh.attrib.get("filename")
                            if file_name and file_name not in robot.assets:
                                robot.assets[file_name] = Asset.from_file(file_name)

            elif element.tag == "joint":
                joint = set_joint_from_xml(element)
                if joint:
                    robot.add_joint(joint)

        return robot

    @classmethod
    def from_url(
        cls,
        name: str,
        url: str,
        client: Client,
        max_depth: int = 0,
        use_user_defined_root: bool = False,
        robot_type: RobotType = RobotType.URDF,
    ) -> "Robot":
        """Create a robot model from an Onshape CAD assembly."""

        document = Document.from_url(url=url)
        client.set_base_url(document.base_url)

        assembly = client.get_assembly(
            did=document.did,
            wtype=document.wtype,
            wid=document.wid,
            eid=document.eid,
            log_response=False,
            with_meta_data=True,
        )

        instances, occurrences, id_to_name_map = get_instances(assembly=assembly, max_depth=max_depth)
        subassemblies, rigid_subassemblies = get_subassemblies(assembly=assembly, client=client, instances=instances)

        parts = get_parts(
            assembly=assembly, rigid_subassemblies=rigid_subassemblies, client=client, instances=instances
        )
        mates, relations = get_mates_and_relations(
            assembly=assembly,
            subassemblies=subassemblies,
            rigid_subassemblies=rigid_subassemblies,
            id_to_name_map=id_to_name_map,
            parts=parts,
        )

        graph, root_node = create_graph(
            occurrences=occurrences,
            instances=instances,
            parts=parts,
            mates=mates,
            use_user_defined_root=use_user_defined_root,
        )

        robot = get_robot(
            assembly=assembly,
            graph=graph,
            root_node=root_node,
            parts=parts,
            mates=mates,
            relations=relations,
            client=client,
            robot_name=name,
        )

        robot.parts = parts
        robot.mates = mates
        robot.relations = relations

        robot.subassemblies = subassemblies
        robot.rigid_subassemblies = rigid_subassemblies

        robot.assembly = assembly

        robot.type = robot_type

        return robot


def get_robot(
    assembly: Assembly,
    graph: nx.DiGraph,
    root_node: str,
    parts: dict[str, Part],
    mates: dict[str, MateFeatureData],
    relations: dict[str, MateRelationFeatureData],
    client: Client,
    robot_name: str,
) -> Robot:
    """
    Generate a Robot instance from an Onshape assembly.

    Args:
        assembly: The Onshape assembly object.
        graph: The graph representation of the assembly.
        root_node: The root node of the graph.
        parts: The dictionary of parts in the assembly.
        mates: The dictionary of mates in the assembly.
        relations: The dictionary of mate relations in the assembly.
        client: The Onshape client object.
        robot_name: Name of the robot.

    Returns:
        Robot: The generated Robot instance.
    """
    robot = Robot(name=robot_name)

    assets_map = {}
    stl_to_link_tf_map = {}
    topological_mates, topological_relations = get_topological_mates(graph, mates, relations)

    LOGGER.info(f"Processing root node: {root_node}")

    root_link, stl_to_root_tf, root_asset = get_robot_link(
        name=root_node, part=parts[root_node], wid=assembly.document.wid, client=client, mate=None
    )
    robot.add_link(root_link)
    assets_map[root_node] = root_asset
    stl_to_link_tf_map[root_node] = stl_to_root_tf

    LOGGER.info(f"Processing {len(graph.edges)} edges in the graph.")

    for parent, child in graph.edges:
        mate_key = f"{parent}{MATE_JOINER}{child}"
        LOGGER.info(f"Processing edge: {parent} -> {child}")
        parent_tf = stl_to_link_tf_map[parent]

        if parent not in parts or child not in parts:
            LOGGER.warning(f"Part {parent} or {child} not found in parts dictionary. Skipping.")
            continue

        joint_mimic = None
        relation = topological_relations.get(topological_mates[mate_key].id)
        if relation:
            multiplier = (
                relation.relationLength
                if relation.relationType == RelationType.RACK_AND_PINION
                else relation.relationRatio
            )
            joint_mimic = JointMimic(
                joint=get_joint_name(relation.mates[RELATION_PARENT].featureId, mates),
                multiplier=multiplier,
                offset=0.0,
            )

        joint_list, link_list = get_robot_joint(
            parent,
            child,
            topological_mates[mate_key],
            parent_tf,
            joint_mimic,
            is_rigid_assembly=parts[parent].isRigidAssembly,
        )

        link, stl_to_link_tf, asset = get_robot_link(
            child, parts[child], assembly.document.wid, client, topological_mates[mate_key]
        )
        stl_to_link_tf_map[child] = stl_to_link_tf
        assets_map[child] = asset

        if child not in robot.graph:
            robot.add_link(link)
        else:
            LOGGER.warning(f"Link {child} already exists in the robot graph. Skipping.")

        for link in link_list:
            if link.name not in robot.graph:
                robot.add_link(link)
            else:
                LOGGER.warning(f"Link {link.name} already exists in the robot graph. Skipping.")

        for joint in joint_list:
            robot.add_joint(joint)

    robot.assets = assets_map
    return robot


if __name__ == "__main__":
    LOGGER.set_file_name("test.log")

    robot = Robot.from_urdf(file_name="E:/onshape-api/playground/ballbot.urdf", robot_type=RobotType.MJCF)
    robot.set_robot_position((0, 0, 0.6))
    robot.show_tree()
    robot.save(file_path="E:/onshape-api/playground/ballbot.xml")

    # import mujoco
    # model = mujoco.MjModel.from_xml_path(file_name="E:/onshape-api/playground/ballbot.urdf")
    # mujoco.mj_saveLastXML("ballbot-raw-ref.xml", model)

    # simulate_robot("test.xml")

    # robot = Robot.from_urdf("E:/onshape-api/playground/20240920_umv_mini/20240920_umv_mini/20240920_umv_mini.urdf")
    # robot.save(file_path="E:/onshape-api/playground/test.urdf", download_assets=False)
