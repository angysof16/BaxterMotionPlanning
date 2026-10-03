# BaxIt!

Baxter robot simulation in ROS2 Jazzy + Gazebo Harmonic, with distributed motion planning via a custom ROS2 action interface and Zenoh as the RMW bridge, plus a second phase that brings the pipeline to the physical robot with autonomous pick & place using computer vision.

> **Status:** Phase 1 (simulation) complete. <br/> Phase 2 (physical robot + vision) in progress.

---

## Overview

This project brings Rethink Robotics' Baxter robot into a modern ROS2 stack, in two phases:

- **Phase 1 - Simulation:** a complete Baxter simulation in Gazebo Harmonic, with `ros2_control`, MoveIt2 for motion planning, and a custom `MoveArm` action interface that abstracts MoveIt2. The long-term goal of this phase is a two-machine architecture with Gazebo running on one machine, MoveIt2 and a high-level controller on another, communicating over **Zenoh** instead of the default DDS middleware.
- **Phase 2 - Physical robot:** the same pipeline brought to the physical Baxter at Pontificia Universidad Javeriana. A vision node using OpenCV detects an object from the wrist camera, computes its 3D position, and the robot executes pick & place fully autonomously without pre-recorded motions. Communication with the robot (ROS1 Indigo) happens through Docker + `rosbridge_suite` + `roslibpy`, without installing ROS1 natively.

---

## Planned Architecture (Phase 1)

<div align="center">
    <img height="500" alt="Image" src="https://github.com/user-attachments/assets/e53076b4-87a3-45d0-976b-5db25c7f14a2" />
</div>

## Phase 2 Architecture - Physical robot

<div align="center">
    <img height="500" alt="Image" src="https://github.com/user-attachments/assets/965b3600-7877-47d6-a32a-09907858a73a" />
</div>

The Docker container runs with `network_mode: host` to share the PC's network and reach the robot directly. `rosbridge_server` exposes all ROS1 topics as a WebSocket at `ws://localhost:9090`. The ROS2 node subscribes to the camera and publishes motion commands through the WebSocket.

---

## Repository Structure

```
baxter/src/
└── baxter/
    ├── gazebo_baxter/
    │   ├── config/
    │   │   ├── ros_gz_bridge.yaml
    │   │   └── controllers.yaml
    │   ├── launch/
    │   │   └── gazebo.launch.py
    │   ├── urdf/
    │   │   ├── robots/
    │   │   │   └── baxter_gazebo.urdf.xacro
    │   │   └── sensors/
    │   └── worlds/
    │       └── empty.sdf
    ├── baxter_description/
    │   ├── launch/
    │   │   └── display.launch.py
    │   ├── meshes/
    │   └── urdf/
    │       ├── baxter.urdf.xacro
    │       ├── baxter_standalone.urdf.xacro
    │       ├── parts/
    │       │   ├── baxter_base.urdf.xacro
    │       │   ├── baxter_torso.urdf.xacro
    │       │   ├── baxter_head.urdf.xacro
    │       │   └── arms/
    │       │       ├── baxter_right_arm.urdf.xacro
    │       │       └── baxter_left_arm.urdf.xacro
    │       ├── electric_gripper/
    │       │   ├── baxter_electric_gripper.xacro
    │       │   └── fingers/
    │       └── sensors/
    ├── baxter_moveit_config/
    │   ├── config/
    │   │   ├── baxter.srdf
    │   │   ├── joint_limits.yaml
    │   │   ├── kinematics.yaml
    │   │   ├── moveit_controllers.yaml
    │   │   ├── ompl_planning.yaml
    │   │   └── pilz_cartesian_limits.yaml
    │   ├── launch/
    │   │   └── demo.launch.py
    │   └── rviz/
    │       └── moveit.rviz
    └── baxter_arm_action/+
        ├── action/
        │   └── MoveArm.action
        └── baxter_arm_action/
            ├── move_arm_server.py
            └── move_arm_client.py
```

---

## Prerequisites

### Phase 1 - Simulation

