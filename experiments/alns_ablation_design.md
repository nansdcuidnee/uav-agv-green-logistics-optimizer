# ALNS Unified Strategy 消融实验设计文档

## 1. 实验概述

### 1.1 实验目的
本消融实验旨在系统评估 ALNS Unified 策略中各核心组件对整体性能的贡献，识别关键设计决策的有效性，为算法优化和学术论文撰写提供实证依据。

### 1.2 研究问题
1. 直送/中继统一决策机制的必要性和有效性？
2. 候选池构建策略（多样性 vs 贪婪 vs 随机）对解质量的影响？
3. 算子自适应权重机制是否能提升搜索效率？
4. 算子复杂度对最终性能的影响程度？

### 1.3 实验约束
- 不修改核心 ALNS 算法逻辑（如迭代框架、接受准则等）
- 保持仿真环境和参数一致性
- 确保实验结果可复现
- 不虚构实验结果

---

## 2. 方法与变体定义

### 2.1 参考组
**参考方法**: `unified_full`（完整 ALNS Unified 策略）
- 同时支持直送和中继配送模式
- 使用 `diverse_topk` 候选池策略（平衡贪婪选择与多样性）
- 启用自适应算子权重机制
- 使用完整算子集（3种destroy算子 + 3种repair算子）

### 2.2 消融变体

所有消融变体均与 `unified_full` 进行比较，仅改变指定组件，其余参数保持一致。

#### 2.2.1 direct_only（仅直送模式）
- **实验目的**: 评估直送模式的独立贡献，验证纯直送策略的性能边界
- **改动组件**: 禁用中继配送能力
- **控制变量**: `allow_relay=False`，其余参数与 unified_full 一致
- **验证假设**: 直送模式在电量充足时可独立完成大部分任务，但可能在远距离任务上表现较差
- **主要观察指标**: `completion_rate`, `total_energy`, `direct_count`, `relay_count`
- **比较方式**: 对比 unified_full，评估直送模式的效率-能耗权衡
- **可能风险**: 若任务距离普遍较远，直送模式可能无法完成所有任务

#### 2.2.2 relay_only（仅中继模式）
- **实验目的**: 评估中继模式的独立贡献，验证 AGV-UAV 协同的必要性
- **改动组件**: 禁用直送配送能力
- **控制变量**: `allow_direct=False`，其余参数与 unified_full 一致
- **验证假设**: 中继模式可完成任务但效率较低，存在 AGV 配合开销
- **主要观察指标**: `completion_rate`, `avg_wait_time_at_relay`, `total_distance_agv`, `relay_count`
- **比较方式**: 对比 unified_full，评估中继模式的协同开销
- **可能风险**: 中继点等待时间可能过长，影响整体效率

#### 2.2.3 greedy_pool（贪婪候选池）
- **实验目的**: 评估贪婪候选选择对搜索效率的影响
- **改动组件**: 将 `diverse_topk` 替换为 `greedy_topk`
- **控制变量**: `candidate_pool_strategy="greedy_topk"`，其余参数与 unified_full 一致
- **验证假设**: 贪婪选择可能陷入局部最优，牺牲解质量以换取初期收敛速度
- **主要观察指标**: `completion_rate`, `total_energy`, `avg_delivery_time`
- **比较方式**: 对比 unified_full，评估多样性保持的价值
- **可能风险**: 贪婪选择可能过早收敛到较差解

#### 2.2.4 random_pool（随机候选池）
- **实验目的**: 评估随机候选选择对搜索多样性的影响
- **改动组件**: 将 `diverse_topk` 替换为 `random_topk`
- **控制变量**: `candidate_pool_strategy="random_topk"`，其余参数与 unified_full 一致
- **验证假设**: 随机选择可增加搜索多样性但降低结果稳定性
- **主要观察指标**: `completion_rate`（均值和标准差）, `total_energy`
- **比较方式**: 对比 unified_full，评估策略性选择的必要性
- **可能风险**: 随机性可能导致结果波动较大

#### 2.2.5 fixed_weights（固定算子权重）
- **实验目的**: 评估自适应算子权重机制的价值
- **改动组件**: 禁用算子权重自适应更新机制
- **控制变量**: `adaptive_operator_weights=False`，其余参数与 unified_full 一致
- **验证假设**: 自适应权重可根据问题动态调整搜索策略，提升搜索效率
- **主要观察指标**: `completion_rate`, `total_energy`, `avg_delivery_time`
- **比较方式**: 对比 unified_full，评估自适应机制的有效性
- **可能风险**: 固定权重可能无法适应不同问题特征

