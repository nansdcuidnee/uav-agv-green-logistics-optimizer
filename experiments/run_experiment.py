import argparse
import random

from config.config import AGV_MAX_BATTERY, MAP_SIZE, UAV_MAX_BATTERY
from src.core.agv import AGV
from src.core.uav import UAV
from src.energy.energy_model import EnergyModel
from src.planning.path_planner import PathPlanner
from src.scheduling.scheduler import Scheduler
from src.simulation.environment import Environment
from src.simulation.simulator import Simulator


def run_experiment(
    experiment_name: str,
    num_uavs: int = 2,
    num_agvs: int = 2,
    num_tasks: int = 3,
    max_steps: int = 50,
    strategy_type: str = "baseline_direct",
    seed: int = 42,
):
    """Run one simulation experiment with deterministic setup."""
    random.seed(seed)

    print(f"Running experiment: {experiment_name}")
    print(
        f"strategy={strategy_type}, seed={seed}, "
        f"uavs={num_uavs}, agvs={num_agvs}, tasks={num_tasks}, max_steps={max_steps}"
    )

    environment = Environment(map_size=MAP_SIZE)

    from src.utils.math_utils import generate_random_point

    for i in range(num_uavs):
        position = generate_random_point(MAP_SIZE)
        uav = UAV(i + 1, position)
        uav.battery = UAV_MAX_BATTERY
        environment.uavs.append(uav)

    for i in range(num_agvs):
        position = generate_random_point(MAP_SIZE)
        agv = AGV(i + 1, position)
        agv.charging_power = AGV_MAX_BATTERY * 2
        environment.agvs.append(agv)

    environment.generate_tasks(num_tasks, seed=seed)

    simulator = Simulator(
        environment=environment,
        energy_model=EnergyModel(),
        path_planner=PathPlanner(),
        scheduler=Scheduler(),
        strategy_type=strategy_type,
    )

    output_dir = simulator.run(max_steps=max_steps, experiment_name=experiment_name)
    print(f"Experiment completed. Results saved to: {output_dir}")
    return output_dir


def _build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run UAV-AGV experiment.")
    parser.add_argument("--experiment-name", default="default_experiment")
    parser.add_argument("--num-uavs", type=int, default=2)
    parser.add_argument("--num-agvs", type=int, default=2)
    parser.add_argument("--num-tasks", type=int, default=3)
    parser.add_argument("--max-steps", type=int, default=50)
    parser.add_argument(
        "--strategy",
        default="baseline_direct",
        choices=["baseline_direct", "relay_coop", "energy_priority"],
    )
    parser.add_argument("--seed", type=int, default=42)
    return parser


def main() -> None:
    parser = _build_arg_parser()
    args = parser.parse_args()

    run_experiment(
        experiment_name=args.experiment_name,
        num_uavs=args.num_uavs,
        num_agvs=args.num_agvs,
        num_tasks=args.num_tasks,
        max_steps=args.max_steps,
        strategy_type=args.strategy,
        seed=args.seed,
    )


if __name__ == "__main__":
    main()
