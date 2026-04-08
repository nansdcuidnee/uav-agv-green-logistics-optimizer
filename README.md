# 低空绿色物流能耗与碳效优化仿真系统

## 项目简介

本项目是一个面向低空物流配送的能耗与碳效优化仿真平台，支持空地协同（UAV+AGV）配送场景下的能耗建模、碳效评估和策略优化研究。

## 项目结构

```
uav-agv-green-logistics-optimizer/
├── config/                  # Python配置代码与常量模块
├── configs/                 # YAML场景配置文件
├── data/                    # 数据目录
├── experiments/             # 实验脚本
├── logs/                    # 日志文件
├── pytest.ini               # pytest最小配置文件
├── results/                 # 实验结果
├── scripts/                 # 辅助脚本
├── src/                     # 源代码
│   ├── core/                # 核心实体（UAV、AGV、Task）
│   ├── energy/              # 能耗模型
│   ├── planning/            # 路径规划
│   ├── scheduling/          # 调度系统
│   ├── simulation/          # 仿真系统
│   ├── strategy/            # 充电相关策略（legacy保留）
│   ├── strategies/          # 配送策略集合
│   ├── utils/               # 工具函数
│   └── visualization/       # 可视化
├── tests/                   # 测试文件
├── test-strategy.py         # 充电策略演示脚本（legacy）
├── README.md                # 项目说明
├── requirements.txt         # 依赖项
└── .gitignore               # Git忽略文件
```

## 快速开始

### 安装依赖

```bash
pip install -r requirements.txt
```

### 运行主程序

```bash
# 从仓库根目录运行
python main.py
```

### 运行实验

```bash
# 从仓库根目录运行
python -m experiments.run_experiment --experiment-name=test --num-uavs=2 --num-agvs=2 --num-tasks=3 --max-steps=50 --strategy=baseline_direct --seed=42
```

### 运行集成检查

```bash
# 从仓库根目录运行
python -m scripts.self_check --strategy=baseline_direct --seed=42
```

### 运行测试

```bash
# 从仓库根目录运行
python -m pytest -q
```

## 核心模块职责

| 模块 | 职责 |
|------|------|
| **config/** | Python配置代码与常量模块，包含系统配置参数 |
| **configs/** | YAML场景配置文件，包含不同规模的场景配置 |
| **src/core/** | 核心实体定义，包括 UAV、AGV、Task、ChargingStation 等 |
| **src/energy/** | 能耗模型，计算 UAV 和 AGV 的能耗 |
| **src/planning/** | 路径规划，为 UAV 和 AGV 规划路径 |
| **src/scheduling/** | 调度系统，分配任务和资源 |
| **src/simulation/** | 仿真系统，模拟整个物流系统的运行 |
| **src/strategies/** | 配送策略集合，包括基线直送、协同中继、能耗优先等策略 |
| **src/strategy/** | 充电相关策略（legacy保留），包含固定充电、移动充电、预测性充电等 |
| **src/utils/** | 工具函数，包括数学工具、结果生成器等 |
| **src/visualization/** | 可视化工具，生成仿真结果的图表和地图 |
| **experiments/** | 实验脚本，运行不同参数的实验 |
| **scripts/** | 辅助脚本，包括自检查脚本、验证脚本等 |
| **tests/** | 测试文件，包含冒烟测试、功能测试等 |

## 配置说明

### config/ 与 configs/ 的区别

- **config/**：Python配置代码与常量模块，包含系统配置参数
- **configs/**：YAML场景配置文件，包含不同规模的场景配置

## 策略说明

### src/strategies/ 与 src/strategy/ 的当前状态

- **src/strategies/**：主要的配送策略目录，包含三种配送策略：
  - `baseline_direct.py`：基线直送策略
  - `relay_coop.py`：协同中继策略
  - `energy_priority.py`：能耗优先策略

- **src/strategy/**：充电相关策略，当前按 legacy 保留，包含：
  - `charging_strategy.py`：充电策略实现

- **test-strategy.py**：根目录的充电策略演示脚本（legacy），与 src/strategy/ 的 legacy 状态一致

## 配送策略说明

### 1. Baseline Direct (基线直送)
- UAV直接从起点飞到终点
- 简单先到先服务任务分配
- 最近AGV充电选择

### 2. Relay Coop (协同中继)
- AGV移动到任务区域附近释放UAV
- 考虑AGV位置的任务分配
- 优先使用任务分配AGV充电

### 3. Energy Priority (能耗优先)
- 基于能耗预测选择最优UAV
- 考虑距离、电量、负载的分配策略
- 综合距离和充电功率的充电选择

## 核心指标定义

### 能耗指标

| 指标 | 单位 | 说明 |
|------|------|------|
| total_energy | - | 总能耗 |
| avg_energy_per_task | - | 单任务平均能耗 |
| energy_per_km | - | 单位距离能耗 |
| energy_saving_rate_vs_baseline | % | 相对基线的节能率 |
| emission_reduction_rate_vs_baseline | % | 相对基线的减排率 |

### 任务指标

| 指标 | 单位 | 说明 |
|------|------|------|
| task_completion_rate | % | 任务完成率 |
| completed_tasks | count | 完成任务数 |
| total_time | - | 总运行时间 |
| charging_count | count | 充电次数 |
| total_distance_km | km | 总行驶距离 |

## 团队成员分工

| 模块 | 负责人 | 说明 |
|------|--------|------|
| energy_model | 成员A | UAV分阶段能耗 + AGV距离能耗 |
| path_planner | 成员B | 路径规划算法 |
| scheduler | 成员C | AGV调度算法 |
| charging_strategy | 成员D | 充电策略优化 |
| visualizer | 成员E | 可视化展示 |
| simulation_framework | 组长 | 系统架构与仿真流程 |

## 许可证

MIT License

## 联系方式

项目负责人：[姓名]
邮箱：[邮箱]
