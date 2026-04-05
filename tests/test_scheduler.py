import pytest
from src.scheduling.scheduler import Scheduler
from src.core.uav import UAV
from src.core.agv import AGV


def test_scheduler_select_agv():
    """测试调度器选择 AGV"""
    scheduler = Scheduler()
    uav = UAV(uav_id=1, position=(0, 0))
    agv1 = AGV(agv_id=1, position=(10, 10))
    agv2 = AGV(agv_id=2, position=(20, 20))
    agvs = [agv1, agv2]
    
    selected_agv = scheduler.select_agv(uav, agvs)
    assert selected_agv is not None
    assert selected_agv.id in [1, 2]


def test_scheduler_select_agv_empty():
    """测试调度器在没有 AGV 时的行为"""
    scheduler = Scheduler()
    uav = UAV(uav_id=1, position=(0, 0))
    agvs = []
    
    selected_agv = scheduler.select_agv(uav, agvs)
    assert selected_agv is None