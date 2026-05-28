"""ALNS unified strategy with adaptive large neighborhood search.

Single depot assumption:
- All tasks originate from a single depot (depot_position)
- task.start_point is NOT used as a real pickup point in cost calculation

This strategy unifies direct delivery, relay-fixed delivery modes into a single
candidate space, using ALNS to search for the minimum cost solution.
"""

import math
import random
from typing import Any, Dict, List, Optional, Tuple

from .base import BaseStrategy
from .alns import (
    DeliveryMode, DeliveryOption, Solution,
    DestroyOperator, RepairOperator,
    CostScorer, ALNSOperators
)
from src.planning.relay_candidate_generator import RelayCandidateGenerator


class ALNSUnifiedStrategy(BaseStrategy):
    """ALNS unified strategy entry point."""

    def __init__(
        self,
        energy_model=None,
        path_planner=None,
        seed: int = 42,
        max_iterations: int = 30,
        initial_temperature: float = 100.0,
        cooling_rate: float = 0.95,
        destroy_count: int = 1,
        repair_count: int = 1,
        wait_timeout: int = 10,
        battery_low_threshold: float = 20.0,
    ):
        super().__init__("alns_unified")
        self.energy_model = energy_model
        self.path_planner = path_planner
        self.seed = seed
        self.max_iterations = max_iterations
        self.initial_temperature = initial_temperature
        self.cooling_rate = cooling_rate
        self.destroy_count = destroy_count
        self.repair_count = repair_count
        self.wait_timeout = wait_timeout
        self.battery_low_threshold = battery_low_threshold

        self.fallback_count = 0
        self.replan_count = 0
        self.relay_count = 0
        self.direct_count = 0
        self.infeasible_count = 0

        self._rng = random.Random(seed)
        self._scorer = CostScorer(energy_model)
        self._operators = ALNSOperators(energy_model, seed)

    def assign_tasks(self, environment) -> Dict[str, Any]:
        """Main task assignment method."""
        self._reset_counters()
        depot_pos = self._get_depot_position(environment)

        events = []
        actions = []

        waiting_tasks = [t for t in environment.tasks if t.status == "waiting_for_agv"]
        for task in waiting_tasks:
            fallback_result = self._check_and_apply_fallback(task, environment, depot_pos)
            if fallback_result["action"] != "none":
                events.append({
                    "type": fallback_result["event_type"],
                    "task_id": task.id,
                    "details": fallback_result.get("reason", "")
                })
                if fallback_result.get("action") == "relay_reselected":
                    self.replan_count += 1
                    actions.append({
                        "action": "move_agv_to_relay",
                        "agv_id": fallback_result.get("agv_id"),
                        "relay_point": fallback_result.get("relay_point"),
                        "task_id": task.id
                    })
                elif fallback_result.get("action") == "relay_to_direct":
                    self.fallback_count += 1

        idle_uavs = self.get_idle_uavs(environment)
        pending_tasks = self.get_pending_tasks(environment)

        if not idle_uavs or not pending_tasks:
            return {
                "strategy": self.name,
                "assignments": [],
                "actions": actions,
                "events": events,
                "assigned_count": 0,
            }

        initial_solution = self._generate_greedy_initial_solution(
            idle_uavs, pending_tasks, environment, depot_pos
        )

        best_solution = self._alns_search(
            initial_solution, idle_uavs, pending_tasks, environment, depot_pos
        )

        assignments = []

        for option in best_solution.assignments:
            uav = self._get_uav_by_id(option.uav_id, environment)
            task = self._get_task_by_id(option.task_id, environment)
            if not uav or not task:
                continue

            uav.assign_task(task)
            task.assigned_uav = uav

            if option.mode == DeliveryMode.DIRECT:
                task.status = "in_progress"
                self.direct_count += 1
            elif option.mode == DeliveryMode.RELAY_FIXED:
                agv = self._get_agv_by_id(option.agv_id, environment)
                relay_point = option.relay_point
                task.relay_point = relay_point
                task.assigned_agv = agv
                task.status = "waiting_for_agv"
                self.relay_count += 1
                if agv:
                    actions.append({
                        "action": "move_agv_to_relay",
                        "agv_id": agv.id,
                        "relay_point": relay_point,
                        "task_id": task.id,
                    })
                    events.append({
                        "type": "RELAY_REQUEST",
                        "task_id": task.id,
                        "agv_id": agv.id,
                        "details": f"Relay via AGV {agv.id}"
                    })

            assignments.append({
                "uav_id": uav.id,
                "task_id": task.id,
                "mode": option.mode.value,
                "relay_point": option.relay_point,
                "agv_id": option.agv_id,
                "cost": option.cost,
            })

        return {
            "strategy": self.name,
            "assignments": assignments,
            "actions": actions,
            "events": events,
            "assigned_count": len(assignments),
            "solution_cost": best_solution.total_cost,
        }

    def select_charging_station(self, uav, environment):
        """Select charging station for UAV."""
        available_agvs = self.get_available_agvs(environment)
        if not available_agvs:
            return None
        return min(
            available_agvs,
            key=lambda agv: self._distance(agv.position, uav.position)
        )

    def _reset_counters(self):
        """Reset statistics counters."""
        self.fallback_count = 0
        self.replan_count = 0
        self.relay_count = 0
        self.direct_count = 0
        self.infeasible_count = 0

    def _get_depot_position(self, environment) -> Tuple[float, float]:
        """Get depot position with fallback logic."""
        if hasattr(environment, 'uavs') and environment.uavs and hasattr(environment, 'agvs') and environment.agvs:
            positions = [uav.position for uav in environment.uavs] + [agv.position for agv in environment.agvs]
            if positions:
                first_pos = positions[0]
                all_same = True
                for p in positions[1:]:
                    if abs(p[0] - first_pos[0]) > 1e-6 or abs(p[1] - first_pos[1]) > 1e-6:
                        all_same = False
                        break
                if all_same:
                    return first_pos

        if hasattr(environment, 'uavs') and environment.uavs:
            return environment.uavs[0].position

        if hasattr(environment, 'tasks') and environment.tasks:
            return environment.tasks[0].start_point

        return (0.0, 0.0)

    def _get_uav_by_id(self, uav_id: int, environment):
        """Get UAV by ID."""
        for uav in environment.uavs:
            if uav.id == uav_id:
                return uav
        return None

    def _get_agv_by_id(self, agv_id: int, environment):
        """Get AGV by ID."""
        if agv_id is None:
            return None
        for agv in environment.agvs:
            if agv.id == agv_id:
                return agv
        return None

    def _get_task_by_id(self, task_id: int, environment):
        """Get task by ID."""
        for task in environment.tasks:
            if task.id == task_id:
                return task
        return None

    def _distance(self, p1: Tuple[float, float], p2: Tuple[float, float]) -> float:
        """Calculate Euclidean distance."""
        return math.sqrt((p1[0] - p2[0])**2 + (p1[1] - p2[1])**2)

    def _check_and_apply_fallback(
        self,
        task,
        environment,
        depot_pos: Tuple[float, float]
    ) -> Dict[str, Any]:
        """Check and apply fallback for waiting tasks."""
        uav = getattr(task, 'assigned_uav', None)
        if not uav:
            return {"action": "none", "event_type": "NONE"}

        should_fallback = False
        reason = ""

        if uav.battery < self.battery_low_threshold:
            should_fallback = True
            reason = "low_battery"

        wait_time = getattr(task, 'wait_time_at_relay', 0)
        if wait_time > self.wait_timeout:
            should_fallback = True
            reason = "wait_timeout"

        relay_point = getattr(task, 'relay_point', None)
        if relay_point and not environment.is_valid_position(relay_point):
            should_fallback = True
            reason = "invalid_relay_point"

        deadline = self._get_task_deadline(task)
        if deadline is not None:
            remaining_time = deadline - getattr(environment, 'current_time', 0)
            if remaining_time < 10:
                should_fallback = True
                reason = "time_window_urgent"

        if not should_fallback:
            return {"action": "none", "event_type": "NONE"}

        available_agvs = [agv for agv in environment.agvs if getattr(agv, 'status', 'idle') == 'idle']
        if available_agvs:
            best_agv = min(available_agvs, key=lambda agv: self._distance(agv.position, task.end_point))
            best_relay = RelayCandidateGenerator.generate_for_agv(uav, task, best_agv, environment, depot_pos)
            if best_relay:
                task.relay_point = best_relay
                task.assigned_agv = best_agv
                if hasattr(task, 'wait_time_at_relay'):
                    task.wait_time_at_relay = 0
                return {
                    "action": "relay_reselected",
                    "event_type": "RELAY_RESELECTED",
                    "relay_point": best_relay,
                    "agv_id": best_agv.id,
                    "reason": f"Reselected relay: {reason}"
                }

        if self._can_uav_complete_direct(uav, task, depot_pos):
            task.status = "in_progress"
            if hasattr(task, 'relay_point'):
                delattr(task, 'relay_point')
            if hasattr(task, 'assigned_agv'):
                task.assigned_agv = None
            return {
                "action": "relay_to_direct",
                "event_type": "RELAY_TO_DIRECT_FALLBACK",
                "reason": f"Fallback to direct: {reason}"
            }

        task.status = "pending"
        if hasattr(task, 'assigned_uav'):
            task.assigned_uav = None
        if hasattr(task, 'relay_point'):
            delattr(task, 'relay_point')
        if hasattr(task, 'assigned_agv'):
            task.assigned_agv = None
        if hasattr(task, 'uav'):
            task.uav = None
        self.infeasible_count += 1
        return {
            "action": "keep_pending",
            "event_type": "INFEASIBLE_TASK",
            "reason": f"Infeasible: {reason}"
        }

    def _get_task_deadline(self, task) -> Optional[float]:
        """Get task deadline."""
        deadline = getattr(task, 'deadline', None)
        if deadline is not None:
            return deadline
        time_window = getattr(task, 'time_window', None)
        if isinstance(time_window, (tuple, list)) and len(time_window) >= 2:
            return time_window[1]
        return None

    def _generate_greedy_initial_solution(
        self,
        idle_uavs: List,
        pending_tasks: List,
        environment,
        depot_pos: Tuple[float, float]
    ) -> Solution:
        """Generate greedy initial solution."""
        assignments = []
        mode_counts = {"direct": 0, "relay_fixed": 0}

        for task in pending_tasks:
            if not idle_uavs:
                break

            best_option = None
            best_cost = float('inf')

            for uav in idle_uavs:
                direct_option = self._scorer.evaluate(
                    uav, task, DeliveryMode.DIRECT, depot_pos=depot_pos
                )
                if direct_option.cost < best_cost:
                    best_cost = direct_option.cost
                    best_option = direct_option

                relay_candidates = RelayCandidateGenerator.generate_bound_candidates(uav, task, environment, depot_pos)
                for relay_point, agv in relay_candidates:
                    relay_option = self._scorer.evaluate(
                        uav, task, DeliveryMode.RELAY_FIXED,
                        relay_point=relay_point, agv=agv, depot_pos=depot_pos
                    )
                    if relay_option.cost < best_cost:
                        best_cost = relay_option.cost
                        best_option = relay_option

            if best_option:
                assignments.append(best_option)
                mode_counts[best_option.mode.value] += 1
                idle_uavs = [u for u in idle_uavs if u.id != best_option.uav_id]

        total_cost = sum(a.cost for a in assignments)
        return Solution(assignments=assignments, total_cost=total_cost, mode_counts=mode_counts)

    def _alns_search(
        self,
        initial_solution: Solution,
        idle_uavs: List,
        pending_tasks: List,
        environment,
        depot_pos: Tuple[float, float]
    ) -> Solution:
        """Perform ALNS search."""
        rng = self._rng
        current = initial_solution.copy()
        best = current.copy()
        temperature = self.initial_temperature

        destroy_ops = [DestroyOperator.RANDOM_REMOVE, DestroyOperator.WORST_REMOVE]
        repair_ops = [RepairOperator.GREEDY_INSERT, RepairOperator.REGRET_INSERT]

        for iteration in range(self.max_iterations):
            prev_cost = current.total_cost

            selected_destroy = self._operators.select_operator(destroy_ops)
            destroyed = self._operators.destroy(current, selected_destroy, self.destroy_count)

            selected_repair = self._operators.select_operator(repair_ops)
            repaired = self._operators.repair(
                destroyed, pending_tasks, idle_uavs, environment, depot_pos,
                selected_repair, self.repair_count
            )

            delta = repaired.total_cost - current.total_cost

            accepted = delta < 0 or rng.random() < math.exp(-delta / temperature)

            if accepted:
                improved = delta < 0
                self._operators.update_operator_weights(
                    selected_destroy, selected_repair, improved,
                    repaired.total_cost < best.total_cost
                )
                current = repaired
                if current.total_cost < best.total_cost:
                    best = current.copy()

            temperature *= self.cooling_rate

        return best

    def _can_uav_complete_direct(self, uav, task, depot_pos):
        """Check if UAV can complete direct delivery."""
        end_point = task.end_point
        required_range = (
            self._distance(depot_pos, end_point) +
            self._distance(end_point, depot_pos)
        )
        max_range = getattr(uav, 'max_range', 500)
        remaining_range = uav.battery * max_range / 100.0
        return required_range <= remaining_range

    def get_operator_weights(self) -> Dict[str, float]:
        """Get current operator weights."""
        return self._operators.get_operator_weights()
