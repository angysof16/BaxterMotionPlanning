# Baxter ROS2

Baxter robot simulation in ROS2 Jazzy + Gazebo Harmonic, with a roadmap toward distributed motion planning via a custom ROS2 Action interface and Zenoh as RMW bridge.

> **Status:** Phase 1 complete simulation running. <br/> Phase 2 (Zenoh + MoveIt2) in progress.

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
    │   │   └── ros_gz_bridge.yaml
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

### 3. Visualize URDF

```bash
ros2 launch baxter_description display.launch.py
```
---

## Troubleshooting

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
| 2 | `ros2_control` integration + joint trajectory controller | In progress |
| 3 | MoveIt2 motion planning for pick & place | Planned |
| 4 | Custom `MoveArm` action interface | Planned |
| 5 | Zenoh RMW bridge - two-machine architecture | Planned |
| 6 | Wii Remote teleoperation via `joy` + custom ROS2 node | Planned |
| 7 | FastDDS vs Zenoh latency benchmarks | Possible |

---

## References

- [ROS2 Jazzy docs](https://docs.ros.org/en/jazzy/)
- [Gazebo Harmonic](https://gazebosim.org/docs/harmonic/)
- [MoveIt2](https://moveit.picknik.ai/)
- [rmw_zenoh](https://github.com/ros2/rmw_zenoh)
- Macenski et al., *Robot Operating System 2: Design, architecture, and uses in the wild*, Science Robotics, 2022
