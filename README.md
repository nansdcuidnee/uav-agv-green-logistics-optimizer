# 基于空地协同移动充电的无人机配送能耗优化系统

## 项目简介

本项目旨在构建一个仿真系统，包含无人机（UAV）与地面车辆（AGV）协同工作，实现路径规划、能耗计算、协同调度和移动充电策略。

## 项目结构

```
uav-agv-mobile-charging/
├── src/              # 源代码目录
│   ├── core/         # 核心模块
│   ├── energy/       # 能耗模型
│   ├── planning/     # 路径规划
│   ├── scheduling/   # 任务调度
│   ├── strategy/     # 充电策略
│   ├── simulation/   # 系统仿真
│   ├── visualization/ # 可视化
│   └── utils/        # 工具函数
├── config/           # 配置文件
├── experiments/      # 实验脚本
├── results/          # 实验结果
├── logs/             # 日志文件
├── main.py           # 主入口
├── requirements.txt  # 依赖包
└── README.md         # 项目说明
```

## 核心功能

- **无人机与AGV协同**：实现了UAV和AGV的基本类结构
- **能耗计算**：提供了考虑距离、负载和风速的能耗模型
- **路径规划**：包含了最近邻算法框架
- **任务调度**：实现了基于多因素评分的任务分配
- **充电策略**：包含了固定、移动和预测性三种充电方法
- **系统仿真**：实现了模拟运行的框架
- **可视化**：使用matplotlib实现了系统状态的可视化

## 快速开始

### 安装依赖

```bash
pip install -r requirements.txt
```

### 运行示例

```bash
python main.py
```

### 运行实验

```bash
python experiments/run_experiment.py
```

## 配置说明

配置文件位于 `config/config.py`，包含了系统的各项参数配置，如地图尺寸、UAV和AGV的参数、调度权重等。

## 模块说明

### core 模块
- **UAV类**：无人机的基本属性和方法
- **AGV类**：地面车辆的基本属性和方法
- **Task类**：配送任务的基本属性和方法
- **Environment类**：环境的基本属性和方法

### energy 模块
- **EnergyModel类**：能耗计算模型

### planning 模块
- **PathPlanner类**：路径规划算法

### scheduling 模块
- **Scheduler类**：任务调度和充电调度

### strategy 模块
- **ChargingStrategy类**：充电策略实现

### simulation 模块
- **Simulator类**：系统仿真器

### visualization 模块
- **Visualizer类**：系统状态可视化

### utils 模块
- **math_utils.py**：数学工具函数

## 扩展指南

1. **添加新的路径规划算法**：在 `planning/path_planner.py` 中实现新的算法
2. **添加新的充电策略**：在 `strategy/charging_strategy.py` 中实现新的策略
3. **修改能耗模型**：在 `energy/energy_model.py` 中调整能耗计算逻辑
4. **添加新的实验**：在 `experiments/run_experiment.py` 中添加新的实验配置

## 团队协作

本项目采用模块化设计，方便多人协作开发。团队成员可以根据自己的职责负责相应的模块：

- 核心模块：负责UAV、AGV、任务和环境的实现
- 能耗模块：负责能耗计算模型的实现
- 规划模块：负责路径规划算法的实现
- 调度模块：负责任务调度和充电调度的实现
- 策略模块：负责充电策略的实现
- 仿真模块：负责系统仿真器的实现
- 可视化模块：负责系统状态可视化的实现

## 注意事项

- 本项目为框架结构，需要团队成员根据具体需求实现各个方法
- 所有参数应从配置文件中读取，避免硬编码
- 新增功能应遵循模块化设计原则，保持代码结构清晰
- 实验结果应保存到 results 目录，日志应保存到 logs 目录