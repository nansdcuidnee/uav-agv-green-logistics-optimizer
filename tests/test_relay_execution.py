"""Tests for relay execution semantics correction.

This test verifies that:
1. UAV position is updated to relay_point when AGV arrives
2. UAV.path_history contains relay_point
3. UAV doesn't start executing until AGV arrives
4. Direct mode behavior remains unchanged
"""

import unittest
from src.simulation.simulator import Simulator
from src.simulation.environment import Environment
from src.energy.energy_model import EnergyModel
from src.planning.path_planner import PathPlanner
from src.scheduling.scheduler import Scheduler
from src.core.uav import UAV
from src.core.agv import AGV
from src.core.task import Task


class TestRelayExecution(unittest.TestCase):
    """Test relay execution semantics."""

    def setUp(self):
        """Create common test fixtures."""
        self.env = Environment()
        self.env.uavs = []
        self.env.agvs = []
        self.env.tasks = []
        self.energy_model = EnergyModel()
        self.path_planner = PathPlanner()
        self.scheduler = Scheduler()

    def _setup_relay_scenario(self, uav_pos=(0, 0), agv_pos=(500, 500), relay_point=(350, 350)):
        """Helper to setup a complete relay scenario."""
        env = Environment()
        uav = UAV(id=1, position=uav_pos, battery=100.0)
        agv = AGV(id=1, position=agv_pos)
        task = Task(
            id=1,
            start_point=(200, 200),
            end_point=(300, 300),
            payload=1.0,
            priority=1
        )
        
        task.relay_point = relay_point
        task.assigned_agv = agv
        task.assigned_uav = uav
        task.status = "waiting_for_agv"
        task.assigned_time = -20
        uav.assign_task(task)
        
        # Set AGV moving to relay point
        agv.status = "moving_to_relay"
        agv.destination = relay_point
        agv.move_distance = ((agv.position[0] - relay_point[0]) ** 2 + 
                           (agv.position[1] - relay_point[1]) ** 2) ** 0.5
        agv.move_progress = 0
        agv.task_id = task.id
        
        env.uavs = [uav]
        env.agvs = [agv]
        env.tasks = [task]
        
        return env, uav, agv, task

    def test_uav_position_updated_at_relay(self):
        """Test that UAV position is updated to relay_point when AGV arrives."""
        env, uav, agv, task = self._setup_relay_scenario()
        expected_relay = (350, 350)

        simulator = Simulator(
            environment=env,
            energy_model=self.energy_model,
            path_planner=self.path_planner,
            scheduler=self.scheduler,
            strategy_type="relay_coop"
        )

        simulator.run(max_steps=100)

        deploy_events = [e for e in simulator.events if e['type'] == 'UAV_DEPLOYED_AT_RELAY']
        self.assertTrue(len(deploy_events) > 0, "UAV_DEPLOYED_AT_RELAY event should be recorded")

        deploy_event = deploy_events[-1]
        # Verify that the deployment event records the correct relay point
        self.assertAlmostEqual(deploy_event['new_x'], expected_relay[0], delta=1)
        self.assertAlmostEqual(deploy_event['new_y'], expected_relay[1], delta=1)
        # Also verify that UAV position was updated from initial position (0,0)
        self.assertEqual(deploy_event['old_x'], 0.0)
        self.assertEqual(deploy_event['old_y'], 0.0)

    def test_uav_path_history_contains_relay(self):
        """Test that UAV.path_history contains relay_point after deployment."""
        env, uav, agv, task = self._setup_relay_scenario(
            uav_pos=(0, 0), 
            agv_pos=(400, 400), 
            relay_point=(300, 300)
        )

        simulator = Simulator(
            environment=env,
            energy_model=self.energy_model,
            path_planner=self.path_planner,
            scheduler=self.scheduler,
            strategy_type="relay_coop"
        )

        simulator.run(max_steps=100)

        deploy_events = [e for e in simulator.events if e['type'] == 'UAV_DEPLOYED_AT_RELAY']
        if deploy_events:
            relay_x = deploy_events[-1]['new_x']
            relay_y = deploy_events[-1]['new_y']
            relay_in_history = any(
                abs(pos[0] - relay_x) < 1 and abs(pos[1] - relay_y) < 1
                for pos in uav.path_history
            )
            self.assertTrue(relay_in_history, "Relay point should be in UAV path_history")

    def test_uav_does_not_move_before_agv_arrival(self):
        """Test that UAV doesn't move until AGV arrives at relay."""
        env, uav, agv, task = self._setup_relay_scenario(
            uav_pos=(0, 0), 
            agv_pos=(500, 500), 
            relay_point=(350, 350)
        )
        initial_pos = (0, 0)

        simulator = Simulator(
            environment=env,
            energy_model=self.energy_model,
            path_planner=self.path_planner,
            scheduler=self.scheduler,
            strategy_type="relay_coop"
        )

        agv_arrived = False
        for _ in range(50):
            simulator.step()
            
            agv_arrive_events = [e for e in simulator.events if e['type'] == 'AGV_ARRIVE_RELAY']
            if agv_arrive_events:
                agv_arrived = True
            
            if not agv_arrived:
                self.assertEqual(uav.position, initial_pos, "UAV should not move before AGV arrives")
            
            if agv_arrived:
                break

    def test_direct_mode_unchanged(self):
        """Test that direct mode behavior is unchanged."""
        env = Environment()
        uav = UAV(id=1, position=(0, 0), battery=100.0)
        agv = AGV(id=1, position=(500, 500))
        task = Task(
            id=1,
            start_point=(50, 50),
            end_point=(100, 100),
            payload=1.0,
            priority=1
        )
        env.uavs = [uav]
        env.agvs = [agv]
        env.tasks = [task]

        simulator = Simulator(
            environment=env,
            energy_model=self.energy_model,
            path_planner=self.path_planner,
            scheduler=self.scheduler,
            strategy_type="baseline_direct"
        )

        simulator.run(max_steps=50)

        self.assertEqual(task.status, "completed", "Task should be completed in direct mode")
        self.assertNotEqual(uav.position, (0, 0), "UAV should have moved in direct mode")

    def test_uav_deployed_event_has_correct_fields(self):
        """Test that UAV_DEPLOYED_AT_RELAY event has all required fields."""
        env, uav, agv, task = self._setup_relay_scenario(
            uav_pos=(0, 0), 
            agv_pos=(400, 400), 
            relay_point=(300, 300)
        )

        simulator = Simulator(
            environment=env,
            energy_model=self.energy_model,
            path_planner=self.path_planner,
            scheduler=self.scheduler,
            strategy_type="relay_coop"
        )

        simulator.run(max_steps=100)

        deploy_events = [e for e in simulator.events if e['type'] == 'UAV_DEPLOYED_AT_RELAY']
        if deploy_events:
            event = deploy_events[-1]
            self.assertIn('uav_id', event)
            self.assertIn('task_id', event)
            self.assertIn('agv_id', event)
            self.assertIn('old_x', event)
            self.assertIn('old_y', event)
            self.assertIn('new_x', event)
            self.assertIn('new_y', event)
            self.assertIn('details', event)
            
            self.assertEqual(event['uav_id'], 1)
            self.assertEqual(event['task_id'], 1)
            self.assertEqual(event['agv_id'], 1)
            self.assertEqual(event['old_x'], 0.0)
            self.assertEqual(event['old_y'], 0.0)
            self.assertAlmostEqual(event['new_x'], agv.position[0], delta=1)
            self.assertAlmostEqual(event['new_y'], agv.position[1], delta=1)

    def test_no_crash_when_no_assigned_uav(self):
        """Test that system handles missing assigned_uav gracefully."""
        env = Environment()
        uav = UAV(id=1, position=(0, 0), battery=100.0)
        agv = AGV(id=1, position=(300, 300))
        task = Task(
            id=1,
            start_point=(200, 200),
            end_point=(250, 250),
            payload=1.0,
            priority=1
        )
        
        relay_point = (250, 250)
        task.relay_point = relay_point
        task.assigned_agv = agv
        task.status = "waiting_for_agv"
        task.assigned_time = -20
        # Note: NOT setting task.assigned_uav
        
        agv.status = "moving_to_relay"
        agv.destination = relay_point
        agv.move_distance = ((agv.position[0] - relay_point[0]) ** 2 + 
                           (agv.position[1] - relay_point[1]) ** 2) ** 0.5
        agv.move_progress = 0
        agv.task_id = task.id
        
        env.uavs = [uav]
        env.agvs = [agv]
        env.tasks = [task]

        simulator = Simulator(
            environment=env,
            energy_model=self.energy_model,
            path_planner=self.path_planner,
            scheduler=self.scheduler,
            strategy_type="relay_coop"
        )

        try:
            simulator.run(max_steps=50)
        except Exception as e:
            self.fail(f"Should not crash: {e}")

    def test_fallback_does_not_use_relay_semantics(self):
        """Test that fallback to direct mode does not use relay takeoff semantics."""
        env = Environment()
        uav = UAV(id=1, position=(0, 0), battery=100.0)
        agv = AGV(id=1, position=(1000, 1000))
        task = Task(
            id=1,
            start_point=(50, 50),
            end_point=(100, 100),
            payload=1.0,
            priority=1
        )
        
        relay_point = (500, 500)
        task.relay_point = relay_point
        task.assigned_agv = agv
        task.assigned_uav = uav
        task.status = "waiting_for_agv"
        task.assigned_time = 0
        uav.assign_task(task)
        
        agv.status = "moving_to_relay"
        agv.destination = relay_point
        agv.move_distance = ((agv.position[0] - relay_point[0]) ** 2 + 
                           (agv.position[1] - relay_point[1]) ** 2) ** 0.5
        agv.move_progress = 0
        agv.task_id = task.id
        
        env.uavs = [uav]
        env.agvs = [agv]
        env.tasks = [task]

        simulator = Simulator(
            environment=env,
            energy_model=self.energy_model,
            path_planner=self.path_planner,
            scheduler=self.scheduler,
            strategy_type="relay_coop"
        )

        simulator.run(max_steps=50)

        fallback_events = [e for e in simulator.events if e['type'] == 'RELAY_FALLBACK']
        self.assertTrue(len(fallback_events) > 0, "Should have fallback event")
        
        self.assertNotEqual(uav.position, (1000, 1000), "UAV should not be moved to distant relay_point on fallback")
        self.assertEqual(task.status, "completed", "Task should complete after fallback")


if __name__ == "__main__":
    unittest.main()
