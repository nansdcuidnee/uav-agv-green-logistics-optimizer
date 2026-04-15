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
    if 'environment' in config and 'map_size' in config['environment']:
        map_size = tuple(config['environment']['map_size'])
    elif 'map_size' in config:
        map_size = (config['map_size']['width'], config['map_size']['height'])
    else:
        map_size = (1000, 1000)  # 默认值
    
    env = Environment(map_size=map_size)
    
    # 设置随机种子，确保可复现性
    seed = config.get('seed')
    if seed is not None:
        import random
        random.seed(seed)
    
    # 检查是否有显式定义的 uavs、agvs、tasks
    if 'uavs' in config and 'agvs' in config and 'tasks' in config:
        # 使用配置文件中显式定义的 UAV、AGV 和任务
        from src.core.uav import UAV
        from src.core.agv import AGV
        from src.core.task import Task
        
        # 清空默认生成的列表
        env.tasks = []
        env.uavs = []
        env.agvs = []
        
        # 添加 UAVs
        for uav_config in config['uavs']:
            uav = UAV(
                id=uav_config['id'],
                position=tuple(uav_config['position']),
                max_payload=uav_config.get('max_payload', 5.0),
                battery=uav_config.get('battery_capacity', 100.0)
            )
            env.uavs.append(uav)
        
        # 添加 AGVs
        for agv_config in config['agvs']:
            agv = AGV(
                id=agv_config['id'],
                position=tuple(agv_config['position'])
            )
            env.agvs.append(agv)
        
        # 添加任务
        for task_config in config['tasks']:
            task = Task(
                id=task_config['id'],
                start_point=tuple(task_config['start_point']),
                end_point=tuple(task_config['end_point']),
                payload=task_config.get('payload', 1.0),
                priority=task_config.get('priority', 1)
            )
            env.tasks.append(task)
    else:
        # 使用原来的方式生成场景
        scenario_config = {
            'num_tasks': config.get('num_tasks', 5),
            'num_uavs': config.get('num_uavs', 2),
            'num_agvs': config.get('num_agvs', 2),
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
    
    # 确保环境对象具有所有必要的属性
    if not hasattr(env, 'current_time'):
        env.current_time = 0.0
    if not hasattr(env, 'seed'):
        env.seed = seed
    
    return env


def build_simulator(environment, strategy_type="baseline_direct", scenario_name="default", seed=42):
    """构建仿真器
    
    Args:
        environment: 环境对象
        strategy_type: 策略类型
        scenario_name: 场景名称
        seed: 随机种子
    
    Returns:
        Simulator: 仿真器对象
    """
    return Simulator(
        environment=environment,
        energy_model=EnergyModel(),
        path_planner=PathPlanner(),
        scheduler=Scheduler(),
        strategy_type=strategy_type,
        scenario_name=scenario_name,
        seed=seed,
    )
