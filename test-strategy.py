from src.strategy.charging_strategy import ChargingStrategy, ChargingStation
from src.core.uav import UAV
from src.core.agv import AGV

# 创建示例数据

# 1. 创建需要充电的无人机（电量低于20%）
uavs = [
    UAV(1, (100, 100)),  # ID: 1, 位置: (100, 100)
    UAV(2, (200, 200)),  # ID: 2, 位置: (200, 200)
    UAV(3, (300, 300))   # ID: 3, 位置: (300, 300)
]

# 设置无人机电量，展示不同充电方式
uavs[0].update_battery(-90)  # UAV 1: 电量10%，触发移动充电
uavs[1].update_battery(-70)  # UAV 2: 电量30%，可能触发固定充电
uavs[2].update_battery(-60)  # UAV 3: 电量40%，可能触发固定充电

# 2. 创建AGV
agvs = [
    AGV(1, (150, 150)),  # ID: 1, 位置: (150, 150)
    AGV(2, (250, 250))   # ID: 2, 位置: (250, 250)
]

# 3. 创建固定充电站
charging_stations = [
    ChargingStation(1, (50, 50)),    # ID: 1, 位置: (50, 50)
    ChargingStation(2, (400, 400))   # ID: 2, 位置: (400, 400)
]

# 4. 创建任务（可选）
tasks = []

# 创建充电策略并启用可视化
charging_strategy = ChargingStrategy(mode="smart", enable_visualization=True)

# 执行充电策略，可视化窗口会自动显示
charging_strategy.smart_charging(uavs, charging_stations, agvs, tasks)