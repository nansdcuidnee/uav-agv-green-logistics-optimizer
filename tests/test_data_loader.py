#!/usr/bin/env python3
"""数据加载器测试"""
import pytest
from pathlib import Path
from src.utils.data_loader import (
    get_data_root,
    resolve_data_path,
    load_yaml,
    load_json,
    load_data
)


def test_get_data_root():
    """测试获取数据根目录"""
    data_root = get_data_root()
    assert isinstance(data_root, Path)
    assert data_root.name == "data"
    assert data_root.exists()


def test_resolve_data_path():
    """测试解析数据文件路径"""
    # 测试存在的文件
    map_path = resolve_data_path("maps", "example_map.yaml")
    assert isinstance(map_path, Path)
    assert map_path.exists()
    assert map_path.name == "example_map.yaml"
    
    # 测试不存在的文件
    with pytest.raises(FileNotFoundError):
        resolve_data_path("maps", "non_existent_file.yaml")


def test_load_yaml():
    """测试加载 YAML 文件"""
    # 测试通过类别和文件名加载
    data = load_yaml("scenarios", "example_scenario.yaml")
    assert isinstance(data, dict)
    assert "num_tasks" in data
    assert "num_uavs" in data
    assert "num_agvs" in data
    
    # 测试通过完整路径加载
    scenario_path = resolve_data_path("scenarios", "example_scenario.yaml")
    data2 = load_yaml(scenario_path)
    assert data == data2
    
    # 测试不支持的文件格式（使用临时文件）
    import tempfile
    with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
        f.write("test")
        temp_txt_path = f.name
    
    try:
        with pytest.raises(ValueError):
            load_yaml(temp_txt_path)
    finally:
        import os
        if os.path.exists(temp_txt_path):
            os.unlink(temp_txt_path)


def test_load_json():
    """测试加载 JSON 文件"""
    # 创建临时 JSON 文件用于测试
    import json
    import tempfile
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        json.dump({"test": "value"}, f)
        temp_json_path = f.name
    
    try:
        # 测试加载 JSON 文件
        data = load_json(temp_json_path)
        assert isinstance(data, dict)
        assert data["test"] == "value"
        
        # 测试不支持的文件格式
        with pytest.raises(ValueError):
            load_json("scenarios", "example_scenario.yaml")
    finally:
        import os
        if os.path.exists(temp_json_path):
            os.unlink(temp_json_path)


def test_load_data():
    """测试自动加载数据文件"""
    # 测试加载 YAML 文件
    data = load_data("scenarios", "example_scenario.yaml")
    assert isinstance(data, dict)
    assert "num_tasks" in data
    
    # 测试不支持的文件格式（使用临时文件）
    import tempfile
    with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
        f.write("test")
        temp_txt_path = f.name
    
    try:
        with pytest.raises(ValueError):
            load_data(temp_txt_path)
    finally:
        import os
        if os.path.exists(temp_txt_path):
            os.unlink(temp_txt_path)


def test_file_not_found():
    """测试文件不存在的情况"""
    # 测试不存在的类别
    with pytest.raises(FileNotFoundError):
        resolve_data_path("non_existent_category", "example.yaml")
    
    # 测试不存在的文件
    with pytest.raises(FileNotFoundError):
        load_data("maps", "non_existent_file.yaml")
