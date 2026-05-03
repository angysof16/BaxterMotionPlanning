import os
import yaml
from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription, TimerAction
from launch.conditions import IfCondition
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node
from xacro import process_file


ARGUMENTS = [
    DeclareLaunchArgument(
        "use_sim_time",
        default_value="true",
        description="Use simulation clock.",
    ),
    DeclareLaunchArgument(
        "use_rviz",
        default_value="true",
        description="Launch RViz with MoveIt plugin.",
    ),
]


def load_yaml(package_name, file_path):
    pkg = get_package_share_directory(package_name)
    abs_path = os.path.join(pkg, file_path)
    with open(abs_path, "r") as f:
        return yaml.safe_load(f)


def get_robot_description():
    pkg_gazebo = get_package_share_directory("gazebo_baxter")
    pkg_urdf = get_package_share_directory("baxter_description")
    urdf_path = os.path.join(pkg_gazebo, "urdf", "robots", "baxter_gazebo.urdf.xacro")
    robot_desc = process_file(urdf_path, mappings={}).toprettyxml(indent="  ")
    robot_desc = robot_desc.replace("package://baxter_description/", f"file://{pkg_urdf}/")
    return robot_desc


def generate_launch_description():
    ld = LaunchDescription(ARGUMENTS)

    pkg_gazebo = get_package_share_directory("gazebo_baxter")
    pkg_moveit = get_package_share_directory("baxter_moveit_config")

    # GAZEBO
    gazebo_launch = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(pkg_gazebo, "launch", "gazebo.launch.py")
        ),
        launch_arguments={"use_sim_time": LaunchConfiguration("use_sim_time")}.items(),
    )
    ld.add_action(gazebo_launch)

    # ROBOT DESCRIPTION
    robot_description = {"robot_description": get_robot_description()}

    robot_description_semantic = {
        "robot_description_semantic": open(
            os.path.join(pkg_moveit, "config", "baxter.srdf")
        ).read()
    }

    # CONFIG
    kinematics_yaml = load_yaml("baxter_moveit_config", "config/kinematics.yaml")
    ompl_planning_yaml = load_yaml("baxter_moveit_config", "config/ompl_planning.yaml")
    joint_limits_yaml = load_yaml("baxter_moveit_config", "config/joint_limits.yaml")
    pilz_cartesian_limits_yaml = load_yaml("baxter_moveit_config", "config/pilz_cartesian_limits.yaml")
    moveit_controllers_yaml = load_yaml("baxter_moveit_config", "config/moveit_controllers.yaml")


    planning_pipelines = {
        "planning_pipelines": ["ompl"],
        "default_planning_pipeline": "ompl",
        "ompl": ompl_planning_yaml,
    }

    trajectory_execution = {
        "moveit_manage_controllers": True,
        "trajectory_execution.allowed_execution_duration_scaling": 1.2,
        "trajectory_execution.allowed_goal_duration_margin": 0.5,
        "trajectory_execution.allowed_start_tolerance": 0.01,
    }

    move_group_params = [
        robot_description,
        robot_description_semantic,
        kinematics_yaml,
        planning_pipelines,
        trajectory_execution,
        joint_limits_yaml,
        pilz_cartesian_limits_yaml,
        moveit_controllers_yaml,
        {"use_sim_time": LaunchConfiguration("use_sim_time")},
    ]

    # MOVE GROUP
    move_group_node = Node(
        package = "moveit_ros_move_group",
        executable = "move_group",
        output = "screen",
        parameters = move_group_params,
    )
    ld.add_action(TimerAction(period=5.0, actions=[move_group_node]))

    # RVIZ
    rviz_config = os.path.join(pkg_moveit, "rviz", "moveit.rviz")

    rviz_node = Node(
        package="rviz2",
        executable="rviz2",
        name="rviz2",
        output="screen",
        arguments=["-d", rviz_config],
        parameters=[
            robot_description,
            robot_description_semantic,
            kinematics_yaml,
            planning_pipelines,
            joint_limits_yaml,
            {"use_sim_time": LaunchConfiguration("use_sim_time")},
        ],
        condition=IfCondition(LaunchConfiguration("use_rviz")),
    )
    ld.add_action(TimerAction(period=6.0, actions=[rviz_node]))

    return ld