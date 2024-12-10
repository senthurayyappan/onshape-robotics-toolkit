"""
This module contains classes for creating a URDF robot model

Dataclass:
    - **Robot**: Represents a robot model in URDF format, containing links and joints.

"""

import asyncio
import xml.etree.ElementTree as ET
from enum import Enum
from pathlib import Path
from typing import Optional

from defusedxml import minidom

from onshape_api.connect import Client, DownloadableLink
from onshape_api.graph import create_graph
from onshape_api.log import LOGGER
from onshape_api.models.document import Document
from onshape_api.models.joint import BaseJoint, FixedJoint
from onshape_api.models.link import Link, Origin
from onshape_api.parse import get_instances, get_mates_and_relations, get_parts, get_subassemblies
from onshape_api.urdf import get_urdf_components
from onshape_api.utilities.helpers import save_model_as_json


class RobotType(str, Enum):
    """
    Enum for different types of robots.
    """

    URDF = "urdf"
    MJCF = "xml"

    def __str__(self):
        return self.value


class Robot:
    """
    Represents a robot model in URDF format, containing links and joints.

    Attributes:
        name: str: The name of the robot.
        links: list[Link]: The links of the robot.
        joints: list[BaseJoint]: The joints of the robot.
        document: Document: The document associated with the robot.
        assembly: Assembly: The assembly associated with the robot.

    Methods:
        to_xml: Converts the robot model to an XML element.
        save: Saves the robot model to a URDF file.

    Examples:
        >>> robot = Robot( ... )
        >>> robot.to_xml()
        <Element 'robot' at 0x7f8b3c0b4c70>

        >>> robot.save("robot.urdf")
    """

    def __init__(
        self,
        name: str,
        links: dict[str, Link],
        joints: dict[str, BaseJoint],
        assets: Optional[dict[str, DownloadableLink]] = None,
        robot_type: RobotType = RobotType.URDF,
    ):
        self.name = name
        self.links = links
        self.joints = joints
        self.assets = assets
        self.type = robot_type

        self.element: ET.Element = self.to_xml(robot_type=self.type)
        self.tree: ET.ElementTree = ET.ElementTree(self.element)

    def to_xml(self, robot_type: RobotType) -> ET.Element:
        """
        Convert the robot model to an XML element.

        Returns:
            The XML element representing the robot model.

        Examples:
            >>> robot = Robot( ... )
            >>> robot.to_xml()
            <Element 'robot' at 0x7f8b3c0b4c70>
        """
        robot = ET.Element("robot", name=self.name)
        for link in self.links.values():
            link.to_xml(robot)

        for joint in self.joints.values():
            joint.to_xml(robot)
        return robot

    def save(self) -> None:
        """
        Save the robot model to a URDF file.

        Examples:
            >>> robot = Robot( ... )
            >>> robot.save()
        """
        path = f"{self.name}.{self.type}"
        # download assets before saving the URDF file
        asyncio.run(self._download_assets())

        if isinstance(path, (str, Path)):
            xml_str = ET.tostring(self.tree.getroot(), encoding="unicode")
            pretty_xml_str = minidom.parseString(xml_str).toprettyxml(indent="    ")
            with open(path, "w", encoding="utf-8") as f:
                f.write(pretty_xml_str)

        LOGGER.info(f"Robot model saved to {path}")

    def show(self) -> None:
        """
        Display the robot model in a GUI window.

        Examples:
            >>> robot = Robot( ... )
            >>> robot.show()
        """

        def print_tree(element: ET.Element, prefix: str = ""):
            """
            Recursive helper function to print the tree structure.

            Args:
                element (ET.Element): The current XML element.
                prefix (str): The current prefix for formatting the tree.
            """
            print(f"{prefix}└── {element.tag} (Attributes: {element.attrib})")
            children = list(element)
            for i, child in enumerate(children):
                is_last = i == len(children) - 1
                next_prefix = f"{prefix}    " if is_last else f"{prefix}│   "
                print_tree(child, next_prefix)

        print(f"Robot Tree for '{self.name}':")
        print_tree(self.element)

    async def _download_assets(self) -> None:
        """
        Asynchronously download the assets of the robot model.

        Logs progress and errors during the download process.
        """
        if not self.assets:
            LOGGER.warning("No assets found for the robot model.")
            return

        LOGGER.info("Downloading assets for the robot model.")

        # Create tasks for all asset downloads
        tasks = [asset.download() for asset in self.assets.values()]
        try:
            await asyncio.gather(*tasks)
            LOGGER.info("All assets downloaded successfully.")
        except Exception as e:
            LOGGER.error(f"Error during asset download: {e}")
            return


def get_robot(
    robot_name: str,
    url: str,
    env: str = "./.env",
    max_traversal_depth: int = 5,
    use_user_defined_root: bool = False,
    save_assembly_as_json: bool = False,
) -> Robot:
    """
    Get a robot model from an Onshape assembly. A convenience function that combines the parsing and
    URDF generation steps. It is recommended to use this function for most use cases but if you need more
    control over the process, you can use the individual functions in the `parse` and `urdf` modules.

    Args:
        robot_name (str): The name of the robot.
        url (str): The URL of the Onshape document.
        env (str): The path to the environment file.
        max_traversal_depth (int): The maximum depth to traverse the assembly tree.
        use_user_defined_root (bool): Whether to use the user-defined root node.
        save_assembly_as_json (bool): Whether to save the assembly as a JSON file.

    Returns:
        Robot: The robot model.

    Examples:
        >>> robot = get_robot(
        ...     robot_name="Test",
        ...     url="https://cad.onshape.com/documents/1f42f849180e6e5c9abfce52/w/0c00b6520fac5fada24b2104/e/c96b40ef586e60c182f41d29",
        ...     env="./.env",
        ...     max_traversal_depth=5,
        ...     use_user_defined_root=False,
        ...     save_assembly_as_json=False
        ... )
    """

    document = Document.from_url(url)
    client = Client(base_url=document.base_url, env=env)
    assembly = client.get_assembly(
        did=document.did,
        wtype=document.wtype,
        wid=document.wid,
        eid=document.eid,
        log_response=False,
    )

    if save_assembly_as_json:
        assembly_robot_name = f"{assembly.document.name + '-' + assembly.name}"
        save_model_as_json(assembly, f"{assembly_robot_name}.json")

    LOGGER.info(assembly.document.url)

    instances, occurrences, id_to_name_map = get_instances(assembly, max_depth=max_traversal_depth)
    subassemblies, rigid_subassemblies = get_subassemblies(assembly, client, instances)

    parts = get_parts(assembly, rigid_subassemblies, client, instances)
    mates, relations = get_mates_and_relations(assembly, subassemblies, rigid_subassemblies, id_to_name_map, parts)

    graph, root_node = create_graph(
        occurrences=occurrences,
        instances=instances,
        parts=parts,
        mates=mates,
        use_user_defined_root=use_user_defined_root,
    )

    links, joints, assets = get_urdf_components(
        assembly=assembly,
        graph=graph,
        root_node=root_node,
        parts=parts,
        mates=mates,
        relations=relations,
        client=client,
    )

    return Robot(name=robot_name, links=links, joints=joints, assets=assets)


if __name__ == "__main__":
    robot = Robot(
        name="Test",
        links={
            "link1": Link(name="link1"),
            "link2": Link(name="link2"),
        },
        joints={
            "joint1": FixedJoint(name="joint1", parent="link1", child="link2", origin=Origin.zero_origin()),
        },
        robot_type=RobotType.MJCF,
    )

    robot.save()
