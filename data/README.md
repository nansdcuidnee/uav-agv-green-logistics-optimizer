# Data Directory Documentation

## 目录结构

### 主要目录
- **maps/**: 存储地图配置文件
  - 包含地图尺寸、障碍物分布、禁飞区等信息
  - 示例：`example_map.yaml`

- **scenarios/**: 存储场景配置文件
  - 包含任务数量、资源配置、障碍物信息等
  - 示例：`example_scenario.yaml`

- **constants/**: 存储系统常量和参数
  - 包含设备参数、物理常量等
  - 示例：`device_params.yaml`

- **templates/**: 存储配置模板
  - 包含任务模板、设备配置模板等
  - 示例：`task_template.yaml`

### 辅助目录
- **raw/**: 存储原始数据
  - 未处理的原始输入数据

- **processed/**: 存储处理后的数据
  - 经过预处理的中间数据

## 文件命名规范

- 使用小写字母和下划线
- 避免使用空格和特殊字符
- 文件名应描述文件内容
- 示例：`warehouse_map.yaml`、`rush_hour_scenario.yaml`

## 数据格式规范

- **优先格式**：YAML（可读性强，适合配置文件）
- **备选格式**：JSON（适合结构化数据）
- **其他格式**：CSV（适合表格数据）

### YAML 格式建议
- 使用 2 空格缩进
- 为关键参数添加注释
- 保持结构清晰，避免过深嵌套

## 新增数据文件步骤

1. **确定数据类型**：根据数据用途选择合适的子目录
2. **创建文件**：按照命名规范创建数据文件
3. **填写内容**：根据模板或示例填写数据内容
4. **验证格式**：确保数据格式正确，无语法错误
5. **更新文档**：如果新增了数据类型或重要参数，更新此文档

## Git 管理建议

### 建议纳入版本控制的文件
- **配置文件**：maps/、scenarios/、constants/、templates/ 目录下的文件
- **示例数据**：用于测试和示例的文件
- **文档**：README.md 等说明文档

### 建议忽略的文件
- **原始数据**：raw/ 目录下的大型原始数据文件
- **处理后数据**：processed/ 目录下的中间数据
- **临时文件**：*.tmp、*.temp 等临时文件
- **日志文件**：*.log 文件

## 数据加载

使用 `src/utils/data_loader.py` 中的函数加载数据：

```python
from src.utils.data_loader import load_data

# 加载场景配置
data = load_data('scenarios', 'example_scenario.yaml')

# 加载设备参数
device_params = load_data('constants', 'device_params.yaml')
```

## 示例数据说明

- **maps/example_map.yaml**：示例地图配置，包含地图尺寸、障碍物和充电站信息
- **scenarios/example_scenario.yaml**：示例场景配置，包含任务数量、资源配置等
- **constants/device_params.yaml**：设备参数配置，包含 UAV 和 AGV 的参数
- **templates/task_template.yaml**：任务模板配置，包含任务类型、优先级等
