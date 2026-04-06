import yaml
import os

from src.simulation.environment import Environment
from src.utils.result_generator import ResultGenerator


def load_config(config_path):
    """加载场景配置文件
    
    Args:
        config_path: 配置文件路径
    
    Returns:
        dict: 配置信息
    """
    with open(config_path, 'r', encoding='utf-8') as f:
        config = yaml.safe_load(f)
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
    env.generate_scenario({
        'num_tasks': config['num_tasks'],
        'num_uavs': config['num_uavs'],
        'num_agvs': config['num_agvs'],
        'num_obstacles': config['obstacles']['num'],
        'num_no_fly_zones': config.get('num_no_fly_zones', 0),
        'seed': config.get('seed')
    })
    
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
        result_generator = ResultGenerator(env)
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
