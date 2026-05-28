"""ALNS operators module.

Contains destroy operators, repair operators, and adaptive weight management.
"""

import random
from typing import Any, Dict, List

from .solution import (
    DeliveryMode, DeliveryOption, Solution,
    DestroyOperator, RepairOperator
)
from .scoring import CostScorer
from src.planning.relay_candidate_generator import RelayCandidateGenerator


class ALNSOperators:
    """ALNS operators manager."""

    def __init__(self, energy_model=None, seed: int = 42):
        self._rng = random.Random(seed)
        self._scorer = CostScorer(energy_model)

        self._operator_weights = {
            DestroyOperator.RANDOM_REMOVE: 1.0,
            DestroyOperator.WORST_REMOVE: 1.0,
            RepairOperator.GREEDY_INSERT: 1.0,
            RepairOperator.REGRET_INSERT: 1.0,
        }
        self._operator_stats = {
            DestroyOperator.RANDOM_REMOVE: {"use": 0, "improve": 0},
            DestroyOperator.WORST_REMOVE: {"use": 0, "improve": 0},
            RepairOperator.GREEDY_INSERT: {"use": 0, "improve": 0},
            RepairOperator.REGRET_INSERT: {"use": 0, "improve": 0},
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
                    removed = new_solution.assignments.pop(idx)
                    new_solution.total_cost -= removed.cost
                    mode = removed.mode.value
                    new_solution.mode_counts[mode] = max(
                        0, new_solution.mode_counts.get(mode, 0) - 1
                    )

        elif operator == DestroyOperator.WORST_REMOVE:
            sorted_assignments = sorted(
                new_solution.assignments,
                key=lambda a: a.cost,
                reverse=True
            )
            for i in range(min(num_remove, len(sorted_assignments))):
                removed = sorted_assignments[i]
                if removed in new_solution.assignments:
                    new_solution.assignments.remove(removed)
                    new_solution.total_cost -= removed.cost
                    mode = removed.mode.value
                    new_solution.mode_counts[mode] = max(
                        0, new_solution.mode_counts.get(mode, 0) - 1
                    )

        return new_solution

    def repair(
        self,
        solution: Solution,
        pending_tasks: List,
        idle_uavs: List,
        environment,
        depot_pos: tuple,
        operator: RepairOperator,
        repair_count: int = 1
    ) -> Solution:
        """Apply a repair operator to the solution."""
        new_solution = solution.copy()
        assigned_uav_ids = {a.uav_id for a in new_solution.assignments}
        assigned_task_ids = {a.task_id for a in new_solution.assignments}

        available_uavs = [u for u in idle_uavs if u.id not in assigned_uav_ids]
        available_tasks = [t for t in pending_tasks if t.id not in assigned_task_ids]

        if not available_uavs or not available_tasks:
            return new_solution

        if operator == RepairOperator.GREEDY_INSERT:
            for _ in range(min(repair_count, len(available_uavs) * len(available_tasks))):
                if not available_uavs or not available_tasks:
                    break
                best_insert = None
                best_insert_cost = float('inf')
                best_uav = None
                best_task = None

                for uav in available_uavs:
                    for task in available_tasks:
                        direct_option = self._scorer.evaluate(
                            uav, task, DeliveryMode.DIRECT, depot_pos=depot_pos
                        )
                        if direct_option.cost < best_insert_cost:
                            best_insert_cost = direct_option.cost
                            best_insert = direct_option
                            best_uav = uav
                            best_task = task

                        relay_candidates = RelayCandidateGenerator.generate_bound_candidates(
                            uav, task, environment, depot_pos
                        )
                        for relay_point, agv in relay_candidates:
                            relay_option = self._scorer.evaluate(
                                uav, task, DeliveryMode.RELAY_FIXED,
                                relay_point=relay_point, agv=agv, depot_pos=depot_pos
                            )
                            if relay_option.cost < best_insert_cost:
                                best_insert_cost = relay_option.cost
                                best_insert = relay_option
                                best_uav = uav
                                best_task = task

                if best_insert:
                    new_solution.assignments.append(best_insert)
                    new_solution.total_cost += best_insert.cost
                    new_solution.mode_counts[best_insert.mode.value] = new_solution.mode_counts.get(
                        best_insert.mode.value, 0
                    ) + 1
                    available_uavs = [u for u in available_uavs if u.id != best_uav.id]
                    available_tasks = [t for t in available_tasks if t.id != best_task.id]

        elif operator == RepairOperator.REGRET_INSERT:
            regret_scores = []
            for task in available_tasks:
                for uav in available_uavs:
                    costs = []
                    direct_option = self._scorer.evaluate(
                        uav, task, DeliveryMode.DIRECT, depot_pos=depot_pos
                    )
                    costs.append(direct_option.cost)

                    relay_candidates = RelayCandidateGenerator.generate_bound_candidates(
                        uav, task, environment, depot_pos
                    )
                    for relay_point, agv in relay_candidates:
                        relay_option = self._scorer.evaluate(
                            uav, task, DeliveryMode.RELAY_FIXED,
                            relay_point=relay_point, agv=agv, depot_pos=depot_pos
                        )
                        costs.append(relay_option.cost)

                    if len(costs) >= 2:
                        sorted_costs = sorted(costs)
                        regret = sorted_costs[1] - sorted_costs[0]
                    elif len(costs) == 1:
                        regret = costs[0]
                    else:
                        regret = 0

                    best_option = direct_option
                    if relay_candidates:
                        for relay_point, agv in relay_candidates:
                            relay_option = self._scorer.evaluate(
                                uav, task, DeliveryMode.RELAY_FIXED,
                                relay_point=relay_point, agv=agv, depot_pos=depot_pos
                            )
                            if relay_option.cost < best_option.cost:
                                best_option = relay_option

                    regret_scores.append((regret, best_option, uav, task))

            regret_scores.sort(key=lambda x: x[0], reverse=True)

            for _, best_option, best_uav, best_task in regret_scores[:repair_count]:
                if best_uav in available_uavs and best_task in available_tasks:
                    new_solution.assignments.append(best_option)
                    new_solution.total_cost += best_option.cost
                    new_solution.mode_counts[best_option.mode.value] = new_solution.mode_counts.get(
                        best_option.mode.value, 0
                    ) + 1
                    available_uavs = [u for u in available_uavs if u.id != best_uav.id]
                    available_tasks = [t for t in available_tasks if t.id != best_task.id]

        return new_solution

    def select_operator(self, operators: List):
        """Select an operator based on adaptive weights."""
        total_weight = sum(self._operator_weights[op] for op in operators)
        r = self._rng.random() * total_weight
        cumulative = 0
        for op in operators:
            cumulative += self._operator_weights[op]
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
        self._operator_stats[destroy_op]["use"] += 1
        self._operator_stats[repair_op]["use"] += 1

        if best_improved:
            self._operator_weights[destroy_op] += 0.5
            self._operator_weights[repair_op] += 0.5
            self._operator_stats[destroy_op]["improve"] += 1
            self._operator_stats[repair_op]["improve"] += 1
        elif improved:
            self._operator_weights[destroy_op] += 0.1
            self._operator_weights[repair_op] += 0.1
        else:
            decay = 0.95
            self._operator_weights[destroy_op] *= decay
            self._operator_weights[repair_op] *= decay

        for op in self._operator_weights:
            self._operator_weights[op] = max(0.1, self._operator_weights[op])

    def get_operator_weights(self) -> Dict[str, float]:
        """Get current operator weights."""
        return {op.value: self._operator_weights[op] for op in DestroyOperator}
