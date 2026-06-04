cmake_minimum_required(VERSION 3.8)
project(baxter_arm_control)

if(CMAKE_COMPILER_IS_GNUCXX OR CMAKE_CXX_COMPILER_ID MATCHES "Clang")
  add_compile_options(-Wall -Wextra -Wpedantic)
endif()

find_package(ament_cmake REQUIRED)
find_package(rclcpp REQUIRED)
find_package(rclcpp_action REQUIRED)
find_package(moveit_ros_planning_interface REQUIRED)
find_package(baxter_interfaces REQUIRED)
find_package(geometry_msgs REQUIRED)

add_executable(move_arm_server src/move_arm_server.cpp)

ament_target_dependencies(move_arm_server
  rclcpp
  rclcpp_action
  moveit_ros_planning_interface
  baxter_interfaces
  geometry_msgs
)

install(TARGETS move_arm_server
  DESTINATION lib/${PROJECT_NAME}
)

ament_package()