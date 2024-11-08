"""
This module contains dataclasses for creating a link in a URDF robot model.

Data Classes:
    - **Origin**: Represents the origin of a link in the robot model.
    - **Axis**: Represents the axis of a link in the robot model.
    - **Inertia**: Represents the inertia properties of a link in the robot model.
    - **Material**: Represents the material properties of a link in the robot model.
    - **InertialLink**: Represents the inertial properties of a link in the robot model.
    - **VisualLink**: Represents the visual properties of a link in the robot model.
    - **CollisionLink**: Represents the collision properties of a link in the robot model.
    - **Link**: Represents a link in the robot model.

Enums:
    - **Colors**: Enumerates the possible colors for a link in the robot model.
"""

import xml.etree.ElementTree as ET
from dataclasses import dataclass
from enum import Enum

import numpy as np
from scipy.spatial.transform import Rotation

from onshape_api.models.assembly import Part
from onshape_api.models.geometry import BaseGeometry
from onshape_api.utilities import format_number


class Colors(tuple[float, float, float], Enum):
    """
    Enumerates the possible colors in RGBA format for a link in the robot model.

    Attributes:
        RED (tuple[float, float, float]): Color red.
        GREEN (tuple[float, float, float]): Color green.
        BLUE (tuple[float, float, float]): Color blue.
        YELLOW (tuple[float, float, float]): Color yellow.
        CYAN (tuple[float, float, float]): Color cyan.
        MAGENTA (tuple[float, float, float]): Color magenta.
        WHITE (tuple[float, float, float]): Color white.
        BLACK (tuple[float, float, float]): Color black.
        ORANGE (tuple[float, float, float]): Color orange.
        PINK (tuple[float, float, float]): Color pink.

    Examples:
        >>> Colors.RED
        <Colors.RED: (1.0, 0.0, 0.0)>
    """

    RED = (1.0, 0.0, 0.0, 1.0)
    GREEN = (0.0, 1.0, 0.0, 1.0)
    BLUE = (0.0, 0.0, 1.0, 1.0)
    YELLOW = (1.0, 1.0, 0.0, 1.0)
    CYAN = (0.0, 1.0, 1.0, 1.0)
    MAGENTA = (1.0, 0.0, 1.0, 1.0)
    WHITE = (1.0, 1.0, 1.0, 1.0)
    BLACK = (0.0, 0.0, 0.0, 1.0)
    ORANGE = (1.0, 0.5, 0.0, 1.0)
    PINK = (1.0, 0.0, 0.5, 1.0)


