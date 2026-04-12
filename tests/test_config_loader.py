import os
import pytest
from main import load_config


def test_config_inheritance():
    """测试配置继承和深合并"""
    # 测试场景配置继承
    config_path = os.path.join('configs', 'scene_large.yaml')
    config = load_config(config_path)
    
    # 验证继承的基础配置
    assert config['map_size']['width'] == 2000
    assert config['map_size']['height'] == 2000
    assert config['num_tasks'] == 50
    assert config['num_uavs'] == 10
    assert config['num_agvs'] == 5
    
    # 验证继承的默认值
    assert 'task_density' in config
    assert 'time_window' in config
    assert 'obstacles' in config
    
    # 验证深合并
    assert config['obstacles']['types'] == ['building', 'tree', 'wall', 'tower']
    assert config['seed'] == 44


def test_config_compatibility():
    """测试 count 与 num 字段兼容"""
    # 测试场景配置中的 obstacles.count 字段
    config_path = os.path.join('configs', 'scene_small.yaml')
    config = load_config(config_path)
    
    # 验证障碍物配置
    assert 'obstacles' in config
    assert config['obstacles']['count'] == 5


def test_circular_inheritance(tmp_path):
    """测试循环继承"""
    # 创建临时循环继承配置文件
    temp_config1 = tmp_path / 'temp_config1.yaml'
    temp_config2 = tmp_path / 'temp_config2.yaml'
    
    # 创建循环引用的配置文件
    temp_config1.write_text('extends: temp_config2.yaml\nkey1: value1\n')
    temp_config2.write_text('extends: temp_config1.yaml\nkey2: value2\n')
    
    # 测试循环继承是否抛出异常
    with pytest.raises(ValueError, match="循环继承 detected"):
        load_config(str(temp_config1))


def test_no_extends():
    """测试没有 extends 的配置文件"""
    # 测试基础配置文件
    config_path = os.path.join('configs', 'base.yaml')
    config = load_config(config_path)
    
    # 验证配置加载
    assert 'map_size' in config
    assert 'num_tasks' in config
    assert 'num_uavs' in config
    assert 'num_agvs' in config
    assert 'task_density' in config
    assert 'obstacles' in config
    assert 'num_no_fly_zones' in config
    assert 'time_window' in config
    assert 'seed' in config
