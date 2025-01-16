import os
from functools import partial

import mujoco
import mujoco.include
import mujoco.viewer
import numpy as np
import optuna
from controllers import PIDController
from mods import modify_ballbot
from mujoco.usd import exporter
from optuna.pruners import MedianPruner
from optuna.samplers import NSGAIISampler
from scipy.spatial.transform import Rotation
from transformations import compute_motor_torques

from onshape_robotics_toolkit.connect import Client
from onshape_robotics_toolkit.log import LOGGER, LogLevel
from onshape_robotics_toolkit.models.document import Document
from onshape_robotics_toolkit.robot import Robot, RobotType

HEIGHT = 480
WIDTH = 640

FREQUENCY = 200
USD_FRAME_RATE = 30
dt = 1 / FREQUENCY

# Variable bounds (in mm and degrees)
WHEEL_DIAMETER_BOUNDS = (100, 120)
SPACER_HEIGHT_BOUNDS = (75, 120)
ALPHA_BOUNDS = (30, 55)

SIMULATION_DURATION = 20  # seconds to run each trial
VIBRATION_PENALTY = 1e-3

PERTURBATION_INCREASE = 0.1 # Amount of Newtons to increase perturbation by each time
PERTURBATION_START = 5 # Time delay before perturbations begin
PERTURBATION_REST = 7.5 # Time delay between perturbations

MIN_HEIGHT = 0.15  # minimum height before considering failure
MAX_HEIGHT = 0.35 # maximum height before considering failure

# PID parameters for roll, pitch, and yaw
KP = 13.4
KI = 5.4
KD = 2.4

MAX_PID_TRIALS = 10

TORQUE_LIMIT_HIGH = 5.0
TORQUE_LIMIT_LOW = -5.0

TORQUE_OFFSET = 0.25

def get_theta(data, degrees=False):
    rot = Rotation.from_quat(data.qpos[3:7], scalar_first=True)
    theta = rot.as_euler("XYZ", degrees=degrees)
    return theta[0], theta[1], theta[2]

def get_psi(data):
    return data.qpos[7], data.qpos[8], data.qpos[9]

def get_phi(data, degrees=False):
    rot = Rotation.from_quat(data.qpos[13:17], scalar_first=True)
    phi = rot.as_euler("XYZ", degrees=degrees)
    return phi[0], phi[1], phi[2]

def get_bot_pos(data):
    return data.qpos[0], data.qpos[1], data.qpos[2]

def get_ball_pos(data):
    return data.qpos[10], data.qpos[11], data.qpos[12]

def get_bot_vel(data):
    return data.qvel[0], data.qvel[1], data.qvel[2]

def get_dtheta(data):
    return data.qvel[3], data.qvel[4], data.qvel[5]

def get_dpsi(data):
    return data.qvel[6], data.qvel[7], data.qvel[8]

def get_ball_vel(data):
    return data.qvel[9], data.qvel[10], data.qvel[11]

def get_dphi(data):
    return data.qvel[12], data.qvel[13], data.qvel[14]

def get_states(data):
    theta = get_theta(data)
    phi = get_phi(data)

    dtheta = get_dtheta(data)
    dphi = get_dphi(data)

    return np.array([
        phi[0],
        theta[0],
        dphi[0],
        dtheta[0],
    ]), np.array([
        phi[1],
        theta[1],
        dphi[1],
        dtheta[1],
    ])


def apply_ball_torque(data, torque):
    data.qfrc_applied[12:15] = torque

def apply_ball_force(data, force):
    data.qfrc_applied[9:12] = force

def apply_wheel_torque(data, torque):
    data.qfrc_applied[6:9] = torque

def get_wheel_torque(data):
    return data.qfrc_smooth[6], data.qfrc_smooth[7], data.qfrc_smooth[8]


