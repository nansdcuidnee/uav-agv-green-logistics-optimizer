# ALNS Relay 架构说明

## 一、四层架构总览

```
┌─────────────────────────────────────────────────────────────┐
│              ALNS 全局联合优化层                            │
│  (ALNS Unified Strategy)                                   │
│  ┌───────────────────────────────────────────────────────┐  │
│  │ Destroy/Repair 算子 | 模拟退火接受准则 | 迭代优化     │  │
│  └───────────────────────────────────────────────────────┘  │
├─────────────────────────────────────────────────────────────┤
│              统一评分层                                     │
│  (Unified Scorer)                                          │
│  ┌───────────────────────────────────────────────────────┐  │
│  │ direct/relay 统一评估 | 能耗/时间/距离多指标加权     │  │
│  └───────────────────────────────────────────────────────┘  │
├─────────────────────────────────────────────────────────────┤
│              中继候选生成层                                 │
│  (Relay Candidate Generator)                               │
│  ┌───────────────────────────────────────────────────────┐  │
│  │ 候选点采样 | 可行性预筛选 | 候选池构建               │  │
│  └───────────────────────────────────────────────────────┘  │
├─────────────────────────────────────────────────────────────┤
│              任务与执行模式定义层                           │
│  (Task & Execution Mode Definition)                        │
│  ┌───────────────────────────────────────────────────────┐  │
│  │ 任务模型 | direct/relay 模式语义 | UAV/AGV 模型     │  │
│  └───────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
```

---

## 二、任务与执行模式定义层

### 2.1 任务模型

任务定义包含：
- `start_point`: 任务起点坐标 (x, y)
- `end_point`: 任务终点坐标 (x, y)
- `payload`: 载荷重量
- `priority`: 优先级
- `deadline`: 截止时间（可选）

### 2.2 Direct 模式语义

**定义**: UAV 直接从当前位置起飞，途经任务起点（取货），然后飞往任务终点（送货）。

**路径**: UAV_current_pos → task.start_point → task.end_point

**适用场景**: AGV 距离过远、AGV 不可用、或任务距离较短时。

### 2.3 Relay 模式语义

**定义**: AGV 先移动到中继点 (relay_point)，UAV 在 AGV 到达后从该中继点起飞执行任务。

**路径**: 
1. AGV: AGV_current_pos → relay_point（等待）
2. UAV: UAV_current_pos → [瞬间移动到 relay_point] → task.start_point → task.end_point → relay_point（返航）

**关键假设**:
- UAV 位置在 AGV 到达中继点时**瞬间更新**到 relay_point（无连续移动仿真）
- 任务状态从 `waiting_for_agv` 转为 `in_progress` 触发位置更新
- 记录 `UAV_DEPLOYED_AT_RELAY` 事件标记部署完成

---

## 三、中继候选生成层

### 3.1 候选点生成策略

候选点来源于以下位置：
1. AGV 当前位置
2. 任务起点附近采样点
3. AGV 到任务起点连线上的等距点

### 3.2 候选池构建

候选池按 `(task, uav)` 对组织，包含：
- `direct_candidates`: 直接配送可行性评估结果
- `relay_candidates`: 中继配送候选点列表

### 3.3 预筛选逻辑

候选点需满足：
- 在环境边界内
- 无障碍物碰撞
- UAV 续航可达性初步检查

---

## 四、统一评分层

### 4.1 评分指标体系

| 指标 | 权重 | 计算方式 |
|-----|------|---------|
| 时间成本 | configurable | 飞行距离 / 速度 |
| UAV 能耗 | configurable | 飞行距离 × 单位能耗 |
| AGV 能耗 | configurable | 移动距离 × 单位能耗 |
| 等待惩罚 | 固定值 5.0 | relay 模式固定惩罚 |
| Fallback 风险 | 固定值 0.3 | relay 模式风险系数 |

### 4.2 单目标加权公式

```
total_cost = (time_weight × time_cost) + 
             (uav_energy_weight × uav_energy) + 
             (agv_energy_weight × agv_energy) + 
             wait_penalty + 
             fallback_risk
```

> **重要声明**: 本项目采用**多指标加权单目标优化**，所有指标通过权重系数归一化后合并为单一成本值，**不采用 Pareto 多目标优化**。

### 4.3 Direct vs Relay 评分差异

| 维度 | Direct 模式 | Relay 模式 |
|-----|------------|-----------|
| UAV 路径 | 起点→终点 | 中继点→起点→终点→中继点 |
| AGV 能耗 | 0 | AGV 到中继点距离 × 能耗系数 |
| 等待惩罚 | 0 | 固定值 5.0 |
| Fallback 风险 | 0.1 | 0.3 |
| 时间成本 | 较短 | 包含 AGV 移动时间 |

---

## 五、ALNS 全局联合优化层

### 5.1 核心组件

| 组件 | 职责 |
|-----|------|
| **初始解构造** | 使用 regret-2 启发式构建初始任务分配方案 |
| **Destroy 算子** | 随机或策略性移除部分任务分配 |
| **Repair 算子** | 基于候选池重新插入任务 |
| **模拟退火** | 控制接受劣质解的概率，避免局部最优 |

