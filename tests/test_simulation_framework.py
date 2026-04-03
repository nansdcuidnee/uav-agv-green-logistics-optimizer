import pytest
import os
from src.simulation.simulator import Simulator
from src.simulation.environment import Environment
from src.core.uav import UAV
from src.core.agv import AGV
from src.energy.energy_model import EnergyModel
from src.planning.path_planner import PathPlanner
from src.scheduling.scheduler import Scheduler


def test_simulator_initialization():
    """测试模拟器初始化"""
    # 创建环境
    environment = Environment()
    
    # 添加 UAV 和 AGV
    uav1 = UAV(uav_id=1, position=(0, 0))
    uav2 = UAV(uav_id=2, position=(100, 100))
    agv1 = AGV(agv_id=1, position=(50, 50))
    agv2 = AGV(agv_id=2, position=(150, 150))
    environment.uavs = [uav1, uav2]
    environment.agvs = [agv1, agv2]
    
    # 生成任务
    environment.generate_tasks(2, seed=42)
    
    # 初始化模拟器
    energy_model = EnergyModel()
    path_planner = PathPlanner()
    scheduler = Scheduler()
    
    simulator = Simulator(
        environment=environment,
        energy_model=energy_model,
        path_planner=path_planner,
        scheduler=scheduler,
        strategy_type="baseline_direct"
    )
    
    assert simulator is not None
    assert simulator.environment == environment


def test_simulator_step():
    """测试模拟器单步执行"""
    # 创建环境
    environment = Environment()
    
    # 添加 UAV 和 AGV
    uav = UAV(uav_id=1, position=(0, 0))
    agv = AGV(agv_id=1, position=(50, 50))
    environment.uavs = [uav]
    environment.agvs = [agv]
    
    # 生成任务
    environment.generate_tasks(1, seed=42)
    
    # 初始化模拟器
    energy_model = EnergyModel()
    path_planner = PathPlanner()
    scheduler = Scheduler()
    
    simulator = Simulator(
        environment=environment,
        energy_model=energy_model,
        path_planner=path_planner,
        scheduler=scheduler,
        strategy_type="baseline_direct"
    )
    
    # 测试单步执行
    energy = simulator.step()
    assert isinstance(energy, float)
    assert energy >= 0