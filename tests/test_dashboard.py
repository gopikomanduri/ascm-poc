import time
import unittest
from orchestrator.dashboard import (
    DashboardState,
    GLOBAL_DASHBOARD_STATE,
    check_and_update_staleness,
    get_latest_live_run,
    list_historical_runs,
    load_historical_run,
)


class DashboardTelemetryTests(unittest.TestCase):
    def test_dashboard_state_initialization_and_counts(self):
        state = DashboardState(user_goal="Test Goal")
        snapshot = state.get_snapshot()
        self.assertEqual(snapshot["counts"]["running"], 0)
        self.assertEqual(snapshot["counts"]["completed"], 0)
        self.assertEqual(snapshot["counts"]["waiting"], len(state.known_agents))
        self.assertEqual(snapshot["active_agent"], "None")
        self.assertEqual(snapshot["user_goal"], "Test Goal")

    def test_agent_status_updates_and_timeline(self):
        state = DashboardState(user_goal="Build Feature")
        state.set_phase("Phase 2: Discovery")
        state.update_agent("DiscoveryAgent", "running", "Analyzing repos")
        
        snap1 = state.get_snapshot()
        self.assertEqual(snap1["active_agent"], "DiscoveryAgent")
        self.assertEqual(snap1["counts"]["running"], 1)

        state.update_agent("DiscoveryAgent", "completed", "Done")
        snap2 = state.get_snapshot()
        self.assertEqual(snap2["active_agent"], "None")
        self.assertEqual(snap2["counts"]["completed"], 1)
        self.assertTrue(len(snap2["timeline_events"]) >= 3)

    def test_task_status_updates(self):
        state = DashboardState(user_goal="Task Test")
        tasks = [
            {"id": "TASK-1", "title": "Create DB table", "assigned_agent": "database", "status": "pending"},
            {"id": "TASK-2", "title": "Implement Go handler", "assigned_agent": "coder", "status": "pending"},
        ]
        state.set_tasks(tasks)
        self.assertEqual(state.get_snapshot()["counts"]["total_tasks"], 2)

        state.update_task_status("TASK-1", "completed")
        snap = state.get_snapshot()
        self.assertEqual(snap["tasks"][0]["status"], "completed")
        self.assertEqual(snap["tasks"][1]["status"], "pending")

    def test_disk_persistence_and_historical_loading(self):
        state = DashboardState(user_goal="Persistence Test Goal")
        state.set_phase("Phase 3: Product Clarification")
        state.update_agent("ProductAgent", "running", "Evaluating PRD")
        run_id = state.run_id

        runs_list = list_historical_runs()
        self.assertTrue(any(r["run_id"] == run_id for r in runs_list))

        historical_snapshot = load_historical_run(run_id)
        self.assertIsNotNone(historical_snapshot)
        self.assertEqual(historical_snapshot["user_goal"], "Persistence Test Goal")
        self.assertEqual(historical_snapshot["phase"], "Phase 3: Product Clarification")

    def test_record_crash_telemetry(self):
        state = DashboardState(user_goal="Crash Test Goal")
        state.update_agent("DiscoveryAgent", "running", "Analyzing topology")
        
        try:
            raise ValueError("Simulated network crash")
        except ValueError as err:
            state.record_crash(err)

        snap = state.get_snapshot()
        self.assertTrue("FAILED / CRASHED" in snap["phase"])
        self.assertEqual(snap["agents"]["DiscoveryAgent"]["status"], "failed")
        self.assertTrue(any("Simulated network crash" in line for line in snap["logs"]))

    def test_staleness_detection_on_heartbeat_timeout(self):
        state = DashboardState(user_goal="Stale Session Goal")
        snap = state.get_snapshot()
        snap["last_heartbeat"] = time.time() - 15.0  # 15s ago (> 10s limit)

        updated_snap = check_and_update_staleness(snap, state.file_path)
        self.assertTrue("FAILED / CRASHED" in updated_snap["phase"])
        self.assertTrue("Heartbeat" in updated_snap["phase"] or "Disconnected" in updated_snap["phase"])

    def test_get_latest_live_run(self):
        GLOBAL_DASHBOARD_STATE.new_session("Live Run Resolution Test")
        latest = get_latest_live_run()
        self.assertEqual(latest["run_id"], GLOBAL_DASHBOARD_STATE.run_id)
        self.assertEqual(latest["user_goal"], "Live Run Resolution Test")


if __name__ == "__main__":
    unittest.main()
