import xml.etree.ElementTree as ET
from abc import ABC, abstractmethod
from dataclasses import dataclass

from onshape_api.utilities import format_number, xml_escape


@dataclass
class BaseGeometry(ABC):
    @abstractmethod
    def to_xml(self, root: ET.Element | None = None) -> ET.Element: ...


@dataclass
class BoxGeometry(BaseGeometry):
    size: tuple[float, float, float]

    def to_xml(self, root: ET.Element | None = None) -> ET.Element:
        geometry = ET.Element("geometry") if root is None else ET.SubElement(root, "geometry")
        ET.SubElement(geometry, "box", size=" ".join(format_number(v) for v in self.size))
        return geometry


@dataclass
class CylinderGeometry(BaseGeometry):
    radius: float
    length: float

    def to_xml(self, root: ET.Element | None = None) -> ET.Element:
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
    radius: float

    def to_xml(self, root: ET.Element | None = None) -> ET.Element:
        geometry = ET.Element("geometry") if root is None else ET.SubElement(root, "geometry")
        ET.SubElement(geometry, "sphere", radius=format_number(self.radius))
        return geometry


@dataclass
class MeshGeometry(BaseGeometry):
    filename: str

    def to_xml(self, root: ET.Element | None = None) -> ET.Element:
        geometry = ET.Element("geometry") if root is None else ET.SubElement(root, "geometry")
        ET.SubElement(geometry, "mesh", filename=self.filename)
        return geometry

    def __post_init__(self) -> None:
        self.filename = xml_escape(self.filename)
