import argparse
import random

from src.core.agv import AGV
from src.core.uav import UAV
from src.energy.energy_model import EnergyModel
from src.planning.path_planner import PathPlanner
from src.scheduling.scheduler import Scheduler
from src.simulation.environment import Environment
from src.simulation.simulator import Simulator


def run_once(
    strategy_type: str = "baseline_direct",
    seed: int = 42,
    num_uavs: int = 2,
    num_agvs: int = 1,
    num_tasks: int = 5,
    max_steps: int = 500,
    experiment_name: str = "main_experiment",
):
    """Run one deterministic simulation from the local main entrypoint."""
    random.seed(seed)

    environment = Environment(map_size=(1000, 1000))

    for i in range(num_uavs):
        environment.uavs.append(UAV(i + 1, (500, 500)))

    for i in range(num_agvs):
        environment.agvs.append(AGV(i + 1, (500, 500)))

    environment.generate_tasks(num_tasks, seed=seed)
    print(f"Generated {num_tasks} tasks.")

    simulator = Simulator(
        environment=environment,
        energy_model=EnergyModel(),
        path_planner=PathPlanner(),
        scheduler=Scheduler(),
        strategy_type=strategy_type,
    )

    output_dir = simulator.run(max_steps=max_steps, experiment_name=experiment_name)
    print(f"Results saved to: {output_dir}")
    return output_dir


def _build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run UAV-AGV simulation once.")
    parser.add_argument(
        "--strategy",
        default="baseline_direct",
        choices=["baseline_direct", "relay_coop", "energy_priority"],
    )
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--num-uavs", type=int, default=2)
    parser.add_argument("--num-agvs", type=int, default=1)
    parser.add_argument("--num-tasks", type=int, default=5)
    parser.add_argument("--max-steps", type=int, default=500)
    parser.add_argument("--experiment-name", default="main_experiment")
    return parser


def main() -> None:
    args = _build_arg_parser().parse_args()
    run_once(
        strategy_type=args.strategy,
        seed=args.seed,
        num_uavs=args.num_uavs,
        num_agvs=args.num_agvs,
        num_tasks=args.num_tasks,
        max_steps=args.max_steps,
        experiment_name=args.experiment_name,
    )


if __name__ == "__main__":
    main()