@dataclass
class Origin:
    """
    Represents the origin of a link in the robot model.

    Attributes:
        xyz (tuple[float, float, float]): The x, y, z coordinates of the origin.
        rpy (tuple[float, float, float]): The roll, pitch, yaw angles of the origin.

    Methods:
        to_xml: Converts the origin to an XML element.

    Class Methods:
        from_matrix: Creates an origin from a transformation matrix.
        zero_origin: Creates an origin at the origin (0, 0, 0) with no rotation.

    Examples:
        >>> origin = Origin(xyz=(1.0, 2.0, 3.0), rpy=(0.0, 0.0, 0.0))
        >>> origin.to_xml()
        <Element 'origin' at 0x7f8b3c0b4c70>

        >>> matrix = np.matrix([
        ...     [1, 0, 0, 0],
        ...     [0, 1, 0, 0],
        ...     [0, 0, 1, 0],
        ...     [0, 0, 0, 1],
        ... ])
        >>> Origin.from_matrix(matrix)
        Origin(xyz=(0.0, 0.0, 0.0), rpy=(0.0, 0.0, 0.0))

        >>> Origin.zero_origin()
        Origin(xyz=(0.0, 0.0, 0.0), rpy=(0.0, 0.0, 0.0))
    """

    xyz: tuple[float, float, float]
    rpy: tuple[float, float, float]

    def to_xml(self, root: ET.Element | None = None) -> ET.Element:
        """
        Convert the origin to an XML element.

        Args:
            root: The root element to append the origin to.

        Returns:
            The XML element representing the origin.

        Examples:
            >>> origin = Origin(xyz=(1.0, 2.0, 3.0), rpy=(0.0, 0.0, 0.0))
            >>> origin.to_xml()
            <Element 'origin' at 0x7f8b3c0b4c70>
        """

        origin = ET.Element("origin") if root is None else ET.SubElement(root, "origin")
        origin.set("xyz", " ".join(format_number(v) for v in self.xyz))
        origin.set("rpy", " ".join(format_number(v) for v in self.rpy))
        return origin

    @classmethod
    def from_matrix(cls, matrix: np.matrix) -> "Origin":
        """
        Create an origin from a transformation matrix.

        Args:
            matrix: The transformation matrix.

        Returns:
            The origin created from the transformation matrix.

        Examples:
            >>> matrix = np.matrix([
            ...     [1, 0, 0, 0],
            ...     [0, 1, 0, 0],
            ...     [0, 0, 1, 0],
            ...     [0, 0, 0, 1],
            ... ])
            >>> Origin.from_matrix(matrix)
            Origin(xyz=(0.0, 0.0, 0.0), rpy=(0.0, 0.0, 0.0))
        """

        x = float(matrix[0, 3])
        y = float(matrix[1, 3])
        z = float(matrix[2, 3])
        roll, pitch, yaw = Rotation.from_matrix(matrix[:3, :3]).as_euler("xyz")
        return cls((x, y, z), (roll, pitch, yaw))

    @classmethod
    def zero_origin(cls) -> "Origin":
        """
        Create an origin at the origin (0, 0, 0) with no rotation.

        Returns:
            The origin at the origin (0, 0, 0) with no rotation.

        Examples:
            >>> Origin.zero_origin()
            Origin(xyz=(0.0, 0.0, 0.0), rpy=(0.0, 0.0, 0.0))
        """

        return cls((0.0, 0.0, 0.0), (0.0, 0.0, 0.0))


@dataclass
class Axis:
    """
    Represents the axis of a link in the robot model.

    Attributes:
        xyz (tuple[float, float, float]): The x, y, z coordinates of the axis.

    Methods:
        to_xml: Converts the axis to an XML element.

    Examples:
        >>> axis = Axis(xyz=(1.0, 0.0, 0.0))
        >>> axis.to_xml()
        <Element 'axis' at 0x7f8b3c0b4c70>
    """

    xyz: tuple[float, float, float]

    def to_xml(self, root: ET.Element | None = None) -> ET.Element:
        """
        Convert the axis to an XML element.

        Args:
            root: The root element to append the axis to.

        Returns:
            The XML element representing the axis.

        Examples:
            >>> axis = Axis(xyz=(1.0, 0.0, 0.0))
            >>> axis.to_xml()
            <Element 'axis' at 0x7f8b3c0b4c70>
        """

        axis = ET.Element("axis") if root is None else ET.SubElement(root, "axis")
        axis.set("xyz", " ".join(format_number(v) for v in self.xyz))
        return axis


@dataclass
class Inertia:
    """
    Represents the inertia tensor of a link in the robot model.

    Attributes:
        ixx (float): The inertia tensor element Ixx.
        iyy (float): The inertia tensor element Iyy.
        izz (float): The inertia tensor element Izz.
        ixy (float): The inertia tensor element Ixy.
        ixz (float): The inertia tensor element Ixz.
        iyz (float): The inertia tensor element Iyz.

    Methods:
        to_xml: Converts the inertia tensor to an XML element.

    Examples:
        >>> inertia = Inertia(ixx=1.0, iyy=2.0, izz=3.0, ixy=0.0, ixz=0.0, iyz=0.0)
        >>> inertia.to_xml()
        <Element 'inertia' at 0x7f8b3c0b4c70>
    """

    ixx: float
    iyy: float
    izz: float
    ixy: float
    ixz: float
    iyz: float

    def to_xml(self, root: ET.Element | None = None) -> ET.Element:
        """
        Convert the inertia tensor to an XML element.

        Args:
            root: The root element to append the inertia tensor to.

        Returns:
            The XML element representing the inertia tensor.

        Examples:
            >>> inertia = Inertia(ixx=1.0, iyy=2.0, izz=3.0, ixy=0.0, ixz=0.0, iyz=0.0)
            >>> inertia.to_xml()
            <Element 'inertia' at 0x7f8b3c0b4c70>
        """

        inertia = ET.Element("inertia") if root is None else ET.SubElement(root, "inertia")
        inertia.set("ixx", format_number(self.ixx))
        inertia.set("iyy", format_number(self.iyy))
        inertia.set("izz", format_number(self.izz))
        inertia.set("ixy", format_number(self.ixy))
        inertia.set("ixz", format_number(self.ixz))
        inertia.set("iyz", format_number(self.iyz))
        return inertia


