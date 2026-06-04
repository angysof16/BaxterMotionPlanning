#include <rclcpp/rclcpp.hpp>
#include <rclcpp_action/rclcpp_action.hpp>
#include <moveit/move_group_interface/move_group_interface.hpp>
#include "baxter_interfaces/action/move_arm.hpp"

using MoveArm = baxter_interfaces::action::MoveArm;
using GoalHandleMoveArm = rclcpp_action::ServerGoalHandle<MoveArm>;

class MoveArmServer : public rclcpp::Node
{
public:
  MoveArmServer() : Node("move_arm_server")
  {
    action_server_ = rclcpp_action::create_server<MoveArm>(
      this,
      "move_arm",
      std::bind(&MoveArmServer::handle_goal, this, std::placeholders::_1, std::placeholders::_2),
      std::bind(&MoveArmServer::handle_cancel, this, std::placeholders::_1),
      std::bind(&MoveArmServer::handle_accepted, this, std::placeholders::_1)
    );
    RCLCPP_INFO(get_logger(), "MoveArm action server ready");
  }

private:
  rclcpp_action::Server<MoveArm>::SharedPtr action_server_;

  rclcpp_action::GoalResponse handle_goal(
    const rclcpp_action::GoalUUID &,
    std::shared_ptr<const MoveArm::Goal> goal)
  {
    RCLCPP_INFO(get_logger(), "Received goal for arm: %s", goal->arm.c_str());
    if (goal->arm != "right" && goal->arm != "left")
      return rclcpp_action::GoalResponse::REJECT;
    return rclcpp_action::GoalResponse::ACCEPT_AND_EXECUTE;
  }

  rclcpp_action::CancelResponse handle_cancel(
    const std::shared_ptr<GoalHandleMoveArm>)
  {
    RCLCPP_INFO(get_logger(), "Goal cancelled");
    return rclcpp_action::CancelResponse::ACCEPT;
  }

  void handle_accepted(const std::shared_ptr<GoalHandleMoveArm> goal_handle)
  {
    std::thread{std::bind(&MoveArmServer::execute, this, std::placeholders::_1), goal_handle}.detach();
  }

  void execute(const std::shared_ptr<GoalHandleMoveArm> goal_handle)
  {
    const auto goal = goal_handle->get_goal();
    auto feedback = std::make_shared<MoveArm::Feedback>();
    auto result = std::make_shared<MoveArm::Result>();

    // Determinar planning group
    std::string group = goal->arm + "_arm";
    auto move_group = std::make_shared<moveit::planning_interface::MoveGroupInterface>(
      shared_from_this(), group);

    move_group->setPoseTarget(goal->target_pose);
    move_group->setGoalTolerance(goal->tolerance > 0 ? goal->tolerance : 0.01);

    // Feedback: planning
    feedback->phase = "planning";
    feedback->progress_percent = 0.0;
    goal_handle->publish_feedback(feedback);

    auto start_time = now();
    moveit::planning_interface::MoveGroupInterface::Plan plan;
    bool planned = (move_group->plan(plan) == moveit::core::MoveItErrorCode::SUCCESS);

    if (!planned) {
      result->success = false;
      result->message = "Planning failed";
      goal_handle->succeed(result);
      return;
    }

    // Feedback: executing
    feedback->phase = "executing";
    feedback->progress_percent = 50.0;
    goal_handle->publish_feedback(feedback);

    bool executed = (move_group->execute(plan) == moveit::core::MoveItErrorCode::SUCCESS);

    result->success = executed;
    result->message = executed ? "Goal reached" : "Execution failed";
    result->execution_time = (now() - start_time).seconds();

    feedback->phase = "done";
    feedback->progress_percent = 100.0;
    goal_handle->publish_feedback(feedback);

    goal_handle->succeed(result);
  }
};

int main(int argc, char ** argv)
{
  rclcpp::init(argc, argv);
  auto node = std::make_shared<MoveArmServer>();
  rclcpp::spin(node);
  rclcpp::shutdown();
  return 0;
}
