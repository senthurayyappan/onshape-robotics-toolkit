"""
This module contains classes for representing geometry in Onshape.

Class:
    - **BaseGeometry**: Abstract base class for geometry objects.
    - **BoxGeometry**: Represents a box geometry.
    - **CylinderGeometry**: Represents a cylinder geometry.
    - **SphereGeometry**: Represents a sphere geometry.
    - **MeshGeometry**: Represents a mesh geometry.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional

import lxml.etree as ET

from onshape_api.utilities import format_number, xml_escape


@dataclass
class BaseGeometry(ABC):
    """
    Abstract base class for geometry objects.

    Abstract Methods:
        to_xml: Converts the geometry object to an XML element.
    """

    @abstractmethod
    def to_xml(self, root: Optional[ET.Element] = None) -> ET.Element: ...

    @classmethod
    @abstractmethod
    def from_xml(cls, element: ET.Element) -> "BaseGeometry": ...


@dataclass
class BoxGeometry(BaseGeometry):
    """
    Represents a box geometry.

    Attributes:
        size (tuple[float, float, float]): The size of the box in the x, y, and z dimensions.

    Methods:
        to_xml: Converts the box geometry to an XML element.

    Examples:
        >>> box = BoxGeometry(size=(1.0, 2.0, 3.0))
        >>> box.to_xml()
        <Element 'geometry' at 0x7f8b3c0b4c70>
    """

    size: tuple[float, float, float]

    def to_xml(self, root: Optional[ET.Element] = None) -> ET.Element:
        """
        Convert the box geometry to an XML element.

        Args:
            root: The root element to append the box geometry to.

        Returns:
            The XML element representing the box geometry.

        Examples:
            >>> box = BoxGeometry(size=(1.0, 2.0, 3.0))
            >>> box.to_xml()
            <Element 'geometry' at 0x7f8b3c0b4c70>
        """
        geometry = ET.Element("geometry") if root is None else ET.SubElement(root, "geometry")
        ET.SubElement(geometry, "box", size=" ".join(format_number(v) for v in self.size))
        return geometry

    @classmethod
    def from_xml(cls, element) -> "BoxGeometry":
        """
        Create a box geometry from an XML element.

        Args:
            element: The XML element to create the box geometry from.

        Returns:
            The box geometry created from the XML element.

        Examples:
            >>> element = ET.Element("geometry")
            >>> ET.SubElement(element, "box", size="1.0 2.0 3.0")
            >>> BoxGeometry.from_xml(element)
            BoxGeometry(size=(1.0, 2.0, 3.0))
        """
        size = tuple(float(v) for v in element.find("box").attrib["size"].split())
        return cls(size)


@dataclass
class CylinderGeometry(BaseGeometry):
    """
    Represents a cylinder geometry.

    Attributes:
        radius (float): The radius of the cylinder.
        length (float): The length of the cylinder.

    Methods:
        to_xml: Converts the cylinder geometry to an XML element.

    Examples:
        >>> cylinder = CylinderGeometry(radius=1.0, length=2.0)
        >>> cylinder.to_xml()
        <Element 'geometry' at 0x7f8b3c0b4c70>
    """

    radius: float
    length: float

    def to_xml(self, root: Optional[ET.Element] = None) -> ET.Element:
        """
        Convert the cylinder geometry to an XML element.

        Args:
            root: The root element to append the cylinder geometry to.

        Returns:
            The XML element representing the cylinder geometry.

        Examples:
            >>> cylinder = CylinderGeometry(radius=1.0, length=2.0)
            >>> cylinder.to_xml()
            <Element 'geometry' at 0x7f8b3c0b4c70>
        """
        geometry = ET.Element("geometry") if root is None else ET.SubElement(root, "geometry")
        ET.SubElement(
            geometry,
            "cylinder",
            radius=format_number(self.radius),
            length=format_number(self.length),
        )
        return geometry

    @classmethod
    def from_xml(cls, element) -> "CylinderGeometry":
        """
        Create a cylinder geometry from an XML element.

        Args:
            element: The XML element to create the cylinder geometry from.

        Returns:
            The cylinder geometry created from the XML element.

        Examples:
            >>> element = ET.Element("geometry")
            >>> ET.SubElement(element, "cylinder", radius="1.0", length="2.0")
            >>> CylinderGeometry.from_xml(element)
            CylinderGeometry(radius=1.0, length=2.0)
        """
        radius = float(element.find("cylinder").attrib["radius"])
        length = float(element.find("cylinder").attrib["length"])
        return cls(radius, length)


@dataclass
class SphereGeometry(BaseGeometry):
    """
    Represents a sphere geometry.

    Attributes:
        radius (float): The radius of the sphere.

    Methods:
        to_xml: Converts the sphere geometry to an XML element.

    Examples:
        >>> sphere = SphereGeometry(radius=1.0)
        >>> sphere.to_xml()
        <Element 'geometry' at 0x7f8b3c0b4c70>
    """

    radius: float

    def to_xml(self, root: Optional[ET.Element] = None) -> ET.Element:
        """
        Convert the sphere geometry to an XML element.

        Args:
            root: The root element to append the sphere geometry to.

        Returns:
            The XML element representing the sphere geometry.

        Examples:
            >>> sphere = SphereGeometry(radius=1.0)
            >>> sphere.to_xml()
            <Element 'geometry' at 0x7f8b3c0b4c70>
        """
        geometry = ET.Element("geometry") if root is None else ET.SubElement(root, "geometry")
        ET.SubElement(geometry, "sphere", radius=format_number(self.radius))
        return geometry

    @classmethod
    def from_xml(cls, element) -> "SphereGeometry":
        """
        Create a sphere geometry from an XML element.

        Args:
            element: The XML element to create the sphere geometry from.

        Returns:
            The sphere geometry created from the XML element.

        Examples:
            >>> element = ET.Element("geometry")
            >>> ET.SubElement(element, "sphere", radius="1.0")
            >>> SphereGeometry.from_xml(element)
            SphereGeometry(radius=1.0)
        """
        radius = float(element.find("sphere").attrib["radius"])
        return cls(radius)


@dataclass
class MeshGeometry(BaseGeometry):
    """
    Represents a mesh geometry.

    Attributes:
        filename (str): The filename of the mesh.

    Methods:
        to_xml: Converts the mesh geometry to an XML element.

    Examples:
        >>> mesh = MeshGeometry(filename="mesh.stl")
        >>> mesh.to_xml()
        <Element 'geometry' at 0x7f8b3c0b4c70>
    """

    filename: str

    def to_xml(self, root: Optional[ET.Element] = None) -> ET.Element:
        """
        Convert the mesh geometry to an XML element.

        Args:
            root: The root element to append the mesh geometry to.

        Returns:
            The XML element representing the mesh geometry.

        Examples:
            >>> mesh = MeshGeometry(filename="mesh.stl")
            >>> mesh.to_xml()
            <Element 'geometry' at 0x7f8b3c0b4c70>
        """
        geometry = ET.Element("geometry") if root is None else ET.SubElement(root, "geometry")
        ET.SubElement(geometry, "mesh", filename=self.filename)
        return geometry

    @classmethod
    def from_xml(cls, element) -> "MeshGeometry":
        """
        Create a mesh geometry from an XML element.

        Args:
            element: The XML element to create the mesh geometry from.

        Returns:
            The mesh geometry created from the XML element.

        Examples:
            >>> element = ET.Element("geometry")
            >>> ET.SubElement(element, "mesh", filename="mesh.stl")
            >>> MeshGeometry.from_xml(element)
            MeshGeometry(filename="mesh.stl")
        """
        filename = element.find("mesh").attrib["filename"]
        return cls(filename)

    def __post_init__(self) -> None:
        self.filename = xml_escape(self.filename)
