# Baxter ROS2

Baxter robot simulation in ROS2 Jazzy + Gazebo Harmonic, with a roadmap toward distributed motion planning via a custom ROS2 Action interface and Zenoh as RMW bridge.

> **Status:** Phase 2 complete - ros2_control integrated. <br/> Phase 3 (MoveIt2) in progress.

---

## Overview

This project brings Rethink Robotics' Baxter robot into a modern ROS2 stack. The long-term goal is a two-machine architecture where Gazebo runs the simulation on one machine while MoveIt2 and a high-level controller run on another, communicating over **Zenoh** instead of the default DDS middleware.

---

## Planned Architecture

<div align="center">
    <img height="500" alt="Image" src="https://github.com/user-attachments/assets/e53076b4-87a3-45d0-976b-5db25c7f14a2" />
</div>

---

## Repository Structure

```
baxter/src/
└── baxter/
    ├── baxter.urdf
    ├── gazebo_baxter/       # Gazebo Harmonic simulation
    │   ├── config/
    │   │   ├── ros_gz_bridge.yaml
    │   │   └── controllers.yaml     # ros2_control configuration
    │   ├── launch/
    │   │   └── gazebo.launch.py
    │   ├── urdf/
    │   │   ├── robots/
    │   │   │   └── baxter_gazebo.urdf.xacro
    │   │   └── sensors/            # Camera RGB, RGBD, IMU, LiDAR
    │   └── worlds/
    │       └── empty.sdf
    └── baxter_description/             # URDF visualization + meshes
        ├── launch/
        │   └── display.launch.py
        ├── meshes/                 # STL/DAE files per link
        └── urdf/
            ├── robots/
            │   ├── baxter.urdf.xacro
            │   └── baxter_standalone.urdf.xacro
            └── sensors/
```

---

## Prerequisites

- ROS2 Jazzy
- Gazebo Harmonic
- `ros-jazzy-ros-gz-bridge`
- `ros-jazzy-xacro`
- `ros-jazzy-robot-state-publisher`
- `ros-jazzy-ros2-control`
- `ros-jazzy-ros2-controllers`
- `ros-jazzy-gz-ros2-control`

---

## Getting Started

### 1. Clone and build

```bash
git clone https://github.com/angysof16/BaxterMotionPlanning.git
cd BaxterMotionPlanning
colcon build --symlink-install
source install/setup.bash
```

### 2. Launch simulation

```bash
ros2 launch gazebo_baxter gazebo.launch.py
```

### 3. Verify controllers are active

In another terminal:

```bash
ros2 control list_controllers
```

Expected output:
```
head_controller         joint_trajectory_controller/JointTrajectoryController  active
left_arm_controller     joint_trajectory_controller/JointTrajectoryController  active
right_arm_controller    joint_trajectory_controller/JointTrajectoryController  active
joint_state_broadcaster joint_state_broadcaster/JointStateBroadcaster          active
```

### 4. Visualize URDF

```bash
ros2 launch baxter_description display.launch.py
```

---

## Usage

### Testing the Controllers

#### Move Right Arm

```bash
ros2 action send_goal /right_arm_controller/follow_joint_trajectory \
  control_msgs/action/FollowJointTrajectory \
  "{trajectory: {
    joint_names: [
      torso_right_upper_shoulder,
      right_upper_shoulder_lower_shoulder,
      right_lower_shoulder_upper_elbow,
      right_upper_elbow_lower_elbow,
      right_lower_elbow_upper_forearm,
      right_upper_forearm_lower_forearm,
      right_lower_forearm_wrist
    ],
    points: [
      {positions: [0.5, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0], time_from_start: {sec: 2}},
      {positions: [0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0], time_from_start: {sec: 4}}
    ]
  }}"
```

#### Move Left Arm

```bash
ros2 action send_goal /left_arm_controller/follow_joint_trajectory \
  control_msgs/action/FollowJointTrajectory \
  "{trajectory: {
    joint_names: [
      torso_left_upper_shoulder,
      left_upper_shoulder_lower_shoulder,
      left_lower_shoulder_upper_elbow,
      left_upper_elbow_lower_elbow,
      left_lower_elbow_upper_forearm,
      left_upper_forearm_lower_forearm,
      left_lower_forearm_wrist
    ],
    points: [
      {positions: [0.5, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0], time_from_start: {sec: 2}},
      {positions: [0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0], time_from_start: {sec: 4}}
    ]
  }}"
```

#### Move Head

```bash
ros2 action send_goal /head_controller/follow_joint_trajectory \
  control_msgs/action/FollowJointTrajectory \
  "{trajectory: {
    joint_names: [torso_head],
    points: [
      {positions: [0.5], time_from_start: {sec: 1}},
      {positions: [-0.5], time_from_start: {sec: 2}},
      {positions: [0.0], time_from_start: {sec: 3}}
    ]
  }}"
```

---

## Troubleshooting

### joint_state_broadcaster stays inactive?

If `ros2 control list_controllers` shows `joint_state_broadcaster` as `inactive`, activate it manually:

```bash
ros2 control set_controller_state joint_state_broadcaster activate
```

Or use:
```bash
ros2 control switch_controllers --activate joint_state_broadcaster
```

Verify all controllers are active:
```bash
ros2 control list_controllers
```

All controllers should show `active` status.

---

### LiDAR not showing in Gazebo simulation?

If you see the error:
```bash
[GUI] [Err] [VisualizeLidar.cc:285] The lidar entity with topic '[/scan]' could not be found.
```
This is a known issue where Gazebo doesn't automatically visualize GPU LiDAR sensors. To fix it, manually list the sensor link:
```bash
gz model -m baxter -l lidar_sensor
```
>Note: This command needs to be run after Gazebo is launched. The sensor will be visible in the GUI after executing the command.

See this <a href="https://robotics.stackexchange.com/questions/118158/entity-spawning-issue-ros-gz-sim-solved-by-listing-link-potentially-bug">StackExchange discussion </a> for more details.

---

## Project Roadmap

| Phase | Description | Status |
|-------|-------------|--------|
| 1 | Baxter URDF + Gazebo Harmonic simulation | Done |
| 2 | `ros2_control` integration + joint trajectory controller | Done |
| 3 | MoveIt2 motion planning for pick & place | In progress |
| 4 | Custom `MoveArm` action interface | Planned |
| 5 | Zenoh RMW bridge - two-machine architecture | Planned |
| 6 | Wii Remote teleoperation via `joy` + custom ROS2 node | Planned |
| 7 | FastDDS vs Zenoh latency benchmarks | Possible |

---

## References

- [ROS2 Jazzy docs](https://docs.ros.org/en/jazzy/)
- [Gazebo Harmonic](https://gazebosim.org/docs/harmonic/)
- [MoveIt2](https://moveit.picknik.ai/)
- [ros2_control documentation](https://control.ros.org/jazzy/index.html)
- [rmw_zenoh](https://github.com/ros2/rmw_zenoh)
- Macenski et al., <a href="https://arxiv.org/pdf/2211.07752"> Robot Operating System 2: Design, architecture, and uses in the wild</a>, Science Robotics, 2022