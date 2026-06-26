# 技术说明书 — 马铃薯病害多Agent智能诊断系统

## 一、系统运行全流程

以下以终端日志为线索，逐步讲解每次用户操作背后发生了什么。

---

### 1.1 病害诊断（POST /diagnosis）

用户上传一张叶片图片，选择「南京」「生长期」，点击「开始诊断」。

```
终端输出：
0169.jpg: 640x640 6 early_blights, 12.6ms
🌦 天气API返回：{... humidity: 26, temp: 29.15 ...}
POST /diagnosis HTTP/1.1" 200
```

**内部执行顺序（共 7 步）：**

```
Step 1  YOLO 目标检测
        文件：yolo/predict.py → predict_image()
        模型：models/best.pt（YOLOv8n）
        输入：640x640 图片
        输出：6 个 early_blight 检测框 + 置信度 + 标注图
        耗时：12.6ms（推理） + 60.5ms（前处理） + 27.5ms（后处理）

Step 2  病害标签标准化
        文件：knowledge/disease_normalizer.py → normalize_disease()
        作用：YOLO 输出的 "early_blight" → 统一 ID "early_blight"

Step 3  病害知识查询
        文件：knowledge/disease_db.py → get_disease_info()
        作用：从 Python 字典查出病害名称、病原体、症状、防治策略
        ⚠️ 这里是字典精确匹配，不是 RAG

Step 4  气象数据获取
        文件：utils/weather_api.py → get_weather("Nanjing")
        API：OpenWeatherMap REST API
        输出：温度 29.15℃、湿度 26%、天气描述、是否降雨
        终端可见：🌦 天气API返回：{...}

Step 5  风险评分计算
        文件：engine/decision_engine.py → compute_risk_score()
        输入：检测数量(6) + 置信度 + 温度 + 湿度 + 降雨 + 生长期
        规则：病斑数量评分 + 置信度评分 + 环境评分 + 生长期评分
        输出：总分（0-100）、风险等级（低/中/高）、评分原因列表

Step 6  初始 SOP 任务
        文件：knowledge/sop_db.py → get_sop("early_blight", "低风险")
        作用：根据病害+风险等级，取出标准防治步骤序列的第一步

Step 7  LLM 生成诊断报告
        文件：agents/supervisor.py → _generate_llm_advice()
        模型：mimo-v2.5-pro（小米 MiMo）
        输入：病害信息 + 环境信息 + 风险评分 + 推荐药剂
        输出：Markdown 格式的诊断报告
        ⚠️ 快速模式下只有这一次 LLM 调用，不经过 Agent
```

**关键点：整个诊断流程只调用一次 LLM（Step 7），YOLO 也只运行一次（Step 1）。**

---

### 1.2 RAG 什么时候调用？

**RAG 在诊断流程中不会被调用。** 具体来说：

| 场景 | 是否调用 RAG | 说明 |
|------|-------------|------|
| 病害诊断（POST /diagnosis） | ❌ 不调用 | 直接查 `disease_db.py` 字典 |
| 诊断报告生成（LLM 建议） | ❌ 不调用 | 直接查 `pesticide_db.py` 字典 |
| 工作流下一步（POST /next_task） | ❌ 不调用 | LLM 根据上下文生成 |
| Agent 模式（run_agent_pipeline） | ✅ 调用 | Treatment Agent 用 `search_knowledge_base` 工具 |

**RAG 的调用路径：**

```
Agent 模式（完整 Multi-Agent）
    └── Treatment Agent
        └── 调用 search_knowledge_base 工具
            └── rag/retriever.py → search_knowledge_base()
                └── ChromaDB 语义检索
                    └── 返回相关文档片段
```

**快速模式为什么不调 RAG？**
快速模式（`run_diagnosis_pipeline`）直接从 Python 字典读取数据，速度快。字典数据和 ChromaDB 里的数据是同一份，只是检索方式不同：
- 字典：精确匹配 key（`disease_db["early_blight"]`）
- RAG：语义搜索（用户输入"叶子长斑" → 匹配到"早疫病"相关内容）

**RAG 的价值体现在 Agent 模式中**，当 LLM 需要自主检索知识时，语义搜索比字典灵活得多。

