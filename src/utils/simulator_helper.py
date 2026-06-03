"""仿真器构建辅助模块"""
import random
from config.config import UAV_INIT_BATTERY, AGV_INIT_BATTERY
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
    scene_type = config.get('scene_type', 'default')
    
    if scene_type == 'pickup_delivery_generated':
        return _build_pickup_delivery_generated(config)
    
    if 'environment' in config and 'map_size' in config['environment']:
        map_size = tuple(config['environment']['map_size'])
    elif 'map_size' in config:
        map_size = (config['map_size']['width'], config['map_size']['height'])
    else:
        map_size = (1000, 1000)
    
    env = Environment(map_size=map_size)
    
    seed = config.get('seed')
    if seed is not None:
        random.seed(seed)
    
    if 'uavs' in config and 'agvs' in config and 'tasks' in config:
        from src.core.uav import UAV
        from src.core.agv import AGV
        from src.core.task import Task
        
        env.tasks = []
        env.uavs = []
        env.agvs = []
        
        for uav_config in config['uavs']:
            uav = UAV(
                id=uav_config['id'],
                position=tuple(uav_config['position']),
                max_payload=uav_config.get('max_payload', 5.0),
                battery=uav_config.get('battery_capacity', UAV_INIT_BATTERY)
            )
            env.uavs.append(uav)
        
        for agv_config in config['agvs']:
            agv = AGV(
                id=agv_config['id'],
                position=tuple(agv_config['position'])
            )
            env.agvs.append(agv)
        
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
        scenario_config = {
            'num_tasks': config.get('num_tasks', 5),
            'num_uavs': config.get('num_uavs', 2),
            'num_agvs': config.get('num_agvs', 2),
            'obstacles': config.get('obstacles', {}),
            'num_no_fly_zones': config.get('num_no_fly_zones', 0),
            'seed': config.get('seed')
        }
        
        if 'task_density' in config:
            scenario_config['task_density'] = config['task_density']
        if 'time_window' in config:
            scenario_config['time_window'] = config['time_window']
        
        env.generate_scenario(scenario_config)
    
    if not hasattr(env, 'current_time'):
        env.current_time = 0.0
    if not hasattr(env, 'seed'):
        env.seed = seed
    
    return env


def _build_pickup_delivery_generated(config):
    """构建 pickup_delivery_generated 场景
    
    单总站模型：
    - UAV 初始位置在 depot
    - AGV 初始位置随机
    - 任务 start_point 和 end_point 随机
    - 中继点由算法运行时动态生成
    """
    from src.core.uav import UAV
    from src.core.agv import AGV
    from src.core.task import Task
    
    if 'map_size' in config:
        map_size = (config['map_size']['width'], config['map_size']['height'])
    else:
        map_size = (1000, 1000)
    
    env = Environment(map_size=map_size)
    
    seed = config.get('seed', 42)
    random.seed(seed)
    
    depot_position = config.get('depot_position', [100, 100])
    if isinstance(depot_position, list):
        depot_position = tuple(depot_position)
    
    num_uavs = config.get('num_uavs', 2)
    num_agvs = config.get('num_agvs', 2)
    num_tasks = config.get('num_tasks', 10)
    
    env.uavs = []
    for i in range(num_uavs):
        uav = UAV(
            id=i + 1,
            position=depot_position,
            max_payload=5.0,
            battery=UAV_INIT_BATTERY
        )
        env.uavs.append(uav)
    
    env.agvs = []
    for i in range(num_agvs):
        agv_x = random.uniform(50, map_size[0] - 50)
        agv_y = random.uniform(50, map_size[1] - 50)
        agv = AGV(
            id=i + 1,
            position=(agv_x, agv_y)
        )
        env.agvs.append(agv)
    
    env.tasks = []
    for i in range(num_tasks):
        start_x = random.uniform(50, map_size[0] - 50)
        start_y = random.uniform(50, map_size[1] - 50)
        end_x = random.uniform(50, map_size[0] - 50)
        end_y = random.uniform(50, map_size[1] - 50)
        
        task = Task(
            id=i + 1,
            start_point=(start_x, start_y),
            end_point=(end_x, end_y),
            payload=1.0,
            priority=1
        )
        env.tasks.append(task)
    
    env.current_time = 0.0
    env.seed = seed
    env.depot_position = depot_position
    
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
