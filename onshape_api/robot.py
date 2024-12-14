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

from onshape_api.connect import Asset
from onshape_api.log import LOGGER
from onshape_api.models.joint import (
    BaseJoint,
    ContinuousJoint,
    FixedJoint,
    FloatingJoint,
    JointType,
    PrismaticJoint,
    RevoluteJoint,
)
from onshape_api.models.link import Link


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
        self.name = name
        self.graph = nx.DiGraph()  # Graph to hold links and joints
        self.assets = assets
        self.type = robot_type

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

    def show(self) -> None:
        """Display the robot's graph as a tree structure."""

        def print_tree(node, depth=0):
            prefix = "    " * depth
            print(f"{prefix}{node}")
            for child in self.graph.successors(node):
                print_tree(child, depth + 1)

        root_nodes = [n for n in self.graph.nodes if self.graph.in_degree(n) == 0]
        for root in root_nodes:
            print_tree(root)

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
    robot.show()
    # plot_graph(robot.graph)
    # robot.save(file_path="E:/onshape-api/playground/test.urdf", download_assets=False)
