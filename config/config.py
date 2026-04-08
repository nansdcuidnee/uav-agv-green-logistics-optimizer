# 系统配置文件

# 环境配置
MAP_SIZE = (200, 200)  # 地图尺寸

# 实验参数
NUM_POINTS = 5  # 配送点数量
NUM_UAV = 2  # 无人机数量
NUM_AGV = 2  # AGV数量
INIT_BATTERY = 40  # 初始电量
SIMULATION_STEPS = 50  # 模拟步数

# UAV配置
UAV_MAX_BATTERY = 100  # 最大电量
UAV_PAYLOAD_CAPACITY = 5  # 最大负载能力
UAV_SPEED = 10  # 飞行速度
UAV_CHARGE_THRESHOLD = 20  # 充电阈值

# AGV配置
AGV_MAX_BATTERY = 100  # 最大电量
AGV_SPEED = 5  # 行驶速度
AGV_CHARGING_CAPACITY = 20  # 充电能力

# 任务配置
DEFAULT_TASK_PRIORITY = 1  # 默认任务优先级

# 调度配置
ALPHA = 0.25  # 距离权重
BETA = 0.25  # 电量权重
GAMMA = 0.25  # 负载权重
DELTA = 0.25  # 优先级权重

# 模拟配置
MAX_SIMULATION_STEPS = 1000  # 最大模拟步数

# 能耗模型配置
BASE_ENERGY_CONSUMPTION = 1.0  # 基础能耗
PAYLOAD_ENERGY_FACTOR = 0.5  # 负载能耗因子
WIND_ENERGY_FACTOR = 0.3  # 风速能耗因子