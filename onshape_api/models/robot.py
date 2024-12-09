"""
This module contains classes for creating a URDF robot model

Dataclass:
    - **Robot**: Represents a robot model in URDF format, containing links and joints.

"""

import asyncio
import io
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Optional

from defusedxml import minidom

from onshape_api.connect import DownloadableLink
from onshape_api.log import LOGGER
from onshape_api.models.joint import BaseJoint, FixedJoint
from onshape_api.models.link import Link, Origin


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
    ):
        self.name = name
        self.links = links
        self.joints = joints
        self.assets = assets

    def to_xml(self) -> ET.Element:
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

    def save(self, path: str | Path | io.StringIO) -> None:
        """
        Save the robot model to a URDF file.

        Args:
            path (str, Path, io.StringIO): The path to save the URDF file.

        Examples:
            >>> robot = Robot( ... )
            >>> robot.save("robot.urdf")
        """
        # download assets before saving the URDF file
        asyncio.run(self.download_assets())

        tree = ET.ElementTree(self.to_xml())
        if isinstance(path, (str, Path)):
            xml_str = ET.tostring(tree.getroot(), encoding="unicode")
            pretty_xml_str = minidom.parseString(xml_str).toprettyxml(indent="    ")
            with open(path, "w", encoding="utf-8") as f:
                f.write(pretty_xml_str)

        LOGGER.info(f"Robot model saved to {path}")

    async def download_assets(self) -> None:
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

    def show(self) -> None:
        """
        Display the robot model in a GUI window.

        Examples:
            >>> robot = Robot( ... )
            >>> robot.show()
        """

        def print_tree(element, prefix=""):
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
        print_tree(self.to_xml())


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
    )

    robot.show()
