import os
from typing import Optional

import mujoco
import mujoco.viewer
import numpy as np
from scipy.spatial.transform import Rotation
from transformations import compute_motor_torques
from utilities import save_gif

from onshape_api.connect import Client
from onshape_api.graph import create_graph
from onshape_api.log import LOGGER
from onshape_api.models.document import Document
from onshape_api.models.robot import Robot
from onshape_api.parse import get_instances, get_mates_and_relations, get_parts, get_subassemblies
from onshape_api.urdf import get_urdf_components

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


def key_callback(keycode):
    if chr(keycode) == "e":
        print("Exiting")
        return False


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


def export_urdf(url, filename: Optional[str] = None) -> str:
    # if file already exists, return
    if filename is not None and os.path.exists(f"{filename}.urdf"):
        return f"{filename}.urdf"

    client = Client()
    document = Document.from_url(url)
    assembly, _ = client.get_assembly(
        did=document.did,
        wtype=document.wtype,
        wid=document.wid,
        eid=document.eid,
    )

    LOGGER.info(assembly.document.url)
    assembly_robot_name = f"{assembly.document.name + '-' + assembly.name}"

    instances, occurrences, id_to_name_map = get_instances(assembly)
    subassemblies, rigid_subassemblies = get_subassemblies(assembly, client, instances)

    parts = get_parts(assembly, rigid_subassemblies, client, instances)
    mates, relations = get_mates_and_relations(assembly, subassemblies, rigid_subassemblies, id_to_name_map, parts)

    graph, root_node = create_graph(
        occurrences=occurrences,
        instances=instances,
        parts=parts,
        mates=mates,
        use_user_defined_root=False,
    )

    links, joints, assets = get_urdf_components(
        assembly=assembly,
        graph=graph,
        root_node=root_node,
        parts=parts,
        mates=mates,
        relations=relations,
        client=client,
    )

    robot = Robot(name=assembly_robot_name, links=links, joints=joints, assets=assets)

    if filename is None:
        filename = assembly_robot_name

    robot.save(f"{filename}.urdf")


if __name__ == "__main__":
    urdf_path = export_urdf(
        url="https://cad.onshape.com/documents/1f42f849180e6e5c9abfce52/w/0c00b6520fac5fada24b2104/e/c96b40ef586e60c182f41d29",
        filename="ballbot",
    )

    model = mujoco.MjModel.from_xml_path(filename=urdf_path)
    data = mujoco.MjData(model)

    # run_simulation(model, data, 20, 60)

    mujoco.mj_resetData(model, data)

    with mujoco.viewer.launch_passive(model, data, key_callback=key_callback) as viewer:
        initial_roll, initial_pitch, initial_yaw = get_theta(data)

        while viewer.is_running():
            mujoco.mj_step(model, data)
            mujoco.mj_forward(model, data)

            control(data)

            viewer.sync()
