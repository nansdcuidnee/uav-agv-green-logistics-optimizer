# UAV-AGV 协同绿色配送 - 前端展示系统

基于 Vue 3 + Vite + TypeScript 构建的实验结果展示前端，用于展示 UAV-AGV 协同配送系统的实验数据和分析结果。

## 技术栈

- **框架**: Vue 3 + Composition API
- **构建工具**: Vite 6
- **语言**: TypeScript
- **路由**: Vue Router 4
- **UI 组件**: Element Plus
- **图表**: Apache ECharts
- **CSV 解析**: PapaParse

## 页面结构

| 路由 | 页面 | 功能描述 |
|------|------|----------|
| `/` | Overview | 总览页，展示核心指标、趋势图、策略洞察 |
| `/runs` | Run Detail | 单次运行详情，包含时序图、任务分析、协同事件 |
| `/ablation` | Ablation | 消融实验对比，支持多场景、多变体对比分析 |

## 核心组件

- `HeroBanner` - 顶部横幅，展示项目标题和核心 CTA
- `KpiGrid` / `MetricCard` - KPI 指标展示
- `RunSelector` - 运行选择器
- `RunTrendChart` - 趋势图表（折线/面积图）
- `ScatterInsightChart` - 散点洞察图
- `TimelinePanel` - 协同事件时间线
- `TaskTable` - 任务表格
- `PlotGallery` - 图片画廊
- `AblationBarChart` - 消融对比柱状图
- `HeatmapPanel` - Scene × Variant 热力图
- `EmptyState` - 空状态组件

## 数据架构

```
src/
├── services/
│   ├── dataLoader.ts      # JSON/CSV 数据加载工具
│   ├── runRepository.ts   # 运行数据仓库
│   └── ablationRepository.ts  # 消融实验数据仓库
├── types/
│   └── index.ts           # TypeScript 类型定义
└── views/                 # 页面组件
```

## 设计规范

### 配色方案

| 颜色类型 | 颜色值 | 用途 |
|----------|--------|------|
| 主色 | `#0a4d68` | 导航栏、按钮、强调文字 |
| 辅色 | `#088395` | 渐变、图标 |
| 强调色 | `#f99500` | 高亮、警告 |
| 成功色 | `#2e7d32` | 正向指标 |
| 危险色 | `#c62828` | 负向指标 |

### 间距规范

- 页面内边距: 24px
- 卡片间距: 16-24px
- 内容区块间距: 24px

## 快速开始

```bash
# 安装依赖
npm install

# 开发模式
npm run dev

# 生产构建
npm run build

# 预览构建结果
npm run preview
```

## 数据加载说明

前端采用静态数据加载模式，数据来源：

1. **Mock 数据**: `public/mock-results/` 目录下的样例数据
2. **真实数据**: 可从 `results/` 目录复制到 `public/mock-results/`

## 项目结构

```
frontend/
├── public/
│   └── mock-results/          # Mock 数据目录
├── src/
│   ├── components/            # 可复用组件
│   ├── views/                 # 页面组件
│   ├── services/              # 数据服务
│   ├── types/                 # 类型定义
│   ├── router/                # 路由配置
│   ├── App.vue                # 根组件
│   ├── main.ts                # 入口文件
│   └── style.css              # 全局样式
├── index.html
├── package.json
├── tsconfig.json
└── vite.config.ts
```

## 浏览器支持

- Chrome (推荐)
- Firefox
- Safari
- Edge

## 开发注意事项

1. 所有数据加载必须处理异常情况（文件缺失、格式错误等）
2. 组件必须提供空状态处理
3. 图表必须响应式适配
4. 使用 Composition API 编写组件逻辑