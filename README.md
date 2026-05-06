# 低空绿色物流能耗与碳效优化仿真系统

## 项目简介

本项目是一个面向低空物流配送的能耗与碳效优化仿真平台，支持空地协同（UAV+AGV）配送场景下的能耗建模、碳效评估和策略优化研究。

## 项目结构

```
uav-agv-green-logistics-optimizer/
├── config/                   # Python配置代码与常量模块
├── configs/                  # YAML场景配置文件
├── data/                     # 数据目录
├── dashboard.py              # Streamlit可视化Dashboard
├── experiments/              # 实验脚本
├── logs/                     # 日志文件
├── pytest.ini                # pytest最小配置文件
├── results/                  # 实验结果
├── scripts/                  # 辅助脚本
├── src/                      # 源代码
│   ├── core/                 # 核心实体（UAV、AGV、Task）
│   ├── communication/        # 通信模块
│   ├── energy/               # 能耗模型
│   ├── planning/             # 路径规划
│   ├── scheduling/           # 调度系统
│   ├── simulation/           # 仿真系统
│   ├── strategies/           # 配送策略集合
│   └── utils/                # 工具函数
├── tests/                    # 测试文件
├── main.py                   # 主程序入口
├── README.md                 # 项目说明
├── requirements.txt          # 依赖项
└── .gitignore                # Git忽略文件
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

### 运行可视化 Dashboard

```bash
# 从仓库根目录运行
streamlit run dashboard.py
```

Dashboard 启动后可以在浏览器中查看实验结果，包括：
- 单次实验的 KPI 指标和可视化图表
- 策略对比结果
- 鲁棒性实验结果

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
| **src/utils/** | 工具函数，包括数学工具、结果生成器等 |
| **experiments/** | 实验脚本，运行不同参数的实验 |
| **scripts/** | 辅助脚本，包括自检查脚本、验证脚本等 |
| **tests/** | 测试文件，包含冒烟测试、功能测试等 |
| **dashboard.py** | Streamlit可视化Dashboard，展示实验结果 |

## 配置说明

### config/ 与 configs/ 的区别

- **config/**：Python配置代码与常量模块，包含系统配置参数
- **configs/**：YAML场景配置文件，包含不同规模的场景配置

## 策略说明

### 配送策略

- **baseline_direct.py**：基线直送策略
- **relay_coop.py**：协同中继策略
- **energy_priority.py**：能耗优先策略

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

## 许可证

MIT License