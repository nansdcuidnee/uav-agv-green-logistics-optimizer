# 项目概述

## 1. 项目定位

本项目当前定位为：

> 构建一个可复现的 UAV-AGV 绿色物流协同配送仿真框架，比较 `baseline_direct`、`energy_priority`、`relay_coop` 三种策略在不同场景下的表现，并分析它们的适用边界。

当前不预设成果方向，先把项目事实、实验结果和待验证问题整理清楚。

## 2. 当前代码结构

| 模块 | 路径 | 作用 |
|---|---|---|
| 核心实体 | `src/core/` | UAV、AGV、Task 等对象 |
| 能耗模型 | `src/energy/energy_model.py` | UAV 分阶段能耗和 AGV 行驶能耗 |
| 路径规划 | `src/planning/path_planner.py` | 路径搜索与障碍处理 |
| 策略实现 | `src/strategies/` | 三种调度策略 |
| 仿真执行 | `src/simulation/` | 环境状态、仿真循环、指标计算 |
| 实验脚本 | `experiments/` | 策略对比、消融、鲁棒性实验 |
| 配置文件 | `configs/` | 场景与实验配置 |
| 结果输出 | `results/` | 指标、日志和图表 |
| 测试 | `tests/` | 基础回归和冒烟测试 |

## 3. 当前策略

| 策略 | 文件 | 当前作用 |
|---|---|---|
| `baseline_direct` | `src/strategies/baseline_direct.py` | 基线直送策略 |
| `energy_priority` | `src/strategies/energy_priority.py` | 能耗感知评分策略 |
| `relay_coop` | `src/strategies/relay_coop.py` | UAV-AGV 中继协同策略 |

这三个策略是候选策略库。实验重点不是证明某一个策略始终最好，而是判断不同策略在不同条件下的表现。

## 4. 当前实验体系

| 实验 | 脚本 | 目的 |
|---|---|---|
| 策略对比 | `experiments/compare_strategies.py` | 比较三种策略核心指标 |
| 消融实验 | `experiments/ablation_experiment.py` | 分析策略和组件影响 |
| 鲁棒性实验 | `experiments/run_robustness.py` | 检查随机种子、规模、电池容量、故障条件下的稳定性 |

## 5. 当前可引用结果

结果文件：

`results/comparisons/strategy_comparison/20260420_221832/comparison_metrics.csv`

| 策略 | 完成率 | 准时率 | 总能耗 | 单任务能耗 | 单位距离能耗 | 充电次数 |
|---|---:|---:|---:|---:|---:|---:|
| `baseline_direct` | 0.70 | 0.70 | 428.82 | 61.26 | 0.226 | 4 |
| `relay_coop` | 1.00 | 1.00 | 497.01 | 49.70 | 0.187 | 0 |
| `energy_priority` | 0.60 | 0.60 | 438.86 | 73.14 | 0.272 | 4 |

当前结论边界：

- `relay_coop` 完成率和准时率最高。
- `relay_coop` 单任务能耗和单位距离能耗更低。
- `relay_coop` 总能耗高于 `baseline_direct`，不能写成总能耗最低。
- `energy_priority` 当前结果不理想，需要进一步分析适用场景和评分机制。

## 6. 当前待确认问题

| 问题 | 说明 |
|---|---|
| 策略适用边界 | 需要通过规模、电池、故障等实验进一步判断 |
| `energy_priority` 的作用 | 当前实验结果不占优，需要单独分析 |
| 总能耗评价方式 | 完成任务数不同，必须同时看单任务能耗和单位距离能耗 |
| 后续方向 | 暂不确定，等实验和老师意见进一步收敛 |
