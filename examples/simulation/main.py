import mujoco
import mujoco.viewer
import numpy as np
from scipy.spatial.transform import Rotation
from transformations import compute_motor_torques

from onshape_api.connect import Client
from onshape_api.log import LOGGER, LogLevel
from onshape_api.robot import Robot, RobotType

# from onshape_api.robot import RobotType, get_robot
from onshape_api.utilities import save_gif

HEIGHT = 480
WIDTH = 640

FREQUENCY = 200
PHASE = 3

KP = 1
KI = 0.1
KD = 0


def run_simulation(model, data, duration, framerate):
    n_frames = int(duration * framerate)
    frames = []

    # visualize contact frames and forces, make body transparent
    options = mujoco.MjvOption()
    mujoco.mjv_defaultOption(options)
    options.flags[mujoco.mjtVisFlag.mjVIS_CONTACTPOINT] = True
    options.flags[mujoco.mjtVisFlag.mjVIS_CONTACTFORCE] = True
    options.flags[mujoco.mjtVisFlag.mjVIS_TRANSPARENT] = True

    # tweak scales of contact visualization elements
    model.vis.scale.contactwidth = 0.01
    model.vis.scale.contactheight = 0.01
    model.vis.scale.forcewidth = 0.02
    model.vis.map.force = 0.1

    # mujoco.mj_resetData(model, data)
    with mujoco.Renderer(model, HEIGHT, WIDTH) as renderer:
        for _i in range(n_frames):
            mujoco.mj_step(model, data)
            control(data)
            renderer.update_scene(data, "track", scene_option=options)
            pixels = renderer.render()
            frames.append(pixels)

    save_gif(frames, framerate=framerate)
    # show_video(frames, framerate=framerate)


def get_theta(data):
    rot = Rotation.from_quat(data.sensor("orientation").data)
    theta = rot.as_euler("xyz", degrees=False)

    return theta[0], theta[1], theta[2]


def control(data, roll_sp=0, pitch_sp=0):
    roll, pitch, yaw = get_theta(data)
    roll = roll - np.pi

    roll_e = roll - roll_sp
    pitch_e = pitch - pitch_sp

    tx_e = 0
    ty_e = 0

    tx = KP * roll_e + tx_e
    ty = KP * pitch_e + ty_e

    t1, t2, t3 = compute_motor_torques(tx, ty, 0)

    data.ctrl[0] = t1
    data.ctrl[2] = t2
    data.ctrl[1] = t3

    print(f"Roll {roll}, Pitch: {pitch}")


if __name__ == "__main__":
    LOGGER.set_file_name("sim.log")
    LOGGER.set_stream_level(LogLevel.INFO)

    # TODO: Add native support for MJCF (XML) exports: #17
    # client = Client()
    # ballbot: Robot = Robot.from_url(
    #     url="https://cad.onshape.com/documents/1f42f849180e6e5c9abfce52/w/0c00b6520fac5fada24b2104/e/c96b40ef586e60c182f41d29",
    #     client=client,
    #     max_depth=1,
    #     name="ballbot",
    #     # robot_type=RobotType.MJCF,
    # )
    # ballbot.save()

    ballbot: Robot = Robot.from_urdf(
        file_name="ballbot.urdf",
        robot_type=RobotType.MJCF,
    )

    ballbot.add_light(
        name="light-1",
        directional=True,
        diffuse=[0.4, 0.4, 0.4],
        specular=[0.1, 0.1, 0.1],
        pos=[0, 0, 5.0],
        direction=[0, 0, -1],
        castshadow=False
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

    ballbot.set_robot_position(pos=(0, 0, 0.6))
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
    ballbot.save("ballbot.xml")

    model = mujoco.MjModel.from_xml_path(filename="ballbot.xml")
    data = mujoco.MjData(model)

    # run_simulation(model, data, 20, 60)

    mujoco.mj_resetData(model, data)

    with mujoco.viewer.launch_passive(model, data) as viewer:
        # initial_roll, initial_pitch, initial_yaw = get_theta(data)

        while viewer.is_running():
            mujoco.mj_step(model, data)
            mujoco.mj_forward(model, data)

            # control(data)

            viewer.sync()