@dataclass
class Material:
    """
    Represents the material properties of a link in the robot model.

    Attributes:
        name (str): The name of the material.
        color (tuple[float, float, float, float]): The color of the material in RGBA format.

    Methods:
        to_xml: Converts the material properties to an XML element.

    Class Methods:
        from_color: Creates a material from a color.

    Examples:
        >>> material = Material(name="material", color=(1.0, 0.0, 0.0, 1.0))
        >>> material.to_xml()
        <Element 'material' at 0x7f8b3c0b4c70>

        >>> Material.from_color(name="material", color=Colors.RED)
        Material(name='material', color=(1.0, 0.0, 0.0, 1.0))
    """

    name: str
    color: tuple[float, float, float, float]

    def to_xml(self, root: ET.Element | None = None) -> ET.Element:
        """
        Convert the material properties to an XML element.

        Args:
            root: The root element to append the material properties to.

        Returns:
            The XML element representing the material properties.

        Examples:
            >>> material = Material(name="material", color=(1.0, 0.0, 0.0, 1.0))
            >>> material.to_xml()
            <Element 'material' at 0x7f8b3c0b4c70>
        """

        material = ET.Element("material") if root is None else ET.SubElement(root, "material")
        material.set("name", self.name)
        ET.SubElement(material, "color", rgba=" ".join(format_number(v) for v in self.color))
        return material

    @classmethod
    def from_color(cls, name: str, color: Colors) -> "Material":
        """
        Create a material from a color.

        Args:
            name: The name of the material.
            color: The color of the material.

        Returns:
            The material created from the color.

        Examples:
            >>> Material.from_color(name="material", color=Colors.RED)
            Material(name='material', color=(1.0, 0.0, 0.0, 1.0))
        """
        return cls(name, color)


@dataclass
class InertialLink:
    """
    Represents the inertial properties of a link in the robot model.

    Attributes:
        mass (float): The mass of the link.
        inertia (Inertia): The inertia properties of the link.
        origin (Origin): The origin of the link.

    Methods:
        to_xml: Converts the inertial properties to an XML element.

    Examples:
        >>> inertial = InertialLink(mass=1.0, inertia=Inertia(...), origin=Origin(...))
        >>> inertial.to_xml()
        <Element 'inertial' at 0x7f8b3c0b4c70>
    """

    mass: float
    inertia: Inertia
    origin: Origin

    def to_xml(self, root: ET.Element | None = None) -> ET.Element:
        """
        Convert the inertial properties to an XML element.

        Args:
            root: The root element to append the inertial properties to.

        Returns:
            The XML element representing the inertial properties.

        Examples:
            >>> inertial = InertialLink(mass=1.0, inertia=Inertia(...), origin=Origin(...))
            >>> inertial.to_xml()
            <Element 'inertial' at 0x7f8b3c0b4c70>
        """
        inertial = ET.Element("inertial") if root is None else ET.SubElement(root, "inertial")
        ET.SubElement(inertial, "mass", value=format_number(self.mass))
        self.inertia.to_xml(inertial)
        self.origin.to_xml(inertial)
        return inertial


