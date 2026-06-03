# 实验矩阵

## 1. 实验目的

实验用于判断三种策略的表现和适用边界，不用于证明某个策略在所有场景下都更好。

## 2. 策略对比实验

运行命令：

```bash
python -m experiments.compare_strategies --config configs/generated/scene_small.yaml --max-steps 50
```

当前可引用结果：

`results/comparisons/strategy_comparison/20260420_221832/comparison_metrics.csv`

| 策略 | 完成率 | 准时率 | 平均配送时间 | 总能耗 | 单任务能耗 | 单位距离能耗 | AGV 距离 | 中继等待 | 充电次数 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| `baseline_direct` | 0.70 | 0.70 | 5.57 | 428.82 | 61.26 | 0.226 | 0.00 | N/A | 4 |
| `relay_coop` | 1.00 | 1.00 | 0.60 | 497.01 | 49.70 | 0.187 | 240.00 | 2.90 | 0 |
| `energy_priority` | 0.60 | 0.60 | 6.83 | 438.86 | 73.14 | 0.272 | 0.00 | N/A | 4 |

当前解释：

- `relay_coop` 完成率、准时率最高。
- `relay_coop` 单任务能耗、单位距离能耗更低。
- `relay_coop` 总能耗高于 `baseline_direct`，可能因为完成任务更多。
- `energy_priority` 当前结果不理想，需要进一步分析适用场景。

输出位置：

```text
results/comparisons/strategy_comparison/{timestamp}/
```

重点文件：

| 文件 | 作用 |
|---|---|
| `comparison_metrics.csv` | 三种策略核心指标 |
| `comparison_summary.txt` | 文本汇总 |
| `comparison_summary.json` | 结构化汇总 |
| `plots/` | 指标图表 |

## 3. 消融实验

运行命令：

```bash
python -m experiments.ablation_experiment --config configs/generated/scene_small.yaml --max-steps 20 --num-runs 1
```

建议关注：

| 问题 | 对应分析 |
|---|---|
| AGV 协同是否有效 | 对比有无 AGV 协同 |
| 中继策略是否有效 | 对比 `relay_coop` 与 `baseline_direct` |
| 能耗模型是否影响结论 | 对比完整能耗模型与简化能耗模型 |
| 完成率和总能耗是否冲突 | 同时报告完成任务数、总能耗、单任务能耗 |

## 4. 鲁棒性实验

| 类型 | 配置 | 目的 |
|---|---|---|
| 多种子 | `configs/experiments/robustness_seed.yaml` | 检查随机性影响 |
| 规模变化 | `configs/experiments/robustness_scale.yaml` | 检查任务数量变化后的趋势 |
| 电池扰动 | `configs/experiments/robustness_battery.yaml` | 检查电池容量变化后的策略表现 |
| 故障扰动 | `configs/experiments/robustness_failure.yaml` | 检查设备故障下的退化情况 |

运行示例：

```bash
python -m experiments.run_robustness --config configs/experiments/robustness_seed.yaml --campaign-name rb_seed_final
python -m experiments.run_robustness --config configs/experiments/robustness_scale.yaml --campaign-name rb_scale_final
python -m experiments.run_robustness --config configs/experiments/robustness_battery.yaml --campaign-name rb_capacity_final
python -m experiments.run_robustness --config configs/experiments/robustness_failure.yaml --campaign-name rb_failure_final
```

只检查配置展开：

```bash
python -m experiments.run_robustness --config configs/experiments/robustness_scale.yaml --campaign-name rb_scale_check --dry-run
```

## 5. 单策略复现命令

```bash
python main.py --config configs/generated/scene_small.yaml --strategy baseline_direct --max-steps 50
python main.py --config configs/generated/scene_small.yaml --strategy relay_coop --max-steps 50
python main.py --config configs/generated/scene_small.yaml --strategy energy_priority --max-steps 50
```

## 6. 环境与测试

```bash
pip install -r requirements.txt
python -m pytest -q
```

## 7. 待补实验

| 待补充内容 | 目的 |
|---|---|
| 多 seed 完整统计 | 判断结论是否稳定 |
| scale 实验完整结果 | 判断大规模任务下策略边界 |
| 电池受限场景 | 判断 `energy_priority` 是否有优势区间 |
| fallback 触发实验 | 判断中继异常时的可靠性 |
