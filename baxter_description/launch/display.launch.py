from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.conditions import IfCondition, UnlessCondition
from launch.substitutions import Command, LaunchConfiguration, PathJoinSubstitution
from launch_ros.actions import Node
from launch_ros.parameter_descriptions import ParameterValue


ARGUMENTS = [
    DeclareLaunchArgument(
        name="gui",
        default_value="true",
        choices=["true", "false"],
        description="Enable joint_state_publisher_gui",
    ),
    DeclareLaunchArgument(
        name="model",
        default_value=PathJoinSubstitution(
            [
                get_package_share_directory("baxter_description"),
                "urdf",
                "robots",
                "baxter_standalone.urdf.xacro",
            ]
        ),
        description="Path to the robot URDF/Xacro",
    ),
    DeclareLaunchArgument(
        name="rviz_config",
        default_value=PathJoinSubstitution(
            [get_package_share_directory("baxter_description"), "rviz", "display.rviz"]
        ),
        description="Path to RViz config file",
    ),
]


def generate_launch_description():
    # Process the URDF/Xacro file
    robot_description = ParameterValue(
        Command(["xacro ", LaunchConfiguration("model")]),
        value_type=str
    )

    # Robot State Publisher
    robot_state_publisher = Node(
        package="robot_state_publisher",
        executable="robot_state_publisher",
        name="robot_state_publisher",
        output="screen",
        parameters=[{"robot_description": robot_description}],
    )

    # Joint State Publisher GUI
    joint_state_publisher_gui = Node(
        package="joint_state_publisher_gui",
        executable="joint_state_publisher_gui",
        name="joint_state_publisher_gui",
        condition=IfCondition(LaunchConfiguration("gui")),
    )

    # Joint State Publisher
    joint_state_publisher = Node(
        package="joint_state_publisher",
        executable="joint_state_publisher",
        name="joint_state_publisher",
        condition=UnlessCondition(LaunchConfiguration("gui")),
    )

    # RViz2
    rviz2 = Node(
        package="rviz2",
        executable="rviz2",
        name="rviz2",
        output="screen",
        arguments=["-d", LaunchConfiguration("rviz_config")],
    )

    ld = LaunchDescription(ARGUMENTS)
    ld.add_action(robot_state_publisher)
    ld.add_action(joint_state_publisher_gui)
    ld.add_action(joint_state_publisher)
    ld.add_action(rviz2)

    return ld