#!/usr/bin/env python3
"""验证配置加载和仿真运行"""
import os
from main import load_config, run_simulation

if __name__ == "__main__":
    # 加载场景配置
    config_path = os.path.join('configs', 'scene_large.yaml')
    config = load_config(config_path)
    
    print("=== 加载 configs/scene_large.yaml 后的最终合并配置 ===")
    print(f"场景描述: {config.get('description')}")
    print(f"地图大小: {config.get('map_size')}")
    print(f"任务数量: {config.get('num_tasks')}")
    print(f"无人机数量: {config.get('num_uavs')}")
    print(f"AGV数量: {config.get('num_agvs')}")
    print(f"障碍物配置: {config.get('obstacles')}")
    print(f"禁飞区数量: {config.get('num_no_fly_zones')}")
    print(f"时间窗口: {config.get('time_window')}")
    print(f"随机种子: {config.get('seed')}")
    
    # 运行仿真
    print("\n=== 运行仿真 ===")
    env = run_simulation(config)
    
    # 打印障碍物数量
    print(f"\n=== 仿真结果 ===")
    print(f"生成的障碍物数量: {len(env.obstacles)}")
    print(f"任务数量: {len(env.tasks)}")
    print(f"UAV数量: {len(env.uavs)}")
    print(f"AGV数量: {len(env.agvs)}")
