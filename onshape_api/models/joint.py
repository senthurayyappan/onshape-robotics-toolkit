"""
This module contains classes for defining joints in a URDF robot model.

Class:
    - **BaseJoint**: Abstract base class for joint objects.
    - **DummyJoint**: Represents a dummy joint.
    - **RevoluteJoint**: Represents a revolute joint.
    - **ContinuousJoint**: Represents a continuous joint.
    - **PrismaticJoint**: Represents a prismatic joint.
    - **FixedJoint**: Represents a fixed joint.
    - **FloatingJoint**: Represents a floating joint.
    - **PlanarJoint**: Represents a planar joint.

Dataclass:
    - **JointLimits**: Contains the limits for a joint.
    - **JointMimic**: Contains the mimic information for a joint.
    - **JointDynamics**: Contains the dynamics information for a joint.
    - **Axis**: Contains the axis information for a joint.
    - **Origin**: Contains the origin information for a joint.

Enum:
    - **JointType**: Enumerates the possible joint types in Onshape (revolute, continuous, prismatic,
      fixed, floating, planar).

"""

import xml.etree.ElementTree as ET
from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum

from onshape_api.models.link import Axis, Origin
from onshape_api.utilities import format_number


class JointType(str, Enum):
    """
    Enumerates the possible joint types in Onshape

    Attributes:
        REVOLUTE (str): Revolute joint
        CONTINUOUS (str): Continuous joint
        PRISMATIC (str): Prismatic joint
        FIXED (str): Fixed joint
        FLOATING (str): Floating joint
        PLANAR (str): Planar joint

    Examples:
        >>> JointType.REVOLUTE
        'revolute'
        >>> JointType.CONTINUOUS
        'continuous'
    """

    REVOLUTE = "revolute"
    CONTINUOUS = "continuous"
    PRISMATIC = "prismatic"
    FIXED = "fixed"
    FLOATING = "floating"
    PLANAR = "planar"


@dataclass
class JointLimits:
    """
    Represents the limits of a joint.

    Attributes:
        effort (float): The effort limit of the joint.
        velocity (float): The velocity limit of the joint.
        lower (float): The lower limit of the joint.
        upper (float): The upper limit of the joint.

    Methods:
        to_xml: Converts the joint limits to an XML element.

    Examples:
        >>> limits = JointLimits(effort=10.0, velocity=1.0, lower=-1.0, upper=1.0)
        >>> limits.to_xml()
        <Element 'limit' at 0x7f8b3c0b4c70>
    """

    effort: float
    velocity: float
    lower: float
    upper: float

    def to_xml(self, root: ET.Element | None = None) -> ET.Element:
        """
        Convert the joint limits to an XML element.

        Args:
            root: The root element to append the joint limits to.

        Returns:
            The XML element representing the joint limits.

        Examples:
            >>> limits = JointLimits(effort=10.0, velocity=1.0, lower=-1.0, upper=1.0)
            >>> limits.to_xml()
            <Element 'limit' at 0x7f8b3c0b4c70>
        """

        limit = ET.Element("limit") if root is None else ET.SubElement(root, "limit")
        limit.set("effort", format_number(self.effort))
        limit.set("velocity", format_number(self.velocity))
        limit.set("lower", format_number(self.lower))
        limit.set("upper", format_number(self.upper))
        return limit


@dataclass
class JointMimic:
    """
    Represents the mimic information for a joint.

    Attributes:
        joint (str): The joint to mimic.
        multiplier (float): The multiplier for the mimic.
        offset (float): The offset for the mimic.

    Methods:
        to_xml: Converts the mimic information to an XML element.

    Examples:
        >>> mimic = JointMimic(joint="joint1", multiplier=1.0, offset=0.0)
        >>> mimic.to_xml()
        <Element 'mimic' at 0x7f8b3c0b4c70>
    """

    joint: str
    multiplier: float = 1.0
    offset: float = 0.0

    def to_xml(self, root: ET.Element | None = None) -> ET.Element:
        """
        Convert the mimic information to an XML element.

        Args:
            root: The root element to append the mimic information to.

        Returns:
            The XML element representing the mimic information.

        Examples:
            >>> mimic = JointMimic(joint="joint1", multiplier=1.0, offset=0.0)
            >>> mimic.to_xml()
            <Element 'mimic' at 0x7f8b3c0b4c70>
        """

        mimic = ET.Element("mimic") if root is None else ET.SubElement(root, "mimic")
        mimic.set("joint", self.joint)
        mimic.set("multiplier", format_number(self.multiplier))
        mimic.set("offset", format_number(self.offset))
        return mimic


