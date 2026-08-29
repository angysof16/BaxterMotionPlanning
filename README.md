# Baxter ROS2

Baxter robot simulation in ROS2 Jazzy + Gazebo Harmonic, with a roadmap toward distributed motion planning via a custom ROS2 Action interface and Zenoh as RMW bridge.

> **Status:** Phase 4 complete - Custom `MoveArm` action interface integrated and functional. <br/> Phase 5 (Zenoh RMW bridge) next.

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
    ├── baxter_description/             # URDF visualization + meshes
    │   ├── launch/
    │   │   └── display.launch.py
    │   ├── meshes/                 # STL/DAE files per link
    │   └── urdf/
    │       ├── robots/
    │       │   ├── baxter.urdf.xacro
    │       │   └── baxter_standalone.urdf.xacro
    │       └── sensors/
    ├── baxter_moveit_config/           # MoveIt2 configuration
    │   ├── config/
    │   │   ├── baxter.srdf
    │   │   ├── joint_limits.yaml
    │   │   ├── kinematics.yaml
    │   │   ├── moveit_controllers.yaml
    │   │   ├── ompl_planning.yaml
    │   │   └── pilz_cartesian_limits.yaml
    │   ├── launch/
    │   │   └── demo.launch.py          # Full MoveIt2 + Gazebo demo
    │   └── rviz/
    │       └── moveit.rviz
    └── baxter_arm_action/              # Custom MoveArm action interface
        ├── action/
        │   └── MoveArm.action          # Goal / Result / Feedback definition
        ├── baxter_arm_action/
        │   ├── move_arm_server.py      # Action server → wraps /move_action
        │   └── move_arm_client.py      # Example client (hardcoded right arm)
        ├── CMakeLists.txt
        └── package.xml
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
- **MoveIt2:**
  - `ros-jazzy-moveit`
  - `ros-jazzy-moveit-ros-control-interface`
  - `ros-jazzy-moveit-planners-ompl`
  - `ros-jazzy-moveit-simple-controller-manager`
  - `ros-jazzy-moveit-ros-control-interface`

---

## Getting Started

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

### 3. Launch with MoveIt2 + custom action server

```bash
ros2 launch baxter_moveit_config demo.launch.py
```

This launches:
- Gazebo Harmonic simulation
- ros2_control controllers
- MoveIt2 move_group node
- RViz2 with MoveIt plugin
- `move_arm_server` action server (on `/move_arm`)

---

## Usage

### Verifying Controllers

Before sending any commands, always verify that controllers are active.

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

All controllers should show **`active`** status. If any show `inactive` or `unconfigured`, see the [Troubleshooting](#troubleshooting) section.

---

### Using the Custom MoveArm Action

The `MoveArm` action lets you command either arm to a Cartesian target pose. The server translates the request into a MoveIt2 `MotionPlanRequest` and forwards it to `/move_action`.

#### Action definition (`MoveArm.action`)

```
# GOAL
string arm # "right" or "left"
geometry_msgs/PoseStamped target_pose
float64 velocity_scaling            # 0.0-1.0 (default 0.1)
bool cartesian                      # true = linear Cartesian motion
---
# RESULT
bool success
string message
float64 planning_time
float64 execution_time
---
# FEEDBACK
float64 progress                    # 0.0-1.0
string state                        # "planning" | "executing" | "done"
```

#### Send a goal from the command line

```bash
ros2 action send_goal /move_arm baxter_arm_action/action/MoveArm \
  "{arm: 'right',
    target_pose: {
      header: {frame_id: 'world'},
      pose: {
        position: {x: 0.65, y: -0.2, z: 1.1},
        orientation: {w: 1.0}
      }
    },
    velocity_scaling: 0.2,
    cartesian: false}"
```

#### Run the example Python client

```bash
ros2 run baxter_arm_action move_arm_client.py
```

The client sends the right arm to `(0.65, -0.20, 1.10)` in the `world` frame at 20% velocity.

#### Key implementation notes

- The server connects to MoveIt2's `/move_action` (not `/move_group`).
- `tip_link` is set to `right_hand` / `left_hand` to match `kinematics.yaml`.
- Goal constraints use a **4 cm tolerance box** for position and **±0.4 rad** for orientation, which gives OMPL enough freedom to find a valid IK solution.

---

### Using MoveIt2 Interactively (RViz)

1. Launch the demo (if not already running):
   ```bash
   ros2 launch baxter_moveit_config demo.launch.py
   ```

2. In RViz:
   - Select Planning Group: `right_arm` or `left_arm`
   - Drag the interactive marker to set a goal pose
   - Click **Plan** to compute a trajectory
   - Click **Execute** to run it on the robot

---

### Testing Controllers Directly via Action Calls

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

## Troubleshooting

### Controllers not activating automatically?

Activate them manually:

```bash
ros2 control switch_controllers \
  --activate joint_state_broadcaster \
  --activate right_arm_controller \
  --activate left_arm_controller \
  --activate head_controller
```

### LiDAR not showing in Gazebo?

```bash
gz model -m baxter -l lidar_sensor
```

Run this after Gazebo is fully launched. See this [StackExchange discussion](https://robotics.stackexchange.com/questions/118158/entity-spawning-issue-ros-gz-sim-solved-by-listing-link-potentially-bug) for details.

---

## Project Roadmap

| Phase | Description | Status |
|-------|-------------|--------|
| 1 | Baxter URDF + Gazebo Harmonic simulation | ✅ Done |
| 2 | `ros2_control` integration + joint trajectory controller | ✅ Done |
| 3 | MoveIt2 motion planning for pick & place | ✅ Done |
| 4 | Custom `MoveArm` action interface | ✅ Done |
| 5 | Zenoh RMW bridge - two-machine architecture | Planned |
| 6 | Wii Remote teleoperation via `joy` + custom ROS2 node | Planned |
| 7 | FastDDS vs Zenoh latency benchmarks | Possible |

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