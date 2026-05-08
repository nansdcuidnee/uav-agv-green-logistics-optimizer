# 系统配置文件 - 优化场景以突出策略差异

# ==================== 环境配置 ====================
MAP_SIZE = (2000, 2000)  # 大幅增大地图尺寸，增加任务距离差异
NUM_OBSTACLES = 10       # 障碍物数量，使路径规划更有意义
OBSTACLE_MIN_SIZE = 50   # 障碍物最小尺寸
OBSTACLE_MAX_SIZE = 150  # 障碍物最大尺寸

# ==================== 实验参数 ====================
NUM_POINTS = 25  # 大幅增加任务数量，体现调度压力
NUM_UAV = 5      # 无人机数量
NUM_AGV = 4      # AGV数量（少于UAV，体现中继资源竞争）

# ==================== 模拟配置 ====================
DEFAULT_SIMULATION_STEPS = 200  # 增加模拟步数
MAX_SIMULATION_STEPS = 2000     # 最大模拟步数

# ==================== UAV配置 ====================
UAV_INIT_BATTERY = 20   # 大幅降低初始电量，制造电量紧张场景
UAV_MAX_BATTERY = 100   # 最大电量
UAV_PAYLOAD_CAPACITY = 5  # 最大负载能力
UAV_SPEED = 12          # 适当降低速度，增加时间差异
UAV_CHARGE_THRESHOLD = 15  # 降低充电阈值
UAV_MAX_RANGE = 800     # 最大飞行范围（限制单次任务距离）

# ==================== AGV配置 ====================
AGV_INIT_BATTERY = 100   # 初始电量
AGV_MAX_BATTERY = 100    # 最大电量
AGV_SPEED = 6            # AGV速度（低于UAV，但可充电）
AGV_CHARGE_RATE_PER_STEP = 25  # 提高AGV充电速度，体现中继优势
AGV_MAX_RANGE = 2000     # AGV活动范围（大于UAV）

# ==================== 任务配置 ====================
DEFAULT_TASK_PRIORITY = 3  # 默认任务优先级
MIN_TASK_PRIORITY = 1      # 最小任务优先级
MAX_TASK_PRIORITY = 5      # 最大任务优先级
TASK_MIN_DISTANCE = 300    # 任务最小距离
TASK_MAX_DISTANCE = 1200   # 任务最大距离（跨越大范围）

# ==================== 调度配置 ====================
# 调整权重使策略差异更明显
ALPHA = 0.15  # 距离权重（降低）
BETA = 0.40   # 电量权重（大幅提高，体现能耗优先策略）
GAMMA = 0.10  # 负载权重（降低）
DELTA = 0.35  # 优先级权重（保持）

# 校验调度权重和为1
assert abs(ALPHA + BETA + GAMMA + DELTA - 1.0) < 1e-6, "调度权重之和必须为1"

# ==================== 中继策略配置 ====================
RELAY_DISTANCE = 150.0   # 缩短中继距离，增加中继次数
SEARCH_RADIUS = 400.0    # 扩大AGV搜索范围
ENABLE_RELAY_OPTIMIZATION = True  # 启用中继优化

# ==================== 随机种子 ====================
RANDOM_SEED = 42  # 随机种子（固定种子保证可重复）

# ==================== 能耗模型配置 ====================
BASE_ENERGY_CONSUMPTION = 2.0   # 大幅提高基础能耗
PAYLOAD_ENERGY_FACTOR = 1.0     # 提高负载能耗因子
WIND_SPEED = 8.0                # 增加风速
WIND_ENERGY_FACTOR = 0.5        # 提高风速影响
ALTITUDE_ENERGY_FACTOR = 0.3    # 新增高度能耗因子
TEMPERATURE = 25                # 环境温度
TEMPERATURE_ENERGY_FACTOR = 0.1 # 温度能耗因子

# 兼容旧名（deprecated）
SIMULATION_STEPS = DEFAULT_SIMULATION_STEPS  # 兼容旧名，已废弃
INIT_BATTERY = UAV_INIT_BATTERY  # 兼容旧名，已废弃