import mujoco
import mujoco.include
import mujoco.viewer
import numpy as np
import optuna
from mods import modify_ballbot
from optuna.pruners import MedianPruner
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
SPACER_HEIGHT_BOUNDS = (75, 120)
ALPHA_BOUNDS = (30, 55)

SIMULATION_DURATION = 20  # seconds to run each trial

PERTURBATION_INCREASE = 0.2 # Amount of Newtons to increase perturbation by each time
PERTURBATION_REST = 10 # Time delay between perturbations - begins after 5 seconds

MIN_HEIGHT = 0.15  # minimum height before considering failure

# PID parameters for roll, pitch, and yaw
KP = 12.0
KI = 6.0
KD = 0.05

TORQUE_LIMIT_HIGH = 5.0
TORQUE_LIMIT_LOW = -5.0

TORQUE_OFFSET = 0.25

integral_error_x = 0.0
integral_error_y = 0.0
integral_error_z = 0.0
previous_error_x = 0.0
previous_error_y = 0.0
previous_error_z = 0.0

def apply_ball_force(data, force):
    data.qfrc_applied[9:12] = force

def get_theta(data, degrees=False):
    rot = Rotation.from_quat(data.qpos[3:7], scalar_first=True)
    theta = rot.as_euler("XYZ", degrees=degrees)
    return theta[0], theta[1], theta[2]

def control(data, alpha):

    global integral_error_x, integral_error_y, integral_error_z, previous_error_x, previous_error_y, previous_error_z

    # Get current orientation
    theta = get_theta(data)

    # Calculate errors
    error_x = 0.0 - theta[0]
    error_y = 0.0 - theta[1]
    error_z = 0.0 - theta[2]

    # Update integral errors
    integral_error_x += error_x * dt
    integral_error_y += error_y * dt
    integral_error_z += error_z * dt

    # Calculate derivative errors
    derivative_error_x = (error_x - previous_error_x) / dt
    derivative_error_y = (error_y - previous_error_y) / dt
    derivative_error_z = (error_z - previous_error_z) / dt

    # Individual terms
    Px_term = KP * error_x
    Ix_term = KI * integral_error_x
    Dx_term = KD * derivative_error_x
    Py_term = KP * error_y
    Iy_term = KI * integral_error_y
    Dy_term = KD * derivative_error_y
    Pz_term = KP * error_z
    Iz_term = KI * integral_error_z
    Dz_term = KD * derivative_error_z

    # PID control calculations
    tx = Px_term + Ix_term + Dx_term
    ty = Py_term + Iy_term + Dy_term
    tz = -(Pz_term + Iz_term + Dz_term)  # EJR thinks this should be negative

    # Adding offset torque to increase sensitivity around zero
    tx = tx + TORQUE_OFFSET * np.sign(tx)
    ty = ty + TORQUE_OFFSET * np.sign(ty)
    #tz = tz + TORQUE_OFFSET * np.sign(tz)

    # Saturate the torque values to be within [TORQUE_LIMIT_LOW, TORQUE_LIMIT_HIGH] Nm
    # XML file specifies actuators with limits at [-50 50]
    tx = np.clip(tx, TORQUE_LIMIT_LOW, TORQUE_LIMIT_HIGH)
    ty = np.clip(ty, TORQUE_LIMIT_LOW, TORQUE_LIMIT_HIGH)
    tz = np.clip(tz, TORQUE_LIMIT_LOW, TORQUE_LIMIT_HIGH)
    #tz = 0.0 # Commenting out the removal of z-axis control for now

    # Update previous errors
    previous_error_x = error_x
    previous_error_y = error_y
    previous_error_z = error_z

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
        timesteps = 0
        max_timesteps = int(SIMULATION_DURATION / model.opt.timestep)
        total_angle_error = 0

        i = 0
        j = 0.0
        direction = [0, 0, 0]

        # reset global PID error values
        global integral_error_x, integral_error_y, integral_error_z
        global previous_error_x, previous_error_y, previous_error_z
        integral_error_x = 0.0
        integral_error_y = 0.0
        integral_error_z = 0.0
        previous_error_x = 0.0
        previous_error_y = 0.0
        previous_error_z = 0.0

        # Reset data for a new trial
        mujoco.mj_resetData(model, data)

        while timesteps < max_timesteps and viewer.is_running():
            i += 1
            mujoco.mj_step(model, data)

            if data.time > 0.3:
                control(data, alpha)

            if data.time > 5 and i % (FREQUENCY*PERTURBATION_REST) == 0:
                j += 1
                LOGGER.info("Applying perturbation...")
                direction = np.random.rand(3)
                direction[2] = 0
                force = direction * j * PERTURBATION_INCREASE
                apply_ball_force(data, force)


            if data.body("ballbot").xpos[2] < MIN_HEIGHT:
                LOGGER.info("Ballbot fell below minimum height, ending trial.")
                break

            roll, pitch, yaw = get_theta(data)
            angle_error = np.sqrt(roll**2 + pitch**2 + yaw**2)
            total_angle_error += angle_error

            timesteps += 1

            viewer.sync()

        if timesteps == 0:
            LOGGER.info("No timesteps executed, returning infinity.")
            return float("inf")

        avg_angle_error = total_angle_error / timesteps
        objective_value = -timesteps * 0.5 + avg_angle_error * 10

    except Exception as e:
        LOGGER.info(f"An error occurred: {e}")
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

    pruner = MedianPruner(n_startup_trials=5, n_warmup_steps=10)
    study = optuna.create_study(direction="minimize", pruner=pruner)
    study.optimize(objective, n_trials=20)

    LOGGER.info("\nOptimization finished!")
    LOGGER.info("Best trial:")
    LOGGER.info(f"  Value: {-study.best_trial.value}")
    LOGGER.info("  Params:")
    for key, value in study.best_trial.params.items():
        LOGGER.info(f"    {key}: {value}")
