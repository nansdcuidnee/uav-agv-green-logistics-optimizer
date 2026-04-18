import os
import argparse

from config.config_loader import load_config
from config.config import DEFAULT_SIMULATION_STEPS, MAX_SIMULATION_STEPS, RANDOM_SEED
from src.utils.simulator_helper import build_environment, build_simulator





def run_simulation(config, config_file=None):
    """运行仿真
    
    Args:
        config: 场景配置
        config_file: 配置文件路径
    
    Returns:
        str: 结果输出目录
    """
    # 构建环境
    env = build_environment(config)
    
    # 确定策略类型
    strategy_type = config.get('strategy', 'baseline_direct')
    
    # 构建仿真器
    simulator = build_simulator(env, strategy_type)
    
    # 确定实验名称
    if 'experiment_name' in config:
        experiment_name = config['experiment_name']
    elif config_file:
        # 从配置文件名推导实验名称
        experiment_name = os.path.splitext(os.path.basename(config_file))[0]
    else:
        experiment_name = 'default_experiment'
    
    # 确定最大步数
    max_steps = config.get('max_steps', DEFAULT_SIMULATION_STEPS)
    # 裁剪max_steps到最大限制
    max_steps = min(max_steps, MAX_SIMULATION_STEPS)
    
    output_dir = simulator.run(max_steps=max_steps, experiment_name=experiment_name)
    return output_dir


def _build_arg_parser() -> argparse.ArgumentParser:
    """构建命令行参数解析器"""
    parser = argparse.ArgumentParser(description="运行 UAV-AGV 仿真")
    parser.add_argument("--config", default="configs/generated/scene_large.yaml", help="配置文件路径")
    parser.add_argument("--strategy", help="策略类型")
    parser.add_argument("--max-steps", type=int, help="最大仿真步数")
    return parser


def main():
    """主函数"""
    # 解析命令行参数
    parser = _build_arg_parser()
    args = parser.parse_args()
    
    config_file = args.config
    
    print(f"运行场景: {config_file}")
    # 加载配置
    config = load_config(config_file)
    
    # 命令行参数覆盖配置
    if args.strategy:
        config['strategy'] = args.strategy
    if args.max_steps is not None:
        config['max_steps'] = args.max_steps
    
    # 运行仿真
    output_dir = run_simulation(config, config_file)
    
    print(f"场景 {config_file} 运行完成")
    print(f"结果保存到: {output_dir}")
    print()


if __name__ == "__main__":
    main()
