# UAV-AGV协同配送优化系统 - 在线演示页面

## 概述

本项目提供了一个基于Streamlit的在线演示页面，用于展示UAV-AGV协同绿色配送优化系统的实验结果。

## 功能特点

- **首页**：项目简介、方法亮点、配送模式说明
- **单次运行展示**：展示已有实验的详细结果和可视化图表
- **消融实验展示**：展示ALNS消融实验的对比结果
- **关于页面**：数据来源说明和项目结构

## 快速开始

### 本地运行

#### 方式1：使用启动脚本（Windows）

双击运行 `run_demo_app.bat`，启动后访问 http://localhost:8501

#### 方式2：命令行运行

必须使用有 streamlit 环境的 Python 解释器：

```bash
"C:\Users\31675\AppData\Local\Programs\Python\Python311\python.exe" -m streamlit run demo_app.py
```

### 部署到云端

#### Streamlit Cloud（推荐，免费）

1. 将代码推送到GitHub仓库
2. 访问 https://streamlit.io/cloud
3. 点击 "New app"
4. 选择仓库和分支
5. 设置 Main file path: `demo_app.py`
6. 点击 "Deploy!"

#### 其他部署方式

**Heroku:**
```bash
echo "web: streamlit run demo_app.py --server.port $PORT" > Procfile
git push heroku main
```

**Docker:**
```dockerfile
FROM python:3.9
WORKDIR /app
RUN pip install streamlit pandas pillow
COPY demo_app.py .
EXPOSE 8501
CMD ["streamlit", "run", "demo_app.py", "--server.port=8501", "--server.address=0.0.0.0"]
```

## 页面说明

### 1. 首页
- 项目标题和简介
- 核心技术亮点（UAV-AGV协同、绿色优化、ALNS）
- 配送模式说明（直接配送、中继配送）

### 2. 单次运行展示
自动选择最新的运行结果目录，展示：
- 关键性能指标（完成率、能耗、配送时间等）
- 可视化图表（轨迹地图、任务进度、能耗曲线等）
- 实验配置信息

### 3. 消融实验展示
自动选择最新的消融实验目录，展示：
- 实验配置信息
- 综合对比图（2x2子图）
- 与Full ALNS的差值对比图
- 详细指标对比图表
- 数据表格

### 4. 关于页面
- 数据来源说明
- 项目结构介绍
- 技术栈信息

## 数据目录

### 单次运行结果
```
results/runs/<场景名>/<时间戳>/
├── metrics.json         # 关键指标
├── metadata.json        # 配置信息
├── plots/              # 可视化图表
│   ├── trajectory_map.png
│   ├── task_progress.png
│   ├── energy_curve.png
│   ├── kpi_summary.png
│   ├── battery_status.png
│   └── coordination_events.png
└── records/            # 详细记录
    ├── steps.csv
    ├── tasks.csv
    └── ...
```

### 消融实验结果
```
results/ablation/alns_ablation_<时间戳>/
├── metadata.json              # 实验元信息
├── summary.json              # 汇总信息
├── aggregate_by_variant.csv   # 聚合数据
├── comparison_vs_full.csv    # 与Full对比数据
├── figures/                  # 汇总图表
│   ├── ablation_overview.png
│   └── ablation_vs_full_delta.png
└── plots_summary/           # 详细图表
    ├── completion_rate_by_variant.png
    ├── total_energy_by_variant.png
    └── ...
```

## 配置选项

页面会自动选择最新的结果目录。如果需要指定特定目录，可以在代码中修改 `demo_app.py` 的以下函数：

```python
def find_latest_run_dir():
    return Path("results/runs/pickup_delivery_generated/20260603_214047")

def find_latest_ablation_dir():
    return Path("results/ablation/alns_ablation_<时间戳>")
```

## 依赖项

- streamlit >= 1.28.0
- pandas >= 2.0.0
- pillow >= 8.0.0

安装命令：
```bash
pip install streamlit pandas pillow
```

## 注意事项

1. **数据来源**：所有展示数据均来源于项目真实实验结果，未经人工修改
2. **离线运行**：页面可以在离线环境下运行，只展示已有数据
3. **无需训练**：页面不执行任何仿真计算，只展示已有结果
4. **响应式设计**：支持不同屏幕尺寸，自动调整布局

## 页面性质

**静态结果展示页面**（非可交互在线仿真）

- 展示已有实验结果
- 可视化图表展示
- 数据表格交互
- 不执行仿真计算
- 不修改实验数据
- 不支持实时仿真

## 支持

如有问题，请查看：
- [项目README](README.md)
- [消融实验设计](experiments/alns_ablation_design.md)
- [ALNS架构说明](docs/alns_relay_architecture.md)
