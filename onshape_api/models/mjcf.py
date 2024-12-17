from dataclasses import dataclass
from typing import Optional

from lxml import etree as ET


@dataclass
class Light:
    """
    Represents a light source in a mujoco model.

    Example Light XML:
    ```xml
    <light directional="true" diffuse="0.4 0.4 0.4"
           specular="0.1 0.1 0.1" pos="0 0 5.0"
           dir="0 0 -1" castshadow="false" />
    ```

    Attributes:
        directional: Whether the light is directional.
        diffuse: The diffuse color of the light.
        specular: The specular color of the light.
        pos: The position of the light.
        dir: The direction of the light.
        castshadow: Whether the light casts shadows.
    """

    directional: bool
    diffuse: tuple[float, float, float]
    specular: tuple[float, float, float]
    pos: tuple[float, float, float]
    dir: tuple[float, float, float]
    castshadow: bool

    def to_mjcf(self, root: ET.Element) -> None:
        """
        Converts the light to an XML element and appends it to the given root element.

        Args:
            root: The root element to append the light to.
        """
        light = ET.Element("light") if root is None else ET.SubElement(root, "light")
        light.set("directional", str(self.directional))
        light.set("diffuse", " ".join(map(str, self.diffuse)))
        light.set("specular", " ".join(map(str, self.specular)))
        light.set("pos", " ".join(map(str, self.pos)))
        light.set("dir", " ".join(map(str, self.dir)))
        light.set("castshadow", str(self.castshadow))


@dataclass
class Camera:
    """
    Represents a camera in a mujoco model.

    Example Camera XML:
    ```xml
    <camera name="track" mode="trackcom" pos="0 -1 0.25" xyaxes="1 0 0 0 0 1" />
    ```

    Attributes:
        name: The name of the camera.
        mode: The mode of the camera.
        pos: The position of the camera.
        xyaxes: The xyaxes of the camera.
    """

    name: str
    mode: str
    pos: tuple[float, float, float]
    xyaxes: tuple[float, float, float, float, float, float]

    def to_mjcf(self, root: ET.Element) -> None:
        """
        Converts the camera to an XML element and appends it to the given root element.

        Args:
            root: The root element to append the camera to.
        """
        camera = ET.Element("camera") if root is None else ET.SubElement(root, "camera")
        camera.set("name", self.name)
        camera.set("mode", self.mode)
        camera.set("pos", " ".join(map(str, self.pos)))
        camera.set("xyaxes", " ".join(map(str, self.xyaxes)))


@dataclass
class Actuator:
    """
    Represents an actuator in a mujoco model.

    Example Actuator XML:
    ```xml
    <motor name="Revolute-1" joint="Revolute-1" ctrllimited="false" gear="70" />
    <motor name="Revolute-1" joint="Revolute-1" ctrllimited="true" ctrlrange="-1 1" gear="70" />
    ```

    Attributes:
        name: The name of the actuator.
        joint: The joint of the actuator.
        ctrllimited: Whether the actuator is control limited.
        ctrlrange: The control range of the actuator.
        gear: The gear of the actuator.
    """

    name: str
    joint: str
    ctrllimited: bool
    ctrlrange: tuple[float, float] = (0, 0)
    gear: float

    def to_mjcf(self, root: ET.Element) -> None:
        """
        Converts the actuator to an XML element and appends it to the given root element.

        Args:
            root: The root element to append the actuator to.
        """
        motor = ET.Element("motor") if root is None else ET.SubElement(root, "motor")
        motor.set("name", self.name)
        motor.set("joint", self.joint)
        motor.set("ctrllimited", str(self.ctrllimited))

        if self.ctrllimited:
            motor.set("ctrlrange", " ".join(map(str, self.ctrlrange)))

        motor.set("gear", str(self.gear))


@dataclass
class IMU:
    """
    Represents an IMU sensor in a mujoco model.

    Example IMU XML:
    ```xml
    <framequat name="orientation" objtype="site" noise="0.001" objname="imu" reftype="site" refname="root" />
    ```

    Attributes:
        name: The name of the IMU.
        objtype: The object type of the IMU.
        noise: The noise of the IMU.
        objname: The object name of the IMU.
        reftype: The reference type of the IMU.
        refname: The reference name of the IMU.
    """

    name: str
    objtype: str
    noise: float
    objname: str
    reftype: Optional[str] = None
    refname: Optional[str] = None

    def to_mjcf(self, root: ET.Element) -> None:
        """
        Converts the IMU to an XML element and appends it to the given root element.

        Args:
            root: The root element to append the IMU to.
        """
        framequat = ET.Element("framequat") if root is None else ET.SubElement(root, "framequat")
        framequat.set("name", self.name)
        framequat.set("objtype", self.objtype)
        framequat.set("noise", str(self.noise))
        framequat.set("objname", self.objname)

        if self.reftype is not None and self.refname is not None:
            framequat.set("reftype", self.reftype)
            framequat.set("refname", self.refname)