def control(data, roll_pid, pitch_pid, variables: dict[str, float]):
    # Get current orientation
    theta = get_theta(data)

    # Calculate errors
    error_x = 0.0 - theta[0]
    error_y = 0.0 - theta[1]

    tx = roll_pid.update(error_x)
    ty = pitch_pid.update(error_y)
    tz = 0.0

    # Compute motor torques
    t1, t2, t3 = compute_motor_torques(np.deg2rad(variables["alpha"]), tx, ty, tz, theta[2])

    data.ctrl[0] = t1
    data.ctrl[1] = t2
    data.ctrl[2] = t3

def apply_perturbation(data, count):
    direction = np.random.rand(3)
    direction[2] = 0 # Only apply force in the x-y plane

    force = direction * count * PERTURBATION_INCREASE
    LOGGER.info(f"Applying perturbation {count}: {force}")
    apply_ball_force(data, force)


def find_best_pid_params(trial, model, data, viewer, variables, usd_output_dir):
    # Suggest values for the PID gains
    kp = trial.suggest_float('kp', low=2, high=25.0, step=0.1)
    ki = trial.suggest_float('ki', low=0.0, high=15.0, step=0.1)
    kd = trial.suggest_float('kd', low=0.0, high=1.0, step=0.001)
    ff = trial.suggest_float('ff', low=0.01, high=1.0, step=0.05)

    LOGGER.info(f"KP: {kp}, KI: {ki}, KD: {kd}")

    usd_exporter = exporter.USDExporter(
        model=model,
        output_directory=usd_output_dir + f"_{trial.number}",
    )

    # Initialize the PID controllers with the suggested gains
    roll_pid = PIDController(
        kp=kp,
        ki=ki,
        kd=kd,
        dt=1.0/FREQUENCY,
        min_output=TORQUE_LIMIT_LOW,
        max_output=TORQUE_LIMIT_HIGH,
        feed_forward_offset=ff,
        derivative_filter_alpha=0.2,
    )
    pitch_pid = PIDController(
        kp=kp,
        ki=ki,
        kd=kd,
        dt=1.0/FREQUENCY,
        min_output=TORQUE_LIMIT_LOW,
        max_output=TORQUE_LIMIT_HIGH,
        feed_forward_offset=ff,
        derivative_filter_alpha=0.2,
    )

    # Reset the simulation
    mujoco.mj_resetData(model, data)
    roll_pid.reset()
    pitch_pid.reset()

    # Initialize vibration accumulator
    vibration_accumulator = 0.0

    # Run the simulation
    j = 0
    dt = 1.0 / FREQUENCY

    while data.time < SIMULATION_DURATION and viewer.is_running():
        mujoco.mj_step(model, data)

        if usd_exporter.frame_count < data.time * USD_FRAME_RATE:
            usd_exporter.update_scene(data=data)

        if data.time > 0.3:
            control(data, roll_pid, pitch_pid, variables)

        if data.time > PERTURBATION_START + j * PERTURBATION_REST:
            j += 1
            apply_perturbation(data, j)

        if data.qpos[2] < MIN_HEIGHT:
            break

        # Accumulate vibration metric (e.g., sum of squared angular velocities)
        if data.qpos[2] < MAX_HEIGHT: # only accumulate vibration till the bot is on the ball
            dtheta = get_dtheta(data)  # Returns (dtheta_x, dtheta_y, dtheta_z)
            vibration_accumulator += dtheta[0]**2 + dtheta[1]**2

        viewer.sync()

    # Combine performance metric with vibration penalty
    time_on_ball = data.time # TODO: Make this more accurate with contact detection
    vibrations = vibration_accumulator / data.time # Normalizing by trial time to not penalize longer trials

    usd_exporter.save_scene(filetype="usd")

    return time_on_ball, vibrations


