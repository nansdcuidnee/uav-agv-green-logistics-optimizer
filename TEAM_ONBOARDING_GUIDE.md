# &#x20;项目全景与协作约定

本文是给 5 位组员的统一说明，目标是让大家在同一套接口、同一套验收门槛下并行开发，避免“各自理解一套”的返工。

## 1. 项目目标（我们在解决什么问题）

这是一个   UAV + AGV 协同配送与移动充电   的仿真系统。核心流程是：

1. 在 `Environment` 中生成任务、放置 UAV/AGV。
2. `Simulator` 按时间步推进。
3. 每一步由策略模块分配任务并选择充电 AGV。
4. UAV 按路径移动，能耗模型计算消耗。
5. 记录指标并落盘到结果目录。

最终产物用于比较不同策略下的能耗、效率、碳效指标。

## 2. 全员硬门槛（PR 退回红线）

以下任一不满足，PR 直接 `Request changes`：

1. 代码必须通过 smoke test，且任务完成率 `> 0`（不是“能跑起来”就算过）。
2. 每个 PR 必须附：输入参数、运行命令、输出样例、至少 1 张截图或图表。
3. 每个模块至少 2 个测试用例：正常路径 1 个 + 边界/异常路径 1 个。
4. 不允许私自改公共接口；涉及接口变更必须先提 RFC（影响文件、调用方、迁移方案）。
5. 所有随机过程必须支持 `seed`；固定 seed 后关键指标误差 `<= 1e-6`。
6. 结果落盘必须包含：`metrics.json`、`records.csv`、`chart.png`。

## 3. 当前代码结构（按“权威模块”看）

### 3.1 入口层

- `main.py`：单次运行入口（手工构建环境、实例化模拟器、运行并保存结果）。
- `experiments/run_experiment.py`：实验脚本入口（批量参数实验应从这里扩展）。

### 3.2 核心域对象（Core）

- `src/core/task.py`：`Task` 任务对象（`id/start_point/end_point/payload/priority/status/assigned_uav`）。
- `src/core/uav.py`：`UAV` 对象（位置、电量、当前路径、当前任务、充电判定）。
- `src/core/agv.py`：`AGV` 对象（位置、状态、充电能力）。

### 3.3 仿真与调度主链路

- `src/simulation/environment.py`：环境容器，持有 `tasks/uavs/agvs`，并生成任务。
- `src/simulation/simulator.py`：主循环（策略分配 -> 路径规划 -> 能耗计算 -> 充电 -> 统计 -> 落盘）。
- `src/planning/path_planner.py`：路径规划（`a_star/rrt/straight`，含平滑、简化、多停靠点）。
- `src/energy/energy_model.py`：能耗模型接口与计算入口（当前实现较简化）。
- `src/scheduling/scheduler.py`：调度器框架（当前多为占位接口）。

### 3.4 策略插件层

- `src/strategies/base.py`：策略基类。
- `src/strategies/baseline_direct.py`：直送基线策略。
- `src/strategies/relay_coop.py`：中继协同策略。
- `src/strategies/energy_priority.py`：能耗优先策略。

> 目录口径说明：当前仓库还存在 `src/strategy/`（单数）历史目录。新开发统一使用 `src/strategies/`（复数）；除非做迁移，不要在 `src/strategy/` 新增逻辑。

### 3.5 输出与可视化

- `src/visualization/visualizer.py`：运行中可视化展示。
- `results/<experiment_name>/<timestamp>/`：实验落盘目录。

## 4. 运行时数据流（建议所有人统一理解）

一次仿真运行应按下面的调用链理解：

1. 入口创建 `Environment`，填充 `uavs/agvs/tasks`。
2. 创建 `Simulator(environment, energy_model, path_planner, scheduler, strategy_type=...)`。
3. `Simulator.run(max_steps, experiment_name)` 进入时间步循环。
4. 每步先调用策略 `assign_tasks(environment)`，给空闲 UAV 分配 `pending` 任务。
5. UAV 若有任务且无路径，则调用 `path_planner.plan_path(...)`。
6. UAV 沿路径移动，调用 `energy_model.compute(uav)` 扣电并累计能耗与距离。
7. 电量低于阈值后，策略 `select_charging_station(uav, environment)` 选择 AGV 充电。
8. 结束后计算指标并写出 `metrics.json`、`records.csv`、图表文件。

## 5. 公共接口边界（不可私改）

以下接口默认视为“公共接口”，改动前必须 RFC：

1. `Environment` 的构造与任务生成接口（`map_size`, `generate_tasks`）。
2. `Task/UAV/AGV` 的关键字段名与状态字段语义（如 `task.status`、`uav.task`）。
3. `Simulator` 的构造参数、`run/step/calculate_metrics/save_results` 的输入输出契约。
4. 策略统一入口参数 `strategy_type` 及三策略标识字符串：
   - `baseline_direct`
   - `relay_coop`
   - `energy_priority`
5. 结果文件名与目录规范：
   - `results/<experiment_name>/<timestamp>/metrics.json`
   - `results/<experiment_name>/<timestamp>/records.csv`
   - `results/<experiment_name>/<timestamp>/chart.png`

## 6. 五位组员分工与落点（代码路径级别）

### 6.1 唐福敏（场景与数据接口）

目标：

1. 只保留一个权威 `Environment`（`main` 与 `experiments` 共用同一接口）。
2. `Task` 统一为单一结构（推荐数据类），禁止 dict/class 混用。
3. 任务生成支持 seed；同 seed 任务集完全一致。

