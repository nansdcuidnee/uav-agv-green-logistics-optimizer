"""ALNS cost scoring module.

Pickup-delivery model:
- Direct mode: UAV depot -> start -> end -> depot
- Relay mode: AGV -> relay_point, UAV relay -> start -> end -> relay

Key semantic rules:
1. UAV always does: start -> end -> return_to_origin
2. For direct: origin = depot_pos or current UAV position
3. For relay: origin = relay_point
4. AGV moves: current_position -> relay_point (no return for AGV in this model)
"""

import math
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

from .solution import DeliveryMode, DeliveryOption, RouteStop


@dataclass
class EvaluationResult:
    """Unified evaluation result for delivery options.

    Fields:
    - cost_delta: Incremental cost change (negative = improvement)
    - cost_breakdown: Detailed cost components
    - feasibility: Whether the option is feasible (energy/range sufficient)
    - predicted_wait: Predicted wait time for relay (heuristic)
    - predicted_slack: Time window slack (heuristic)
    - mode_risk: Mode risk level (0.0-1.0)
    - option: The corresponding DeliveryOption
    """
    cost_delta: float
    cost_breakdown: Dict[str, float] = field(default_factory=dict)
    feasibility: bool = True
    predicted_wait: float = 0.0
    predicted_slack: float = 0.0
    mode_risk: float = 0.0
    option: Optional[DeliveryOption] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for debugging."""
        return {
            "cost_delta": self.cost_delta,
            "feasibility": self.feasibility,
            "predicted_wait": self.predicted_wait,
            "predicted_slack": self.predicted_slack,
            "mode_risk": self.mode_risk,
        }


class CostScorer:
    """Cost scorer for delivery options with pickup-delivery semantics."""

    def __init__(self, energy_model=None):
        self.energy_model = energy_model
        self._cost_weights = {
            "time": 1.0,
            "uav_energy": 0.8,
            "agv_energy": 0.5,
            "carbon": 0.3,
            "wait_penalty": 2.0,
            "timeout_penalty": 5.0,
            "fallback_risk": 3.0,
        }

    def evaluate(
        self,
        uav,
        task,
        mode: DeliveryMode,
        relay_point: Optional[Tuple[float, float]] = None,
        agv=None,
        depot_pos: Tuple[float, float] = None,
        uav_origin: Tuple[float, float] = None
    ) -> DeliveryOption:
        """Evaluate a delivery option and compute its cost.

        Pickup-delivery semantics:
        - Direct: origin -> start -> end -> origin
        - Relay: AGV moves to relay, then UAV relay -> start -> end -> relay
        """
        if depot_pos is None:
            depot_pos = (0.0, 0.0)

        start_point = task.start_point
        end_point = task.end_point
        payload = float(getattr(task, 'payload', 1.0))

        time_cost = 0.0
        uav_energy = 0.0
        agv_energy = 0.0
        wait_penalty = 0.0
        timeout_penalty = 0.0
        fallback_risk = 0.0

        if mode == DeliveryMode.DIRECT:
            if uav_origin is None:
                uav_origin = depot_pos

            dist_origin_to_start = self._distance(uav_origin, start_point)
            dist_start_to_end = self._distance(start_point, end_point)
            dist_end_to_origin = self._distance(end_point, uav_origin)
            total_uav_distance = dist_origin_to_start + dist_start_to_end + dist_end_to_origin

            time_cost = total_uav_distance / getattr(uav, 'max_speed', 10) / 60
            uav_energy = total_uav_distance / 1000 * getattr(
                self.energy_model, 'cruise_energy_per_km', 5.0
            ) if self.energy_model else total_uav_distance / 1000 * 5.0

            fallback_risk = 0.1

            uav_anchor = uav_origin
            agv_anchor = (0.0, 0.0)

        elif mode == DeliveryMode.RELAY_FIXED:
            if agv:
                dist_agv_to_relay = self._distance(agv.position, relay_point)
                agv_energy = dist_agv_to_relay / 1000 * getattr(
                    self.energy_model, 'agv_energy_per_km', 3.0
                ) if self.energy_model else dist_agv_to_relay / 1000 * 3.0

            dist_relay_to_start = self._distance(relay_point, start_point)
            dist_start_to_end = self._distance(start_point, end_point)
            dist_end_to_relay = self._distance(end_point, relay_point)
            total_uav_distance = dist_relay_to_start + dist_start_to_end + dist_end_to_relay

            time_cost = total_uav_distance / getattr(uav, 'max_speed', 10) / 60
            uav_energy = total_uav_distance / 1000 * getattr(
                self.energy_model, 'cruise_energy_per_km', 5.0
            ) if self.energy_model else total_uav_distance / 1000 * 5.0

            wait_penalty = 5.0
            fallback_risk = 0.3

            uav_anchor = relay_point
            agv_anchor = relay_point

        carbon = (uav_energy + agv_energy) * 0.5

        total_cost = (
            self._cost_weights["time"] * time_cost +
            self._cost_weights["uav_energy"] * uav_energy +
            self._cost_weights["agv_energy"] * agv_energy +
            self._cost_weights["carbon"] * carbon +
            self._cost_weights["wait_penalty"] * wait_penalty +
            self._cost_weights["timeout_penalty"] * timeout_penalty +
            self._cost_weights["fallback_risk"] * fallback_risk
        )

        cost_breakdown = {
            "time": time_cost,
            "uav_energy": uav_energy,
            "agv_energy": agv_energy,
            "carbon": carbon,
            "wait_penalty": wait_penalty,
            "timeout_penalty": timeout_penalty,
            "fallback_risk": fallback_risk,
        }

        return DeliveryOption(
            mode=mode,
            uav_id=uav.id,
            task_id=task.id,
            relay_point=relay_point,
            agv_id=agv.id if agv else None,
            cost=total_cost,
            cost_breakdown=cost_breakdown,
            uav_anchor_position=uav_anchor,
            agv_anchor_position=agv_anchor
        )

    def evaluate_direct_insertion_delta(
        self,
        uav,
        task,
        uav_route: List[RouteStop],
        insert_position: int,
        depot_pos: Tuple[float, float]
    ) -> Tuple[float, DeliveryOption]:
        """Evaluate the delta cost of inserting a direct task at a specific position.

        Returns (delta_cost, delivery_option).
        """
        start_point = task.start_point
        end_point = task.end_point

        prev_pos = depot_pos
        if insert_position > 0 and uav_route:
            prev_stop = uav_route[insert_position - 1]
            prev_pos = prev_stop.position if prev_stop.position != (0.0, 0.0) else depot_pos

        next_pos = depot_pos
        if insert_position < len(uav_route) and uav_route:
            next_stop = uav_route[insert_position]
            next_pos = next_stop.position if next_stop.position != (0.0, 0.0) else depot_pos

        dist_prev_to_next = self._distance(prev_pos, next_pos)
        dist_prev_to_start = self._distance(prev_pos, start_point)
        dist_start_to_end = self._distance(start_point, end_point)
        dist_end_to_next = self._distance(end_point, next_pos)

        delta_distance = dist_prev_to_start + dist_start_to_end + dist_end_to_next - dist_prev_to_next

        time_delta = delta_distance / getattr(uav, 'max_speed', 10) / 60
        uav_energy_delta = delta_distance / 1000 * getattr(
            self.energy_model, 'cruise_energy_per_km', 5.0
        ) if self.energy_model else delta_distance / 1000 * 5.0

        fallback_risk = 0.1
        carbon_delta = uav_energy_delta * 0.5

        delta_cost = (
            self._cost_weights["time"] * time_delta +
            self._cost_weights["uav_energy"] * uav_energy_delta +
            self._cost_weights["carbon"] * carbon_delta +
            self._cost_weights["fallback_risk"] * fallback_risk
        )

        option = DeliveryOption(
            mode=DeliveryMode.DIRECT,
            uav_id=uav.id,
            task_id=task.id,
            cost=delta_cost,
            uav_route_position=insert_position,
            uav_anchor_position=depot_pos,
            agv_anchor_position=(0.0, 0.0)
        )

        return delta_cost, option

    def evaluate_relay_insertion_delta(
        self,
        uav,
        task,
        agv,
        relay_point: Tuple[float, float],
        uav_route: List[RouteStop],
        agv_route: List[RouteStop],
        uav_insert_position: int,
        agv_insert_position: int,
        depot_pos: Tuple[float, float]
    ) -> Tuple[float, DeliveryOption]:
        """Evaluate the delta cost of a relay insertion with joint UAV+AGV positions.

        Returns (delta_cost, delivery_option).
        """
        start_point = task.start_point
        end_point = task.end_point

        uav_prev_pos = relay_point
        if uav_insert_position > 0 and uav_route:
            prev_stop = uav_route[uav_insert_position - 1]
            uav_prev_pos = prev_stop.position if prev_stop.position != (0.0, 0.0) else relay_point

        uav_next_pos = relay_point
        if uav_insert_position < len(uav_route) and uav_route:
            next_stop = uav_route[uav_insert_position]
            uav_next_pos = next_stop.position if next_stop.position != (0.0, 0.0) else relay_point

        dist_uav_prev_to_next = self._distance(uav_prev_pos, uav_next_pos)
        dist_uav_prev_to_start = self._distance(uav_prev_pos, start_point)
        dist_start_to_end = self._distance(start_point, end_point)
        dist_end_to_uav_next = self._distance(end_point, uav_next_pos)

        uav_delta_distance = (
            dist_uav_prev_to_start + dist_start_to_end + dist_end_to_uav_next - dist_uav_prev_to_next
        )

        agv_prev_pos = agv.position
        if agv_insert_position > 0 and agv_route:
            prev_stop = agv_route[agv_insert_position - 1]
            agv_prev_pos = prev_stop.position if prev_stop.position != (0.0, 0.0) else agv.position

        agv_next_pos = agv.position
        if agv_insert_position < len(agv_route) and agv_route:
            next_stop = agv_route[agv_insert_position]
            agv_next_pos = next_stop.position if next_stop.position != (0.0, 0.0) else agv.position

        dist_agv_prev_to_next = self._distance(agv_prev_pos, agv_next_pos)
        dist_agv_prev_to_relay = self._distance(agv_prev_pos, relay_point)
        dist_relay_to_agv_next = self._distance(relay_point, agv_next_pos)

        agv_delta_distance = dist_agv_prev_to_relay + dist_relay_to_agv_next - dist_agv_prev_to_next

        time_delta = uav_delta_distance / getattr(uav, 'max_speed', 10) / 60
        uav_energy_delta = uav_delta_distance / 1000 * getattr(
            self.energy_model, 'cruise_energy_per_km', 5.0
        ) if self.energy_model else uav_delta_distance / 1000 * 5.0

        agv_energy_delta = agv_delta_distance / 1000 * getattr(
            self.energy_model, 'agv_energy_per_km', 3.0
        ) if self.energy_model else agv_delta_distance / 1000 * 3.0

        wait_penalty = 5.0
        fallback_risk = 0.3
        carbon_delta = (uav_energy_delta + agv_energy_delta) * 0.5

        delta_cost = (
            self._cost_weights["time"] * time_delta +
            self._cost_weights["uav_energy"] * uav_energy_delta +
            self._cost_weights["agv_energy"] * agv_energy_delta +
            self._cost_weights["carbon"] * carbon_delta +
            self._cost_weights["wait_penalty"] * wait_penalty +
            self._cost_weights["fallback_risk"] * fallback_risk
        )

        option = DeliveryOption(
            mode=DeliveryMode.RELAY_FIXED,
            uav_id=uav.id,
            task_id=task.id,
            relay_point=relay_point,
            agv_id=agv.id,
            cost=delta_cost,
            uav_route_position=uav_insert_position,
            agv_route_position=agv_insert_position,
            uav_anchor_position=relay_point,
            agv_anchor_position=relay_point
        )

        return delta_cost, option

    def evaluate_direct_insertion_unified(
        self,
        uav,
        task,
        uav_route: List[RouteStop],
        insert_position: int,
        depot_pos: Tuple[float, float]
    ) -> EvaluationResult:
        """Unified evaluation of direct insertion with full result.

        Returns EvaluationResult with:
        - cost_delta
        - cost_breakdown
        - feasibility (energy/range check)
        - predicted_wait (0.0 for direct)
        - predicted_slack (time window slack, heuristic)
        - mode_risk (0.1 for direct)
        - option

        Note: predicted_wait and predicted_slack are heuristic approximations,
        not real-time simulation results.
        """
        start_point = task.start_point
        end_point = task.end_point
        remaining_range = uav.battery * uav.max_range / 100.0

        required_range = (
            self._distance(depot_pos, start_point) +
            self._distance(start_point, end_point) +
            self._distance(end_point, depot_pos)
        )

        feasibility = required_range <= remaining_range

        delta_cost, option = self.evaluate_direct_insertion_delta(
            uav, task, uav_route, insert_position, depot_pos
        )

        uav_energy = required_range / 1000 * getattr(
            self.energy_model, 'cruise_energy_per_km', 5.0
        ) if self.energy_model else required_range / 1000 * 5.0

        deadline = getattr(task, 'deadline', None)
        if deadline is not None:
            slack = max(0.0, deadline - (required_range / getattr(uav, 'max_speed', 10)))
        else:
            slack = 100.0

        cost_breakdown = {
            "time": delta_cost * self._cost_weights.get("time", 1.0),
            "uav_energy": uav_energy * self._cost_weights.get("uav_energy", 0.8),
            "agv_energy": 0.0,
            "carbon": uav_energy * 0.5 * self._cost_weights.get("carbon", 0.3),
            "wait_penalty": 0.0,
            "timeout_penalty": 0.0,
            "fallback_risk": 0.1 * self._cost_weights.get("fallback_risk", 3.0),
        }

        return EvaluationResult(
            cost_delta=delta_cost,
            cost_breakdown=cost_breakdown,
            feasibility=feasibility,
            predicted_wait=0.0,
            predicted_slack=slack,
            mode_risk=0.1,
            option=option
        )

    def evaluate_relay_insertion_unified(
        self,
        uav,
        task,
        agv,
        relay_point: Tuple[float, float],
        uav_route: List[RouteStop],
        agv_route: List[RouteStop],
        uav_insert_position: int,
        agv_insert_position: int,
        depot_pos: Tuple[float, float]
    ) -> EvaluationResult:
        """Unified evaluation of relay insertion with full result.

        Returns EvaluationResult with:
        - cost_delta
        - cost_breakdown
        - feasibility (UAV range + energy check)
        - predicted_wait (heuristic based on AGV travel)
        - predicted_slack (time window slack, heuristic)
        - mode_risk (0.3 for relay, higher than direct)
        - option

        Note: predicted_wait and predicted_slack are heuristic approximations.
        Real wait time depends on AGV-UAV synchronization which is not
        modeled in this simplified evaluation.
        """
        start_point = task.start_point
        end_point = task.end_point
        remaining_range = uav.battery * uav.max_range / 100.0

        required_range = (
            self._distance(relay_point, start_point) +
            self._distance(start_point, end_point) +
            self._distance(end_point, relay_point)
        )

        feasibility = required_range <= remaining_range

        delta_cost, option = self.evaluate_relay_insertion_delta(
            uav, task, agv, relay_point,
            uav_route, agv_route,
            uav_insert_position, agv_insert_position, depot_pos
        )

        uav_energy = required_range / 1000 * getattr(
            self.energy_model, 'cruise_energy_per_km', 5.0
        ) if self.energy_model else required_range / 1000 * 5.0

        agv_travel = self._distance(agv.position, relay_point)
        agv_energy = agv_travel / 1000 * getattr(
            self.energy_model, 'agv_energy_per_km', 3.0
        ) if self.energy_model else agv_travel / 1000 * 3.0

        agv_speed = getattr(agv, 'max_speed', 5.0)
        predicted_wait = agv_travel / agv_speed if agv_speed > 0 else 5.0

        deadline = getattr(task, 'deadline', None)
        if deadline is not None:
            slack = max(0.0, deadline - (required_range / getattr(uav, 'max_speed', 10)))
        else:
            slack = 100.0

        cost_breakdown = {
            "time": delta_cost * self._cost_weights.get("time", 1.0),
            "uav_energy": uav_energy * self._cost_weights.get("uav_energy", 0.8),
            "agv_energy": agv_energy * self._cost_weights.get("agv_energy", 0.5),
            "carbon": (uav_energy + agv_energy) * 0.5 * self._cost_weights.get("carbon", 0.3),
            "wait_penalty": predicted_wait * self._cost_weights.get("wait_penalty", 2.0),
            "timeout_penalty": 0.0,
            "fallback_risk": 0.3 * self._cost_weights.get("fallback_risk", 3.0),
        }

        return EvaluationResult(
            cost_delta=delta_cost,
            cost_breakdown=cost_breakdown,
            feasibility=feasibility,
            predicted_wait=predicted_wait,
            predicted_slack=slack,
            mode_risk=0.3,
            option=option
        )

    def _distance(self, p1: Tuple[float, float], p2: Tuple[float, float]) -> float:
        return math.sqrt((p1[0] - p2[0])**2 + (p1[1] - p2[1])**2)

    def get_cost_weights(self) -> Dict[str, float]:
        """Get cost weights."""
        return self._cost_weights.copy()
