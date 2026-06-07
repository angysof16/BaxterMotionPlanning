#!/usr/bin/env python3
import threading
import rclpy
from rclpy.node import Node
from rclpy.action import ActionServer, ActionClient, CancelResponse, GoalResponse
from rclpy.callback_groups import ReentrantCallbackGroup
from rclpy.executors import MultiThreadedExecutor

from baxter_arm_action.action import MoveArm
from moveit_msgs.action import MoveGroup
from moveit_msgs.msg import (
  MotionPlanRequest, WorkspaceParameters,
  Constraints, PositionConstraint, OrientationConstraint,
  BoundingVolume, MoveItErrorCodes
)
from shape_msgs.msg import SolidPrimitive
from geometry_msgs.msg import Vector3
from std_msgs.msg import Header

MOVE_GROUP_ACTION = '/move_action'

TIP_LINKS = {
  'right': 'right_hand',
  'left':  'left_hand',
}


class MoveArmServer(Node):
  def __init__(self):
    super().__init__( 'move_arm_server' )
    cb = ReentrantCallbackGroup()

    self._move_group_client = ActionClient(
      self, MoveGroup, MOVE_GROUP_ACTION, callback_group=cb)

    self._action_server = ActionServer(
      self, MoveArm, 'move_arm',
      execute_callback=self.execute_cb,
      goal_callback=self.goal_cb,
      cancel_callback=self.cancel_cb,
      callback_group=cb,
    )

    self._init_timer = self.create_timer(
      1.0, self._check_move_group, callback_group=cb)
    self.get_logger().info( 'Servidor MoveArm iniciando...' )
  # end def

  def _check_move_group(self):
      if self._move_group_client.server_is_ready():
        self._init_timer.cancel()
        self.get_logger().info( f'Servidor MoveArm listo :)  ({MOVE_GROUP_ACTION})' )
      else:
        self.get_logger().info( f'Esperando {MOVE_GROUP_ACTION}...' )
  # end def
  
  def goal_cb( self, goal_request ):
      if goal_request.arm not in ( 'right', 'left' ):
        self.get_logger().warn( f'Brazo inválido: {goal_request.arm}' )
        return GoalResponse.REJECT
      return GoalResponse.ACCEPT
  # end def
  
  def cancel_cb( self, _ ):
    return CancelResponse.ACCEPT
  # end def
  
  def execute_cb( self, goal_handle ):
    goal = goal_handle.request
    result = MoveArm.Result()
    fb = MoveArm.Feedback()

    group = f'{goal.arm}_arm'
    tip_link = TIP_LINKS[goal.arm]

    self.get_logger().info(
      f'MoveArm → {group} (tip: {tip_link}) | '
      f'pos: {goal.target_pose.pose.position}')

    fb.state = 'planning'; fb.progress = 0.1
    goal_handle.publish_feedback(fb)

    # MotionPlanRequest
    req = MotionPlanRequest()
    req.group_name = group
    req.num_planning_attempts = 5
    req.allowed_planning_time = 10.0
    req.max_velocity_scaling_factor = (
      float(goal.velocity_scaling) if goal.velocity_scaling > 0 else 0.1)
    req.max_acceleration_scaling_factor = 0.1

    req.workspace_parameters = WorkspaceParameters()
    req.workspace_parameters.header.frame_id = 'world'
    req.workspace_parameters.min_corner.x = -2.0
    req.workspace_parameters.min_corner.y = -2.0
    req.workspace_parameters.min_corner.z =  0.0
    req.workspace_parameters.max_corner.x =  2.0
    req.workspace_parameters.max_corner.y =  2.0
    req.workspace_parameters.max_corner.z =  2.5
    req.start_state.is_diff = True

    pose = goal.target_pose
    header = Header( frame_id='world' )

    # Position constraint box with +-2 cm tolerance
    pos_c = PositionConstraint()
    pos_c.header = header
    pos_c.link_name = tip_link
    pos_c.target_point_offset = Vector3( x=0.0, y=0.0, z=0.0 )

    box = SolidPrimitive()
    box.type = SolidPrimitive.BOX
    # 4 cm tolerance box
    box.dimensions = [0.04, 0.04, 0.04]

    bv = BoundingVolume()
    bv.primitives       = [box]
    bv.primitive_poses  = [pose.pose]
    pos_c.constraint_region = bv
    pos_c.weight = 1.0

    # Orientation constraint +-0.4 rad (23°) on every axis
    ori_c = OrientationConstraint()
    ori_c.header = header
    ori_c.link_name = tip_link
    ori_c.orientation = pose.pose.orientation
    ori_c.absolute_x_axis_tolerance = 0.4
    ori_c.absolute_y_axis_tolerance = 0.4
    ori_c.absolute_z_axis_tolerance = 0.4
    ori_c.weight = 1.0

    gc = Constraints()
    gc.position_constraints = [pos_c]
    gc.orientation_constraints = [ori_c]
    req.goal_constraints = [gc]

    mg_goal = MoveGroup.Goal()
    mg_goal.request = req
    mg_goal.planning_options.plan_only = False
    mg_goal.planning_options.replan = True
    mg_goal.planning_options.replan_attempts = 3

    # wait for server
    if not self._move_group_client.wait_for_server( timeout_sec=10.0):
      result.success = False
      result.message = f'Timeout esperando {MOVE_GROUP_ACTION}'
      goal_handle.abort()
      return result
    # end if
    
    t0 = self.get_clock().now()

    done_event       = threading.Event()
    result_container = {}

    def on_goal_response(future):
      gh = future.result()
      if not gh or not gh.accepted:
        result_container['error'] = f'{MOVE_GROUP_ACTION} rechazó el goal'
        done_event.set()
        return
      gh.get_result_async().add_done_callback(on_result)
    # end def
    
    def on_result(future):
      result_container['result'] = future.result().result
      done_event.set()
    # end def
    
    self._move_group_client.send_goal_async(mg_goal).add_done_callback(
      on_goal_response)

    if not done_event.wait( timeout=60.0 ):
      result.success = False
      result.message = 'Timeout esperando resultado de move_group'
      goal_handle.abort()
      return result
    # end if
    
    elapsed = ( self.get_clock().now() - t0 ).nanoseconds / 1e9

    if 'error' in result_container:
      result.success = False
      result.message = result_container['error']
      goal_handle.abort()
      return result
    # end if
    
    mg_result = result_container['result']
    if mg_result.error_code.val == MoveItErrorCodes.SUCCESS:
      fb.state = 'done'; fb.progress = 1.0
      goal_handle.publish_feedback(fb)
      result.success = True
      result.execution_time = elapsed
      result.message = f'{group} llegó al objetivo'
      self.get_logger().info( f'✓ {result.message} ({elapsed:.2f}s)' )
      goal_handle.succeed()
    else:
      result.success = False
      result.message = ( f'MoveIt error code: {mg_result.error_code.val}' )
      self.get_logger().error( result.message )
      goal_handle.abort()
    return result
  # end def
# end class

def main( args=None ):
  rclpy.init( args=args ) 
  executor = MultiThreadedExecutor( num_threads=8 )
  node = MoveArmServer()
  executor.add_node(node)
  executor.spin()
  rclpy.shutdown()
# end def

if __name__ == '__main__':
  main()