@dataclass
class JointDynamics:
    """
    Represents the dynamics information for a joint.

    Attributes:
        damping (float): The damping coefficient of the joint.
        friction (float): The friction coefficient of the joint.

    Methods:
        to_xml: Converts the dynamics information to an XML element.

    Examples:
        >>> dynamics = JointDynamics(damping=0.0, friction=0.0)
        >>> dynamics.to_xml()
        <Element 'dynamics' at 0x7f8b3c0b4c70>
    """

    damping: float
    friction: float

    def to_xml(self, root: ET.Element | None = None) -> ET.Element:
        """
        Convert the dynamics information to an XML element.

        Args:
            root: The root element to append the dynamics information to.

        Returns:
            The XML element representing the dynamics information.

        Examples:
            >>> dynamics = JointDynamics(damping=0.0, friction=0.0)
            >>> dynamics.to_xml()
            <Element 'dynamics' at 0x7f8b3c0b4c70>
        """

        joint = ET.Element("dynamics") if root is None else ET.SubElement(root, "dynamics")
        joint.set("damping", format_number(self.damping))
        joint.set("friction", format_number(self.friction))
        return joint


@dataclass
class BaseJoint(ABC):
    """
    Abstract base class for joint objects.

    Attributes:
        name (str): The name of the joint.
        parent (str): The parent link of the joint.
        child (str): The child link of the joint.
        origin (Origin): The origin of the joint.

    Methods:
        to_xml: Converts the joint to an XML element.

    Abstract Properties:
        joint_type: Returns the type of the joint.
    """

    name: str
    parent: str
    child: str
    origin: Origin

    def to_xml(self, root: ET.Element | None = None) -> ET.Element:
        """
        Convert the joint to an XML element.

        Args:
            root: The root element to append the joint to.

        Returns:
            The XML element representing the joint.
        """

        joint = ET.Element("joint") if root is None else ET.SubElement(root, "joint")
        joint.set("name", self.name)
        joint.set("type", self.joint_type())
        self.origin.to_xml(joint)
        ET.SubElement(joint, "parent", link=self.parent)
        ET.SubElement(joint, "child", link=self.child)
        return joint

    @abstractmethod
    @property
    def joint_type(self) -> str:
        """
        The type of the joint.

        Returns:
            The type of the joint.
        """

        pass


@dataclass
class DummyJoint(BaseJoint):
    """
    Represents a dummy joint.

    Properties:
        joint_type: The type of the joint.

    Examples:
        >>> origin = Origin(xyz=(0, 0, 0), rpy=(0, 0, 0))
        >>> joint = DummyJoint(
        ...     name="joint1",
        ...     parent="base_link",
        ...     child="link1",
        ...     origin=origin,
        ... )
        >>> joint.joint_type
        'dummy'
    """

    @property
    def joint_type(self) -> str:
        """
        The type of the joint.

        Returns:
            The type of the joint: "dummy".
        """

        return "dummy"


