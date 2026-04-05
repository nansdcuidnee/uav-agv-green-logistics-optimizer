import pytest
from src.energy.energy_model import EnergyModel
from src.core.uav import UAV


def test_energy_model_compute():
    """测试能耗模型计算"""
    energy_model = EnergyModel()
    uav = UAV(uav_id=1, position=(0, 0))
    
    # 测试基本计算
    energy = energy_model.compute(uav)
    assert isinstance(energy, float)
    assert energy >= 0


def test_energy_model_compute_with_payload():
    """测试带负载的能耗计算"""
    energy_model = EnergyModel()
    uav = UAV(uav_id=1, position=(0, 0))
    
    # 创建一个任务对象模拟负载
    class MockTask:
        def __init__(self):
            self.payload = 5
    
    uav.task = MockTask()
    energy = energy_model.compute(uav)
    assert isinstance(energy, float)
    assert energy >= 0