"""ALNS cost scoring module.

Single depot assumption:
- Direct mode: depot -> end_point -> depot
- Relay mode: AGV -> relay_point, relay_point -> end_point -> depot
"""

import math
from typing import Any, Dict, Optional, Tuple

from .solution import DeliveryMode, DeliveryOption


class CostScorer:
    """Cost scorer for delivery options."""

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
        depot_pos: Tuple[float, float] = None
    ) -> DeliveryOption:
        """Evaluate a delivery option and compute its cost."""
        if depot_pos is None:
            depot_pos = (0.0, 0.0)

        end_point = task.end_point
        payload = float(getattr(task, 'payload', 1.0))

        time_cost = 0.0
        uav_energy = 0.0
        agv_energy = 0.0
        wait_penalty = 0.0
        timeout_penalty = 0.0
        fallback_risk = 0.0

        if mode == DeliveryMode.DIRECT:
            dist_depot_to_end = self._distance(depot_pos, end_point)
            dist_end_to_depot = self._distance(end_point, depot_pos)
            total_uav_distance = dist_depot_to_end + dist_end_to_depot

            time_cost = total_uav_distance / getattr(uav, 'max_speed', 10) / 60
            uav_energy = total_uav_distance / 1000 * getattr(
                self.energy_model, 'cruise_energy_per_km', 5.0
            ) if self.energy_model else total_uav_distance / 1000 * 5.0

            fallback_risk = 0.1

        elif mode == DeliveryMode.RELAY_FIXED:
            if agv:
                dist_agv_to_relay = self._distance(agv.position, relay_point)
                agv_energy = dist_agv_to_relay / 1000 * getattr(
                    self.energy_model, 'agv_energy_per_km', 3.0
                ) if self.energy_model else dist_agv_to_relay / 1000 * 3.0

            dist_relay_to_end = self._distance(relay_point, end_point)
            dist_end_to_depot = self._distance(end_point, depot_pos)
            total_uav_distance = dist_relay_to_end + dist_end_to_depot

            time_cost = total_uav_distance / getattr(uav, 'max_speed', 10) / 60
            uav_energy = total_uav_distance / 1000 * getattr(
                self.energy_model, 'cruise_energy_per_km', 5.0
            ) if self.energy_model else total_uav_distance / 1000 * 5.0

            wait_penalty = 5.0
            fallback_risk = 0.3

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
            cost_breakdown=cost_breakdown
        )

    def _distance(self, p1: Tuple[float, float], p2: Tuple[float, float]) -> float:
        return math.sqrt((p1[0] - p2[0])**2 + (p1[1] - p2[1])**2)

    def get_cost_weights(self) -> Dict[str, float]:
        """Get cost weights."""
        return self._cost_weights.copy()