@dataclass
class RevoluteJoint(BaseJoint):
    """
    Represents a revolute joint.

    Attributes:
        limits (JointLimits): The limits of the joint.
        axis (Axis): The axis of the joint.
        dynamics (JointDynamics): The dynamics of the joint.
        mimic (JointMimic): The mimic information for the joint.

    Methods:
        to_xml: Converts the revolute joint to an XML element.

    Properties:
        joint_type: The type of the joint.

    Examples:
        >>> origin = Origin(xyz=(0, 0, 0), rpy=(0, 0, 0))
        >>> limits = JointLimits(effort=10.0, velocity=1.0, lower=-1.0, upper=1.0)
        >>> axis = Axis(xyz=(0, 0, 1))
        >>> dynamics = JointDynamics(damping=0.0, friction=0.0)
        >>> mimic = JointMimic(joint="joint1", multiplier=1.0, offset=0.0)
        >>> joint = RevoluteJoint(
        ...     name="joint1",
        ...     parent="base_link",
        ...     child="link1",
        ...     origin=origin,
        ...     limits=limits,
        ...     axis=axis,
        ...     dynamics=dynamics,
        ...     mimic=mimic,
        ... )
        >>> joint.to_xml()
        <Element 'joint' at 0x7f8b3c0b4c70>
    """

    limits: JointLimits
    axis: Axis
    dynamics: JointDynamics | None = None
    mimic: JointMimic | None = None

    def to_xml(self, root: ET.Element | None = None) -> ET.Element:
        """
        Convert the revolute joint to an XML element.

        Args:
            root: The root element to append the revolute joint to.

        Returns:
            The XML element representing the revolute joint.

        Examples:
            >>> origin = Origin(xyz=(0, 0, 0), rpy=(0, 0, 0))
            >>> limits = JointLimits(effort=10.0, velocity=1.0, lower=-1.0, upper=1.0)
            >>> axis = Axis(xyz=(0, 0, 1))
            >>> dynamics = JointDynamics(damping=0.0, friction=0.0)
            >>> mimic = JointMimic(joint="joint1", multiplier=1.0, offset=0.0)
            >>> joint = RevoluteJoint(
            ...     name="joint1",
            ...     parent="base_link",
            ...     child="link1",
            ...     origin=origin,
            ...     limits=limits,
            ...     axis=axis,
            ...     dynamics=dynamics,
            ...     mimic=mimic,
            ... )
            >>> joint.to_xml()
            <Element 'joint' at 0x7f8b3c0b4c70>
        """

        joint = super().to_xml(root)
        self.limits.to_xml(joint)
        self.axis.to_xml(joint)
        if self.dynamics is not None:
            self.dynamics.to_xml(joint)
        if self.mimic is not None:
            self.mimic.to_xml(joint)
        return joint

    @property
    def joint_type(self) -> str:
        """
        The type of the joint.

        Returns:
            The type of the joint: "revolute".
        """

        return "revolute"


@dataclass
class ContinuousJoint(BaseJoint):
    """
    Represents a continuous joint.

    Attributes:
        mimic (JointMimic): The mimic information for the joint.

    Methods:
        to_xml: Converts the continuous joint to an XML element.

    Properties:
        joint_type: The type of the joint.

    Examples:
        >>> origin = Origin(xyz=(0, 0, 0), rpy=(0, 0, 0))
        >>> mimic = JointMimic(joint="joint1", multiplier=1.0, offset=0.0)
        >>> joint = ContinuousJoint(
        ...     name="joint1",
        ...     parent="base_link",
        ...     child="link1",
        ...     origin=origin,
        ...     mimic=mimic,
        ... )
        >>> joint.to_xml()
        <Element 'joint' at 0x7f8b3c0b4c70>
    """

    mimic: JointMimic | None = None

    def to_xml(self, root: ET.Element | None = None) -> ET.Element:
        """
        Convert the continuous joint to an XML element.

        Args:
            root: The root element to append the continuous joint to.

        Returns:
            The XML element representing the continuous joint.

        Examples:
            >>> origin = Origin(xyz=(0, 0, 0), rpy=(0, 0, 0))
            >>> mimic = JointMimic(joint="joint1", multiplier=1.0, offset=0.0)
            >>> joint = ContinuousJoint(
            ...     name="joint1",
            ...     parent="base_link",
            ...     child="link1",
            ...     origin=origin,
            ...     mimic=mimic,
            ... )
            >>> joint.to_xml()
            <Element 'joint' at 0x7f8b3c0b4c70>
        """

        joint = super().to_xml(root)
        if self.mimic is not None:
            self.mimic.to_xml(joint)
        return joint

    @property
    def joint_type(self) -> str:
        """
        The type of the joint.

        Returns:
            The type of the joint: "continuous".
        """

        return "continuous"


