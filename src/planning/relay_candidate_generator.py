"""Relay candidate point generator.

Pickup-delivery model:
- Candidates based on task.start_point -> task.end_point corridor
- UAV flies: relay -> start -> end -> relay

Candidate sources:
1. AGV current position
2. task.start_point
3. task.end_point
4. Corridor key points (25%, 50%, 75%)
5. AGV projection onto corridor line segment

All candidates must be bound to an AGV and validated.
"""

import math
from typing import Any, List, Optional, Tuple


class RelayCandidateGenerator:
    """Generator for relay candidate points."""

    @staticmethod
    def generate_candidates_for_agv(
        uav,
        task,
        agv,
        environment,
        depot_pos: Tuple[float, float] = None
    ) -> List[Tuple[float, float]]:
        """Generate all valid relay candidates for a specific AGV.

        Returns a list of all feasible relay points for the given AGV,
        based on pickup-delivery corridor.
        """
        start_point = task.start_point
        end_point = task.end_point
        candidates = []

        if RelayCandidateGenerator.is_valid_candidate(agv.position, uav, task, environment):
            candidates.append(agv.position)

        if RelayCandidateGenerator.is_valid_candidate(start_point, uav, task, environment):
            candidates.append(start_point)

        if RelayCandidateGenerator.is_valid_candidate(end_point, uav, task, environment):
            candidates.append(end_point)

        for ratio in [0.25, 0.50, 0.75]:
            x = start_point[0] + ratio * (end_point[0] - start_point[0])
            y = start_point[1] + ratio * (end_point[1] - start_point[1])
            candidate = (x, y)
            if RelayCandidateGenerator.is_valid_candidate(candidate, uav, task, environment):
                candidates.append(candidate)

        projection = RelayCandidateGenerator._project_point_to_segment(
            agv.position, start_point, end_point
        )
        if RelayCandidateGenerator.is_valid_candidate(projection, uav, task, environment):
            candidates.append(projection)

        seen = set()
        unique = []
        for c in candidates:
            key = (round(c[0], 1), round(c[1], 1))
            if key not in seen:
                seen.add(key)
                unique.append(c)

        return unique

    @staticmethod
    def generate_for_agv(
        uav,
        task,
        agv,
        environment,
        depot_pos: Tuple[float, float] = None
    ) -> Optional[Tuple[float, float]]:
        """Generate best relay candidate for a specific AGV (legacy compatibility).

        Returns the relay point with minimum cost:
        score = dist(agv, point) + dist(point, start) + dist(start, end) + dist(end, point)
        """
        candidates = RelayCandidateGenerator.generate_candidates_for_agv(
            uav, task, agv, environment, depot_pos
        )

        if not candidates:
            return None

        def cost(p):
            return (
                RelayCandidateGenerator._distance(agv.position, p) +
                RelayCandidateGenerator._distance(p, task.start_point) +
                RelayCandidateGenerator._distance(task.start_point, task.end_point) +
                RelayCandidateGenerator._distance(task.end_point, p)
            )

        return min(candidates, key=cost)

    @staticmethod
    def generate_bound_candidates(
        uav,
        task,
        environment,
        depot_pos: Tuple[float, float] = None
    ) -> List[Tuple[Tuple[float, float], Any]]:
        """Generate all valid relay candidates with bound AGVs.

        Returns all (relay_point, agv) combinations, not just one per AGV.
        """
        candidates = []
        available_agvs = [
            agv for agv in environment.agvs
            if getattr(agv, 'status', 'idle') == 'idle'
        ]

        if not available_agvs:
            return []

        for agv in available_agvs:
            agv_candidates = RelayCandidateGenerator.generate_candidates_for_agv(
                uav, task, agv, environment, depot_pos
            )
            for relay_point in agv_candidates:
                candidates.append((relay_point, agv))

        return candidates

    @staticmethod
    def is_valid_candidate(point, uav, task, environment) -> bool:
        """Check if a point is a valid relay candidate.

        Pickup-delivery model:
        UAV flies: uav_current -> relay -> start -> end -> relay

        Validation conditions:
        1. Position is valid (not in obstacle/no-fly zone)
        2. UAV can fly from current position to relay point
        3. After reaching relay, UAV still has enough range to complete delivery
        4. Total range requirement does not exceed remaining battery
        5. Optional: deadline/slack check if available
        """
        if not environment.is_valid_position(point):
            return False

        start_point = task.start_point
        end_point = task.end_point

        uav_current_pos = uav.position if hasattr(uav, 'position') else (0.0, 0.0)

        dist_uav_to_relay = RelayCandidateGenerator._distance(uav_current_pos, point)
        dist_relay_to_start = RelayCandidateGenerator._distance(point, start_point)
        dist_start_to_end = RelayCandidateGenerator._distance(start_point, end_point)
        dist_end_to_relay = RelayCandidateGenerator._distance(end_point, point)

        delivery_range = dist_relay_to_start + dist_start_to_end + dist_end_to_relay
        total_required_range = dist_uav_to_relay + delivery_range

        max_range = getattr(uav, 'max_range', 500)
        remaining_range = uav.battery * max_range / 100.0

        if total_required_range > remaining_range:
            return False

        remaining_after_relay = remaining_range - dist_uav_to_relay
        if remaining_after_relay < delivery_range:
            return False

        deadline = getattr(task, 'deadline', None)
        if deadline is not None:
            uav_speed = getattr(uav, 'max_speed', 10.0)
            total_time = total_required_range / uav_speed
            if total_time > deadline:
                return False

        return True

    @staticmethod
    def _distance(p1: Tuple[float, float], p2: Tuple[float, float]) -> float:
        """Calculate Euclidean distance."""
        return math.sqrt((p1[0] - p2[0])**2 + (p1[1] - p2[1])**2)

    @staticmethod
    def _project_point_to_segment(
        point: Tuple[float, float],
        seg_start: Tuple[float, float],
        seg_end: Tuple[float, float]
    ) -> Tuple[float, float]:
        """Project a point onto a line segment.

        If projection falls outside segment, clamp to nearest endpoint.
        """
        px, py = point
        x1, y1 = seg_start
        x2, y2 = seg_end

        dx = x2 - x1
        dy = y2 - y1

        if dx == 0 and dy == 0:
            return seg_start

        t = max(0.0, min(1.0, ((px - x1) * dx + (py - y1) * dy) / (dx * dx + dy * dy)))

        proj_x = x1 + t * dx
        proj_y = y1 + t * dy

        return (proj_x, proj_y)
