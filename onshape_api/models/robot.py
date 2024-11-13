"""
This module contains classes for creating a URDF robot model

Dataclass:
    - **Robot**: Represents a robot model in URDF format, containing links and joints.

"""

import io
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from pathlib import Path

from defusedxml import minidom

from onshape_api.models.joint import BaseJoint
from onshape_api.models.link import Link


@dataclass
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

    name: str
    links: list[Link]
    joints: list[BaseJoint]

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
        for link in self.links:
            link.to_xml(robot)

        for joint in self.joints:
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

        tree = ET.ElementTree(self.to_xml())
        if isinstance(path, (str, Path)):
            xml_str = ET.tostring(tree.getroot(), encoding="unicode")
            pretty_xml_str = minidom.parseString(xml_str).toprettyxml(indent="    ")
            with open(path, "w", encoding="utf-8") as f:
                f.write(pretty_xml_str)