@dataclass
class PrismaticJoint(BaseJoint):
    """
    Represents a prismatic joint.

    Attributes:
        limits (JointLimits): The limits of the joint.
        axis (Axis): The axis of the joint.
        dynamics (JointDynamics): The dynamics of the joint.
        mimic (JointMimic): The mimic information for the joint.

    Methods:
        to_xml: Converts the prismatic joint to an XML element.

    Properties:
        joint_type: The type of the joint.

    Examples:
        >>> origin = Origin(xyz=(0, 0, 0), rpy=(0, 0, 0))
        >>> limits = JointLimits(effort=10.0, velocity=1.0, lower=-1.0, upper=1.0)
        >>> axis = Axis(xyz=(0, 0, 1))
        >>> dynamics = JointDynamics(damping=0.0, friction=0.0)
        >>> mimic = JointMimic(joint="joint1", multiplier=1.0, offset=0.0)
        >>> joint = PrismaticJoint(
        ...     name="joint1",
        ...     parent="base_link",
        ...     child="link1",
        ...     origin=origin,
        ...     limits=limits,
        ...     axis=axis,
        ...     dynamics=dynamics,
        ...     mimic=mimic,
        ... )
        >>> joint.to_xml()
        <Element 'joint' at 0x7f8b3c0b4c70>
    """

    limits: JointLimits
    axis: Axis
    dynamics: JointDynamics | None = None
    mimic: JointMimic | None = None

    def to_xml(self, root: ET.Element | None = None) -> ET.Element:
        """
        Convert the prismatic joint to an XML element.

        Args:
            root: The root element to append the prismatic joint to.

        Returns:
            The XML element representing the prismatic joint

        Examples:
            >>> origin = Origin(xyz=(0, 0, 0), rpy=(0, 0, 0))
            >>> limits = JointLimits(effort=10.0, velocity=1.0, lower=-1.0, upper=1.0)
            >>> axis = Axis(xyz=(0, 0, 1))
            >>> dynamics = JointDynamics(damping=0.0, friction=0.0)
            >>> mimic = JointMimic(joint="joint1", multiplier=1.0, offset=0.0)
            >>> joint = PrismaticJoint(
            ...     name="joint1",
            ...     parent="base_link",
            ...     child="link1",
            ...     origin=origin,
            ...     limits=limits,
            ...     axis=axis,
            ...     dynamics=dynamics,
            ...     mimic=mimic,
            ... )
            >>> joint.to_xml()
            <Element 'joint' at 0x7f8b3c0b4c70>
        """

        joint = super().to_xml(root)
        self.limits.to_xml(joint)
        self.axis.to_xml(joint)
        if self.dynamics is not None:
            self.dynamics.to_xml(joint)
        if self.mimic is not None:
            self.mimic.to_xml(joint)
        return joint

    @property
    def joint_type(self) -> str:
        """
        The type of the joint.

        Returns:
            The type of the joint: "prismatic".
        """

        return "prismatic"


@dataclass
class FixedJoint(BaseJoint):
    """
    Represents a fixed joint.

    Methods:
        to_xml: Converts the fixed joint to an XML element.

    Properties:
        joint_type: The type of the joint.

    Examples:
        >>> origin = Origin(xyz=(0, 0, 0), rpy=(0, 0, 0))
        >>> joint = FixedJoint(
        ...     name="joint1",
        ...     parent="base_link",
        ...     child="link1",
        ...     origin=origin,
        ... )
        >>> joint.to_xml()
        <Element 'joint' at 0x7f8b3c0b4c70>
    """

    def to_xml(self, root: ET.Element | None = None) -> ET.Element:
        """
        Convert the fixed joint to an XML element.

        Args:
            root: The root element to append the fixed joint to.

        Returns:
            The XML element representing the fixed joint.

        Examples:
            >>> origin = Origin(xyz=(0, 0, 0), rpy=(0, 0, 0))
            >>> joint = FixedJoint(
            ...     name="joint1",
            ...     parent="base_link",
            ...     child="link1",
            ...     origin=origin,
            ... )
            >>> joint.to_xml()
            <Element 'joint' at 0x7f8b3c0b4c70>
        """

        joint = super().to_xml(root)
        return joint

    @property
    def joint_type(self) -> str:
        """
        The type of the joint.

        Returns:
            The type of the joint: "fixed".
        """

        return "fixed"


