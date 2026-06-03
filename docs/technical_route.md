# 技术路线

## 1. 当前路线

```text
场景建模
  -> UAV / AGV / Task 建模
  -> 能耗模型与路径规划
  -> 三种候选策略
  -> 仿真实验
  -> 指标对比与适用场景分析
```

当前只写已实现内容，不把尚未实现的策略自动选择机制写进主线。

## 2. 场景与对象建模

| 对象 | 路径 | 当前作用 |
|---|---|---|
| UAV | `src/core/uav.py` | 位置、电量、任务状态、负载能力 |
| AGV | `src/core/agv.py` | 位置、电量、移动与充电支撑 |
| Task | `src/core/task.py` | 起点、终点、优先级、状态 |
| Environment | `src/simulation/environment.py` | 维护设备、任务、地图状态 |

## 3. 能耗与路径

| 模块 | 路径 | 当前作用 |
|---|---|---|
| UAV 能耗 | `src/energy/energy_model.py` | 起飞、巡航、悬停、降落分阶段计算 |
| AGV 能耗 | `src/energy/energy_model.py` | 根据行驶距离计算 |
| 路径规划 | `src/planning/path_planner.py` | 提供路径规划能力 |

## 4. 策略设计

### baseline_direct

基线直送策略，用来对照不引入中继协同时的表现。

### energy_priority

能耗感知评分策略，使用距离、电量、负载、任务优先级等因素进行任务分配。当前实验结果不占优，后续需要检查适用场景。

### relay_coop

UAV-AGV 中继协同策略，核心流程：

```text
选择可用 AGV
  -> 计算 AGV 到任务起点距离
  -> 计算中继点
  -> AGV 移动到中继点
  -> UAV 等待或执行任务
  -> 等待超时则 fallback 到直接配送
```

## 5. 实验验证

| 实验 | 目的 |
|---|---|
| 策略对比 | 在同一场景下比较三种策略 |
| 消融实验 | 拆分策略、协同、能耗模型等因素 |
| 鲁棒性实验 | 检查多随机种子、规模、电池容量、故障下的稳定性 |

## 6. 当前已实现技术点

| 技术点 | 支撑文件 | 说明 |
|---|---|---|
| UAV-AGV 中继协同 | `src/strategies/relay_coop.py` | AGV 移动到中继点，UAV 执行配送 |
| 动态中继点计算 | `src/strategies/relay_coop.py` | 中继距离由 AGV 到任务起点距离约束 |
| 中继等待 fallback | `src/simulation/simulator.py` | 等待 AGV 超时后切换到直接配送 |
| 能耗感知任务评分 | `src/strategies/energy_priority.py` | 使用距离、电量、负载、优先级等因素评分 |
| UAV 分阶段能耗模型 | `src/energy/energy_model.py` | 起飞、巡航、悬停、降落分别计算 |
| 多策略对比实验 | `experiments/compare_strategies.py` | 同一配置下比较三种策略 |
| 鲁棒性实验框架 | `experiments/run_robustness.py` | 支持 seed、scale、battery、failure 等配置 |

## 7. 当前不能过度表述的点

| 表述风险 | 当前情况 | 建议写法 |
|---|---|---|
| 某策略始终最好 | 目前只有有限场景结果 | 写策略适用性分析 |
| `relay_coop` 总能耗最低 | 最新结果不支持 | 写完成率、准时率、单任务能耗、单位距离能耗更好 |
| 自动选择策略 | 当前没有独立策略选择器 | 写多策略对比框架 |
| 充分验证 | 实验规模仍有限 | 写当前配置下观察到 |

## 8. 指标解释

不同策略完成任务数可能不同，因此不能只看总能耗。建议同时看：

- `completion_rate`
- `on_time_rate`
- `total_energy`
- `avg_energy_per_task`
- `energy_per_km`
- `charging_count`
- `total_distance_agv`
- `avg_wait_time_at_relay`
