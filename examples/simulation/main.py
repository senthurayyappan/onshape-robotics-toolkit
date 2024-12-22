import mujoco
import mujoco.viewer
import numpy as np
from mods import modify_ballbot
from scipy.spatial.transform import Rotation
from transformations import compute_motor_torques

from onshape_api.connect import Client
from onshape_api.log import LOGGER, LogLevel
from onshape_api.models.document import Document
from onshape_api.robot import Robot, RobotType

# from onshape_api.robot import RobotType, get_robot
from onshape_api.utilities import save_gif

HEIGHT = 480
WIDTH = 640

FREQUENCY = 200
PHASE = 3

KP = 2
KI = 0
KD = 0

# Variable bounds (in mm)
WHEEL_DIAMETER_BOUNDS = (100, 300)
CLEARANCE_BOUNDS = (5, 100)
STANDOFF_LENGTH_BOUNDS = (20, 200)


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
    rot = Rotation.from_quat(data.sensor("imu").data)
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

    # print(f"Roll {roll}, Pitch: {pitch}")


if __name__ == "__main__":
    LOGGER.set_file_name("sim.log")
    LOGGER.set_stream_level(LogLevel.INFO)

    client = Client()
    doc = Document.from_url(
        url="https://cad.onshape.com/documents/1f42f849180e6e5c9abfce52/w/0c00b6520fac5fada24b2104/e/c96b40ef586e60c182f41d29"
    )

    elements = client.get_elements(doc.did, doc.wtype, doc.wid)
    variables = client.get_variables(doc.did, doc.wid, elements["variables"].id)

    variables["wheel_diameter"].expression = "120 mm"
    variables["clearance"].expression = "20 mm"
    variables["standoff_length"].expression = "100 mm"

    client.set_variables(doc.did, doc.wid, elements["variables"].id, variables)

    ballbot: Robot = Robot.from_url(
        url=doc.url,
        client=client,
        max_depth=1,
        name="ballbot",
        robot_type=RobotType.MJCF,
    )

    # ballbot: Robot = Robot.from_urdf(
    #     file_name="ballbot.urdf",
    #     robot_type=RobotType.MJCF,
    # )
    ballbot.set_robot_position(pos=(0, 0, 0.35))
    ballbot = modify_ballbot(ballbot)
    ballbot.save("ballbot.xml")

    model = mujoco.MjModel.from_xml_path(filename="ballbot.xml")
    data = mujoco.MjData(model)

    # run_simulation(model, data, 20, 60)

    mujoco.mj_resetData(model, data)

    with mujoco.viewer.launch_passive(model, data) as viewer:
        initial_roll, initial_pitch, initial_yaw = get_theta(data)

        while viewer.is_running():
            mujoco.mj_step(model, data)
            mujoco.mj_forward(model, data)

            control(data)

            # get the position of the bot and if it is too low, reset the simulation
            if data.body("ballbot").xpos[2] < 0.15:
                # Generate random values within bounds
                random_wheel = np.random.uniform(*WHEEL_DIAMETER_BOUNDS)
                random_clearance = np.random.uniform(*CLEARANCE_BOUNDS)
                random_standoff = np.random.uniform(*STANDOFF_LENGTH_BOUNDS)

                # Update variables with random values
                variables["wheel_diameter"].expression = f"{random_wheel:.1f} mm"
                variables["clearance"].expression = f"{random_clearance:.1f} mm"
                variables["standoff_length"].expression = f"{random_standoff:.1f} mm"
                client.set_variables(doc.did, doc.wid, elements["variables"].id, variables)

                ballbot: Robot = Robot.from_url(
                    url=doc.url,
                    client=client,
                    max_depth=1,
                    name="ballbot",
                    robot_type=RobotType.MJCF,
                )
                ballbot.set_robot_position(pos=(0, 0, 0.35))
                ballbot = modify_ballbot(ballbot)
                ballbot.save("ballbot.xml")
                # Close the current viewer
                viewer.close()

                # Create new model and data
                model = mujoco.MjModel.from_xml_path(filename="ballbot.xml")
                data = mujoco.MjData(model)
                mujoco.mj_resetData(model, data)
                # Launch new viewer with updated model
                viewer = mujoco.viewer.launch_passive(model, data)
                continue

            viewer.sync()