@dataclass
class FloatingJoint(BaseJoint):
    """
    Represents a floating joint.

    Attributes:
        mimic (JointMimic): The mimic information for the joint.

    Methods:
        to_xml: Converts the floating joint to an XML element.

    Properties:
        joint_type: The type of the joint.

    Examples:
        >>> origin = Origin(xyz=(0, 0, 0), rpy=(0, 0, 0))
        >>> mimic = JointMimic(joint="joint1", multiplier=1.0, offset=0.0)
        >>> joint = FloatingJoint(
        ...     name="joint1",
        ...     parent="base_link",
        ...     child="link1",
        ...     origin=origin,
        ...     mimic=mimic,
        ... )
        >>> joint.to_xml()
        <Element 'joint' at 0x7f8b3c0b4c70>
    """

    mimic: JointMimic | None = None

    def to_xml(self, root: ET.Element | None = None) -> ET.Element:
        """
        Convert the floating joint to an XML element.

        Args:
            root: The root element to append the floating joint to.

        Returns:
            The XML element representing the floating joint.

        Examples:
            >>> origin = Origin(xyz=(0, 0, 0), rpy=(0, 0, 0))
            >>> mimic = JointMimic(joint="joint1", multiplier=1.0, offset=0.0)
            >>> joint = FloatingJoint(
            ...     name="joint1",
            ...     parent="base_link",
            ...     child="link1",
            ...     origin=origin,
            ...     mimic=mimic,
            ... )
            >>> joint.to_xml()
            <Element 'joint' at 0x7f8b3c0b4c70>
        """

        joint = super().to_xml(root)
        if self.mimic is not None:
            self.mimic.to_xml(joint)
        return joint

    @property
    def joint_type(self) -> str:
        """
        The type of the joint.

        Returns:
            The type of the joint: "floating".
        """

        return "floating"


@dataclass
class PlanarJoint(BaseJoint):
    """
    Represents a planar joint.

    Attributes:
        limits (JointLimits): The limits of the joint.
        axis (Axis): The axis of the joint.
        mimic (JointMimic): The mimic information for the joint.

    Methods:
        to_xml: Converts the planar joint to an XML element.

    Properties:
        joint_type: The type of the joint.

    Examples:
        >>> origin = Origin(xyz=(0, 0, 0), rpy=(0, 0, 0))
        >>> limits = JointLimits(effort=10.0, velocity=1.0, lower=-1.0, upper=1.0)
        >>> axis = Axis(xyz=(0, 0, 1))
        >>> mimic = JointMimic(joint="joint1", multiplier=1.0, offset=0.0)
        >>> joint = PlanarJoint(
        ...     name="joint1",
        ...     parent="base_link",
        ...     child="link1",
        ...     origin=origin,
        ...     limits=limits,
        ...     axis=axis,
        ...     mimic=mimic,
        ... )
        >>> joint.to_xml()
        <Element 'joint' at 0x7f8b3c0b4c70>
    """

    limits: JointLimits
    axis: Axis
    mimic: JointMimic | None = None

    def to_xml(self, root: ET.Element | None = None) -> ET.Element:
        """
        Convert the planar joint to an XML element.

        Args:
            root: The root element to append the planar joint to.

        Returns:
            The XML element representing the planar joint.

        Examples:
            >>> origin = Origin(xyz=(0, 0, 0), rpy=(0, 0, 0))
            >>> limits = JointLimits(effort=10.0, velocity=1.0, lower=-1.0, upper=1.0)
            >>> axis = Axis(xyz=(0, 0, 1))
            >>> mimic = JointMimic(joint="joint1", multiplier=1.0, offset=0.0)
            >>> joint = PlanarJoint(
            ...     name="joint1",
            ...     parent="base_link",
            ...     child="link1",
            ...     origin=origin,
            ...     limits=limits,
            ...     axis=axis,
            ...     mimic=mimic,
            ... )
            >>> joint.to_xml()
            <Element 'joint' at 0x7f8b3c0b4c70>
        """

        joint = super().to_xml(root)
        self.limits.to_xml(joint)
        self.axis.to_xml(joint)
        if self.mimic is not None:
            self.mimic.to_xml(joint)
        return joint

    @property
    def joint_type(self) -> str:
        """
        The type of the joint.

        Returns:
            The type of the joint: "planar".
        """

        return "planar"
