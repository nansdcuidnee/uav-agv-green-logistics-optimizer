import pytest
from src.strategies.baseline_direct import BaselineDirectStrategy
from src.strategies.relay_coop import RelayCoopStrategy
from src.strategies.energy_priority import EnergyPriorityStrategy
from src.core.uav import UAV
from src.core.agv import AGV
from src.simulation.environment import Environment


def test_baseline_direct_strategy_assign_tasks():
    """测试基线直送策略的任务分配"""
    strategy = BaselineDirectStrategy()
    environment = Environment()
    
    # 添加 UAV 和任务
    uav1 = UAV(uav_id=1, position=(0, 0))
    uav2 = UAV(uav_id=2, position=(100, 100))
    environment.uavs = [uav1, uav2]
    
    # 生成任务
    environment.generate_tasks(2, seed=42)
    
    # 测试任务分配
    result = strategy.assign_tasks(environment)
    assert isinstance(result, dict)
    assert 'assignments' in result
    assert len(result['assignments']) > 0


def test_baseline_direct_strategy_select_charging_station():
    """测试基线直送策略的充电站选择"""
    strategy = BaselineDirectStrategy()
    environment = Environment()
    
    # 添加 UAV 和 AGV
    uav = UAV(uav_id=1, position=(0, 0))
    agv = AGV(agv_id=1, position=(10, 10))
    environment.agvs = [agv]
    
    # 测试充电站选择
    selected_agv = strategy.select_charging_station(uav, environment)
    assert selected_agv is not None
    assert selected_agv.id == 1


def test_relay_coop_strategy_assign_tasks():
    """测试协同中继策略的任务分配"""
    strategy = RelayCoopStrategy()
    environment = Environment()
    
    # 添加 UAV 和 AGV
    uav = UAV(uav_id=1, position=(0, 0))
    agv = AGV(agv_id=1, position=(50, 50))
    environment.uavs = [uav]
    environment.agvs = [agv]
    
    # 生成任务
    environment.generate_tasks(1, seed=42)
    
    # 测试任务分配
    result = strategy.assign_tasks(environment)
    assert isinstance(result, dict)
    assert 'assignments' in result
    assert len(result['assignments']) > 0


def test_energy_priority_strategy_assign_tasks():
    """测试能耗优先策略的任务分配"""
    strategy = EnergyPriorityStrategy()
    environment = Environment()
    
    # 添加 UAV
    uav1 = UAV(uav_id=1, position=(0, 0))
    uav2 = UAV(uav_id=2, position=(100, 100))
    environment.uavs = [uav1, uav2]
    
    # 生成任务
    environment.generate_tasks(2, seed=42)
    
    # 测试任务分配
    result = strategy.assign_tasks(environment)
    assert isinstance(result, dict)
    assert 'assignments' in result
    assert len(result['assignments']) > 0