主要改动目录：

- `src/simulation/environment.py`
- `src/core/task.py`
- `main.py`
- `experiments/run_experiment.py`

必交测试：

- `test_environment_seed_stable`
- `test_task_schema_consistent`

PR 必附：

- 接口变更说明
- 调用方影响清单

### 6.2 易颜章（UAV 能耗模型）

目标：

1. 实现可解释的分阶段能耗：起飞/巡航/悬停/降落。
2. 参数可配置，禁止业务逻辑中散落硬编码常量。
3. 同输入重复计算一致，误差 `<= 1e-6`。

主要改动目录：

- `src/energy/energy_model.py`
- `config/config.py`（或新增专门能耗配置文件）
- `src/simulation/simulator.py`（仅接线，避免改公共签名）

必交测试：

- `test_uav_energy_phase_positive`
- `test_uav_energy_repeatable`

PR 必附：

- 公式说明
- 样例输入输出
- 对比图（至少 1 张）

### 6.3 陈舟然（AGV 与碳效指标）

目标：

1. 指标完整：
   - `total_energy`
   - `avg_energy_per_task`
   - `energy_per_km`
   - `energy_saving_rate_vs_baseline`
   - `emission_reduction_rate_vs_baseline`
2. `energy_per_km` 必须基于真实执行距离。
3. baseline 定义固定并写入文档。

主要改动目录：

- `src/simulation/simulator.py`（`calculate_metrics` 与距离统计）
- `docs` 或本文件中的指标定义补充

必交测试：

- `test_metrics_fields_complete`
- `test_metrics_numeric_valid`

PR 必附：

- `metrics.json` 样例
- 字段解释表

### 6.4 刘琪（策略插件与调度）

目标：

1. 三策略可切换并已接线：
   - `baseline_direct`
   - `relay_coop`
   - `energy_priority`
2. 切换必须走统一入口参数（命令行或配置），禁止写死。
3. 三策略同场景可运行并输出差异化结果。

主要改动目录：

- `src/strategies/*.py`
- `main.py` / `experiments/run_experiment.py`（策略参数注入）
- `src/scheduling/scheduler.py`（如需要）

必交测试：

- `test_strategy_switching`
- `test_strategy_output_schema`

PR 必附：

- 三策略对比截图或表格

### 6.5 于江楠（实验编排、落盘、可视化）

目标：

1. 每次实验输出路径规范：`results/<experiment_name>/<timestamp>/`。
2. 目录中必须包含 `metrics.json`、`records.csv`、`chart.png`。
3. `records.csv` 字段固定、可追踪、可复现。

主要改动目录：

- `experiments/run_experiment.py`
- `src/simulation/simulator.py`（`save_results`）
- `src/visualization/visualizer.py`

必交测试：

- `test_result_files_exist`
- `test_records_schema_valid`

PR 必附：

- 一次完整实验产物路径
- 图表截图

## 7. 测试组织建议（统一到 tests/）

建议按模块拆成以下文件，便于门槛检查：

1. `tests/test_environment_and_task.py`
2. `tests/test_uav_energy.py`
3. `tests/test_metrics.py`
4. `tests/test_strategies.py`
5. `tests/test_results_io.py`
6. `tests/test_smoke.py`

其中 `tests/test_smoke.py` 负责全链路最小可运行性和产物完整性校验。

## 8. PR 提交模板（每个 PR 都要有）

复制下面模板到 PR 描述：

## 变更范围

- 模块：
- 文件：
- 是否涉及公共接口变更：是/否

## 输入参数

- seed:
- num\_uavs:
- num\_agvs:
- num\_tasks:
- strategy\_type:
- max\_steps:

## 运行命令

- `python ...`

## 输出样例

- 关键日志：
- metrics.json 片段：
- records.csv 片段：

## 图表/截图

- [ ] 已附至少 1 张（chart.png 或对比图）

## 测试

- 新增测试：
- 结果：

## 兼容性与迁移（如改接口必填）

- 影响文件：
- 调用方：
- 迁移方案：

## 9. 当前仓库状态（截至 2026-04-03，已核验）

以下结论来自本地实际核验，供开工前统一基线：

1. `experiments/run_experiment.py` 的冲突标记已清理（无 `<<<<<<< / ======= / >>>>>>>`）。
2. `src/strategies/base.py` 已不再依赖 `src/domain`，导入链路正常。
3. `main.py` 语法可通过校验。
4. `pytest` 已安装（`pytest 9.0.2`），关键测试通过：
   - `tests/test_smoke.py`
   - `tests/test_strategies.py`
   - `tests/test_simulation_framework.py`

当前仍建议优先处理的事项：

1. `pytest` 会出现 `.pytest_cache` 写入权限 warning（`WinError 5`），建议统一处理目录权限或清理策略。
2. `src/strategies/` 与 `src/strategy/` 并存，建议在组内明确“新代码只进 `src/strategies/`”。

## 10. 建议的协作节奏（避免互相阻塞）

1. 先做“主干稳定 PR”：统一 `.pytest_cache` 权限策略、明确 `strategy/strategies` 目录口径。
2. 再按 5 人分工并行开发，每人只改自己目录。
3. 每晚合并前跑一次 smoke + 模块测试，严格卡门槛。
4. 所有接口变更先 RFC，再开发，再迁移，最后删旧逻辑。

***

如果你是新加入同学：先看 `src/simulation/simulator.py`，再看 `src/simulation/environment.py`，最后看你负责模块；不要一上来改策略或指标字段名。
