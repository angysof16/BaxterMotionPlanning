import os
import yaml
from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node
from xacro import process_file


ARGUMENTS = [
    DeclareLaunchArgument(
        "use_sim_time",
        default_value="true",
        description="Use simulation clock.",
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

    pkg_moveit = get_package_share_directory("baxter_moveit_config")

    robot_description = {"robot_description": get_robot_description()}

    robot_description_semantic = {
        "robot_description_semantic": open(
            os.path.join(pkg_moveit, "config", "baxter.srdf")
        ).read()
    }

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

    move_group_node = Node(
        package = "moveit_ros_move_group",
        executable = "move_group",
        output = "screen",
        parameters = [
            robot_description,
            robot_description_semantic,
            kinematics_yaml,
            planning_pipelines,
            trajectory_execution,
            joint_limits_yaml,
            pilz_cartesian_limits_yaml,
            moveit_controllers_yaml,
            {"use_sim_time": LaunchConfiguration("use_sim_time")},
        ],
    )
    ld.add_action(move_group_node)

    return ld