import mujoco
import mujoco.include
import mujoco.viewer
import numpy as np
import optuna
from mods import modify_ballbot
from scipy.spatial.transform import Rotation
from transformations import compute_motor_torques

from onshape_robotics_toolkit.connect import Client
from onshape_robotics_toolkit.log import LOGGER, LogLevel
from onshape_robotics_toolkit.models.document import Document
from onshape_robotics_toolkit.robot import Robot, RobotType

HEIGHT = 480
WIDTH = 640

FREQUENCY = 200
dt = 1 / FREQUENCY
PHASE = 3

# Variable bounds (in mm and degrees)
WHEEL_DIAMETER_BOUNDS = (100, 120)
SPACER_HEIGHT_BOUNDS = (65, 120)
ALPHA_BOUNDS = (30, 55)

SIMULATION_DURATION = 10  # seconds to run each trial
MIN_HEIGHT = 0.15  # minimum height before considering failure

# PID parameters for roll, pitch, and yaw
KP = 160.0
KI = 10.0
KD = 2.0

integral_error_x = 0.0
integral_error_y = 0.0
previous_error_x = 0.0
previous_error_y = 0.0

def get_theta(data, degrees=False):
    rot = Rotation.from_quat(data.qpos[3:7], scalar_first=True)
    theta = rot.as_euler("XYZ", degrees=degrees)
    return theta[0], theta[1], theta[2]

def control(data, alpha):
    global integral_error_x, integral_error_y, previous_error_x, previous_error_y

    # Get current orientation
    theta = get_theta(data)

    # Calculate errors
    error_x = 0.0 - theta[0]
    error_y = 0.0 - theta[1]

    # Update integral errors
    integral_error_x += error_x * dt
    integral_error_y += error_y * dt

    # Calculate derivative errors
    derivative_error_x = (error_x - previous_error_x) / dt
    derivative_error_y = (error_y - previous_error_y) / dt

    # PID control calculations
    tx = KP * error_x + KI * integral_error_x + KD * derivative_error_x
    ty = KP * error_y + KI * integral_error_y + KD * derivative_error_y
    tz = 0.0

    # Saturate the torque values to be within [-3, 3] Nm
    tx = np.clip(tx, -3.0, 3.0)
    ty = np.clip(ty, -3.0, 3.0)
    tz = np.clip(tz, -3.0, 3.0)

    # Update previous errors
    previous_error_x = error_x
    previous_error_y = error_y

    # Compute motor torques
    t1, t2, t3 = compute_motor_torques(np.deg2rad(alpha), tx, ty, tz)
    data.ctrl[0] = t1
    data.ctrl[1] = t2
    data.ctrl[2] = t3


def objective(trial):
    # reset global PID error values
    wheel_diameter = trial.suggest_float("wheel_diameter", WHEEL_DIAMETER_BOUNDS[0], WHEEL_DIAMETER_BOUNDS[1])
    spacer_height = trial.suggest_float("spacer_height", SPACER_HEIGHT_BOUNDS[0], SPACER_HEIGHT_BOUNDS[1])
    alpha = trial.suggest_float("alpha", ALPHA_BOUNDS[0], ALPHA_BOUNDS[1])

    variables["wheel_diameter"].expression = f"{wheel_diameter:.1f} mm"
    variables["alpha"].expression = f"{alpha:.1f} deg"
    variables["spacer_height"].expression = f"{spacer_height:.1f} mm"
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

    model = mujoco.MjModel.from_xml_path(filename="ballbot.xml")
    data = mujoco.MjData(model)
    mujoco.mj_resetData(model, data)

    viewer = mujoco.viewer.launch_passive(model, data)
    try:
        while True:
            timesteps = 0
            max_timesteps = int(SIMULATION_DURATION / model.opt.timestep)
            total_angle_error = 0
            # reset global PID error values
            global integral_error_x, integral_error_y, previous_error_x, previous_error_y
            integral_error_x = 0.0
            integral_error_y = 0.0
            previous_error_x = 0.0
            previous_error_y = 0.0

            # Reset data for a new trial
            mujoco.mj_resetData(model, data)

            while timesteps < max_timesteps and viewer.is_running():
                mujoco.mj_step(model, data)

                if data.time > 0.3:
                    control(data, alpha)

                if data.body("ballbot").xpos[2] < MIN_HEIGHT:
                    print("Ballbot fell below minimum height, ending trial.")
                    break

                roll, pitch, _ = get_theta(data)
                angle_error = np.sqrt(roll**2 + pitch**2)
                total_angle_error += angle_error

                timesteps += 1

                viewer.sync()

            if timesteps == 0:
                print("No timesteps executed, returning infinity.")
                return float("inf")

            avg_angle_error = total_angle_error / timesteps
            objective_value = -timesteps * 0.5 + avg_angle_error * 10

            break

    except Exception as e:
        print(f"An error occurred: {e}")
        return float("inf")
    finally:
        viewer.close()

    return objective_value


if __name__ == "__main__":
    LOGGER.set_file_name("sim.log")
    LOGGER.set_stream_level(LogLevel.INFO)

    client = Client()
    doc = Document.from_url(
        url="https://cad.onshape.com/documents/3a2986509d7fb01c702e8777/w/f1d24a845d320aa654868a90/e/1f70844c54c3ce8edba39060"
    )

    elements = client.get_elements(doc.did, doc.wtype, doc.wid)
    variables = client.get_variables(doc.did, doc.wid, elements["variables"].id)

    study = optuna.create_study(direction="minimize")
    study.optimize(objective, n_trials=10)

    print("\nOptimization finished!")
    print("Best trial:")
    print(f"  Value: {-study.best_trial.value}")
    print("  Params:")
    for key, value in study.best_trial.params.items():
        print(f"    {key}: {value}")
