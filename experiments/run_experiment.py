import argparse
import random
import yaml
import os

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
    parser.add_argument("--config", help="Configuration file path")
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

    # 从配置文件加载参数（如果提供）
    config = {}
    if args.config:
        config_path = args.config
        if not os.path.isabs(config_path):
            # 相对路径相对于 experiments 目录
            config_path = os.path.join(os.path.dirname(__file__), config_path)
        
        if os.path.exists(config_path):
            with open(config_path, 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f)
            print(f"Loaded configuration from: {config_path}")
        else:
            print(f"Warning: Configuration file not found: {config_path}")

    # 命令行参数覆盖配置文件参数
    experiment_name = args.experiment_name or config.get('experiment_name', 'default_experiment')
    num_uavs = args.num_uavs if args.num_uavs is not None else config.get('num_uavs', 2)
    num_agvs = args.num_agvs if args.num_agvs is not None else config.get('num_agvs', 2)
    num_tasks = args.num_tasks if args.num_tasks is not None else config.get('num_tasks', 3)
    max_steps = args.max_steps if args.max_steps is not None else config.get('max_steps', 50)
    strategy_type = args.strategy or config.get('strategy', 'baseline_direct')
    seed = args.seed if args.seed is not None else config.get('seed', 42)

    run_experiment(
        experiment_name=experiment_name,
        num_uavs=num_uavs,
        num_agvs=num_agvs,
        num_tasks=num_tasks,
        max_steps=max_steps,
        strategy_type=strategy_type,
        seed=seed,
    )


if __name__ == "__main__":
    main()
