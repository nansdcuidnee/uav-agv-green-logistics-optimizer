# 数据审计报告

日期：2026-04-20

范围：
- 指标生成链路：`src/simulation/simulator.py`
- 结果布局与元数据：`src/utils/result_layout.py`
- 对比/消融脚本：`experiments/compare_strategies.py`、`experiments/ablation_experiment.py`
- 历史结果抽样：`results/runs/...`、`results/tests/...`

结论：
- 当前项目的结果目录里同时存在“真实策略缺陷”和“指标口径/落盘缺陷”。
- 因此，现有图表里凡是涉及 `relay_coop` 的“平均配送时间最短”结论，当前都不能直接用于论文或汇报。
- 原因不是单点 bug，而是至少 6 个数据问题叠加。

## 一、严重问题

### 1. `relay_coop` 允许同一 AGV 在同一轮被多个任务重复占用，直接拉低完成率

证据：
- `src/strategies/relay_coop.py:22-35` 对每个 `pending task` 都从 `environment.agvs` 全量挑最近 AGV，没有从可用 AGV 集合中移除已分配 AGV。
- `src/strategies/relay_coop.py:47-56` 为每个任务都写入 `assigned_agv` 和 `move_agv_to_relay` 动作。
- `src/simulation/simulator.py:236-241` 每次动作执行时都会覆盖同一 AGV 的 `destination`、`move_progress`、`task_id`。
- 抽样结果 `results/runs/relay_coop/20260417_190610/records/event_timeline.txt:19-29` 显示 Step 22 同时给 task 3 和 task 4 请求 AGV 2，但 Step 41 只有 task 4 收到到达事件。
- 同一运行的 `results/runs/relay_coop/20260417_190610/records/tasks.csv:4` 显示 task 3 最终未完成。

影响：
- `relay_coop` 的完成率偏低并不是实验现象，而是实现缺陷。
- 任何基于当前 `relay_coop` 完成率做的横向对比都不可信。

### 2. `avg_delivery_time` 与 `completion_rate` 不是同一统计样本，导致“时间最短但完成率最低”的表象

证据：
- `src/simulation/simulator.py:734-741` 只有 `start_time` 和 `completion_time` 都存在的任务才进入 `execution_times`，因此 `avg_delivery_time` 只对已完成任务取平均。
- `src/simulation/simulator.py:737-742` `avg_wait_time_at_relay` 则会把所有有等待时间的任务都纳入平均，包括最终失败任务。
- `results/runs/relay_coop/20260417_190610/metrics.json:5-14` 显示该运行 `completion_rate = 0.8333`，但 `avg_delivery_time = 3.8`。
- `results/runs/relay_coop/20260417_190610/records/tasks.csv:4` 中失败的 task 3 有 `wait_time_at_relay = 178.0`，却没有 `finish_time`。

解释：
- 这正是你看到“协同中继耗时最少，但任务完成率最低”的直接原因。
- 这里的“平均配送时间”不是全任务平均耗时，而是“已完成任务的平均执行时间”。

影响：
- 现在的 `avg_delivery_time` 不能独立反映策略整体效率。
- 如果要做策略总效能比较，至少要同时看 `completion_rate`、`avg_delivery_time`、失败任务占比，或者改成统一分母。

### 3. `relay_coop` 的时间建模被严重压缩，长距离飞行会被算成 1-2 个 step

证据：
- `src/simulation/simulator.py:528-545` 中，`relay_coop` 在 AGV 到位后直接把 UAV 路径写成 `[uav.position, relay_point, uav.task.end_point]`。
- `src/simulation/simulator.py:517-526` 每个 step 只取 `uav.path[0]` 作为下一个点，然后立刻把 UAV 位置更新到该点。
- 这意味着无论两点距离多远，只要是一个路径节点，就只消耗 1 个仿真 step。
- 抽样结果 `results/runs/relay_coop/20260417_190610/metrics.json:12-18` 显示总时间 200 step、总距离 4795.61，但 `avg_delivery_time` 只有 3.8 step，明显不符合距离规模。

影响：
- `relay_coop` 的时间指标被系统性低估。
- 这不是“策略快”，而是“路径离散方式和其他策略不一致”。

### 4. `tasks.csv` 的任务级距离/能耗字段基本失真，`assigned_time` 也没有真正落盘

证据：
- `src/simulation/simulator.py:98-113` 只初始化了 `uav_distance`、`agv_distance`、`uav_energy`、`agv_energy`、`total_energy`、`assigned_time` 等字段。
- 全仓库搜索 `_add_task_stat(` 只有定义，没有调用：`src/simulation/simulator.py:135`。
- `src/simulation/simulator.py:883-900` 导出 `tasks.csv` 时直接读取这些字段。
- 抽样结果 `results/runs/baseline_direct/20260417_190609/records/tasks.csv:2-7` 中，所有任务的 `uav_distance/agv_distance/uav_energy/agv_energy/total_energy` 都是 `0.0`。
- 同一文件以及 `results/runs/relay_coop/20260417_190610/records/tasks.csv:2-7` 中，`assigned_time` 全为空。

