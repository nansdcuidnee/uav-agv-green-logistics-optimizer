"""Relay candidate point generator.

Candidate sources:
1. AGV current position
2. Key points on depot->end_line (25%, 50%, 75%)
3. Boundary points around end_point based on UAV range

All candidates must be bound to an AGV and validated.
"""

import math
from typing import Any, List, Optional, Tuple


class RelayCandidateGenerator:
    """Generator for relay candidate points."""

    @staticmethod
    def generate_for_agv(
        uav,
        task,
        agv,
        environment,
        depot_pos: Tuple[float, float]
    ) -> Optional[Tuple[float, float]]:
        """Generate best relay candidate for a specific AGV."""
        end_point = task.end_point
        candidates = []

        candidates.append(agv.position)

        for ratio in [0.25, 0.50, 0.75]:
            x = depot_pos[0] + ratio * (end_point[0] - depot_pos[0])
            y = depot_pos[1] + ratio * (end_point[1] - depot_pos[1])
            candidate = (x, y)
            if RelayCandidateGenerator.is_valid_candidate(candidate, uav, task, environment):
                candidates.append(candidate)

        remaining_range = uav.battery * getattr(uav, 'max_range', 500) / 100.0
        for dx, dy in [(1, 0), (-1, 0), (0, 1), (0, -1)]:
            boundary_x = end_point[0] + dx * remaining_range / 2
            boundary_y = end_point[1] + dy * remaining_range / 2
            boundary = (boundary_x, boundary_y)
            if RelayCandidateGenerator.is_valid_candidate(boundary, uav, task, environment):
                candidates.append(boundary)

        seen = set()
        unique = []
        for c in candidates:
            key = (round(c[0], 1), round(c[1], 1))
            if key not in seen:
                seen.add(key)
                unique.append(c)

        if not unique:
            return None

        return min(unique, key=lambda p: RelayCandidateGenerator._distance(p, end_point))

    @staticmethod
    def generate_bound_candidates(
        uav,
        task,
        environment,
        depot_pos: Tuple[float, float]
    ) -> List[Tuple[Tuple[float, float], Any]]:
        """Generate relay candidates with bound AGVs."""
        candidates = []
        available_agvs = [
            agv for agv in environment.agvs
            if getattr(agv, 'status', 'idle') == 'idle'
        ]

        if not available_agvs:
            return []

        for agv in available_agvs:
            relay_point = RelayCandidateGenerator.generate_for_agv(
                uav, task, agv, environment, depot_pos
            )
            if relay_point and RelayCandidateGenerator.is_valid_candidate(
                relay_point, uav, task, environment
            ):
                candidates.append((relay_point, agv))

        return candidates

    @staticmethod
    def is_valid_candidate(point, uav, task, environment) -> bool:
        """Check if a point is a valid relay candidate."""
        if not environment.is_valid_position(point):
            return False

        required_range = 2 * RelayCandidateGenerator._distance(point, task.end_point)
        max_range = getattr(uav, 'max_range', 500)
        remaining_range = uav.battery * max_range / 100.0

        return required_range <= remaining_range

    @staticmethod
    def _distance(p1: Tuple[float, float], p2: Tuple[float, float]) -> float:
        """Calculate Euclidean distance."""
        return math.sqrt((p1[0] - p2[0])**2 + (p1[1] - p2[1])**2)