@dataclass
class VisualLink:
    """
    Represents the visual properties of a link in the robot model.

    Attributes:
        origin (Origin): The origin of the link.
        geometry (BaseGeometry): The geometry of the link.
        material (Material): The material properties of the link.

    Methods:
        to_xml: Converts the visual properties to an XML element.

    Examples:
        >>> visual = VisualLink(origin=Origin(...), geometry=BoxGeometry(...), material=Material(...))
        >>> visual.to_xml()
        <Element 'visual' at 0x7f8b3c0b4c70>
    """

    origin: Origin
    geometry: BaseGeometry
    material: Material

    def to_xml(self, root: ET.Element | None = None) -> ET.Element:
        """
        Convert the visual properties to an XML element.

        Args:
            root: The root element to append the visual properties to.

        Returns:
            The XML element representing the visual properties.

        Examples:
            >>> visual = VisualLink(origin=Origin(...), geometry=BoxGeometry(...), material=Material(...))
            >>> visual.to_xml()
            <Element 'visual' at 0x7f8b3c0b4c70>
        """
        visual = ET.Element("visual") if root is None else ET.SubElement(root, "visual")
        self.origin.to_xml(visual)
        self.geometry.to_xml(visual)
        self.material.to_xml(visual)
        return visual


@dataclass
class CollisionLink:
    """
    Represents the collision properties of a link in the robot model.

    Attributes:
        origin (Origin): The origin of the link.
        geometry (BaseGeometry): The geometry of the link.

    Methods:
        to_xml: Converts the collision properties to an XML element.

    Examples:
        >>> collision = CollisionLink(origin=Origin(...), geometry=BoxGeometry(...))
        >>> collision.to_xml()
        <Element 'collision' at 0x7f8b3c0b4c70>
    """

    origin: Origin
    geometry: BaseGeometry

    def to_xml(self, root: ET.Element | None = None) -> ET.Element:
        """
        Convert the collision properties to an XML element.

        Args:
            root: The root element to append the collision properties to.

        Returns:
            The XML element representing the collision properties.

        Examples:
            >>> collision = CollisionLink(origin=Origin(...), geometry=BoxGeometry(...))
            >>> collision.to_xml()
            <Element 'collision' at 0x7f8b3c0b4c70>
        """
        collision = ET.Element("collision") if root is None else ET.SubElement(root, "collision")
        self.origin.to_xml(collision)
        self.geometry.to_xml(collision)
        return collision


@dataclass
class Link:
    """
    Represents a link in the robot model.

    Attributes:
        name (str): The name of the link.
        visual (VisualLink): The visual properties of the link.
        collision (CollisionLink): The collision properties of the link.
        inertial (InertialLink): The inertial properties of the link.

    Methods:
        to_xml: Converts the link to an XML element.

    Class Methods:
        from_part: Creates a link from a part.

    Examples:
        >>> link = Link(name="link", visual=VisualLink(...), collision=CollisionLink(...), inertial=InertialLink(...))
        >>> link.to_xml()
        <Element 'link' at 0x7f8b3c0b4c70>

        >>> part = Part(...)
        >>> Link.from_part(part)
        Link(name='partId', visual=None, collision=None, inertial=None)
    """

    name: str
    visual: VisualLink | None = None
    collision: CollisionLink | None = None
    inertial: InertialLink | None = None

    def to_xml(self, root: ET.Element | None = None) -> ET.Element:
        """
        Convert the link to an XML element.

        Args:
            root: The root element to append the link to.

        Returns:
            The XML element representing the link.

        Examples:
            >>> link = Link(
            ...     name="link",
            ...     visual=VisualLink(...),
            ...     collision=CollisionLink(...),
            ...     inertial=InertialLink(...),
            ... )
            >>> link.to_xml()
            <Element 'link' at 0x7f8b3c0b4c70>
        """
        link = ET.Element("link") if root is None else ET.SubElement(root, "link")
        link.set("name", self.name)
        if self.visual is not None:
            self.visual.to_xml(link)
        if self.collision is not None:
            self.collision.to_xml(link)
        if self.inertial is not None:
            self.inertial.to_xml(link)
        return link

    @classmethod
    def from_part(cls, part: Part) -> "Link":
        """
        Create a link from a part.

        Args:
            part: The part to create the link from.

        Returns:
            The link created from the part.

        Examples:
            >>> part = Part(...)
            >>> Link.from_part(part)
            Link(name='partId', visual=None, collision=None, inertial=None)
        """
        # TODO: Retrieve visual, collision, and inertial properties from the part
        _cls = cls(name=part.partId)
        return _cls