- ROS2 Jazzy
- Gazebo Harmonic
- `ros-jazzy-ros-gz-bridge`
- `ros-jazzy-xacro`
- `ros-jazzy-robot-state-publisher`
- `ros-jazzy-ros2-control`
- `ros-jazzy-ros2-controllers`
- `ros-jazzy-gz-ros2-control`
- **MoveIt2:**
  - `ros-jazzy-moveit`
  - `ros-jazzy-moveit-ros-control-interface`
  - `ros-jazzy-moveit-planners-ompl`
  - `ros-jazzy-moveit-simple-controller-manager`

### Phase 2 - Physical robot

- Docker
- `rosbridge_suite` (inside the ROS1 Indigo container)
- `roslibpy`
- OpenCV
- Network access to the physical Baxter (same LAN/WiFi segment)

---

## Getting Started - Phase 1 (Simulation)

### 1. Clone and build

```bash
source /opt/ros/jazzy/setup.bash
git clone https://github.com/angysof16/BaxterMotionPlanning.git
cd BaxterMotionPlanning
colcon build --symlink-install
source install/setup.bash
```

### 2. Launch simulation (Gazebo only)

```bash
ros2 launch gazebo_baxter gazebo.launch.py
```

### 3. Launch with MoveIt2 (for motion planning)

```bash
ros2 launch baxter_moveit_config demo.launch.py
```

This launches:
- Gazebo Harmonic simulation
- ros2_control controllers
- MoveIt2 move_group node
- RViz2 with the MoveIt plugin

---

## Usage

### Verifying Controllers

Before sending any commands (via action calls or MoveIt2), always verify that controllers are active. Controller activation can sometimes fail during launch.

```bash
ros2 control list_controllers
```

**Expected output:**
```
head_controller         joint_trajectory_controller/JointTrajectoryController  active
left_arm_controller     joint_trajectory_controller/JointTrajectoryController  active
right_arm_controller    joint_trajectory_controller/JointTrajectoryController  active
joint_state_broadcaster joint_state_broadcaster/JointStateBroadcaster          active
```