def find_best_design_variables(trial):
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
    viewer = mujoco.viewer.launch_passive(model, data)
    mujoco.mj_resetData(model, data)

    # find the best PID parameters
    # setup a partial function to pass in the model and data
    this_pid_study = partial(
        find_best_pid_params,
        model=model,
        data=data,
        viewer=viewer,
        variables={
            "wheel_diameter": wheel_diameter,
            "spacer_height": spacer_height,
            "alpha": alpha,
        },
        usd_output_dir=f"scenes/trial_{trial.number}/pid",
    )
    pid_study = optuna.create_study(directions=["maximize", "minimize"], sampler=NSGAIISampler())
    pid_study.optimize(this_pid_study, n_trials=MAX_PID_TRIALS)
    viewer.close()

    # Print the best parameters
    best_trial = None
    best_score = float('-inf')

    for trial in pid_study.best_trials:
        time_on_ball, vibrations = trial.values
        score = time_on_ball - VIBRATION_PENALTY * vibrations

        if score > best_score:
            best_score = score
            best_trial = trial

    if best_trial is None:
        LOGGER.error("No best trial found")
        kp = KP
        ki = KI
        kd = KD
        ff = 0.2
    else:
        print("Chosen single best trial according to custom scoring:")
        print("  Score:", best_score)
        print("  Params:", best_trial.params)
        print("  Objective values (time, vibrations):", best_trial.values)

        kp = best_trial.params["kp"]
        ki = best_trial.params["ki"]
        kd = best_trial.params["kd"]
        ff = best_trial.params["ff"]

    best_roll_pid = PIDController(
        kp=kp,
        ki=ki,
        kd=kd,
        dt=1.0/FREQUENCY,
        min_output=TORQUE_LIMIT_LOW,
        max_output=TORQUE_LIMIT_HIGH,
        feed_forward_offset=ff,
        derivative_filter_alpha=0.2,
    )
    best_pitch_pid = PIDController(
        kp=kp,
        ki=ki,
        kd=kd,
        dt=1.0/FREQUENCY,
        min_output=TORQUE_LIMIT_LOW,
        max_output=TORQUE_LIMIT_HIGH,
        feed_forward_offset=ff,
        derivative_filter_alpha=0.2,
    )

    mujoco.mj_resetData(model, data)

    usd_exporter = exporter.USDExporter(
        model=model,
        output_directory=f"scenes/trial_{trial.number}",
    )

    total_angle_error = 0
    j = 0
    viewer = mujoco.viewer.launch_passive(model, data)
    # Reset data for a new trial
    mujoco.mj_resetData(model, data)

    while data.time < SIMULATION_DURATION and viewer.is_running():
        mujoco.mj_step(model, data)

        if usd_exporter.frame_count < data.time * USD_FRAME_RATE:
            usd_exporter.update_scene(data=data)

        if data.time > 0.3:
            control(data, best_roll_pid, best_pitch_pid, {"alpha": alpha, "wheel_diameter": wheel_diameter, "spacer_height": spacer_height})

        if data.time > PERTURBATION_START + j * PERTURBATION_REST:
            j += 1
            apply_perturbation(data, j)

        if data.body("ballbot").xpos[2] < MIN_HEIGHT:
            LOGGER.info("Ballbot fell below minimum height, ending trial.")
            break

        if data.qpos[2] < MAX_HEIGHT:
            roll, pitch, yaw = get_theta(data)
            angle_error = np.sqrt(roll**2 + pitch**2 + yaw**2)
            total_angle_error += angle_error

        viewer.sync()

    avg_angle_error = total_angle_error / data.time
    objective_value = -data.time * 0.5 + avg_angle_error * 10

    viewer.close()
    usd_exporter.save_scene(filetype="usd")

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
    study.optimize(find_best_design_variables, n_trials=5)

    LOGGER.info("\nOptimization finished!")
    LOGGER.info("Best trial:")
    LOGGER.info(f"  Value: {-study.best_trial.value}")
    LOGGER.info("  Params:")
    for key, value in study.best_trial.params.items():
        LOGGER.info(f"    {key}: {value}")
