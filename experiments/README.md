# Experiments Directory Documentation

## 目录说明

本目录包含 UAV-AGV 智能配送系统的实验脚本，用于运行仿真实验和生成结果。

### 主要文件
- **run_experiment.py**：真实仿真实验脚本，运行完整的仿真系统
- **run_experiment_mock.py**：模拟实验脚本，用于演示和占位
- **configs/**：实验配置文件目录

## 脚本用途与使用方法

### 1. run_experiment.py（真实仿真）

**用途**：运行真实的 UAV-AGV 智能配送系统仿真实验，使用实际的系统组件和算法。

**命令示例**：

```bash
# 基本运行
python -m experiments.run_experiment --experiment-name=exp_test --num-uavs=2 --num-agvs=2 --num-tasks=3 --max-steps=50 --strategy=baseline_direct --seed=42

# 使用配置文件运行
python -m experiments.run_experiment --config=configs/default_experiment.yaml --experiment-name=exp_test
```

**参数说明**：
- `--experiment-name`：实验名称，用于结果目录命名
- `--num-uavs`：无人机数量
- `--num-agvs`：AGV 数量
- `--num-tasks`：任务数量
- `--max-steps`：最大仿真步数
- `--strategy`：调度策略（baseline_direct、relay_coop、energy_priority）
- `--seed`：随机种子
- `--config`：配置文件路径（可选）

### 2. run_experiment_mock.py（占位/演示）

**用途**：模拟实验脚本，用于演示实验流程和结果格式，不运行真实仿真。

**命令示例**：

```bash
python -m experiments.run_experiment_mock
```

**注意**：本脚本生成的结果不可用于正式结论/论文，仅用于演示目的。

## 两者区别和适用场景

| 脚本 | 类型 | 适用场景 | 特点 |
|------|------|----------|------|
| run_experiment.py | 真实仿真 | 正式实验、性能评估、算法验证 | 运行完整仿真，结果真实可靠 |
| run_experiment_mock.py | 模拟演示 | 流程演示、结果格式验证、快速测试 | 运行速度快，结果为模拟数据 |

## 输出目录规范

所有实验结果都存储在以下目录结构中：

```
results/<experiment_name>/<timestamp>/
```

其中：
- `<experiment_name>`：实验名称，由 `--experiment-name` 参数指定
- `<timestamp>`：实验运行的时间戳，格式为 `YYYYMMDD_HHMMSS`

### 输出文件

真实仿真实验（run_experiment.py）会生成：
- `metrics.json`：实验性能指标
- `records.csv`：任务执行记录
- `chart.png`：性能对比图表
- 其他可视化文件（如地图、路径等）

模拟实验（run_experiment_mock.py）会生成：
- `metrics.json`：模拟性能指标
- `records.csv`：模拟任务记录
- `chart.png`：模拟性能对比图表

## 配置文件

实验配置文件存储在 `configs/` 目录中，使用 YAML 格式。默认配置文件为 `configs/default_experiment.yaml`，包含以下字段：

- `experiment_name`：实验名称
- `num_uavs`：无人机数量
- `num_agvs`：AGV 数量
- `num_tasks`：任务数量
- `max_steps`：最大仿真步数
- `strategy`：调度策略
- `seed`：随机种子

当使用 `--config` 参数时，会从配置文件加载默认参数，然后由命令行参数覆盖。
