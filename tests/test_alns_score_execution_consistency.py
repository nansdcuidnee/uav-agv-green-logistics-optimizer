"""Consistency tests between ALNS scoring and actual execution.

This verifies that scoring predictions are directionally consistent with
actual simulation outcomes, ensuring the ALNS search optimizes for real
execution costs rather than abstract metrics.
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
from src.strategies.alns.scoring import CostScorer


class TestALNSScoreExecutionConsistency(unittest.TestCase):
    """Test consistency between ALNS scoring and actual execution."""

    def setUp(self):
        """Create common test fixtures."""
        self.energy_model = EnergyModel()
        self.path_planner = PathPlanner()
        self.scheduler = Scheduler()
        self.scorer = CostScorer(self.energy_model)

    def _setup_relay_scenario(self, uav_pos, agv_pos, relay_point, task_start, task_end):
        """Helper to setup relay scenario."""
        env = Environment()
        uav = UAV(id=1, position=uav_pos, battery=100.0)
        agv = AGV(id=1, position=agv_pos)
        task = Task(
            id=1,
            start_point=task_start,
            end_point=task_end,
            payload=1.0,
            priority=1
        )
        
        task.relay_point = relay_point
        task.assigned_agv = agv
        task.assigned_uav = uav
        task.status = "waiting_for_agv"
        task.assigned_time = -20
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
        
        return env, uav, agv, task

    def test_predicted_wait_direction_consistency(self):
        """Test that predicted_wait correctly reflects arrival time differences.
        
        When UAV is farther from relay than AGV, predicted_wait should reflect
        that UAV will arrive later. When AGV is farther, predicted_wait should
        reflect AGV arrival delay.
        """
        uav_close = UAV(id=1, position=(0, 0), battery=100.0)
        uav_far = UAV(id=2, position=(800, 800), battery=100.0)
        agv = AGV(id=1, position=(200, 200))
        task = Task(
            id=1,
            start_point=(150, 150),
            end_point=(250, 250),
            payload=1.0,
            priority=1
        )
        relay_point = (300, 300)

        result_close = self.scorer.evaluate_relay_insertion_unified(
            uav_close, task, agv, relay_point, [], [], 0, 0, (0, 0)
        )
        result_far = self.scorer.evaluate_relay_insertion_unified(
            uav_far, task, agv, relay_point, [], [], 0, 0, (0, 0)
        )

        self.assertGreater(
            result_far.predicted_wait, result_close.predicted_wait,
            "UAV far from relay should have higher predicted_wait"
        )

    def test_deployment_cost_increases_with_distance(self):
        """Test that deployment cost increases when UAV is farther from relay.
        
        Both scoring predictions and actual execution should show higher energy
        consumption when UAV starts farther from the relay point.
        """
        scenarios = [
            {
                "uav_pos": (180, 180),
                "description": "UAV close to relay"
            },
            {
                "uav_pos": (0, 0),
                "description": "UAV far from relay"
            }
        ]

        relay_point = (200, 200)
        task_start = (150, 150)
        task_end = (250, 250)

        predicted_energies = []
        actual_energies = []

        for scenario in scenarios:
            env, uav, agv, task = self._setup_relay_scenario(
                uav_pos=scenario["uav_pos"],
                agv_pos=(300, 300),
                relay_point=relay_point,
                task_start=task_start,
                task_end=task_end
            )

            result = self.scorer.evaluate_relay_insertion_unified(
                uav, task, agv, relay_point, [], [], 0, 0, (0, 0)
            )
            predicted_energies.append(result.cost_breakdown.get("uav_energy", 0))

            simulator = Simulator(
                environment=env,
                energy_model=self.energy_model,
                path_planner=self.path_planner,
                scheduler=self.scheduler,
                strategy_type="relay_coop"
            )
            simulator.run(max_steps=200)
            actual_energies.append(task.uav_energy)

        self.assertGreater(
            predicted_energies[1], predicted_energies[0],
            "UAV far scenario should have higher predicted energy"
        )
        self.assertGreater(
            actual_energies[1], actual_energies[0],
            "UAV far scenario should have higher actual energy"
        )

    def test_deployment_cost_changes_relay_direct_preference(self):
        """Test that deployment cost affects relay/direct preference correctly.
        
        When UAV is far from relay but close to task start, adding deployment
        cost should make direct mode more preferred, which matches real execution.
        """
        uav = UAV(id=1, position=(0, 0), battery=100.0)
        agv = AGV(id=1, position=(500, 500))
        task = Task(
            id=1,
            start_point=(50, 50),
            end_point=(100, 100),
            payload=1.0,
            priority=1
        )

        relay_point = (400, 400)
        
        relay_result = self.scorer.evaluate_relay_insertion_unified(
            uav, task, agv, relay_point, [], [], 0, 0, (0, 0)
        )
        direct_result = self.scorer.evaluate_direct_insertion_unified(
            uav, task, [], 0, (0, 0)
        )

        relay_cost = relay_result.cost_delta
        direct_cost = direct_result.cost_delta

        self.assertGreater(
            relay_cost, direct_cost,
            "Direct mode should be preferred when UAV is close to task but far from relay"
        )

        env_relay, uav_relay, agv_relay, task_relay = self._setup_relay_scenario(
            uav_pos=(0, 0),
            agv_pos=(500, 500),
            relay_point=(400, 400),
            task_start=(50, 50),
            task_end=(100, 100)
        )
        simulator_relay = Simulator(
            environment=env_relay,
            energy_model=self.energy_model,
            path_planner=self.path_planner,
            scheduler=self.scheduler,
            strategy_type="relay_coop"
        )
        simulator_relay.run(max_steps=200)
        relay_actual_energy = simulator_relay.total_uav_energy

        env_direct = Environment()
        uav_direct = UAV(id=1, position=(0, 0), battery=100.0)
        agv_direct = AGV(id=1, position=(500, 500))
        task_direct = Task(
            id=1,
            start_point=(50, 50),
            end_point=(100, 100),
            payload=1.0,
            priority=1
        )
        env_direct.uavs = [uav_direct]
        env_direct.agvs = [agv_direct]
        env_direct.tasks = [task_direct]

        simulator_direct = Simulator(
            environment=env_direct,
            energy_model=self.energy_model,
            path_planner=self.path_planner,
            scheduler=self.scheduler,
            strategy_type="baseline_direct"
        )
        simulator_direct.run(max_steps=50)
        direct_actual_energy = simulator_direct.total_uav_energy

        self.assertGreater(
            relay_actual_energy, direct_actual_energy,
            "Actual execution should match scoring preference: direct is cheaper"
        )


if __name__ == "__main__":
    unittest.main()