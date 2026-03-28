import os
from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import (
    AppendEnvironmentVariable,
    DeclareLaunchArgument,
    SetEnvironmentVariable,
    IncludeLaunchDescription,
)
from launch.conditions import IfCondition
from launch.substitutions import PathJoinSubstitution, LaunchConfiguration
from launch_ros.actions import Node
from launch.launch_description_sources import PythonLaunchDescriptionSource
from xacro import process_file
from nav2_common.launch import ReplaceString

ARGUMENTS = [
    DeclareLaunchArgument(
        "world_name",
        default_value="empty.sdf",
        description="Name of the world to load.",
    ),
    DeclareLaunchArgument(
        "ros_bridge", default_value="True", description="Run ROS bridge node."
    ),
    DeclareLaunchArgument(
        "initial_pose_x",
        default_value="0.0",
        description="Initial x pose of Baxter in the simulation.",
    ),
    DeclareLaunchArgument(
        "initial_pose_y",
        default_value="0.0",
        description="Initial y pose of Baxter in the simulation.",
    ),
    DeclareLaunchArgument(
        "initial_pose_z",
        default_value="0.0",
        description="Initial z pose of Baxter in the simulation.",
    ),
    DeclareLaunchArgument(
        "initial_pose_yaw",
        default_value="0.0",
        description="Initial yaw of Baxter in the simulation.",
    ),
    DeclareLaunchArgument(
        "robot_description_topic",
        default_value="robot_description",
        description="Robot description topic.",
    ),
    DeclareLaunchArgument(
        "rsp_frequency",
        default_value="30.0",
        description="Robot State Publisher frequency.",
    ),
    DeclareLaunchArgument(
        "use_sim_time",
        default_value="true",
        description="Use simulation (Gazebo) clock if true.",
    ),
    DeclareLaunchArgument(
        "entity",
        default_value="baxter",
        description="Name of the robot entity in Gazebo.",
    ),
]


def get_robot_description():
    # ── Package paths ──────────────────────────────────────────────────────────
    pkg_gazebo = get_package_share_directory("gazebo_baxter")
    pkg_urdf = get_package_share_directory("baxter_description")

    # ── Process xacro ─────────────────────────────────────────────────────────
    urdf_path = os.path.join(pkg_gazebo, "urdf", "robots", "baxter_gazebo.urdf.xacro")
    robot_description_config = process_file(urdf_path, mappings={})
    robot_desc = robot_description_config.toprettyxml(indent="  ")

    # Replace package:// URIs with absolute file:// paths so Gazebo finds meshes
    robot_desc = robot_desc.replace("package://baxter_description/", f"file://{pkg_urdf}/")
    return robot_desc


def generate_launch_description():
    ld = LaunchDescription(ARGUMENTS)

    # ── Package paths ──────────────────────────────────────────────────────────
    pkg_ros_gz_sim = get_package_share_directory("ros_gz_sim")
    pkg_gazebo = get_package_share_directory("gazebo_baxter")
    pkg_urdf = get_package_share_directory("baxter_description")

    # ── Paths ─────────────────────────────────────────────────────────────────
    gz_launch_path = PathJoinSubstitution(
        [pkg_ros_gz_sim, "launch", "gz_sim.launch.py"]
    )
    world_path = PathJoinSubstitution(
        [pkg_gazebo, "worlds", LaunchConfiguration("world_name")]
    )
    bridge_config_path = os.path.join(pkg_gazebo, "config", "ros_gz_bridge.yaml")

    # ── Resource paths for Gazebo (meshes + models) ───────────────────────────
    ld.add_action(
        AppendEnvironmentVariable(
            "GZ_SIM_RESOURCE_PATH",
            [
                os.path.join(pkg_gazebo, "models"),
                os.path.join(pkg_urdf, "meshes"),
                pkg_urdf,
            ],
        )
    )
    ld.add_action(
        SetEnvironmentVariable(
            "GZ_SIM_RESOURCE_PATH",
            f"{os.path.join(pkg_gazebo, 'models')}"
            f":{os.path.join(pkg_urdf, 'meshes')}"
            f":{pkg_urdf}",
        )
    )

    # ── Gazebo Harmonic ───────────────────────────────────────────────────────
    ld.add_action(
        IncludeLaunchDescription(
            PythonLaunchDescriptionSource(gz_launch_path),
            launch_arguments={
                "gz_args": [world_path],
                "on_exit_shutdown": "True",
            }.items(),
        )
    )

    # ── /clock bridge (always needed) ─────────────────────────────────────────
    ld.add_action(
        Node(
            package="ros_gz_bridge",
            executable="parameter_bridge",
            arguments=["/clock@rosgraph_msgs/msg/Clock[gz.msgs.Clock"],
            output="screen",
            condition=IfCondition(LaunchConfiguration("ros_bridge")),
        )
    )

    # ── Robot State Publisher ─────────────────────────────────────────────────
    ld.add_action(
        Node(
            package="robot_state_publisher",
            executable="robot_state_publisher",
            name="robot_state_publisher",
            output="both",
            parameters=[
                {
                    "use_sim_time": LaunchConfiguration("use_sim_time"),
                    "publish_frequency": LaunchConfiguration("rsp_frequency"),
                    "robot_description": get_robot_description(),
                }
            ],
        )
    )

    # ── Spawn Baxter in Gazebo ────────────────────────────────────────────────
    ld.add_action(
        Node(
            package="ros_gz_sim",
            executable="create",
            arguments=[
                "-name",
                LaunchConfiguration("entity"),
                "-topic",
                LaunchConfiguration("robot_description_topic"),
                "-x",
                LaunchConfiguration("initial_pose_x"),
                "-y",
                LaunchConfiguration("initial_pose_y"),
                "-z",
                LaunchConfiguration("initial_pose_z"),
                "-R",
                "0",
                "-P",
                "0",
                "-Y",
                LaunchConfiguration("initial_pose_yaw"),
            ],
            output="screen",
        )
    )

    # ── Full sensor/topic bridge ──────────────────────────────────────────────
    bridge_config = ReplaceString(
        source_file=bridge_config_path,
        replacements={"<entity>": LaunchConfiguration("entity")},
    )
    ld.add_action(
        Node(
            package="ros_gz_bridge",
            executable="parameter_bridge",
            output="screen",
            parameters=[{"config_file": bridge_config}],
            condition=IfCondition(LaunchConfiguration("ros_bridge")),
        )
    )

    return ld
