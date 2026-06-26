# 前端产品化改造 & Multi-Agent 升级说明

## 一、启动方式

```bash
cd potato_disease_project
python app.py
```

浏览器访问 `http://localhost:5000`，会自动跳转到 Dashboard 首页。

---

## 二、测试流程

### 1. Dashboard 首页（`/dashboard`）

- 左侧菜单点击「数据看板」
- 首次打开数据为空，进行几次诊断后会自动填充统计卡片和图表
- 包含：今日诊断数、累计诊断数、高风险数、病害分布饼图、风险等级柱状图、最近记录表格

### 2. 病害诊断（`/diagnosis`）

- 点击左侧「病害诊断」
- 上传一张马铃薯叶片图片（jpg/png）
- 选择地区和生长期
- 点击「开始诊断」
- 等待 YOLO + LLM 处理（首次约 5-10 秒）
- 页面会展示：检测病斑数、风险等级、风险评分、原始图片、检测结果、诊断详情表格、AI 诊断报告
- 诊断结果会自动保存到历史记录

### 3. 防治工作流（`/workflow`）

- 诊断完成后，页面底部有「进入工作流」按钮
- 也可以直接访问 `/workflow?disease=early_blight&risk_level=中风险`
- 显示步骤导航条、当前步骤详情、反馈面板
- 选择反馈标签（效果明显/无改善/情况恶化等），点击「提交反馈，获取下一步」
- AI 会根据反馈动态调整下一步建议

### 4. 历史记录（`/history`）

- 查看所有诊断记录
- 支持按病害类型、风险等级筛选

### 5. 病害知识库（`/knowledge`）

- 左侧选择病害（早疫病/晚疫病）
- 右侧展示：病原体、症状、发病条件、防治策略、推荐药剂详情表格

### 6. 数据分析（`/analytics`）

- 病害类型分布饼图、风险等级分布柱状图、风险评分趋势折线图
- 诊断记录明细表格

### 7. 系统设置（`/settings`）

- 模型配置、LLM 配置、系统信息、气象 API 配置（只读展示）

---

## 三、修改内容清单

### 3.1 Multi-Agent 架构改造（第一阶段）

| 文件 | 变更 | 说明 |
|------|------|------|
| `agents/supervisor.py` | 重写 | 拆分为 fast 模式（直接调用）和 agent 模式（完整 Supervisor） |
| `agents/tools.py` | 新增 | 7 个 `@tool` 定义，封装 YOLO/天气/风险/知识库/SOP/LLM |
| `agents/diagnosis_agent.py` | 新增 | LangGraph ReAct Agent，负责病害检测 |
| `agents/risk_agent.py` | 新增 | LangGraph ReAct Agent，负责风险评估 |
| `agents/treatment_agent.py` | 新增 | LangGraph ReAct Agent，负责防治建议 |
| `rag/vectorstore.py` | 新增 | ChromaDB 向量数据库初始化 |
| `rag/ingest.py` | 新增 | 知识库数据灌入 ChromaDB |
| `rag/retriever.py` | 新增 | 语义检索接口 |

### 3.2 性能优化（第二阶段）

| 文件 | 变更 | 说明 |
|------|------|------|
| `agents/supervisor.py` | 优化 | fast 模式下 YOLO 只调用一次，避免重复推理 |

**核心改动**：原来 Supervisor 的 Diagnosis Agent 会再次调用 YOLO，导致同一张图推理两次。现在 fast 模式直接调用函数获取结构化数据，只用一次 LLM 调用生成建议。

### 3.3 前端产品化（第三阶段）

#### 新增文件

| 文件 | 说明 |
|------|------|
| `static/css/main.css` | 全局 CSS 框架（CSS 变量、组件库、响应式） |
| `static/js/main.js` | 全局 JS（侧边栏切换、工具函数） |
| `templates/base.html` | 基础模板（侧边栏 + 顶栏 + 内容区骨架） |
| `templates/dashboard.html` | Dashboard 首页（统计卡片 + Chart.js 图表） |
| `templates/diagnosis.html` | 病害诊断页（上传 + 三列结果 + AI 报告） |
| `templates/workflow.html` | 防治工作流页（步骤流 + 反馈面板） |
| `templates/history.html` | 历史记录页（筛选 + 表格） |
| `templates/knowledge.html` | 病害知识库页（病害列表 + 详情） |
| `templates/analytics.html` | 数据分析页（Chart.js 图表 + 明细表） |
| `templates/settings.html` | 系统设置页（配置信息展示） |

#### 修改文件

| 文件 | 变更 | 说明 |
|------|------|------|
| `app.py` | 重写路由 | 新增 7 个页面路由，根路由重定向到 Dashboard，诊断结果自动保存历史 |

#### 保留文件

| 文件 | 说明 |
|------|------|
| `templates/index.html` | 旧版单页界面，保留备用（不再被路由引用） |
| `templates/token_dashboard.html` | Token 统计面板，通过 `/token_dashboard` 访问 |

---

## 四、页面路由对照

| 路由 | 页面 | 功能 |
|------|------|------|
| `/` | 重定向 | 自动跳转到 `/dashboard` |
| `/dashboard` | 数据看板 | 统计概览、图表、最近记录 |
| `/diagnosis` | 病害诊断 | 图片上传、YOLO 检测、AI 报告 |
| `/workflow` | 防治工作流 | SOP 步骤流、反馈驱动 |
| `/history` | 历史记录 | 诊断历史、筛选过滤 |
| `/knowledge` | 病害知识库 | 病害信息、药剂详情 |
| `/analytics` | 数据分析 | 趋势图表、统计分析 |
| `/settings` | 系统设置 | 配置信息展示 |
| `/next_task` | API | 工作流下一步（POST） |
| `/token_dashboard` | Token 面板 | LLM Token 使用统计 |

---

## 五、数据存储

诊断历史保存在 `logs/diagnosis_history.json`，格式：

```json
[
  {
    "time": "2026-06-09 14:30:00",
    "disease": "early_blight",
    "disease_name": "马铃薯早疫病",
    "risk_level": "中风险",
    "risk_score": 55,
    "detection_count": 8,
    "location": "Beijing",
    "growth_stage": "vegetative",
    "temperature": 25,
    "humidity": 72
  }
]
```

每次诊断完成后自动追加记录，Dashboard 和 Analytics 页面从该文件读取统计数据。

---

## 六、技术栈

- **前端**：自定义 CSS（CSS 变量 + Grid + Flexbox）、Chart.js、Lucide Icons
- **后端**：Flask + Jinja2 模板
- **AI**：YOLOv8n 目标检测 + mimo-v2.5-pro LLM + ChromaDB RAG
- **Agent**：LangGraph + LangChain（Supervisor 模式）
- **天气**：OpenWeatherMap API
