# 系统配置文件

# 环境配置
MAP_SIZE = (200, 200)  # 地图尺寸

# 实验参数
NUM_POINTS = 5  # 配送点数量
NUM_UAV = 2  # 无人机数量
NUM_AGV = 2  # AGV数量

# 模拟配置
DEFAULT_SIMULATION_STEPS = 50  # 默认模拟步数
MAX_SIMULATION_STEPS = 1000  # 最大模拟步数（硬上限）

# UAV配置
UAV_INIT_BATTERY = 40  # 初始电量
UAV_MAX_BATTERY = 100  # 最大电量
UAV_PAYLOAD_CAPACITY = 5  # 最大负载能力
UAV_SPEED = 10  # 飞行速度
UAV_CHARGE_THRESHOLD = 20  # 充电阈值

# AGV配置
AGV_INIT_BATTERY = 100  # 初始电量
AGV_MAX_BATTERY = 100  # 最大电量
AGV_SPEED = 5  # 行驶速度
AGV_CHARGE_RATE_PER_STEP = 20  # 每步充电速率

# 任务配置
DEFAULT_TASK_PRIORITY = 1  # 默认任务优先级

# 调度配置
# score = ALPHA * distance_score + BETA * battery_score + GAMMA * load_score + DELTA * priority_score
ALPHA = 0.25  # 距离权重
BETA = 0.25  # 电量权重
GAMMA = 0.25  # 负载权重
DELTA = 0.25  # 优先级权重

# 校验调度权重和为1
assert abs(ALPHA + BETA + GAMMA + DELTA - 1.0) < 1e-6, "调度权重之和必须为1"

# 随机种子
RANDOM_SEED = 42  # 随机种子

# 能耗模型配置
BASE_ENERGY_CONSUMPTION = 1.0  # 基础能耗
PAYLOAD_ENERGY_FACTOR = 0.5  # 负载能耗因子
WIND_SPEED = 0.0  # 风速
WIND_ENERGY_FACTOR = 0.3  # 风速能耗因子

# 兼容旧名（deprecated）
SIMULATION_STEPS = DEFAULT_SIMULATION_STEPS  # 兼容旧名，已废弃
INIT_BATTERY = UAV_INIT_BATTERY  # 兼容旧名，已废弃