---

### 1.3 防治工作流是怎么运行的？

用户在诊断结果页点击「进入工作流」，跳转到 `/workflow?disease=early_blight&risk_level=低风险`。

#### 第一步：页面加载

```
终端输出：
🌦 天气API返回：{... Beijing ...}
GET /workflow?disease=early_blight&risk_level=低风险 HTTP/1.1" 200
```

**内部执行：**
1. 调用 `get_weather("Beijing")` 获取实时天气（用于后续 LLM 参考）
2. 调用 `get_sop("early_blight", "低风险")` 获取 SOP 步骤列表
3. 将步骤数据传给模板渲染

#### 第二步：用户提交反馈

用户看到第一步「田间巡查」，选择反馈标签「无明显改善」，点击提交。

```
终端输出：
LLM原始返回: {"title":"加强杀菌剂应用","content":"...","tips":[...],"reasoning":"...","is_final":false}
POST /next_task HTTP/1.1" 200
```

**内部执行：**
1. 前端 JS 发送 `POST /next_task`，携带：病害、风险等级、当前步骤、反馈文本、环境数据、已完成步骤
2. `engine/workflow_engine.py` → `generate_next_task()`
3. 调用 `ai/llm_agent.py` → `generate_workflow_step()`
4. LLM（mimo-v2.5-pro）根据反馈生成下一步建议，返回 JSON
5. 前端 JS 更新页面，显示新步骤

#### 第三步：继续反馈

用户看到第二步「加强杀菌剂应用」，选择「效果明显」，提交。

```
LLM原始返回: {"title":"马铃薯早期枯萎病控制后进阶管理","content":"...","is_final":false}
```

LLM 判断「效果明显」→ 进入进阶预防阶段。

#### 第四步：流程结束

用户选择「效果明显」，提交。

```
LLM原始返回: {"title":"马铃薯早疫病治疗完成与收获后管理","content":"...","is_final":true}
```

LLM 判断治疗完成 → `is_final: true` → 前端显示「防治流程已完成」。

**工作流核心机制：**

```
┌─────────────────────────────────────────────┐
│  SOP 标准流程（knowledge/sop_db.py）         │
│  定义了每个病害+风险等级的标准步骤序列        │
│  例：低风险 = [田间巡查, 环境管理]           │
└─────────────────┬───────────────────────────┘
                  │
                  ▼
┌─────────────────────────────────────────────┐
│  LLM 动态调整（ai/llm_agent.py）            │
│  根据农户反馈实时生成下一步                   │
│  - 效果明显 → 进阶/收尾                      │
│  - 无改善 → 加强措施                         │
│  - 情况恶化 → 紧急方案                       │
│  - 遇到困难 → 替代方案                       │
└─────────────────────────────────────────────┘
```

SOP 提供初始框架，LLM 根据实际反馈动态调整，两者结合实现「标准流程 + 个性化」。

---

### 1.4 什么时候调用智能体（Agent）？

**当前系统有两种运行模式：**

| 模式 | 入口函数 | 是否用 Agent | 速度 |
|------|---------|-------------|------|
| 快速模式（默认） | `run_diagnosis_pipeline()` | ❌ 不用 | 快（~3秒） |
| Agent 模式 | `run_agent_pipeline()` | ✅ 用 | 慢（~15秒） |

**快速模式（默认，app.py 使用的）：**
- YOLO、天气、风险评分 → 直接函数调用
- LLM 建议 → 单次 LLM 调用
- 不经过 LangGraph Agent，不用 Function Calling

**Agent 模式（需要手动切换）：**
- 创建 3 个 LangGraph ReAct Agent
- Supervisor 编排调用顺序
- LLM 通过 Function Calling 自主调用工具
- 每个 Agent 内部可能多次调用 LLM（思考→调工具→再思考）

**如何切换到 Agent 模式：**
在 `app.py` 中将 `from agents.supervisor import run_diagnosis_pipeline` 改为 `from agents.supervisor import run_agent_pipeline`，然后在诊断路由中调用 `run_agent_pipeline()`。

**Agent 模式下调用链：**