影响：
- 任务级明细表目前不能用于任务级能耗分析、任务级距离分析、排队分析。
- 任何基于 `tasks.csv` 的二次统计都可能是错的。

### 5. 历史结果同时混用了百分制和比例制，旧结果与新结果不能直接合并

证据：
- 新口径示例：`results/runs/relay_coop/20260417_190610/metrics.json:8` 中 `completion_rate = 0.8333333333333334`。
- 旧口径示例：`results/tests/metrics_test/20260412_101001/metrics.json:8` 中 `completion_rate = 100.0`。
- 同一旧文件还保留了 `task_completion_rate` 风格字段，说明历史上至少存在两套指标定义。

影响：
- 只要有人把旧 `results/tests` 或早期 `results/runs` 混进新脚本汇总，图表就会被污染。
- 现有 `results` 目录不能被视为同一口径下的可直接复用数据仓。

### 6. 元数据声明的必需产物和实际产物不一致，结果包自描述不可信

证据：
- `src/utils/result_layout.py:11` 将 `plots/chart.png` 写入 `REQUIRED_ARTIFACTS`。
- `src/simulation/simulator.py:1071-1080` 把这组 `REQUIRED_ARTIFACTS` 原样写入运行元数据。
- 抽样结果 `results/runs/relay_coop/20260417_190610/metadata.json:6-19` 声称必需图是 `plots/chart.png`，但真实图列表只有 `task_progress.png`、`battery_status.png`、`kpi_summary.png` 等。
- 实际目录 `results/runs/relay_coop/20260417_190610/plots/` 中不存在 `chart.png`。

影响：
- 下游如果按 `metadata.json` 做结果完整性校验，会误判结果包缺失文件。
- 这会影响自动汇总、打包和归档。

## 二、次级污染风险

### 7. 消融实验的 fallback 指标拼装会静默写入错误值

证据：
- `experiments/ablation_experiment.py:411-415` 在 `metrics.json` 不存在时，直接读取 `simulator.total_energy`、`getattr(simulator, 'on_time_rate', 0.0)`、`getattr(simulator, 'avg_delivery_time', 0.0)`、`getattr(simulator, 'avg_wait_time_at_relay', None)`。
- 但 `src/simulation/simulator.py` 中并没有 `self.on_time_rate`、`self.avg_delivery_time`、`self.avg_wait_time_at_relay` 这类持续更新属性，真实值只在 `calculate_metrics()` 的返回字典里生成。

影响：
- 一旦某次实验因为落盘失败走 fallback，消融结果会被静默写成 0 或 None，而不是报错。
- 这是“结果看起来正常，但字段其实已坏”的高风险路径。

### 8. 仓库里保留了会产出假数据/旧格式数据的脚本，容易污染 `results`

证据：
- `experiments/run_experiment_mock.py` 文件头已经注明“仅用于演示和占位”，且 `run_experiment()` 直接把 `completed_tasks = 10`、`task_completion_rate = 1.0` 写死。
- `src/utils/result_generator.py:47-79` 还保留了另一套旧的指标生成逻辑，其能源、利用率、记录格式都与当前 `Simulator.save_results()` 不一致。

影响：
- 只要团队成员误跑这些脚本，`results` 就会继续混入口径不兼容的数据。

## 三、当前哪些数据还能用

相对更可信：
- `metrics.json` 中的 `completed_tasks`、`failed_tasks`、`total_energy`、`total_distance`，因为它们来自 `Simulator.calculate_metrics()` 的主链路。
- `records/steps.csv` 的累计能耗、累计距离，与 `metrics.json` 有一致性检查。
- `records/event_timeline.txt` 适合用来追状态流转问题。

当前不建议直接用于结论：
- `relay_coop` 的 `avg_delivery_time`
- 所有任务级 `uav_distance/agv_distance/*energy/total_energy`
- 所有混有旧结果目录的横向汇总
- 任何依赖 `metadata.required_artifacts` 的自动校验

## 四、修复优先级

1. 修 `relay_coop` 的 AGV 重复分配问题。
2. 统一 `relay_coop` 与其他策略的路径/时间建模。
3. 修复任务级统计写入，把 `assigned_time`、任务级距离、任务级能耗真正更新起来。
4. 清理结果口径：统一 `completion_rate` 为 0-1 或 0-100，只保留一种。
5. 修 `metadata.required_artifacts` 与实际产物列表不一致的问题。
6. 禁止 `run_experiment_mock.py` 和旧 `result_generator.py` 写入正式 `results`。

