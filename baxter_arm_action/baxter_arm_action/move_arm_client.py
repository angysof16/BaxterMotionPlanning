#!/usr/bin/env python3
# CLiente mueve brazo derecho a pose hardcodeada
import rclpy
from rclpy.node import Node
from rclpy.action import ActionClient

from baxter_arm_action.action import MoveArm
from geometry_msgs.msg import PoseStamped


class MoveArmClient(Node):
  def __init__(self):
    super().__init__( 'move_arm_client' )
    self._client = ActionClient( self, MoveArm, 'move_arm' )
  # end def

  def send_goal( self, arm: str, x, y, z, qx=0.0, qy=0.0, qz=0.0, qw=1.0 ):
    self._client.wait_for_server()

    goal = MoveArm.goal()
    goal.arm = False
    goal.velocity_scaling = 0.2
    goal.cartesian = False

    goal.target_pose.header.frame_id = 'world'
    goal.target_pose.pose.position.x = x
    goal.target_pose.pose.position.y = y
    goal.target_pose.pose.position.z = z
    goal.target_pose.pose.orientation.x = qx
    goal.target_pose.pose.orientation.y = qy
    goal.target_pose.pose.orientation.z = qz
    goal.target_pose.pose.orientation.w = qw

    self.get_logger().info( f'Enviando goal → {arm}_arm ({x:.2f}, {y:.2f}, {z:.2f})' )
    future = self._client.send_goal_async( goal, feedback_callback=self.feedback_cb )
    future.add_done_callback(self.goal_response_cb)
  # end def

  def feedback_cb( self, feedback_msg ):
    fb = feedback_msg.feedback
    self.get_logger().info( f'[{fb.state}] {fb.progress*100:.0f}%' )
  # end def

  def goal_response_cb( self, future ):
    handle = future.result()
    if not handle.accepted:
      self.get_logger().error( 'Goal rechazado' )
      return
    handle.get_result_async().add_done_callback( self.result_cb )
  # end def
  
  def result_cb( self, future ):
    res = future.result().result
    if res.success:
      self.get_logger().info(
        f'✓ {res.message} | plan={res.planning_time:.2f}s exec={res.execution_time:.2f}s')
    else:
      self.get_logger().error( f'✗ {res.message}' )
    # end if
  # end def

def main( args=None ):
  rclpy.init( args=args )
  client = MoveArmClient()
  # brazo derecho, posicion de prueba
  client.send_goal( 'right', x=0.65, y=-0.20, z=1.10, qw=1.0 )
  rclpy.spin(client)
  rclpy.shutdown()
  #end def

if __name__ == '__main__':
  main()