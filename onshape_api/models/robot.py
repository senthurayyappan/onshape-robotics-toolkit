"""
This module contains classes for creating a URDF robot model

Classes:
    - **Robot**: Represents a robot model in URDF format, containing links and joints.

"""

import io
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from pathlib import Path

from onshape_api.models.geometry import BoxGeometry, CylinderGeometry
from onshape_api.models.joint import BaseJoint, JointDynamics, JointLimits, RevoluteJoint
from onshape_api.models.link import (
    Axis,
    CollisionLink,
    Colors,
    Inertia,
    InertialLink,
    Link,
    Material,
    Origin,
    VisualLink,
)


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
            tree.write(path, encoding="unicode", xml_declaration=True)


if __name__ == "__main__":
    """
    Example usage of the Robot class to create a URDF robot model.
    """
    robot = Robot(
        name="my_robot",
        parts=[
            Link(
                name="base_link",
                visual=VisualLink(
                    origin=Origin.zero_origin(),
                    geometry=CylinderGeometry(radius=0.1, length=0.1),
                    material=Material.from_color(Colors.RED),
                ),
                collision=CollisionLink(
                    origin=Origin.zero_origin(),
                    geometry=CylinderGeometry(radius=0.1, length=0.1),
                ),
                inertial=InertialLink(
                    mass=1.0,
                    inertia=Inertia(
                        ixx=0.1,
                        iyy=0.1,
                        izz=0.1,
                        ixy=0.0,
                        ixz=0.0,
                        iyz=0.0,
                    ),
                    origin=Origin.zero_origin(),
                ),
            ),
            Link(
                name="link1",
                visual=VisualLink(
                    origin=Origin((0.2, 0.0, 0.0), (0.0, 0.0, 0.0)),
                    geometry=BoxGeometry(size=(0.2, 0.1, 0.1)),
                    material=Material.from_color(Colors.CYAN),
                ),
                collision=CollisionLink(
                    origin=Origin.zero_origin(),
                    geometry=BoxGeometry(size=(0.2, 0.1, 0.1)),
                ),
                inertial=InertialLink(
                    mass=1.0,
                    inertia=Inertia(
                        ixx=0.1,
                        iyy=0.1,
                        izz=0.1,
                        ixy=0.0,
                        ixz=0.0,
                        iyz=0.0,
                    ),
                    origin=Origin.zero_origin(),
                ),
            ),
            RevoluteJoint(
                name="joint1",
                parent="base_link",
                child="link1",
                origin=Origin.zero_origin(),
                limits=JointLimits(effort=1.0, velocity=1.0, lower=-1.0, upper=1.0),
                axis=Axis(xyz=(0.0, 0.0, 1.0)),
                dynamics=JointDynamics(damping=0.1, friction=0.1),
            ),
        ],
    )
    robot.save("test.urdf")