### 5.2 候选池与 ALNS 的关系

```
候选池 (Candidate Pool)                    ALNS 迭代优化
    │                                          │
    ▼                                          ▼
预筛选 + 粗评                          带路线上下文的精评
    │                                          │
    └──────────────────┬───────────────────────┘
                       │
                       ▼
               共用统一评分器
               (Unified Scorer)
```

**关键区别**:
- **候选池**: 无路线上下文，独立评估每个 `(task, uav, [agv])` 组合
- **ALNS**: 考虑 UAV/AGV 已有路线，评估插入位置对整体路线的影响

---

## 六、完整流程示例

### 场景设定

- **UAV**: 位置 (0, 0)，电量 100%
- **AGV**: 位置 (500, 500)
- **任务**: 起点 (200, 200)，终点 (300, 300)

### 步骤 1：候选生成

```python
# 生成 relay 候选点
relay_candidates = RelayCandidateGenerator.generate_candidates(
    uav=uav, 
    task=task, 
    agv=agv, 
    environment=env
)
# 输出: [(350, 350), (300, 300), ...]

# 评估 direct 可行性
direct_result = scorer.evaluate_direct_insertion(uav, task)
# 输出: {"cost_delta": 15.2, "feasibility": True}
```

### 步骤 2：候选评分

```python
# 评估每个 relay 候选点
for relay_point in relay_candidates:
    result = scorer.evaluate_relay_insertion(
        uav=uav,
        task=task,
        agv=agv,
        relay_point=relay_point
    )
    # 输出: {"cost_delta": 12.8, "feasibility": True}
```

### 步骤 3：ALNS 选择

```python
# ALNS 迭代过程
initial_solution = regret2_initial_solution(uavs, tasks, candidates)

for iteration in range(max_iterations):
    # Destroy: 移除部分分配
    destroyed_solution = destroy_operator(initial_solution)
    
    # Repair: 重新插入
    repaired_solution = repair_operator(destroyed_solution, candidates)
    
    # 模拟退火接受判断
    if accept_criterion(initial_solution, repaired_solution, temperature):
        initial_solution = repaired_solution
```

### 步骤 4：仿真执行

```python
# 策略返回分配结果
assignment = {
    "task_id": 1,
    "uav_id": 1,
    "agv_id": 1,
    "mode": "RELAY",
    "relay_point": (350, 350)
}

# 执行阶段 1: AGV 移动
agv.status = "moving_to_relay"
agv.destination = (350, 350)
# ... AGV 逐步移动 ...

# 执行阶段 2: AGV 到达，UAV 部署
# [AGV_ARRIVE_RELAY 事件]
# [UAV_DEPLOYED_AT_RELAY 事件]
uav.update_position((350, 350))  # 瞬间移动
task.status = "in_progress"

# 执行阶段 3: UAV 执行任务
uav.path = path_planner.plan_path((350, 350), (300, 300))
# ... UAV 逐步飞行 ...
task.complete()
```

---

## 七、当前实现中的语义不一致与风险

### 7.1 执行层与评分层语义差异

| 层面 | 评分层假设 | 执行层实际 |
|-----|-----------|-----------|
| UAV 初始位置 | 假设在 relay_point 起飞 | 需通过 `UAV_DEPLOYED_AT_RELAY` 事件更新 |
| 返航路径 | 假设返回 relay_point | 实际执行可能不返航 |

### 7.2 状态转换风险

1. **任务状态时序**: `waiting_for_agv` → `in_progress` 的转换依赖 AGV 到达事件
2. **Fallback 机制**: 等待超时后自动切换到 direct 模式，可能导致路径规划不一致
3. **空值安全**: `task.assigned_uav` 可能为 None，需防御性检查

### 7.3 优化层假设

1. **静态评估**: 评分时假设 AGV 能按时到达，但实际可能因其他任务延迟
2. **独立评估**: 候选池评估不考虑 AGV 路线冲突，可能导致执行时冲突
3. **能量模型简化**: 能耗计算基于距离线性模型，未考虑实际飞行条件

### 7.4 事件记录完整性

部分边界情况缺少事件记录：
- AGV 到达但任务已取消
- UAV 部署失败（无 assigned_uav）
- Fallback 触发时的状态转换

---

## 八、参考文献

1. [src/strategies/alns_unified.py](file:///d:/uav-agv-green-logistics-optimizer/src/strategies/alns_unified.py) - ALNS 统一策略实现
2. [src/strategies/alns/scoring.py](file:///d:/uav-agv-green-logistics-optimizer/src/strategies/alns/scoring.py) - 统一评分器
3. [src/simulation/simulator.py](file:///d:/uav-agv-green-logistics-optimizer/src/simulation/simulator.py) - 仿真执行层
4. [src/strategies/alns/operators.py](file:///d:/uav-agv-green-logistics-optimizer/src/strategies/alns/operators.py) - Destroy/Repair 算子
