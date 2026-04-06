# 低空绿色物流能耗与碳效优化仿真系统

## 项目简介

本项目是一个面向低空物流配送的能耗与碳效优化仿真平台，支持空地协同（UAV+AGV）配送场景下的能耗建模、碳效评估和策略优化研究。

## 项目结构

```
uav-agv-green-logistics/
├── src/                      # 源代码
│   ├── domain/              # 统一数据模型
│   │   ├── entities.py      # UAV/AGV/Task/Scenario实体
│   │   └── enums.py         # 枚举类型定义
│   ├── models/              # 研究模型
│   │   ├── energy/          # 能耗模型
│   │   │   ├── uav_energy.py    # UAV分阶段能耗
│   │   │   └── agv_energy.py    # AGV距离能耗
│   │   └── carbon/          # 碳效模型
│   │       └── carbon_model.py  # 碳排放与效率评估
│   ├── strategies/          # 配送策略
│   │   ├── baseline_direct.py   # 基线直送
│   │   ├── relay_coop.py        # 协同中继
│   │   └── energy_priority.py   # 能耗优先
│   ├── simulation/          # 仿真引擎
│   │   └── engine.py        # 事件驱动仿真
│   ├── calibration/         # 实飞标定
│   │   ├── flight_data_loader.py
│   │   └── energy_calibrator.py
│   └── visualization/       # 可视化
├── experiments/             # 实验脚本
│   └── runner.py           # 批量实验运行器
├── configs/                 # 配置文件
├── data/                    # 数据目录
│   ├── raw/                # 实飞原始数据
│   └── processed/          # 处理后数据
├── results/                 # 实验结果
└── reports/                 # 分析报告
```

## 快速开始

### 安装依赖

```bash
pip install -r requirements.txt
```

### 本地验证

为确保代码质量，每个模块开发者在修改代码后应执行本地验证：

```powershell
# 验证特定模块
.\scripts\verify_module.ps1 -Module <module_name>

# 提交前总验收
.\scripts\verify_module.ps1 -Module all
```

### 运行策略对比实验

```bash
python -m experiments.run_experiment
```

### 运行集成检查

```bash
python scripts/self_check.py --strategy baseline_direct --seed 42
```

## 研究流程

### 1. 数据准备

将实飞数据放入 `data/raw/` 目录，支持CSV格式：
- `timestamp`: 时间戳
- `phase`: 飞行阶段 (takeoff/cruise/hover/landing)
- `battery_voltage`: 电池电压 (V)
- `battery_current`: 电池电流 (A)
- `latitude/longitude/altitude`: 位置坐标

### 2. 模型标定

```python
from src.calibration.energy_calibrator import EnergyCalibrator

calibrator = EnergyCalibrator()
log_files = ['flight1.csv', 'flight2.csv']
params = calibrator.calibrate_from_flight_logs(log_files)
calibrator.save_params(params, 'data/processed/calibrated_params.json')
```

### 3. 运行仿真实验

```python
from experiments.runner import ExperimentRunner

runner = ExperimentRunner()
scenario_config = {
    'name': 'test',
    'num_uavs': 2,
    'num_agvs': 1,
    'num_tasks': 5
}

results = runner.run_comparison(scenario_config, num_runs=3)
runner.save_results(results, 'my_experiment')
```

### 4. 结果分析

实验结果保存在 `results/` 目录：
- `results.json`: 完整结果数据
- `results.csv`: CSV格式结果
- `comparison.png`: 策略对比图

## 核心指标定义

### 能耗指标

| 指标 | 单位 | 说明 |
|------|------|------|
| total_energy_wh | Wh | 总能耗 |
| uav_energy_wh | Wh | UAV能耗 |
| agv_energy_wh | Wh | AGV能耗 |
| avg_energy_per_task | Wh | 单任务平均能耗 |
| avg_energy_per_km | Wh/km | 单位距离能耗 |

### 碳效指标

| 指标 | 单位 | 说明 |
|------|------|------|
| total_carbon_kg | kg CO2 | 总碳排放 |
| carbon_saving_rate | % | 碳减排率（对比传统货车） |
| energy_saving_rate | % | 节能率 |
| carbon_efficiency | tasks/kg | 碳效（单位碳排放完成的任务数） |

### 任务指标

| 指标 | 单位 | 说明 |
|------|------|------|
| completed_tasks | count | 完成任务数 |
| task_completion_rate | % | 任务完成率 |
| avg_task_duration | s | 平均任务耗时 |

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

## 团队成员分工

| 模块 | 负责人 | 说明 |
|------|--------|------|
| energy_model | 成员A | UAV分阶段能耗 + AGV距离能耗 |
| path_planner | 成员B | 路径规划算法 |
| scheduler | 成员C | AGV调度算法 |
| charging_strategy | 成员D | 充电策略优化 |
| visualizer | 成员E | 可视化展示 |
| simulation_framework | 组长 | 系统架构与仿真流程 |

## 扩展开发

### 添加新策略

```python
from src.strategies.base import BaseStrategy
from src.domain.enums import StrategyType

class MyStrategy(BaseStrategy):
    def __init__(self):
        super().__init__(StrategyType.MY_STRATEGY)
    
    def assign_tasks(self, scenario):
        # 实现任务分配逻辑
        pass
    
    def select_charging_station(self, uav, scenario):
        # 实现充电选择逻辑
        pass
```

### 添加新能耗模型

```python
from src.models.energy.uav_energy import UAVEnergyModel

class MyEnergyModel(UAVEnergyModel):
    def calculate_cruise_energy(self, uav, distance, wind_speed=0):
        # 自定义巡航能耗计算
        pass
```

## 论文使用建议

### 实验设计

1. **基线对比实验**: 三种策略在相同场景下的性能对比
2. **规模扩展实验**: 改变UAV/AGV/任务数量，观察系统性能变化
3. **参数敏感性分析**: 调整能耗参数，分析对结果的影响

### 图表生成

运行实验后自动生成：
- 能耗对比箱线图
- 碳排放对比图
- 减排率/节能率对比图

### 数据导出

```python
# 导出为LaTeX表格格式
import pandas as pd

df = pd.read_csv('results/my_experiment/results.csv')
print(df.to_latex(index=False))
```

## 许可证

MIT License

## 联系方式

项目负责人：[姓名]
邮箱：[邮箱]
