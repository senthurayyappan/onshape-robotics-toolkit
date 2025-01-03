from lxml import etree as ET

from onshape_robotics_toolkit.models.mjcf import IMU, Gyro
from onshape_robotics_toolkit.robot import Robot, load_element


def modify_ballbot(ballbot: Robot) -> Robot:
    ballbot.add_light(
        name="light-1",
        directional=True,
        diffuse=[0.4, 0.4, 0.4],
        specular=[0.1, 0.1, 0.1],
        pos=[0, 0, 5.0],
        direction=[0, 0, -1],
        castshadow=False,
    )
    ballbot.add_light(
        name="light-2",
        directional=True,
        diffuse=[0.6, 0.6, 0.6],
        specular=[0.2, 0.2, 0.2],
        pos=[0, 0, 4],
        direction=[0, 0, -1],
        castshadow=False,
    )

    ballbot.add_actuator(
        actuator_name="motor-1",
        joint_name="Revolute-1",
        ctrl_limited=False,
        gear=70,
        add_encoder=True,
        add_force_sensor=True,
    )
    ballbot.add_actuator(
        actuator_name="motor-2",
        joint_name="Revolute-2",
        ctrl_limited=False,
        gear=70,
        add_encoder=True,
        add_force_sensor=True,
    )
    ballbot.add_actuator(
        actuator_name="motor-3",
        joint_name="Revolute-3",
        ctrl_limited=False,
        gear=70,
        add_encoder=True,
        add_force_sensor=True,
    )

    # For adding to specific named elements (like bodies)
    imu_site = ET.Element("site", name="imu", size="0.01", pos="0 0 0")
    ballbot.add_custom_element_by_name("imu", "Part-3-1", imu_site)

    # Add sensor
    ballbot.add_sensor(
        name="imu",
        sensor=IMU(name="imu", objtype="site", objname="imu", noise=0.001),
    )
    ballbot.add_sensor(
        name="gyro-1",
        sensor=Gyro(name="gyro-1", site="imu", noise=0.001, cutoff=34.9),
    )

    ballbot_mesh = ET.Element("mesh", attrib={"name": "Part-1-1", "file": "meshes/ball.stl"})
    ballbot.add_custom_element_by_tag(name="ballbot", parent_tag="asset", element=ballbot_mesh)
    ball = load_element("ball.xml")
    ballbot.add_custom_element_by_tag(name="ball", parent_tag="worldbody", element=ball)

    # # set friction="1.0 0.01 0.001" for Part-2-1, Part-2-2, Part-2-3
    # ballbot.set_element_attributes(element_name="Part-2-1-collision", attributes={"friction": "0.1 0.05 0.001"})
    # ballbot.set_element_attributes(element_name="Part-2-2-collision", attributes={"friction": "0.1 0.05 0.001"})
    # ballbot.set_element_attributes(element_name="Part-2-3-collision", attributes={"friction": "0.1 0.05 0.001"})

    # set force range to -1 to 1 for all joints
    ballbot.set_element_attributes(element_name="Revolute-1", attributes={"actuatorfrcrange": "-3 3"})
    ballbot.set_element_attributes(element_name="Revolute-2", attributes={"actuatorfrcrange": "-3 3"})
    ballbot.set_element_attributes(element_name="Revolute-3", attributes={"actuatorfrcrange": "-3 3"})

    return ballbot
