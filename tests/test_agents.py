import unittest
from orchestrator.state import SharedBlackboard, TaskItem, RepoContract


class MultiAgentArchitectureTests(unittest.TestCase):
    def test_shared_blackboard_initialization(self):
        state = SharedBlackboard(
            user_goal="Build payment API",
            target_repos=["/tmp/repo1"]
        )
        self.assertEqual(state.user_goal, "Build payment API")
        self.assertEqual(state.clarified_prd, "")
        self.assertEqual(state.task_breakdown, [])

    def test_task_item_model(self):
        task = TaskItem(
            id="TASK-1",
            title="Create database schema",
            description="Add user_accounts table",
            assigned_agent="database",
            target_file="internal/db/schema.go"
        )
        self.assertEqual(task.id, "TASK-1")
        self.assertEqual(task.assigned_agent, "database")
        self.assertEqual(task.status, "pending")


if __name__ == "__main__":
    unittest.main()
