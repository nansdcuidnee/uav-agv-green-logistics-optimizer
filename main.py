import yaml
import os
import argparse

from src.utils.simulator_helper import build_environment, build_simulator


def deep_merge(base, override):
    """深合并两个字典
    
    Args:
        base: 基础字典
        override: 覆盖字典
    
    Returns:
        dict: 合并后的字典
    """
    result = base.copy()
    for key, value in override.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = deep_merge(result[key], value)
        else:
            result[key] = value
    return result


def load_config(config_path, visited=None):
    """加载场景配置文件，支持继承
    
    Args:
        config_path: 配置文件路径
        visited: 已访问的配置文件路径，用于检测循环继承
    
    Returns:
        dict: 配置信息
    """
    if visited is None:
        visited = set()
    
    # 检测循环继承
    if config_path in visited:
        raise ValueError(f"循环继承 detected: {config_path}")
    visited.add(config_path)
    
    # 加载当前配置
    with open(config_path, 'r', encoding='utf-8') as f:
        config = yaml.safe_load(f)
    
    # 处理继承
    if 'extends' in config:
        extends_path = config['extends']
        # 构建继承文件的完整路径
        extends_full_path = os.path.join(os.path.dirname(config_path), extends_path)
        # 递归加载父配置
        parent_config = load_config(extends_full_path, visited.copy())
        # 深合并配置（子配置覆盖父配置）
        config = deep_merge(parent_config, config)
        # 移除 extends 字段
        del config['extends']
    
    return config


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
    max_steps = config.get('max_steps', 600)
    
    output_dir = simulator.run(max_steps=max_steps, experiment_name=experiment_name)
    return output_dir


def _build_arg_parser() -> argparse.ArgumentParser:
    """构建命令行参数解析器"""
    parser = argparse.ArgumentParser(description="运行 UAV-AGV 仿真")
    parser.add_argument("--config", default="configs/scene_large.yaml", help="配置文件路径")
    parser.add_argument("--strategy", help="策略类型")
    parser.add_argument("--max-steps", type=int, help="最大仿真步数")
    return parser


def main():
    """主函数"""
    # 解析命令行参数
    parser = _build_arg_parser()
    args = parser.parse_args()
    
    config_file = args.config
    
    if os.path.exists(config_file):
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
    else:
        print(f"配置文件不存在: {config_file}")


if __name__ == "__main__":
    main()
