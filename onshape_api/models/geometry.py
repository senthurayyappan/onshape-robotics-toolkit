"""
This module contains classes for representing geometry in Onshape.

Class:
    - **BaseGeometry**: Abstract base class for geometry objects.
    - **BoxGeometry**: Represents a box geometry.
    - **CylinderGeometry**: Represents a cylinder geometry.
    - **SphereGeometry**: Represents a sphere geometry.
    - **MeshGeometry**: Represents a mesh geometry.
"""

import xml.etree.ElementTree as ET
from abc import ABC, abstractmethod
from dataclasses import dataclass

from onshape_api.utilities import format_number, xml_escape


@dataclass
class BaseGeometry(ABC):
    """
    Abstract base class for geometry objects.

    Abstract Methods:
        to_xml: Converts the geometry object to an XML element.
    """

    @abstractmethod
    def to_xml(self, root: ET.Element | None = None) -> ET.Element: ...


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

    def to_xml(self, root: ET.Element | None = None) -> ET.Element:
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

    def to_xml(self, root: ET.Element | None = None) -> ET.Element:
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

    def to_xml(self, root: ET.Element | None = None) -> ET.Element:
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

    def to_xml(self, root: ET.Element | None = None) -> ET.Element:
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

    def __post_init__(self) -> None:
        self.filename = xml_escape(self.filename)
