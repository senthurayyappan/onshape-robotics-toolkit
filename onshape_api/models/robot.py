import io
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from pathlib import Path

from onshape_api.models.assembly import Assembly
from onshape_api.models.document import Document
from onshape_api.models.geometry import BoxGeometry, CylinderGeometry
from onshape_api.models.joint import BaseJoint, JointDynamics, JointLimits, RevoluteJoint
from onshape_api.models.link import (
    COLORS,
    Axis,
    CollisionLink,
    Inertia,
    InertialLink,
    Link,
    Material,
    Origin,
    VisualLink,
)


@dataclass
class Robot:
    name: str
    parts: list[Link | BaseJoint]
    document: Document = None
    assembly: Assembly = None

    def to_xml(self) -> ET.Element:
        robot = ET.Element("robot", name=self.name)
        for part in self.parts:
            part.to_xml(robot)
        return robot

    def save(self, path: str | Path | io.StringIO) -> None:
        tree = ET.ElementTree(self.to_xml())
        # save to file
        if isinstance(path, (str, Path)):
            tree.write(path, encoding="unicode", xml_declaration=True)


if __name__ == "__main__":
    """
    Example usage of the URDF classes
    """
    # Define the robot
    robot = Robot(
        name="my_robot",
        parts=[
            Link(
                name="base_link",
                visual=VisualLink(
                    origin=Origin.zero_origin(),
                    geometry=CylinderGeometry(radius=0.1, length=0.1),
                    material=Material.from_color(COLORS.RED),
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
            RevoluteJoint(
                name="joint1",
                parent="base_link",
                child="link1",
                origin=Origin.zero_origin(),
                limits=JointLimits(effort=1.0, velocity=1.0, lower=-1.0, upper=1.0),
                axis=Axis(xyz=(0.0, 0.0, 1.0)),
                dynamics=JointDynamics(damping=0.1, friction=0.1),
            ),
            Link(
                name="link1",
                visual=VisualLink(
                    origin=Origin((0.2, 0.0, 0.0), (0.0, 0.0, 0.0)),
                    geometry=BoxGeometry(size=(0.2, 0.1, 0.1)),
                    material=Material.from_color(COLORS.CYAN),
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
        ],
    )

    # Save the robot to a file
    robot.save("test.urdf")
