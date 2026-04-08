import yaml
import os

from src.simulation.environment import Environment
from src.utils.result_bundle import ResultGenerator


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


def run_simulation(config):
    """运行仿真
    
    Args:
        config: 场景配置
    
    Returns:
        Environment: 环境对象
    """
    # 初始化环境
    map_size = (config['map_size']['width'], config['map_size']['height'])
    env = Environment(map_size=map_size)
    
    # 生成场景
    scenario_config = {
        'num_tasks': config['num_tasks'],
        'num_uavs': config['num_uavs'],
        'num_agvs': config['num_agvs'],
        'obstacles': config.get('obstacles', {}),
        'num_no_fly_zones': config.get('num_no_fly_zones', 0),
        'seed': config.get('seed')
    }
    
    # 添加额外配置项
    if 'task_density' in config:
        scenario_config['task_density'] = config['task_density']
    if 'time_window' in config:
        scenario_config['time_window'] = config['time_window']
    
    env.generate_scenario(scenario_config)
    
    # 运行仿真
    simulation_time = 600  # 10小时，延长仿真时间以观察任务完成情况
    time_step = 1.0  # 1分钟
    
    for _ in range(int(simulation_time / time_step)):
        env.update(time_step)
    
    return env


def main():
    """主函数"""
    # 场景配置文件路径
    config_file = 'configs/scene_large.yaml'  # 只运行一个场景
    
    if os.path.exists(config_file):
        print(f"运行场景: {config_file}")
        # 加载配置
        config = load_config(config_file)
        
        # 运行仿真
        env = run_simulation(config)
        
        # 生成结果
        print("正在生成可视化结果...")
        experiment_name = os.path.splitext(os.path.basename(config_file))[0]
        result_generator = ResultGenerator(env, experiment_name=experiment_name)
        result_paths = result_generator.generate_all()
        
        print(f"场景 {config_file} 运行完成")
        print("生成的文件:")
        for key, path in result_paths.items():
            if isinstance(path, list):
                for i, p in enumerate(path):
                    print(f"  - {key} {i+1}: {p}")
            else:
                print(f"  - {key}: {path}")
        print()
    else:
        print(f"配置文件不存在: {config_file}")


if __name__ == "__main__":
    main()