```
用户请求
    │
    ▼
Supervisor Agent（LangGraph create_supervisor）
    │
    ├──→ Diagnosis Agent（create_react_agent）
    │    ├── LLM 思考：需要检测病害
    │    ├── 调用 detect_disease 工具 → YOLO
    │    ├── 调用 get_disease_info 工具 → 知识库字典
    │    └── 返回诊断结果
    │
    ├──→ Risk Agent（create_react_agent）
    │    ├── LLM 思考：需要评估风险
    │    ├── 调用 get_weather 工具 → OpenWeatherMap
    │    ├── 调用 compute_risk_score 工具 → 风险引擎
    │    └── 返回风险评估
    │
    └──→ Treatment Agent（create_react_agent）
         ├── LLM 思考：需要生成治疗方案
         ├── 调用 search_knowledge_base 工具 → ChromaDB RAG ✅
         ├── 调用 get_sop 工具 → SOP 数据库
         ├── 调用 generate_treatment_advice 工具 → LLM
         └── 返回治疗建议
```

---

## 二、技术栈调用关系图

```
┌─────────────────────────────────────────────────────────────────┐
│                        浏览器（前端）                             │
│  HTML + CSS + JavaScript + Chart.js                             │
│  - 页面渲染：Jinja2 模板                                         │
│  - 异步请求：fetch API（工作流反馈）                               │
│  - 图表：Chart.js（Dashboard、Analytics）                        │
└──────────────────────────┬──────────────────────────────────────┘
                           │ HTTP
                           ▼
┌─────────────────────────────────────────────────────────────────┐
│                     Flask 后端（app.py）                          │
│  路由：/  /dashboard  /diagnosis  /workflow  /history            │
│        /knowledge  /analytics  /settings  /next_task            │
│  模板：Jinja2（templates/*.html）                                 │
│  数据：JSON 文件（logs/diagnosis_history.json）                   │
└──────┬──────────┬──────────┬──────────┬──────────┬──────────────┘
       │          │          │          │          │
       ▼          ▼          ▼          ▼          ▼
┌──────────┐┌──────────┐┌──────────┐┌──────────┐┌──────────┐
│ YOLO     ││ Weather  ││ Risk     ││ LLM      ││ Knowledge│
│ Detection││ API      ││ Engine   ││ Agent    ││ Base     │
│          ││          ││          ││          ││          │
│ultralytics││OpenWeather││规则引擎  ││mimo-v2.5 ││Python    │
│ YOLOv8n ││ Map API  ││多因子评分 ││ -pro     ││ 字典     │
│          ││          ││          ││          ││          │
│best.pt  ││REST API  ││decision_ ││OpenAI API││disease_db│
│          ││          ││engine.py ││兼容接口  ││pesticide │
└──────────┘└──────────┘└──────────┘────┬─────┘│_db       │
                                        │      │sop_db    │
                                        ▼      └──────────┘
                                 ┌──────────────┐
                                 │  Multi-Agent │
                                 │  (可选模式)   │
                                 │              │
                                 │ LangGraph    │
                                 │ Supervisor   │
                                 │  ├─Diagnosis │
                                 │  ├─Risk      │
                                 │  └─Treatment │
                                 │     └─RAG ✅ │
                                 └──────┬───────┘
                                        │
                                        ▼
                                 ┌──────────────┐
                                 │ ChromaDB     │
                                 │ 向量数据库    │
                                 │              │
                                 │ bge-small-zh │
                                 │ Embedding    │
                                 └──────────────┘
```

---

## 三、各技术栈具体用途

### 3.1 YOLOv8n（Ultralytics）

- **用途**：叶片病斑目标检测
- **模型文件**：`models/best.pt`
- **输入**：640×640 RGB 图片
- **输出**：检测框坐标、类别标签（early_blight/late_blight）、置信度百分比
- **调用时机**：每次诊断（POST /diagnosis）调用一次
- **调用位置**：`yolo/predict.py` → `predict_image()`
- **耗时**：约 100ms（CPU）

### 3.2 OpenWeatherMap API

