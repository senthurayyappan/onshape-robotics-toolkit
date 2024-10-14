import xml.etree.ElementTree as ET
from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum

from onshape_api.models.link import Axis, Origin
from onshape_api.utilities import format_number


class JOINTTYPE(str, Enum):
    REVOLUTE = "revolute"
    CONTINUOUS = "continuous"
    PRISMATIC = "prismatic"
    FIXED = "fixed"
    FLOATING = "floating"
    PLANAR = "planar"


@dataclass
class JointLimits:
    effort: float
    velocity: float
    lower: float
    upper: float

    def to_xml(self, root: ET.Element | None = None) -> ET.Element:
        limit = ET.Element("limit") if root is None else ET.SubElement(root, "limit")
        limit.set("effort", format_number(self.effort))
        limit.set("velocity", format_number(self.velocity))
        limit.set("lower", format_number(self.lower))
        limit.set("upper", format_number(self.upper))
        return limit


@dataclass
class JointMimic:
    joint: str
    multiplier: float = 1.0
    offset: float = 0.0

    def to_xml(self, root: ET.Element | None = None) -> ET.Element:
        mimic = ET.Element("mimic") if root is None else ET.SubElement(root, "mimic")
        mimic.set("joint", self.joint)
        mimic.set("multiplier", format_number(self.multiplier))
        mimic.set("offset", format_number(self.offset))
        return mimic


@dataclass
class JointDynamics:
    damping: float
    friction: float

    def to_xml(self, root: ET.Element | None = None) -> ET.Element:
        joint = ET.Element("dynamics") if root is None else ET.SubElement(root, "dynamics")
        joint.set("damping", format_number(self.damping))
        joint.set("friction", format_number(self.friction))
        return joint


@dataclass
class BaseJoint(ABC):
    name: str
    parent: str
    child: str
    origin: Origin

    def to_xml(self, root: ET.Element | None = None) -> ET.Element:
        joint = ET.Element("joint") if root is None else ET.SubElement(root, "joint")
        joint.set("name", self.name)
        joint.set("type", self.joint_type())
        self.origin.to_xml(joint)
        ET.SubElement(joint, "parent", link=self.parent)
        ET.SubElement(joint, "child", link=self.child)
        return joint

    @abstractmethod
    def joint_type(self) -> str: ...


@dataclass
class RevoluteJoint(BaseJoint):
    limits: JointLimits
    axis: Axis
    dynamics: JointDynamics | None = None
    mimic: JointMimic | None = None

    def to_xml(self, root: ET.Element | None = None) -> ET.Element:
        joint = super().to_xml(root)
        self.limits.to_xml(joint)
        self.axis.to_xml(joint)
        if self.dynamics is not None:
            self.dynamics.to_xml(joint)
        if self.mimic is not None:
            self.mimic.to_xml(joint)
        return joint

    def joint_type(self) -> str:
        return "revolute"


@dataclass
class ContinuousJoint(BaseJoint):
    mimic: JointMimic | None = None

    def to_xml(self, root: ET.Element | None = None) -> ET.Element:
        joint = super().to_xml(root)
        if self.mimic is not None:
            self.mimic.to_xml(joint)
        return joint

    def joint_type(self) -> str:
        return "continuous"


@dataclass
class PrismaticJoint(BaseJoint):
    limits: JointLimits
    axis: Axis
    dynamics: JointDynamics | None = None
    mimic: JointMimic | None = None

    def to_xml(self, root: ET.Element | None = None) -> ET.Element:
        joint = super().to_xml(root)
        self.limits.to_xml(joint)
        self.axis.to_xml(joint)
        if self.dynamics is not None:
            self.dynamics.to_xml(joint)
        if self.mimic is not None:
            self.mimic.to_xml(joint)
        return joint

    def joint_type(self) -> str:
        return "prismatic"


@dataclass
class FixedJoint(BaseJoint):
    def to_xml(self, root: ET.Element | None = None) -> ET.Element:
        joint = super().to_xml(root)
        return joint

    def joint_type(self) -> str:
        return "fixed"


@dataclass
class FloatingJoint(BaseJoint):
    mimic: JointMimic | None = None

    def to_xml(self, root: ET.Element | None = None) -> ET.Element:
        joint = super().to_xml(root)
        if self.mimic is not None:
            self.mimic.to_xml(joint)
        return joint

    def joint_type(self) -> str:
        return "floating"


@dataclass
class PlanarJoint(BaseJoint):
    limits: JointLimits
    axis: Axis
    mimic: JointMimic | None = None

    def to_xml(self, root: ET.Element | None = None) -> ET.Element:
        joint = super().to_xml(root)
        self.limits.to_xml(joint)
        self.axis.to_xml(joint)
        if self.mimic is not None:
            self.mimic.to_xml(joint)
        return joint

    def joint_type(self) -> str:
        return "planar"