#### 2.2.6 simple_ops（简化算子集）
- **实验目的**: 评估算子复杂度对性能的影响
- **改动组件**: 将完整算子集替换为基础算子
- **控制变量**: `destroy_operator_set=["random_remove"]`, `repair_operator_set=["greedy_insert"]`
- **验证假设**: 复杂算子可提升解质量但增加计算开销
- **主要观察指标**: `completion_rate`, `total_energy`, `avg_delivery_time`
- **比较方式**: 对比 unified_full，评估算子多样性的价值
- **可能风险**: 简化算子可能缺乏足够的搜索能力

### 2.3 可选未来工作（无独立开关）
以下消融项目前无独立代码开关支持，列为未来工作：
- **no_fallback**: 禁用 fallback 机制
- **no_charging_loop**: 禁用充电循环优化

---

## 3. 实验设置

### 3.1 实验场景

| 场景名称 | 配置文件 | UAV数量 | AGV数量 | 任务数量 | 地图大小 |
|----------|----------|---------|---------|---------|----------|
| pickup_delivery_generated（主场景） | configs/generated/pickup_delivery_generated.yaml | 2 | 2 | 5 | 1000x1000 |
| scene_small（扩展场景） | configs/generated/scene_small.yaml | 1 | 1 | 3 | 500x500 |
| scene_medium（扩展场景） | configs/generated/scene_medium.yaml | 2 | 2 | 5 | 1000x1000 |
| scene_large（扩展场景） | configs/generated/scene_large.yaml | 3 | 3 | 10 | 1500x1500 |

### 3.2 随机种子
- **种子列表**: `[42, 123, 456, 789, 1024]`
- **目的**: 确保统计稳定性，减少随机波动对结果的影响

### 3.3 仿真参数
- **最大步数**: 500 步（所有变体保持一致）
- **UAV 初始电量**: 100%
- **充电阈值**: 30%（低于此值触发充电）

### 3.4 评价指标体系

| 指标 | 类别 | 说明 | 单位 |
|------|------|------|------|
| `completion_rate` | 主指标-效率 | 任务完成率（核心性能指标） | % |
| `total_energy` | 主指标-能耗 | 总能耗（能量效率指标） | Wh |
| `avg_delivery_time` | 主指标-效率 | 平均配送时间（时间效率指标） | 步 |
| `relay_count` | 行为指标 | 中继任务数（协同行为度量） | 个 |
| `direct_count` | 行为指标 | 直送任务数（直送行为度量） | 个 |
| `avg_wait_time_at_relay` | 行为指标 | 中继平均等待时间（协同效率度量） | 步 |
| `fallback_count` | 鲁棒性指标 | Fallback 触发次数（鲁棒性度量） | 次 |
| `charging_count` | 鲁棒性指标 | 充电次数（能量管理度量） | 次 |
| `failed_tasks` | 鲁棒性指标 | 失败任务数（任务完成度量） | 个 |
| `total_distance` | 距离指标 | 总行驶距离（整体路径长度） | 米 |
| `total_distance_uav` | 距离指标 | UAV 总行驶距离 | 米 |
| `total_distance_agv` | 距离指标 | AGV 总行驶距离 | 米 |

**指标分类说明**:
- **主指标**: 用于评估核心性能，包括效率（completion_rate, avg_delivery_time）和能耗（total_energy）
- **行为指标**: 用于解释策略的行为特征，分析直送/中继决策模式和协同效率
- **鲁棒性指标**: 用于评估系统的稳定性和容错能力
- **距离指标**: 用于分析路径规划质量和资源利用

---

## 4. 实验矩阵

### 4.1 变体配置矩阵

