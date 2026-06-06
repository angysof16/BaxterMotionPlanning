#!/usr/bin/env python3
import time
import rclpy
from rclpy.node import Node
from rclpy.action import ActionServer, ActionClient, CancelResponse, GoalResponse
from rclpy.callback_groups import ReentrantCallbackGroup
from rclpy.executors import MultiThreadedExecutor

from baxter_arm_action.action import MoveArm
from moveit_msgs.action import MoveGroup
from moveit_msgs.msg import (
  MotionPlanRequest, WorkspaceParameters, RobotState,
  Constraints, PositionConstraint, OrientationConstraint,
  BoundingVolume, MoveItErrorCodes
)
from shape_msgs.msg import SolidPrimitive
from geometry_msgs.msg import PoseStamped, Vector3
from std_msgs.msg import Header


class MoveArmServer(Node):
  def __init__(self):
    super().__init__('move_arm_server')

    server_cb = ReentrantCallbackGroup()
    client_cb = ReentrantCallbackGroup()
    timer_cb  = ReentrantCallbackGroup()

    self._move_group_client = ActionClient(
        self, MoveGroup, '/move_group', callback_group=client_cb)

    self._action_server = ActionServer(
        self, MoveArm, 'move_arm',
        execute_callback=self.execute_cb,
        goal_callback=self.goal_cb,
        cancel_callback=self.cancel_cb,
        callback_group=server_cb,
    )

    self._client_cb = client_cb  # guardar referencia para usarla en execute_cb

    self._init_timer = self.create_timer(
        1.0, self._check_move_group, callback_group=timer_cb)
    self.get_logger().info('Servidor MoveArm iniciando...')
  # end def

  def _check_move_group(self):
    if self._move_group_client.server_is_ready():
      self._init_timer.cancel()
      self.get_logger().info('Servidor MoveArm listo ✓')
    else:
      self.get_logger().info('Esperando /move_group...')

  def goal_cb(self, goal_request):
    self.get_logger().info('goal_cb_llamado')
    if goal_request.arm not in ('right', 'left'):
      self.get_logger().warn(f'Brazo inválido: {goal_request.arm}')
      return GoalResponse.REJECT
    # end if

    return GoalResponse.ACCEPT
  #end def

  def cancel_cb(self, _):
    return CancelResponse.ACCEPT
  # end def

  def execute_cb(self, goal_handle):
    import threading
    goal = goal_handle.request
    result = MoveArm.Result()
    feedback = MoveArm.Feedback()

    group = f'{goal.arm}_arm'
    ee_link = f'{goal.arm}_gripper'
    self.get_logger().info(f'MoveArm → {group} | pose: {goal.target_pose.pose.position}')

    feedback.state = 'planning'
    feedback.progress = 0.1
    goal_handle.publish_feedback(feedback)

    req = MotionPlanRequest()
    req.group_name = group
    req.num_planning_attempts = 5
    req.allowed_planning_time = 5.0
    req.max_velocity_scaling_factor = float(goal.velocity_scaling) if goal.velocity_scaling > 0 else 0.1
    req.max_acceleration_scaling_factor = 0.1

    req.workspace_parameters = WorkspaceParameters()
    req.workspace_parameters.header.frame_id = 'world'
    req.workspace_parameters.min_corner.x = -2.0
    req.workspace_parameters.min_corner.y = -2.0
    req.workspace_parameters.min_corner.z = -2.0
    req.workspace_parameters.max_corner.x =  2.0
    req.workspace_parameters.max_corner.y =  2.0
    req.workspace_parameters.max_corner.z =  2.0

    req.start_state.is_diff = True
    pose = goal.target_pose

    pos_c = PositionConstraint()
    pos_c.header = Header(frame_id='world')
    pos_c.link_name = ee_link
    pos_c.target_point_offset = Vector3(x=0.0, y=0.0, z=0.0)
    sphere = BoundingVolume()
    solid = SolidPrimitive()
    solid.type = SolidPrimitive.SPHERE
    solid.dimensions = [0.01]
    sphere.primitives = [solid]
    sphere.primitive_poses = [pose.pose]
    pos_c.constraint_region = sphere
    pos_c.weight = 1.0

    ori_c = OrientationConstraint()
    ori_c.header = Header(frame_id='world')
    ori_c.link_name = ee_link
    ori_c.orientation = pose.pose.orientation
    ori_c.absolute_x_axis_tolerance = 0.1
    ori_c.absolute_y_axis_tolerance = 0.1
    ori_c.absolute_z_axis_tolerance = 0.1
    ori_c.weight = 1.0

    goal_constraints = Constraints()
    goal_constraints.position_constraints = [pos_c]
    goal_constraints.orientation_constraints = [ori_c]
    req.goal_constraints = [goal_constraints]

    mg_goal = MoveGroup.Goal()
    mg_goal.request = req
    mg_goal.planning_options.plan_only = False
    mg_goal.planning_options.replan = True
    mg_goal.planning_options.replan_attempts = 3

    t0 = self.get_clock().now()

    # Nodo y executor dedicados solo para esta llamada al move_group
    result_container = {}
    done_event = threading.Event()

    def run_client():
      client_node = rclpy.create_node('move_arm_mg_client')
      executor = rclpy.executors.SingleThreadedExecutor()
      executor.add_node(client_node)

      client = ActionClient(client_node, MoveGroup, '/move_group')

      # Esperar servidor con timeout usando spin_once
      timeout = 10.0
      start = time.time()
      while not client.server_is_ready():
          executor.spin_once(timeout_sec=0.1)
          if time.time() - start > timeout:
              result_container['error'] = 'Timeout esperando /move_group'
              client_node.destroy_node()
              done_event.set()
              return

      future = client.send_goal_async(mg_goal)
      while not future.done():
          executor.spin_once(timeout_sec=0.1)

      gh = future.result()
      if not gh or not gh.accepted:
          result_container['error'] = 'move_group rechazó el goal'
          executor.shutdown()
          client_node.destroy_node()
          done_event.set()
          return

      res_future = gh.get_result_async()
      while not res_future.done():
          executor.spin_once(timeout_sec=0.1)

      result_container['result'] = res_future.result().result
      executor.shutdown()
      client_node.destroy_node()
      done_event.set()
    # end def

    t = threading.Thread(target=run_client, daemon=True)
    t.start()
    done_event.wait(timeout=60.0)

    elapsed = (self.get_clock().now() - t0).nanoseconds / 1e9

    if 'error' in result_container:
        result.success = False
        result.message = result_container['error']
        goal_handle.abort()
        return result

    if 'result' not in result_container:
        result.success = False
        result.message = 'Timeout esperando resultado de move_group'
        goal_handle.abort()
        return result

    mg_result = result_container['result']
    if mg_result.error_code.val == MoveItErrorCodes.SUCCESS:
        feedback.state = 'done'
        feedback.progress = 1.0
        goal_handle.publish_feedback(feedback)
        result.success = True
        result.execution_time = elapsed
        result.message = f'{group} llegó al objetivo'
        self.get_logger().info(f'✓ {result.message} ({elapsed:.2f}s)')
        goal_handle.succeed()
    else:
        result.success = False
        result.message = f'MoveIt error: {mg_result.error_code.val}'
        self.get_logger().error(result.message)
        goal_handle.abort()

    return result
  # end def
# end class

def main(args=None):
  rclpy.init(args=args)
  executor = MultiThreadedExecutor(num_threads=8)
  node = MoveArmServer()
  executor.add_node(node)
  executor.spin()
  rclpy.shutdown()
# end def

if __name__ == '__main__':
  main()