All controllers should show **`active`** status. If any controller shows `inactive` or `unconfigured`, see the [Troubleshooting](#troubleshooting) section below.

---

### Using MoveIt2 (Interactive Planning)

1. Launch the demo (if you haven't already):
   ```bash
   ros2 launch baxter_moveit_config demo.launch.py
   ```

2. In RViz:
   - Select Planning Group: `right_arm` or `left_arm`
   - Drag the interactive marker to set a goal pose
   - Click Plan to compute a trajectory
   - Click Execute to run it on the robot

3. The robot in Gazebo should move to match the planned trajectory.

---

### Testing Controllers via Action Calls (Command Line)

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

### Visualize URDF in RViz2 (without Gazebo)

```bash
ros2 launch baxter_description display.launch.py
```

---

### Using the custom `MoveArm` action interface

`baxter_arm_action` abstracts MoveIt2 behind a simple action: it takes an arm + target pose + velocity scaling, and returns success/message + execution time, publishing progress feedback (`planning` → `executing` → `done`).

```bash
ros2 run baxter_arm_action move_arm_server.py
```

```bash
ros2 run baxter_arm_action move_arm_client.py
```

---

## Getting Started - Phase 2 (Physical Robot)

> This phase is under active development; the steps below reflect the planned architecture.

```bash
# Bring up Docker with ROS Indigo + rosbridge
docker-compose up baxter-indigo

# In another terminal - connect the PC to the robot
./baxter.sh

# Run the ROS2 vision node
ros2 run baxter_arm_action vision_pick_place
```

**Docker setup (reference):**

```yaml
services:
  baxter-indigo:
    image: ubuntu:14.04
    network_mode: host
    environment:
      - ROS_MASTER_URI=http://011511P0010.local:11311
      - ROS_IP=<your_local_ip>
    volumes:
      - ./ros_ws:/root/ros_ws
    command: >
      bash -c "source /opt/ros/indigo/setup.bash &&
               source /root/ros_ws/devel/setup.bash &&
               roslaunch rosbridge_server rosbridge_websocket.launch"
```

---

## Troubleshooting

### Controllers not activating automatically?

If `ros2 control list_controllers` shows any controller as `inactive` or `unconfigured`, activate them manually:

```bash
ros2 control switch_controllers \
  --activate joint_state_broadcaster \
  --activate right_arm_controller \
  --activate left_arm_controller \
  --activate head_controller
```

Verify all controllers are now active:
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
> Note: This command needs to be run after Gazebo is launched. The sensor will be visible in the GUI after executing the command.

See this <a href="https://robotics.stackexchange.com/questions/118158/entity-spawning-issue-ros-gz-sim-solved-by-listing-link-potentially-bug">StackExchange discussion</a> for more details.

---

### Xacro can't find a file after modifying the URDF?

If `xacro` fails with `No such file or directory` pointing somewhere inside `urdf/parts/`, check that:

1. The paths in the `xacro:include` statements of `baxter.urdf.xacro` exactly match the real location of each file (including the `arms/` subfolder for the arms).
2. Any other package that includes `baxter.urdf.xacro` (e.g. `gazebo_baxter/urdf/robots/baxter_gazebo.urdf.xacro`) uses the updated path `$(find baxter_description)/urdf/baxter.urdf.xacro`.
3. You rebuilt after the change:
   ```bash
   colcon build --symlink-install --packages-select baxter_description gazebo_baxter
   source install/setup.bash
   ```

---

## Project Roadmap

### Phase 1 - Simulation

| Phase | Description | Status |
|-------|-------------|--------|
| 1 | Baxter URDF + Gazebo Harmonic simulation | ✅ Done |
| 2 | `ros2_control` integration + joint trajectory controller | ✅ Done |
| 3 | MoveIt2 motion planning for pick & place | ✅ Done |
| 4 | Custom `MoveArm` action interface | ✅ Done |
| 5 | Zenoh RMW bridge - two-machine architecture | Planned |
| 6 | Wii Remote teleoperation via `joy` + custom ROS2 node | Planned |
| 7 | FastDDS vs Zenoh latency benchmarks | Possible |

### Phase 2 - Physical Robot (8 weeks)

| Weeks | Stage | Tasks | Status |
|---|---|---|---|
| 1–2 | Setup & Verification | ROS Indigo workspace in Docker, verify camera and grippers, confirm PC ↔ Baxter communication | 🔄 In progress |
| 3–4 | Vision pipeline | Color-based (HSV) cube detection with OpenCV, wrist camera calibration, (u,v) coordinates | 📋 Planned |
| 5–6 | Vision + planning integration | Pixel → 3D conversion via TF, motion to detected position, gripper control | 📋 Planned |
| 7–8 | Full pick and place | End-to-end integrated pipeline, tolerance tuning, repeatability testing, final documentation | 📋 Planned |

---

## Tech Stack

| Component | Phase 1 - Simulation | Phase 2 - Physical Robot |
|---|---|---|
| Framework | ROS2 Jazzy | ROS2 Jazzy + ROS1 Indigo (bridge) |
| Simulator / Robot | Gazebo Harmonic | Physical Baxter (Pontificia Universidad Javeriana) |
| Motion planning | MoveIt2 + OMPL | MoveIt / `baxter_interface` SDK |
| Control | `ros2_control` + `gz_ros2_control` | Baxter electric gripper |
| Inverse kinematics | KDL Kinematics Plugin | - |
| Vision | - | OpenCV (HSV segmentation) |
| Communication | RMW (DDS, Zenoh coming soon) | `rosbridge_suite` + `roslibpy` (WebSocket) |
| Language | Python | Python |

---

## References

- [ROS2 Jazzy docs](https://docs.ros.org/en/jazzy/)
- [Gazebo Harmonic](https://gazebosim.org/docs/harmonic/)
- [MoveIt2](https://moveit.picknik.ai/)
- [ros2_control documentation](https://control.ros.org/jazzy/index.html)
- [MoveIt2 + ros2_control tutorial](https://moveit.picknik.ai/jazzy/doc/examples/controller_configuration/controller_configuration_tutorial.html)
- [rmw_zenoh](https://github.com/ros2/rmw_zenoh)
- [ROS2 Jazzy docs](https://docs.ros.org/en/jazzy/)
- [Macenski et al., Robot Operating System 2: Design, architecture, and uses in the wild](https://arxiv.org/pdf/2211.07752)