| 变体名称 | allow_direct | allow_relay | candidate_pool_strategy | adaptive_operator_weights | destroy_operator_set | repair_operator_set |
|----------|-------------|-------------|------------------------|--------------------------|---------------------|---------------------|
| unified_full | True | True | diverse_topk | True | ["random_remove", "worst_remove", "high_energy_remove"] | ["greedy_insert", "regret_insert", "relay_aware_regret_insert"] |
| direct_only | True | False | diverse_topk | True | ["random_remove", "worst_remove", "high_energy_remove"] | ["greedy_insert", "regret_insert", "relay_aware_regret_insert"] |
| relay_only | False | True | diverse_topk | True | ["random_remove", "worst_remove", "high_energy_remove"] | ["greedy_insert", "regret_insert", "relay_aware_regret_insert"] |
| greedy_pool | True | True | greedy_topk | True | ["random_remove", "worst_remove", "high_energy_remove"] | ["greedy_insert", "regret_insert", "relay_aware_regret_insert"] |
| random_pool | True | True | random_topk | True | ["random_remove", "worst_remove", "high_energy_remove"] | ["greedy_insert", "regret_insert", "relay_aware_regret_insert"] |
| fixed_weights | True | True | diverse_topk | False | ["random_remove", "worst_remove", "high_energy_remove"] | ["greedy_insert", "regret_insert", "relay_aware_regret_insert"] |
| simple_ops | True | True | diverse_topk | True | ["random_remove"] | ["greedy_insert"] |

### 4.2 实验流程
1. 对每个场景，使用相同配置运行所有变体
2. 每个变体使用 5 个种子独立运行
3. 记录每个种子的详细指标数据
4. 计算每个变体在各场景下的均值和标准差
5. 每个消融变体仅与 unified_full 进行比较

---

## 5. 统计分析方法

### 5.1 描述性统计
- **报告内容**: 每个变体在各指标上的均值（Mean）和标准差（Std）
- **格式**: `指标名 = 均值 ± 标准差`

### 5.2 比较方法
- **比较基准**: 所有消融变体仅与 `unified_full` 比较
- **效果评估**: 计算相对差异百分比
  ```
  Relative Change = (Variant Value - unified_full Value) / unified_full Value × 100%
  ```

### 5.3 统计显著性（计划）
- **检验方法**: 配对 t-test（同一组种子运行不同变体）
- **显著性水平**: α = 0.05
- **注意**: 本设计文档仅描述检验计划，实际显著性结论需在运行实验后得出

---

## 6. 消融开关有效性验证

### 6.1 验证方法与预期行为

#### 6.1.1 allow_direct=False 验证
- **预期行为**: 候选池中所有任务的 `direct` 字段均为 `False`

#### 6.1.2 allow_relay=False 验证
- **预期行为**: 候选池中所有任务的 `relay` 列表均为空

#### 6.1.3 candidate_pool_strategy 验证
- **预期行为**: 不同策略在同一候选集上产生可区分的选择结果

#### 6.1.4 adaptive_operator_weights=False 验证
- **预期行为**: 调用 `update_operator_weights` 后权重不发生变化

#### 6.1.5 simple_ops 验证
- **预期行为**: 只返回指定的算子集合

### 6.2 验证标准
- 所有验证测试必须通过
- 消融开关必须确实改变策略行为
- 结果必须在相同种子下可复现

---

## 7. 结果保存与归档

### 7.1 输出目录结构
```
results/ablation/alns_ablation_<timestamp>/
├── summary.csv              # 所有实验汇总（含均值和标准差）
├── summary.json             # 汇总数据（结构化格式）
└── runs/
    ├── unified_full_seed_42/
    │   ├── metrics.json     # 单轮运行指标
    │   ├── records/         # 详细记录
    │   └── plots/           # 可视化图表
    ├── direct_only_seed_42/
    └── ...
```

### 7.2 归档要求
- 保留所有原始数据文件
- 记录完整实验参数配置
- 生成可读的实验报告

---

## 8. 风险与注意事项

### 8.1 潜在风险
1. **场景特异性**: 实验结果可能仅适用于当前场景配置
2. **种子数量**: 5个种子可能不足以保证统计显著性
3. **参数敏感性**: 结果可能对未控制的参数敏感

### 8.2 缓解措施
1. 测试多种场景规模（small/medium/large）
2. 必要时增加种子数量至 10 个以上
3. 进行参数敏感性分析

---

## 附录：消融开关实现位置

| 参数 | 文件 | 行号 |
|------|------|------|
| allow_direct | src/strategies/alns_unified.py | 第 54-55 行 |
| allow_relay | src/strategies/alns_unified.py | 第 55-56 行 |
| candidate_pool_strategy | src/strategies/alns_unified.py | 第 56-57 行 |
| adaptive_operator_weights | src/strategies/alns_unified.py | 第 61-62 行 |
| destroy_operator_set | src/strategies/alns_unified.py | 第 498-512 行 |
| repair_operator_set | src/strategies/alns_unified.py | 第 514-528 行 |