- **用途**：获取实时气象数据
- **调用时机**：诊断时获取环境数据 + 工作流页面加载时获取天气
- **调用位置**：`utils/weather_api.py` → `get_weather(city)`
- **返回数据**：温度、湿度、天气描述、是否降雨
- **支持城市**：20 个中国主要城市

### 3.3 风险评分引擎（规则引擎）

- **用途**：多因子风险评估
- **调用时机**：每次诊断
- **调用位置**：`engine/decision_engine.py` → `compute_risk_score()`
- **评分因子**：病斑数量（0-40分）+ 置信度（0-20分）+ 湿度（0-25分）+ 降雨（0-20分）+ 温度适宜度（0-20分）+ 生长期（0-15分）
- **风险等级**：<40 低风险 / 40-69 中风险 / ≥70 高风险

### 3.4 mimo-v2.5-pro（LLM）

- **用途**：生成诊断报告 + 工作流动态决策
- **API**：OpenAI 兼容接口（小米 MiMo 平台）
- **调用时机 1**：诊断完成后，生成 Markdown 格式的诊断报告（`_generate_llm_advice()`）
- **调用时机 2**：工作流中，根据农户反馈生成下一步建议（`generate_workflow_step()`）
- **调用时机 3**：Agent 模式下，各 Agent 内部的 ReAct 推理循环

### 3.5 ChromaDB（向量数据库）

- **用途**：农业知识语义检索
- **Embedding 模型**：`BAAI/bge-small-zh-v1.5`（HuggingFace）
- **存储内容**：病害信息、农药数据、SOP 流程
- **调用时机**：仅在 Agent 模式下，Treatment Agent 调用 `search_knowledge_base` 工具时
- **调用位置**：`rag/retriever.py` → `search_knowledge_base()`
- **快速模式下不调用**，直接用 Python 字典查询

### 3.6 LangGraph + LangChain（Agent 框架）

- **用途**：Multi-Agent 编排和工具调用
- **核心组件**：
  - `create_react_agent`：创建 ReAct 模式的子 Agent
  - `create_supervisor`：创建 Supervisor 编排 Agent
  - `@tool` 装饰器：定义 LLM 可调用的工具
- **调用时机**：仅在 Agent 模式下（`run_agent_pipeline()`）
- **快速模式下不使用**

### 3.7 Flask + Jinja2（Web 框架）

- **用途**：HTTP 路由、模板渲染、静态文件服务
- **路由数量**：10 个（7 页面 + 2 API + 1 重定向）
- **模板引擎**：Jinja2（模板继承、条件渲染、循环）
- **自定义 Filter**：`markdown`（将 Markdown 文本转为 HTML）

### 3.8 Chart.js（前端图表）

- **用途**：数据可视化
- **使用页面**：Dashboard（饼图+柱状图）、Analytics（饼图+柱状图+折线图）
- **图表类型**：Doughnut（病害分布）、Bar（风险等级）、Line（趋势）

### 3.9 自定义 CSS 框架

- **用途**：全局 UI 样式
- **文件**：`static/css/main.css`
- **设计系统**：CSS 变量（颜色、间距、圆角、阴影）
- **组件**：侧边栏、顶栏、卡片、统计卡片、表格、标签、按钮、表单、空状态
- **响应式**：3 个断点（1024px / 768px / 480px）

---

## 四、数据流总结

```
诊断数据流：
图片 → YOLO → 检测结果 → 标准化 → 字典查病害信息
                                       ↓
城市 → 天气API → 环境数据 ──────→ 风险引擎 → 风险评分
                                       ↓
                              字典查药剂 + LLM → 诊断报告
                                       ↓
                              保存到 diagnosis_history.json

工作流数据流：
SOP字典 → 初始步骤 → 前端展示
                        ↓
               用户反馈 → LLM → 下一步建议 → 前端更新
                        ↓
               用户反馈 → LLM → 下一步建议 → ... → is_final: true → 结束

页面数据流：
Dashboard: diagnosis_history.json → 统计 + Chart.js 图表
History:   diagnosis_history.json → 筛选 + 表格
Analytics: diagnosis_history.json → 统计 + Chart.js 图表
Knowledge: disease_db + pesticide_db → 病害详情 + 药剂表格
Settings:  静态配置信息
```
