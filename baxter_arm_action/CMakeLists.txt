cmake_minimum_required(VERSION 3.8)
project(baxter_arm_action)

find_package(ament_cmake REQUIRED)
find_package(rosidl_default_generators REQUIRED)
find_package(geometry_msgs REQUIRED)
find_package(action_msgs REQUIRED)

rosidl_generate_interfaces(${PROJECT_NAME}
  "action/MoveArm.action"
  DEPENDENCIES geometry_msgs action_msgs
)

install(PROGRAMS
  baxter_arm_action/move_arm_server.py
  baxter_arm_action/move_arm_client.py
  DESTINATION lib/${PROJECT_NAME}
)

ament_package()