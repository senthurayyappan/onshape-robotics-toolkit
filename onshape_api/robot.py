"""
This module contains classes for creating a URDF robot model

Dataclass:
    - **Robot**: Represents a robot model in URDF format, containing links and joints.

"""

import asyncio
from enum import Enum
from typing import Optional

import networkx as nx
from lxml import etree as ET

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
from onshape_api.parse import (
    MATE_JOINER,
    RELATION_PARENT,
    get_instances,
    get_mates_and_relations,
    get_parts,
    get_subassemblies,
)
from onshape_api.urdf import get_joint_name, get_robot_joint, get_robot_link, get_topological_mates


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
        self.assets: Optional[dict[str, Asset]] = assets
        self.type: RobotType = robot_type

        # Onshape assembly attributes
        self.parts: dict[str, Part] = {}
        self.mates: dict[str, MateFeatureData] = {}
        self.relations: dict[str, MateRelationFeatureData] = {}

        self.subassemblies: dict[str, SubAssembly] = {}
        self.rigid_subassemblies: dict[str, RootAssembly] = {}

        self.assembly: Optional[Assembly] = None

    def add_link(self, link: Link) -> None:
        """Add a link to the graph."""
        self.graph.add_node(link.name, data=link)

    def add_joint(self, joint: BaseJoint) -> None:
        """Add a joint to the graph."""
        self.graph.add_edge(joint.parent, joint.child, data=joint)

    def to_urdf(self) -> str:
        """Generate URDF XML from the graph."""
        robot = ET.Element("robot", name=self.name)

        # Add links
        for link_name, link_data in self.graph.nodes(data="data"):
            if link_data is not None:
                link_data.to_xml(robot)  # Assuming Link has `to_xml`
            else:
                LOGGER.warning(f"Link {link_name} has no data.")
                print(link_data)

        # Add joints
        for parent, child, joint_data in self.graph.edges(data="data"):
            if joint_data is not None:
                joint_data.to_xml(robot)  # Assuming Joint has `to_xml`
            else:
                LOGGER.warning(f"Joint between {parent} and {child} has no data.")

        return ET.tostring(robot, pretty_print=True, encoding="unicode")

    def save(self, file_path: Optional[str] = None, download_assets: bool = True) -> None:
        """Save the robot model to a URDF file."""
        if download_assets and self.assets:
            asyncio.run(self._download_assets())

        if not file_path:
            file_path = f"{self.name}.urdf"

        # Add XML declaration
        xml_declaration = '<?xml version="1.0" ?>\n'
        urdf_str = xml_declaration + self.to_urdf()
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(urdf_str)

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

        tasks = [asset.download() for asset in self.assets.values()]
        try:
            await asyncio.gather(*tasks)
            LOGGER.info("All assets downloaded successfully.")
        except Exception as e:
            LOGGER.error(f"Error downloading assets: {e}")

    @classmethod
    def from_urdf(cls, filename: str) -> "Robot":
        """Load a robot model from a URDF file."""
        tree: ET.ElementTree = ET.parse(filename)  # noqa: S320
        root: ET.Element = tree.getroot()

        name = root.attrib["name"]
        robot = cls(name=name)

        for element in root:
            if element.tag == "link":
                link = Link.from_xml(element)  # Assuming Link.from_xml exists
                robot.add_link(link)
            elif element.tag == "joint":
                joint = set_joint_from_xml(element)  # Assuming set_joint_from_xml exists
                if joint:
                    robot.add_joint(joint)

        return robot

    @classmethod
    def from_url(
        cls, name: str, url: str, client: Client, max_depth: int = 0, use_user_defined_root: bool = False
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
    LOGGER.set_file_name("robot.log")

    # robot = Robot(
    #     name="Test",
    #     links={
    #         "link1": Link(name="link1"),
    #         "link2": Link(name="link2"),
    #     },
    #     joints={
    #         "joint1": FixedJoint(name="joint1", parent="link1", child="link2", origin=Origin.zero_origin()),
    #     },
    #     robot_type=RobotType.URDF,
    # )

    # robot.save()

    robot = Robot.from_urdf("E:/onshape-api/playground/20240920_umv_mini/20240920_umv_mini/20240920_umv_mini.urdf")
    # robot.show()
    plot_graph(robot.graph)
    # robot.save(file_path="E:/onshape-api/playground/test.urdf", download_assets=False)
