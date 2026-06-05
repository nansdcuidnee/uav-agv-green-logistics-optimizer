"""ALNS operators module.

Contains destroy operators, repair operators, and adaptive weight management.
"""

import random
from typing import Any, Dict, List, Tuple

from .solution import (
    DeliveryMode, DeliveryOption, Solution,
    DestroyOperator, RepairOperator
)
from .scoring import CostScorer
from src.planning.relay_candidate_generator import RelayCandidateGenerator


class ALNSOperators:
    """ALNS operators manager."""

    def __init__(self, energy_model=None, seed: int = 42, adaptive_weights: bool = True):
        self._rng = random.Random(seed)
        self._scorer = CostScorer(energy_model)
        self._adaptive_weights = adaptive_weights

        self._operator_weights = {
            DestroyOperator.RANDOM_REMOVE: 1.0,
            DestroyOperator.WORST_REMOVE: 1.0,
            DestroyOperator.HIGH_ENERGY_REMOVE: 1.0,
            RepairOperator.GREEDY_INSERT: 1.0,
            RepairOperator.REGRET_INSERT: 1.0,
            RepairOperator.RELAY_AWARE_REGRET_INSERT: 1.0,
        }
        self._operator_stats = {
            DestroyOperator.RANDOM_REMOVE: {"use": 0, "improve": 0},
            DestroyOperator.WORST_REMOVE: {"use": 0, "improve": 0},
            DestroyOperator.HIGH_ENERGY_REMOVE: {"use": 0, "improve": 0},
            RepairOperator.GREEDY_INSERT: {"use": 0, "improve": 0},
            RepairOperator.REGRET_INSERT: {"use": 0, "improve": 0},
            RepairOperator.RELAY_AWARE_REGRET_INSERT: {"use": 0, "improve": 0},
        }

    def destroy(
        self,
        solution: Solution,
        operator: DestroyOperator,
        destroy_count: int = 1
    ) -> Solution:
        """Apply a destroy operator to the solution."""
        new_solution = solution.copy()
        num_remove = min(destroy_count, len(new_solution.assignments))

        if operator == DestroyOperator.RANDOM_REMOVE:
            for _ in range(num_remove):
                if new_solution.assignments:
                    idx = self._rng.randint(0, len(new_solution.assignments) - 1)
                    removed_option = new_solution.assignments[idx]
                    new_solution.remove_assignment(removed_option)

        elif operator == DestroyOperator.WORST_REMOVE:
            sorted_assignments = sorted(
                new_solution.assignments,
                key=lambda a: a.cost,
                reverse=True
            )
            for i in range(min(num_remove, len(sorted_assignments))):
                removed_option = sorted_assignments[i]
                new_solution.remove_assignment(removed_option)

        elif operator == DestroyOperator.HIGH_ENERGY_REMOVE:
            def get_energy_score(option: DeliveryOption) -> float:
                breakdown = option.cost_breakdown or {}
                uav_energy = breakdown.get("uav_energy", 0.0)
                agv_energy = breakdown.get("agv_energy", 0.0)
                return uav_energy + agv_energy

            sorted_assignments = sorted(
                new_solution.assignments,
                key=get_energy_score,
                reverse=True
            )
            for i in range(min(num_remove, len(sorted_assignments))):
                removed_option = sorted_assignments[i]
                new_solution.remove_assignment(removed_option)

        return new_solution

    def repair(
        self,
        solution: Solution,
        pending_tasks: List,
        idle_uavs: List,
        environment,
        depot_pos: tuple,
        operator: RepairOperator,
        repair_count: int = 1,
        candidate_pools: Dict = None
    ) -> Solution:
        """Apply a repair operator to the solution."""
        new_solution = solution.copy()
        assigned_uav_ids = set(new_solution.uav_routes.keys())
        assigned_task_ids = set(new_solution.task_index.keys())

        available_uavs = [u for u in idle_uavs if u.id not in assigned_uav_ids]
        available_tasks = [t for t in pending_tasks if t.id not in assigned_task_ids]

        if not available_uavs or not available_tasks:
            return new_solution

        if operator == RepairOperator.GREEDY_INSERT:
            for _ in range(min(repair_count, len(available_uavs))):
                if not available_uavs or not available_tasks:
                    break

                best_insert = None
                best_score = (float('inf'), float('inf'), float('inf'))
                best_uav = None
                best_task = None

                for uav in available_uavs:
                    uav_route = new_solution.uav_routes.get(uav.id, [])
                    insert_positions = new_solution.get_insertion_positions(uav.id)

                    for task in available_tasks:
                        pool_key = (task.id, uav.id)
                        pool = candidate_pools.get(pool_key, {}) if candidate_pools else {}
                        direct_available = pool.get("direct", True)

                        if direct_available:
                            for pos in insert_positions:
                                result = self._scorer.evaluate_direct_insertion_unified(
                                    uav, task, uav_route, pos, depot_pos
                                )
                                if not result.feasibility:
                                    continue
                                score = (result.cost_delta, result.mode_risk, result.predicted_wait)
                                if score < best_score:
                                    best_score = score
                                    best_insert = result.option
                                    best_uav = uav
                                    best_task = task

                        relay_candidates = pool.get("relay", []) if candidate_pools else RelayCandidateGenerator.generate_bound_candidates(
                            uav, task, environment, depot_pos
                        )
                        for relay_point, agv in relay_candidates:
                            agv_route = new_solution.agv_routes.get(agv.id, [])
                            uav_positions = new_solution.get_insertion_positions(uav.id)
                            agv_positions = new_solution.get_agv_insertion_positions(agv.id)

                            for uav_pos in uav_positions:
                                for agv_pos in agv_positions:
                                    result = self._scorer.evaluate_relay_insertion_unified(
                                        uav, task, agv, relay_point,
                                        uav_route, agv_route,
                                        uav_pos, agv_pos, depot_pos
                                    )
                                    if not result.feasibility:
                                        continue
                                    score = (result.cost_delta, result.mode_risk, result.predicted_wait)
                                    if score < best_score:
                                        best_score = score
                                        best_insert = result.option
                                        best_uav = uav
                                        best_task = task

                if best_insert:
                    new_solution.add_assignment(best_insert)
                    available_uavs = [u for u in available_uavs if u.id != best_uav.id]
                    available_tasks = [t for t in available_tasks if t.id != best_task.id]

        elif operator == RepairOperator.REGRET_INSERT:
            regret_scores = []

            for task in available_tasks:
                candidates = []

                for uav in available_uavs:
                    uav_route = new_solution.uav_routes.get(uav.id, [])
                    insert_positions = new_solution.get_insertion_positions(uav.id)

                    pool_key = (task.id, uav.id)
                    pool = candidate_pools.get(pool_key, {}) if candidate_pools else {}
                    direct_available = pool.get("direct", True)

                    if direct_available:
                        for pos in insert_positions:
                            result = self._scorer.evaluate_direct_insertion_unified(
                                uav, task, uav_route, pos, depot_pos
                            )
                            if result.feasibility:
                                candidates.append({
                                    'cost_delta': result.cost_delta,
                                    'option': result.option,
                                    'uav': uav,
                                })

                    relay_candidates = pool.get("relay", []) if candidate_pools else RelayCandidateGenerator.generate_bound_candidates(
                        uav, task, environment, depot_pos
                    )
                    for relay_point, agv in relay_candidates:
                        agv_route = new_solution.agv_routes.get(agv.id, [])
                        uav_positions = new_solution.get_insertion_positions(uav.id)
                        agv_positions = new_solution.get_agv_insertion_positions(agv.id)

                        for uav_pos in uav_positions:
                            for agv_pos in agv_positions:
                                result = self._scorer.evaluate_relay_insertion_unified(
                                    uav, task, agv, relay_point,
                                    uav_route, agv_route,
                                    uav_pos, agv_pos, depot_pos
                                )
                                if result.feasibility:
                                    candidates.append({
                                        'cost_delta': result.cost_delta,
                                        'option': result.option,
                                        'uav': uav,
                                    })

                if len(candidates) >= 2:
                    sorted_candidates = sorted(candidates, key=lambda x: x['cost_delta'])
                    best_delta = sorted_candidates[0]['cost_delta']
                    second_best_delta = sorted_candidates[1]['cost_delta']
                    regret = second_best_delta - best_delta
                    regret_scores.append((
                        regret,
                        sorted_candidates[0]['option'],
                        sorted_candidates[0]['uav'],
                        task
                    ))
                elif len(candidates) == 1:
                    regret_scores.append((
                        candidates[0]['cost_delta'],
                        candidates[0]['option'],
                        candidates[0]['uav'],
                        task
                    ))

            regret_scores.sort(key=lambda x: x[0], reverse=True)

            for _, best_option, best_uav, best_task in regret_scores[:repair_count]:
                if best_uav in available_uavs and best_task in available_tasks:
                    new_solution.add_assignment(best_option)
                    available_uavs = [u for u in available_uavs if u.id != best_uav.id]
                    available_tasks = [t for t in available_tasks if t.id != best_task.id]

        elif operator == RepairOperator.RELAY_AWARE_REGRET_INSERT:
            regret_scores = []

            for task in available_tasks:
                candidates = []

                for uav in available_uavs:
                    uav_route = new_solution.uav_routes.get(uav.id, [])
                    insert_positions = new_solution.get_insertion_positions(uav.id)

                    pool_key = (task.id, uav.id)
                    pool = candidate_pools.get(pool_key, {}) if candidate_pools else {}
                    direct_available = pool.get("direct", True)

                    if direct_available:
                        for pos in insert_positions:
                            result = self._scorer.evaluate_direct_insertion_unified(
                                uav, task, uav_route, pos, depot_pos
                            )
                            if result.feasibility:
                                candidates.append({
                                    'cost_delta': result.cost_delta,
                                    'option': result.option,
                                    'uav': uav,
                                    'mode_risk': result.mode_risk,
                                    'predicted_wait': result.predicted_wait,
                                    'predicted_slack': result.predicted_slack,
                                })

                    relay_candidates = pool.get("relay", []) if candidate_pools else RelayCandidateGenerator.generate_bound_candidates(
                        uav, task, environment, depot_pos
                    )
                    for relay_point, agv in relay_candidates:
                        agv_route = new_solution.agv_routes.get(agv.id, [])
                        uav_positions = new_solution.get_insertion_positions(uav.id)
                        agv_positions = new_solution.get_agv_insertion_positions(agv.id)

                        for uav_pos in uav_positions:
                            for agv_pos in agv_positions:
                                result = self._scorer.evaluate_relay_insertion_unified(
                                    uav, task, agv, relay_point,
                                    uav_route, agv_route,
                                    uav_pos, agv_pos, depot_pos
                                )
                                if result.feasibility:
                                    candidates.append({
                                        'cost_delta': result.cost_delta,
                                        'option': result.option,
                                        'uav': uav,
                                        'mode_risk': result.mode_risk,
                                        'predicted_wait': result.predicted_wait,
                                        'predicted_slack': result.predicted_slack,
                                    })

                if len(candidates) >= 2:
                    sorted_candidates = sorted(candidates, key=lambda x: (
                        x['cost_delta'],
                        x['mode_risk'],
                        x['predicted_wait'],
                        -x['predicted_slack']
                    ))
                    best = sorted_candidates[0]
                    second_best = sorted_candidates[1]
                    regret = second_best['cost_delta'] - best['cost_delta']
                    regret_scores.append((regret, best['option'], best['uav'], task))
                elif len(candidates) == 1:
                    regret_scores.append((
                        candidates[0]['cost_delta'],
                        candidates[0]['option'],
                        candidates[0]['uav'],
                        task
                    ))

            regret_scores.sort(key=lambda x: x[0], reverse=True)

            for _, best_option, best_uav, best_task in regret_scores[:repair_count]:
                if best_uav in available_uavs and best_task in available_tasks:
                    new_solution.add_assignment(best_option)
                    available_uavs = [u for u in available_uavs if u.id != best_uav.id]
                    available_tasks = [t for t in available_tasks if t.id != best_task.id]

        return new_solution

    def select_operator(self, operators: List):
        """Select an operator based on adaptive weights."""
        total_weight = sum(self._operator_weights.get(op, 1.0) for op in operators)
        r = self._rng.random() * total_weight
        cumulative = 0
        for op in operators:
            cumulative += self._operator_weights.get(op, 1.0)
            if r <= cumulative:
                return op
        return operators[0]

    def update_operator_weights(
        self,
        destroy_op: DestroyOperator,
        repair_op: RepairOperator,
        improved: bool,
        best_improved: bool
    ):
        """Update operator weights based on performance."""
        if destroy_op in self._operator_stats:
            self._operator_stats[destroy_op]["use"] += 1
        if repair_op in self._operator_stats:
            self._operator_stats[repair_op]["use"] += 1

        if not self._adaptive_weights:
            return

        if best_improved:
            if destroy_op in self._operator_weights:
                self._operator_weights[destroy_op] += 0.5
            if repair_op in self._operator_weights:
                self._operator_weights[repair_op] += 0.5
            if destroy_op in self._operator_stats:
                self._operator_stats[destroy_op]["improve"] += 1
            if repair_op in self._operator_stats:
                self._operator_stats[repair_op]["improve"] += 1
        elif improved:
            if destroy_op in self._operator_weights:
                self._operator_weights[destroy_op] += 0.1
            if repair_op in self._operator_weights:
                self._operator_weights[repair_op] += 0.1
        else:
            decay = 0.95
            if destroy_op in self._operator_weights:
                self._operator_weights[destroy_op] *= decay
            if repair_op in self._operator_weights:
                self._operator_weights[repair_op] *= decay

        for op in list(self._operator_weights.keys()):
            self._operator_weights[op] = max(0.1, self._operator_weights[op])

    def get_operator_weights(self) -> Dict[str, float]:
        """Get current operator weights."""
        result = {}
        for op in list(DestroyOperator) + list(RepairOperator):
            result[op.value] = self._operator_weights.get(op, 1.0)
        return result
