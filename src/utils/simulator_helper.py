"""仿真器构建辅助模块"""
from src.simulation.environment import Environment
from src.simulation.simulator import Simulator
from src.energy.energy_model import EnergyModel
from src.planning.path_planner import PathPlanner
from src.scheduling.scheduler import Scheduler


def build_environment(config):
    """构建环境
    
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
    
    return env


def build_simulator(environment, strategy_type="baseline_direct"):
    """构建仿真器
    
    Args:
        environment: 环境对象
        strategy_type: 策略类型
    
    Returns:
        Simulator: 仿真器对象
    """
    return Simulator(
        environment=environment,
        energy_model=EnergyModel(),
        path_planner=PathPlanner(),
        scheduler=Scheduler(),
        strategy_type=strategy_type,
    )
