"""
This module contains dataclasses for creating a link in a URDF robot model.

Dataclass:
    - **Origin**: Represents the origin of a link in the robot model.
    - **Axis**: Represents the axis of a link in the robot model.
    - **Inertia**: Represents the inertia properties of a link in the robot model.
    - **Material**: Represents the material properties of a link in the robot model.
    - **InertialLink**: Represents the inertial properties of a link in the robot model.
    - **VisualLink**: Represents the visual properties of a link in the robot model.
    - **CollisionLink**: Represents the collision properties of a link in the robot model.
    - **Link**: Represents a link in the robot model.

Enum:
    - **Colors**: Enumerates the possible colors for a link in the robot model.
"""

from dataclasses import dataclass
from enum import Enum
from typing import Optional, Union

import numpy as np
from lxml import etree
from scipy.spatial.transform import Rotation

from onshape_api.models.geometry import BaseGeometry, BoxGeometry, CylinderGeometry, MeshGeometry, SphereGeometry
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

    def transform(self, matrix: np.matrix, inplace: bool = False) -> Union["Origin", None]:
        """
        Apply a transformation matrix to the origin.

        Args:
            matrix: The transformation matrix to apply to the origin.
            inplace: Whether to apply the transformation in place.

        Returns:
            The origin with the transformation applied.

        Examples:
            >>> origin = Origin(xyz=(1.0, 2.0, 3.0), rpy=(0.0, 0.0, 0.0))
            >>> matrix = np.eye(4)
            >>> origin.transform(matrix)
        """
        # Apply the rotation and translation to the position
        new_xyz = np.dot(matrix[:3, :3], np.array(self.xyz)) + matrix[:3, 3]

        # Convert current RPY to a rotation matrix
        current_rotation_matrix = Rotation.from_euler("xyz", self.rpy).as_matrix()

        # Apply the rotation to the current rotation matrix
        new_rotation_matrix = np.dot(matrix[:3, :3], current_rotation_matrix)
        new_rpy = Rotation.from_matrix(new_rotation_matrix).as_euler("xyz")
        if inplace:
            self.xyz = tuple(new_xyz)
            self.rpy = tuple(new_rpy)
            return None

        return Origin(new_xyz, new_rpy)

    def to_xml(self, root: Optional[etree.Element] = None) -> etree.Element:
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

        origin = etree.Element("origin") if root is None else etree.SubElement(root, "origin")
        origin.set("xyz", " ".join(format_number(v) for v in self.xyz))
        origin.set("rpy", " ".join(format_number(v) for v in self.rpy))
        return origin

    @classmethod
    def from_xml(cls, xml: etree.Element) -> "Origin":
        """
        Create an origin from an XML element.

        Args:
            xml: The XML element to create the origin from.

        Returns:
            The origin created from the XML element.

        Examples:
            >>> xml = etree.Element('origin')
            >>> Origin.from_xml(xml)
            Origin(xyz=(0.0, 0.0, 0.0), rpy=(0.0, 0.0, 0.0))
        """

        xyz = tuple(map(float, xml.get("xyz").split()))
        rpy = tuple(map(float, xml.get("rpy").split()))
        return cls(xyz, rpy)

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

    def to_xml(self, root: Optional[etree.Element] = None) -> etree.Element:
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

        axis = etree.Element("axis") if root is None else etree.SubElement(root, "axis")
        axis.set("xyz", " ".join(format_number(v) for v in self.xyz))
        return axis

    @classmethod
    def from_xml(cls, xml: etree.Element) -> "Axis":
        """
        Create an axis from an XML element.

        Args:
            xml: The XML element to create the axis from.

        Returns:
            The axis created from the XML element.

        Examples:
            >>> xml = etree.Element('axis')
            >>> Axis.from_xml(xml)
            Axis(xyz=(0.0, 0.0, 0.0))
        """
        xyz = tuple(map(float, xml.get("xyz").split()))
        return cls(xyz)


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

    def to_xml(self, root: Optional[etree.Element] = None) -> etree.Element:
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

        inertia = etree.Element("inertia") if root is None else etree.SubElement(root, "inertia")
        inertia.set("ixx", format_number(self.ixx))
        inertia.set("iyy", format_number(self.iyy))
        inertia.set("izz", format_number(self.izz))
        inertia.set("ixy", format_number(self.ixy))
        inertia.set("ixz", format_number(self.ixz))
        inertia.set("iyz", format_number(self.iyz))
        return inertia

    @classmethod
    def from_xml(cls, xml: etree.Element) -> "Inertia":
        """
        Create an inertia tensor from an XML element.

        Args:
            xml: The XML element to create the inertia tensor from.

        Returns:
            The inertia tensor created from the XML element.

        Examples:
            >>> xml = etree.Element('inertia')
            >>> Inertia.from_xml(xml)
            Inertia(ixx=0.0, iyy=0.0, izz=0.0, ixy=0.0, ixz=0.0, iyz=0.0)
        """
        ixx = float(xml.get("ixx"))
        iyy = float(xml.get("iyy"))
        izz = float(xml.get("izz"))
        ixy = float(xml.get("ixy"))
        ixz = float(xml.get("ixz"))
        iyz = float(xml.get("iyz"))
        return cls(ixx, iyy, izz, ixy, ixz, iyz)

    @classmethod
    def zero_inertia(cls) -> "Inertia":
        """
        Create an inertia tensor with zero values.

        Returns:
            The inertia tensor with zero values.

        Examples:
            >>> Inertia.zero_inertia()
            Inertia(ixx=0.0, iyy=0.0, izz=0.0, ixy=0.0, ixz=0.0, iyz=0.0)
        """
        return cls(0.0, 0.0, 0.0, 0.0, 0.0, 0.0)


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

    def to_xml(self, root: Optional[etree.Element] = None) -> etree.Element:
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

        material = etree.Element("material") if root is None else etree.SubElement(root, "material")
        material.set("name", self.name)
        etree.SubElement(material, "color", rgba=" ".join(format_number(v) for v in self.color))
        return material

    @classmethod
    def from_xml(cls, xml: etree.Element) -> "Material":
        """
        Create a material from an XML element.

        Args:
            xml: The XML element to create the material from.

        Returns:
            The material created from the XML element.

        Examples:
            >>> xml = etree.Element('material')
            >>> Material.from_xml(xml)
            Material(name='material', color=(1.0, 0.0, 0.0, 1.0))
        """

        name = xml.get("name")
        color = tuple(map(float, xml.find("color").get("rgba").split()))
        return cls(name, color)

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

    def to_xml(self, root: Optional[etree.Element] = None) -> etree.Element:
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
        inertial = etree.Element("inertial") if root is None else etree.SubElement(root, "inertial")
        etree.SubElement(inertial, "mass", value=format_number(self.mass))
        self.inertia.to_xml(inertial)
        self.origin.to_xml(inertial)
        return inertial

    @classmethod
    def from_xml(cls, xml: etree.Element) -> "InertialLink":
        """
        Create inertial properties from an XML element.

        Args:
            xml: The XML element to create the inertial properties from.

        Returns:
            The inertial properties created from the XML element.

        Examples:
            >>> xml = etree.Element('inertial')
            >>> InertialLink.from_xml(xml)
            InertialLink(mass=0.0, inertia=None, origin=None)
        """
        mass = float(xml.find("mass").get("value"))

        inertia_element = xml.find("inertia")
        inertia = Inertia.from_xml(inertia_element) if inertia_element is not None else None

        origin_element = xml.find("origin")
        origin = Origin.from_xml(origin_element) if origin_element is not None else None

        return cls(mass=mass, inertia=inertia, origin=origin)


