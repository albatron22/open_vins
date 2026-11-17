# OpenVINS ROS2 simulation launch file
# This is a port of the ROS1 simulation.launch; note that the ROS1 version
# also launched the ov_eval pose_to_file recorder which is not built in ROS2,
# thus we rely on the save_total_state / filepath_* parameters instead.

import os

from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, LogInfo, OpaqueFunction
from launch.conditions import IfCondition
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node
from ament_index_python.packages import get_package_share_directory

launch_args = [
    DeclareLaunchArgument(name="namespace", default_value="ov_msckf", description="namespace"),
    DeclareLaunchArgument(name="verbosity", default_value="INFO",
                          description="ALL, DEBUG, INFO, WARNING, ERROR, SILENT"),
    DeclareLaunchArgument(name="config", default_value="rpng_sim",
                          description="config name, should match folder in config/"),
    DeclareLaunchArgument(
        name="config_path", default_value="",
        description="path to estimator_config.yaml. If not given, determined based on provided 'config' above",
    ),
    DeclareLaunchArgument(name="seed", default_value="5", description="simulation measurement/perturb seed"),
    DeclareLaunchArgument(name="num_pts", default_value="100", description="number of features to track"),
    DeclareLaunchArgument(name="max_cameras", default_value="2", description="number of cameras"),
    DeclareLaunchArgument(name="use_stereo", default_value="true", description="try to track stereo constraints"),
    DeclareLaunchArgument(name="dataset", default_value="tum_corridor1_512_16_okvis.txt",
                          description="simulation trajectory file in ov_data/sim/"),
    DeclareLaunchArgument(name="freq_cam", default_value="10", description="simulation camera frequency"),
    DeclareLaunchArgument(name="freq_imu", default_value="400", description="simulation imu frequency"),
    DeclareLaunchArgument(name="dosave_state", default_value="false",
                          description="save the total state (see filepath_* keys in the estimator config)"),
    DeclareLaunchArgument(name="rviz_enable", default_value="false", description="enable rviz node"),
]


def launch_setup(context):

    # Resolve the configuration path
    config_path = LaunchConfiguration("config_path").perform(context)
    if not config_path:
        configs_dir = os.path.join(get_package_share_directory("ov_msckf"), "config")
        available_configs = os.listdir(configs_dir)
        config = LaunchConfiguration("config").perform(context)
        if config in available_configs:
            config_path = os.path.join(
                get_package_share_directory("ov_msckf"), "config", config, "estimator_config.yaml"
            )
        else:
            return [
                LogInfo(
                    msg="ERROR: unknown config: '{}' - Available configs are: {} - not starting OpenVINS".format(
                        config, ", ".join(available_configs)
                    )
                )
            ]
    else:
        if not os.path.isfile(config_path):
            return [
                LogInfo(
                    msg="ERROR: config_path file: '{}' - does not exist - not starting OpenVINS".format(config_path)
                )
            ]

    # Path to the simulated trajectory (installed into ov_data share)
    sim_traj_path = os.path.join(
        get_package_share_directory("ov_data"), "sim", LaunchConfiguration("dataset").perform(context)
    )
    if not os.path.isfile(sim_traj_path):
        return [
            LogInfo(
                msg="ERROR: simulation trajectory: '{}' - does not exist - not starting OpenVINS".format(
                    sim_traj_path
                )
            )
        ]

    node1 = Node(
        package="ov_msckf",
        executable="run_simulation",
        namespace=LaunchConfiguration("namespace"),
        output="screen",
        parameters=[
            {"verbosity": LaunchConfiguration("verbosity")},
            {"config_path": config_path},
            # simulation parameters (override the estimator config, see ROS2Visualizer/run_simulation)
            {"sim_traj_path": sim_traj_path},
            {"sim_seed_state_init": 0},
            {"sim_seed_measurements": LaunchConfiguration("seed")},
            {"sim_seed_preturb": LaunchConfiguration("seed")},
            {"sim_do_perturbation": True},
            {"sim_freq_cam": float(int(LaunchConfiguration("freq_cam").perform(context)))},
            {"sim_freq_imu": float(int(LaunchConfiguration("freq_imu").perform(context)))},
            {"num_opencv_threads": 0},
            {"use_stereo": LaunchConfiguration("use_stereo")},
            {"max_cameras": LaunchConfiguration("max_cameras")},
            {"num_pts": LaunchConfiguration("num_pts")},
            {"save_total_state": LaunchConfiguration("dosave_state")},
        ],
    )

    node2 = Node(
        package="rviz2",
        executable="rviz2",
        condition=IfCondition(LaunchConfiguration("rviz_enable")),
        arguments=[
            "-d" + os.path.join(get_package_share_directory("ov_msckf"), "launch", "display_ros2.rviz"),
            "--ros-args", "--log-level", "warn",
        ],
    )

    return [node1, node2]


def generate_launch_description():
    opfunc = OpaqueFunction(function=launch_setup)
    ld = LaunchDescription(launch_args)
    ld.add_action(opfunc)
    return ld
