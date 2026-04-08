#!/usr/bin/env python3
"""数据加载示例"""
from src.utils.data_loader import load_data

if __name__ == "__main__":
    print("=== 数据加载示例 ===\n")
    
    # 加载场景配置
    print("1. 加载场景配置 (scenarios/example_scenario.yaml):")
    scenario_data = load_data('scenarios', 'example_scenario.yaml')
    print(f"   场景描述: {scenario_data.get('description')}")
    print(f"   任务数量: {scenario_data.get('num_tasks')}")
    print(f"   UAV数量: {scenario_data.get('num_uavs')}")
    print(f"   AGV数量: {scenario_data.get('num_agvs')}")
    print(f"   障碍物数量: {scenario_data.get('obstacles', {}).get('count')}")
    print(f"   障碍物类型: {scenario_data.get('obstacles', {}).get('types')}")
    print(f"   任务密度: {scenario_data.get('task_density')}")
    print(f"   禁飞区数量: {scenario_data.get('num_no_fly_zones')}")
    print(f"   时间窗口: {scenario_data.get('time_window')}")
    print(f"   随机种子: {scenario_data.get('seed')}")
    
    print("\n2. 加载设备参数 (constants/device_params.yaml):")
    device_params = load_data('constants', 'device_params.yaml')
    print(f"   UAV 速度: {device_params.get('uav', {}).get('speed')}")
    print(f"   UAV 最大电量: {device_params.get('uav', {}).get('max_battery')}")
    print(f"   AGV 速度: {device_params.get('agv', {}).get('speed')}")
    print(f"   AGV 最大电量: {device_params.get('agv', {}).get('max_battery')}")
    
    print("\n3. 加载地图配置 (maps/example_map.yaml):")
    map_data = load_data('maps', 'example_map.yaml')
    print(f"   地图尺寸: {map_data.get('map_size')}")
    print(f"   障碍物数量: {map_data.get('obstacles', {}).get('count')}")
    
    print("\n4. 加载任务模板 (templates/task_template.yaml):")
    task_template = load_data('templates', 'task_template.yaml')
    print(f"   任务类型: {task_template.get('task_type')}")
    print(f"   优先级: {task_template.get('priority')}")
    print(f"   负载: {task_template.get('payload')}")
    
    print("\n=== 示例完成 ===")