def set_geometry_from_xml(geometry: etree.Element) -> BaseGeometry | None:
    if geometry.find("filename"):
        return MeshGeometry.from_xml(geometry)
    elif geometry.find("box"):
        return BoxGeometry.from_xml(geometry)
    elif geometry.find("length") and geometry.find("radius"):
        return CylinderGeometry.from_xml(geometry)
    elif geometry.find("radius"):
        return SphereGeometry.from_xml(geometry)
    return None


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

    name: str
    origin: Origin
    geometry: BaseGeometry
    material: Material

    def to_xml(self, root: Optional[etree.Element] = None) -> etree.Element:
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
        visual = etree.Element("visual") if root is None else etree.SubElement(root, "visual")
        visual.set("name", self.name)
        self.origin.to_xml(visual)
        self.geometry.to_xml(visual)
        self.material.to_xml(visual)
        return visual

    @classmethod
    def from_xml(cls, xml: etree.Element) -> "VisualLink":
        """
        Create a visual link from an XML element.

        Args:
            xml: The XML element to create the visual link from.

        Returns:
            The visual link created from the XML element.

        Examples:
            >>> xml = etree.Element('visual')
            >>> VisualLink.from_xml(xml)
            VisualLink(name='visual', origin=None, geometry=None, material=None)
        """
        name = xml.get("name")

        origin_element = xml.find("origin")
        origin = Origin.from_xml(origin_element) if origin_element is not None else None

        geometry_element = xml.find("geometry")
        geometry = set_geometry_from_xml(geometry_element) if geometry_element is not None else None

        material_element = xml.find("material")
        material = Material.from_xml(material_element) if material_element is not None else None
        return cls(name=name, origin=origin, geometry=geometry, material=material)


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

    name: str
    origin: Origin
    geometry: BaseGeometry

    def to_xml(self, root: Optional[etree.Element] = None) -> etree.Element:
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
        collision = etree.Element("collision") if root is None else etree.SubElement(root, "collision")
        collision.set("name", self.name)
        self.origin.to_xml(collision)
        self.geometry.to_xml(collision)
        return collision

    @classmethod
    def from_xml(cls, xml: etree.Element) -> "CollisionLink":
        """
        Create a collision link from an XML element.

        Args:
            xml: The XML element to create the collision link from.

        Returns:
            The collision link created from the XML element.

        Examples:
            >>> xml = etree.Element('collision')
            >>> CollisionLink.from_xml(xml)
            CollisionLink(name='collision', origin=None, geometry=None)
        """
        name = xml.get("name")

        origin_element = xml.find("origin")
        origin = Origin.from_xml(origin_element) if origin_element is not None else None

        geometry_element = xml.find("geometry")
        geometry = set_geometry_from_xml(geometry_element) if geometry_element is not None else None

        return cls(name=name, origin=origin, geometry=geometry)


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
        from_xml: Creates a link from an XML element.

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

    def to_xml(self, root: Optional[etree.Element] = None) -> etree.Element:
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
        link = etree.Element("link") if root is None else etree.SubElement(root, "link")
        link.set("name", self.name)
        if self.visual is not None:
            self.visual.to_xml(link)
        if self.collision is not None:
            self.collision.to_xml(link)
        if self.inertial is not None:
            self.inertial.to_xml(link)
        return link

    @classmethod
    def from_xml(cls, xml: etree.Element) -> "Link":
        """
        Create a link from an XML element.

        Args:
            xml: The XML element to create the link from.

        Returns:
            The link created from the XML element.

        Examples:
            >>> xml = etree.Element('link')
            >>> Link.from_xml(xml)
            Link(name='link', visual=None, collision=None, inertial=None)
        """
        name = xml.get("name")

        visual_element = xml.find("visual")
        visual = VisualLink.from_xml(visual_element) if visual_element is not None else None

        collision_element = xml.find("collision")
        collision = CollisionLink.from_xml(collision_element) if collision_element is not None else None

        inertial_element = xml.find("inertial")
        inertial = InertialLink.from_xml(inertial_element) if inertial_element is not None else None

        return cls(name=name, visual=visual, collision=collision, inertial=inertial)

    # TODO: Implement from part method
    # @classmethod
    # def from_part(cls, part: Part) -> "Link":
    #     """
    #     Create a link from a part.

    #     Args:
    #         part: The part to create the link from.

    #     Returns:
    #         The link created from the part.

    #     Examples:
    #         >>> part = Part(...)
    #         >>> Link.from_part(part)
    #         Link(name='partId', visual=None, collision=None, inertial=None)
    #     """
    #     _cls = cls(name=part.partId)
    #     return _cls
