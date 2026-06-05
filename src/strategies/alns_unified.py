"""ALNS unified strategy with adaptive large neighborhood search.

Pickup-delivery model:
- Direct: UAV depot -> start -> end -> depot
- Relay: AGV -> relay_point, UAV relay -> start -> end -> relay

This strategy unifies direct delivery and relay-fixed delivery modes into a single
candidate space, using ALNS to search for the minimum cost solution.

Candidate pool optimization:
- Precompute candidate pools per (task_id, uav_id) before solving
- Each pool contains: direct availability flag + top-K relay anchors
- Initial solution and repair operators reuse the same candidate pool
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

CandidatePool = Dict[str, Any]
CandidatePools = Dict[Tuple[int, int], CandidatePool]


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
        # Ablation parameters
        allow_direct: bool = True,
        allow_relay: bool = True,
        candidate_pool_strategy: str = "diverse_topk",
        candidate_pool_k: int = 5,
        destroy_operator_set: List[str] = None,
        repair_operator_set: List[str] = None,
        adaptive_operator_weights: bool = True,
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
        self._operators = ALNSOperators(energy_model, seed, adaptive_operator_weights)

        self.allow_direct = allow_direct
        self.allow_relay = allow_relay
        self.candidate_pool_strategy = candidate_pool_strategy
        self.candidate_pool_k = candidate_pool_k
        self.destroy_operator_set = destroy_operator_set
        self.repair_operator_set = repair_operator_set
        self.adaptive_operator_weights = adaptive_operator_weights

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

        candidate_pools = self._build_candidate_pools(
            idle_uavs, pending_tasks, environment, depot_pos, k=5
        )

        initial_solution = self._generate_regret2_initial_solution(
            idle_uavs, pending_tasks, candidate_pools, environment, depot_pos
        )

        best_solution = self._alns_search(
            initial_solution, idle_uavs, pending_tasks, candidate_pools, environment, depot_pos
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
        """Check and apply fallback for waiting tasks.

        Uses unified evaluator to assist fallback decisions:
        - relay_reselected: uses unified evaluator to compare relay candidates
        - relay_to_direct: uses unified evaluator to check feasibility

        Note: predicted_wait, mode_risk, and predicted_slack are heuristic
        approximations, not real-time simulation results.
        """
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
            best_relay_result = None
            best_score = (float('inf'), float('inf'), float('inf'))

            for agv in available_agvs:
                relay_candidates = RelayCandidateGenerator.generate_candidates_for_agv(
                    uav, task, agv, environment, depot_pos
                )
                for relay_pt in relay_candidates:
                    result = self._scorer.evaluate_relay_insertion_unified(
                        uav, task, agv, relay_pt,
                        [], [], 0, 0, depot_pos
                    )
                    if not result.feasibility:
                        continue
                    score = (result.cost_delta, result.mode_risk, result.predicted_wait)
                    if score < best_score:
                        best_score = score
                        best_relay_result = (relay_pt, agv, result)

            if best_relay_result:
                relay_pt, best_agv, result = best_relay_result
                task.relay_point = relay_pt
                task.assigned_agv = best_agv
                if hasattr(task, 'wait_time_at_relay'):
                    task.wait_time_at_relay = 0
                return {
                    "action": "relay_reselected",
                    "event_type": "RELAY_RESELECTED",
                    "relay_point": relay_pt,
                    "agv_id": best_agv.id,
                    "reason": f"Reselected relay: {reason}",
                    "evaluator_result": {
                        "cost_delta": result.cost_delta,
                        "mode_risk": result.mode_risk,
                        "predicted_wait": result.predicted_wait,
                        "feasibility": result.feasibility
                    }
                }

        direct_result = self._scorer.evaluate_direct_insertion_unified(
            uav, task, [], 0, depot_pos
        )
        if direct_result.feasibility:
            task.status = "in_progress"
            if hasattr(task, 'relay_point'):
                delattr(task, 'relay_point')
            if hasattr(task, 'assigned_agv'):
                task.assigned_agv = None
            return {
                "action": "relay_to_direct",
                "event_type": "RELAY_TO_DIRECT_FALLBACK",
                "reason": f"Fallback to direct: {reason}",
                "evaluator_result": {
                    "feasibility": direct_result.feasibility,
                    "mode_risk": direct_result.mode_risk
                }
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
        """Generate greedy initial solution with multi-task routes."""
        solution = Solution(assignments=[])
        remaining_tasks = pending_tasks.copy()

        while remaining_tasks:
            best_delta = float('inf')
            best_option = None
            best_task = None

            for task in remaining_tasks:
                for uav in idle_uavs:
                    uav_route = solution.uav_routes.get(uav.id, [])
                    insert_positions = solution.get_insertion_positions(uav.id)

                    for pos in insert_positions:
                        result = self._scorer.evaluate_direct_insertion_unified(
                            uav, task, uav_route, pos, depot_pos
                        )
                        if not result.feasibility:
                            continue
                        if result.cost_delta < best_delta:
                            best_delta = result.cost_delta
                            best_option = result.option
                            best_task = task

                    relay_candidates = RelayCandidateGenerator.generate_bound_candidates(uav, task, environment, depot_pos)
                    for relay_point, agv in relay_candidates:
                        agv_route = solution.agv_routes.get(agv.id, [])
                        uav_positions = solution.get_insertion_positions(uav.id)
                        agv_positions = solution.get_agv_insertion_positions(agv.id)

                        for uav_pos in uav_positions:
                            for agv_pos in agv_positions:
                                result = self._scorer.evaluate_relay_insertion_unified(
                                    uav, task, agv, relay_point,
                                    uav_route, agv_route,
                                    uav_pos, agv_pos, depot_pos
                                )
                                if not result.feasibility:
                                    continue
                                if result.cost_delta < best_delta:
                                    best_delta = result.cost_delta
                                    best_option = result.option
                                    best_task = task

            if best_option and best_task:
                solution.add_assignment(best_option)
                remaining_tasks = [t for t in remaining_tasks if t.id != best_task.id]
            else:
                break

        return solution

    def _alns_search(
        self,
        initial_solution: Solution,
        idle_uavs: List,
        pending_tasks: List,
        candidate_pools: CandidatePools,
        environment,
        depot_pos: Tuple[float, float]
    ) -> Solution:
        """Perform ALNS search with candidate pools."""
        rng = self._rng
        current = initial_solution.copy()
        best = current.copy()
        temperature = self.initial_temperature

        destroy_ops = self._get_destroy_operators()
        repair_ops = self._get_repair_operators()

        for iteration in range(self.max_iterations):
            prev_cost = current.total_cost

            selected_destroy = self._operators.select_operator(destroy_ops)
            destroyed = self._operators.destroy(current, selected_destroy, self.destroy_count)

            selected_repair = self._operators.select_operator(repair_ops)
            repaired = self._operators.repair(
                destroyed, pending_tasks, idle_uavs, environment, depot_pos,
                selected_repair, self.repair_count, candidate_pools
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

    def _get_destroy_operators(self):
        """Get destroy operators based on ablation config."""
        all_ops = {
            "random_remove": DestroyOperator.RANDOM_REMOVE,
            "worst_remove": DestroyOperator.WORST_REMOVE,
            "high_energy_remove": DestroyOperator.HIGH_ENERGY_REMOVE
        }

        if self.destroy_operator_set:
            return [all_ops.get(op) for op in self.destroy_operator_set if all_ops.get(op)]

        return [
            DestroyOperator.RANDOM_REMOVE,
            DestroyOperator.WORST_REMOVE,
            DestroyOperator.HIGH_ENERGY_REMOVE
        ]

    def _get_repair_operators(self):
        """Get repair operators based on ablation config."""
        all_ops = {
            "greedy_insert": RepairOperator.GREEDY_INSERT,
            "regret_insert": RepairOperator.REGRET_INSERT,
            "relay_aware_regret_insert": RepairOperator.RELAY_AWARE_REGRET_INSERT
        }

        if self.repair_operator_set:
            return [all_ops.get(op) for op in self.repair_operator_set if all_ops.get(op)]

        return [
            RepairOperator.GREEDY_INSERT,
            RepairOperator.REGRET_INSERT,
            RepairOperator.RELAY_AWARE_REGRET_INSERT
        ]

    def _can_uav_complete_direct(self, uav, task, depot_pos):
        """Check if UAV can complete direct delivery with pickup-delivery semantics.

        Path: origin -> start -> end -> origin
        """
        start_point = task.start_point
        end_point = task.end_point
        required_range = (
            self._distance(depot_pos, start_point) +
            self._distance(start_point, end_point) +
            self._distance(end_point, depot_pos)
        )
        max_range = getattr(uav, 'max_range', 500)
        remaining_range = uav.battery * max_range / 100.0
        return required_range <= remaining_range

    def _build_candidate_pools(
        self,
        uavs: List,
        tasks: List,
        environment,
        depot_pos: Tuple[float, float],
        k: int = None
    ) -> CandidatePools:
        """Build candidate pools per (task_id, uav_id).

        Each pool contains:
        - direct: bool flag indicating direct mode is feasible
        - relay: list of (relay_point, agv) tuples, filtered to top-K

        Relay candidates are:
        1. Generated using RelayCandidateGenerator.generate_bound_candidates
        2. Evaluated using unified scorer (empty routes, position 0)
        3. Filtered for feasibility
        4. Deduplicated by relay_point (rounded to 0.1 precision)
        5. Sorted by (cost_delta, mode_risk, predicted_wait)
        6. Selected top-K with diversity (prefer different AGVs)

        Ablation parameters:
        - allow_direct: whether to include direct delivery options
        - allow_relay: whether to include relay delivery options
        - candidate_pool_strategy: diverse_topk / greedy_topk / random_topk
        - candidate_pool_k: number of candidates to select
        """
        pools: CandidatePools = {}
        pool_k = k if k is not None else self.candidate_pool_k

        for task in tasks:
            for uav in uavs:
                pool: CandidatePool = {
                    "direct": False,
                    "relay": []
                }

                if self.allow_direct:
                    direct_result = self._scorer.evaluate_direct_insertion_unified(
                        uav, task, [], 0, depot_pos
                    )
                    if direct_result.feasibility:
                        pool["direct"] = True

                if self.allow_relay:
                    relay_candidates = RelayCandidateGenerator.generate_bound_candidates(
                        uav, task, environment, depot_pos
                    )

                    scored_candidates = []
                    for relay_point, agv in relay_candidates:
                        result = self._scorer.evaluate_relay_insertion_unified(
                            uav, task, agv, relay_point,
                            [], [], 0, 0, depot_pos
                        )
                        if result.feasibility:
                            scored_candidates.append({
                                "relay_point": relay_point,
                                "agv": agv,
                                "cost_delta": result.cost_delta,
                                "mode_risk": result.mode_risk,
                                "predicted_wait": result.predicted_wait
                            })

                    deduplicated = self._deduplicate_relay_candidates(scored_candidates)
                    sorted_candidates = sorted(deduplicated, key=lambda x: (
                        x["cost_delta"], x["mode_risk"], x["predicted_wait"]
                    ))

                    pool["relay"] = self._select_top_k_candidates(
                        sorted_candidates, pool_k, self.candidate_pool_strategy
                    )

                pools[(task.id, uav.id)] = pool

        return pools

    def _select_top_k_candidates(
        self,
        candidates: List[Dict[str, Any]],
        k: int,
        strategy: str
    ) -> List[Tuple[Tuple[float, float], Any]]:
        """Select top-K relay candidates based on strategy."""
        if not candidates:
            return []

        if strategy == "greedy_topk":
            sorted_by_cost = sorted(candidates, key=lambda x: (
                x["cost_delta"], x["mode_risk"], x["predicted_wait"]
            ))
            return [(c["relay_point"], c["agv"]) for c in sorted_by_cost[:k]]

        elif strategy == "random_topk":
            shuffled = candidates.copy()
            self._rng.shuffle(shuffled)
            return [(c["relay_point"], c["agv"]) for c in shuffled[:k]]

        else:  # diverse_topk (default)
            return self._select_top_k_with_diversity(candidates, k)

    def _deduplicate_relay_candidates(self, candidates: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Deduplicate relay candidates by rounded relay_point."""
        seen = set()
        unique = []
        for c in candidates:
            point = c["relay_point"]
            key = (round(point[0], 1), round(point[1], 1))
            if key not in seen:
                seen.add(key)
                unique.append(c)
        return unique

    def _select_top_k_with_diversity(self, candidates: List[Dict[str, Any]], k: int) -> List[Tuple[Tuple[float, float], Any]]:
        """Select top-K relay candidates with diversity (prefer different AGVs)."""
        if not candidates:
            return []

        result = []
        used_agv_ids = set()
        sorted_by_cost = sorted(candidates, key=lambda x: (
            x["cost_delta"], x["mode_risk"], x["predicted_wait"]
        ))

        for c in sorted_by_cost:
            if len(result) >= k:
                break
            agv_id = c["agv"].id
            if agv_id not in used_agv_ids:
                result.append((c["relay_point"], c["agv"]))
                used_agv_ids.add(agv_id)

        if len(result) < k:
            for c in sorted_by_cost:
                if len(result) >= k:
                    break
                agv_id = c["agv"].id
                if agv_id in used_agv_ids:
                    result.append((c["relay_point"], c["agv"]))

        return result[:k]

    def _generate_regret2_initial_solution(
        self,
        idle_uavs: List,
        pending_tasks: List,
        candidate_pools: CandidatePools,
        environment,
        depot_pos: Tuple[float, float]
    ) -> Solution:
        """Generate regret-2 initial solution using candidate pools.

        Regret-2 algorithm:
        1. For each remaining task, collect all feasible options across all UAVs
        2. Sort options by cost_delta
        3. Compute regret = second_best_cost_delta - best_cost_delta
        4. Select task with maximum regret
        5. Assign its best option to solution
        6. Repeat until no more tasks can be assigned

        If a task has only 1 option, regret = best_cost_delta
        """
        solution = Solution(assignments=[])
        remaining_tasks = pending_tasks.copy()
        remaining_uavs = idle_uavs.copy()

        while remaining_tasks and remaining_uavs:
            regret_scores = []

            for task in remaining_tasks:
                candidates = []

                for uav in remaining_uavs:
                    pool_key = (task.id, uav.id)
                    pool = candidate_pools.get(pool_key, {"direct": False, "relay": []})

                    if pool["direct"]:
                        uav_route = solution.uav_routes.get(uav.id, [])
                        insert_positions = solution.get_insertion_positions(uav.id)

                        for pos in insert_positions:
                            result = self._scorer.evaluate_direct_insertion_unified(
                                uav, task, uav_route, pos, depot_pos
                            )
                            if result.feasibility:
                                candidates.append({
                                    "cost_delta": result.cost_delta,
                                    "option": result.option,
                                    "uav": uav,
                                    "task": task
                                })

                    for relay_point, agv in pool["relay"]:
                        uav_route = solution.uav_routes.get(uav.id, [])
                        agv_route = solution.agv_routes.get(agv.id, [])
                        uav_positions = solution.get_insertion_positions(uav.id)
                        agv_positions = solution.get_agv_insertion_positions(agv.id)

                        for uav_pos in uav_positions:
                            for agv_pos in agv_positions:
                                result = self._scorer.evaluate_relay_insertion_unified(
                                    uav, task, agv, relay_point,
                                    uav_route, agv_route,
                                    uav_pos, agv_pos, depot_pos
                                )
                                if result.feasibility:
                                    candidates.append({
                                        "cost_delta": result.cost_delta,
                                        "option": result.option,
                                        "uav": uav,
                                        "task": task
                                    })

                if len(candidates) >= 2:
                    sorted_candidates = sorted(candidates, key=lambda x: x["cost_delta"])
                    best_delta = sorted_candidates[0]["cost_delta"]
                    second_best_delta = sorted_candidates[1]["cost_delta"]
                    regret = second_best_delta - best_delta
                    regret_scores.append((regret, sorted_candidates[0]))
                elif len(candidates) == 1:
                    regret_scores.append((candidates[0]["cost_delta"], candidates[0]))

            if not regret_scores:
                break

            regret_scores.sort(key=lambda x: x[0], reverse=True)
            _, best_candidate = regret_scores[0]
            best_option = best_candidate["option"]
            best_uav = best_candidate["uav"]
            best_task = best_candidate["task"]

            solution.add_assignment(best_option)
            remaining_tasks = [t for t in remaining_tasks if t.id != best_task.id]
            remaining_uavs = [u for u in remaining_uavs if u.id != best_uav.id]

        return solution

    def get_operator_weights(self) -> Dict[str, float]:
        """Get current operator weights."""
        return self._operators.get_operator_weights()
