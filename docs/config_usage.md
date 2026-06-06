配置文件使用说明
================

## 配置目录结构

```
configs/
├── base/                 # 基础模板配置
│   ├── base.yaml
│   └── base_explicit.yaml
├── generated/            # 场景配置（自动生成场景）
│   ├── pickup_delivery_generated.yaml
│   ├── scene_small.yaml
│   ├── scene_medium.yaml
│   └── scene_large.yaml
├── explicit/             # 手工定义的 demo/qualification 场景
│   ├── demo.yaml
│   └── qualification.yaml
└── experiments/          # 鲁棒性测试或旧实验配置
    ├── default_experiment.yaml
    ├── robustness_battery.yaml
    ├── robustness_failure.yaml
    ├── robustness_scale.yaml
    └── robustness_seed.yaml
```

## 目录用途说明

### base/ - 基础模板

包含系统的基础配置模板，定义了所有配置项的默认值和结构。其他配置文件通过 `extends` 字段继承基础配置。

- `base.yaml`: 标准基础模板，用于自动生成场景
- `base_explicit.yaml`: 显式场景的基础模板

### generated/ - 场景配置

包含用于自动生成场景的配置文件，系统会根据这些配置自动生成任务、障碍物和环境。

当前 ALNS 消融实验只使用以下 4 个配置文件：

| 配置文件 | 场景类型 | 描述 |
|---------|---------|------|
| `pickup_delivery_generated.yaml` | pickup_delivery_generated | 取送货场景，无障碍物，适合快速验证 |
| `scene_small.yaml` | generated | 小型场景（500x500地图，5个障碍物，2个禁飞区） |
| `scene_medium.yaml` | generated | 中型场景（默认地图，15个障碍物，5个禁飞区） |
| `scene_large.yaml` | generated | 大型场景（2000x2000地图，30个障碍物，10个禁飞区） |

### explicit/ - 手工定义场景

包含手工定义的场景配置，用于特定的演示或验证目的。

- `demo.yaml`: 演示场景
- `qualification.yaml`: 资格验证场景

### experiments/ - 实验配置

包含鲁棒性测试和其他专项实验的配置文件。

- `default_experiment.yaml`: 默认实验配置
- `robustness_battery.yaml`: 电池鲁棒性测试
- `robustness_failure.yaml`: 故障鲁棒性测试
- `robustness_scale.yaml`: 规模鲁棒性测试
- `robustness_seed.yaml`: 种子鲁棒性测试

## ALNS 消融实验配置说明

ALNS 消融实验当前只使用 `configs/generated/` 目录下的 4 个配置文件：

1. **pickup_delivery_generated.yaml**: 无障碍场景，用于验证基本功能
2. **scene_small.yaml**: 小型有障碍场景
3. **scene_medium.yaml**: 中型有障碍场景
4. **scene_large.yaml**: 大型有障碍场景

## 配置加载方式

配置文件通过 `config.config_loader.load_config()` 函数加载，支持继承机制：

```python
from config.config_loader import load_config

# 加载单个配置
config = load_config("configs/generated/scene_small.yaml")

# 加载多个配置用于实验
configs = [
    "configs/generated/pickup_delivery_generated.yaml",
    "configs/generated/scene_small.yaml",
    "configs/generated/scene_medium.yaml",
    "configs/generated/scene_large.yaml"
]
```

## 常用配置字段

### 场景基本配置

| 字段 | 类型 | 描述 |
|-----|------|------|
| `scene_type` | string | 场景类型：generated 或 pickup_delivery_generated |
| `description` | string | 场景描述 |
| `seed` | int | 随机种子 |

### 地图配置

| 字段 | 类型 | 描述 |
|-----|------|------|
| `map_size.width` | int | 地图宽度（米） |
| `map_size.height` | int | 地图高度（米） |

### 设备配置

| 字段 | 类型 | 描述 |
|-----|------|------|
| `num_uavs` | int | 无人机数量 |
| `num_agvs` | int | AGV数量 |

### 任务配置

| 字段 | 类型 | 描述 |
|-----|------|------|
| `num_tasks` | int | 任务数量 |
| `task_density` | float | 任务点分布密度 |

### 障碍物配置

| 字段 | 类型 | 描述 |
|-----|------|------|
| `obstacles.count` | int | 障碍物数量 |
| `obstacles.types` | list | 障碍物类型列表 |

### 禁飞区配置

| 字段 | 类型 | 描述 |
|-----|------|------|
| `no_fly_zones.count` | int | 禁飞区数量 |
