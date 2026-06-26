# 马铃薯病害多Agent智能诊断系统

基于 LangGraph Multi-Agent 架构的马铃薯病害智能诊断平台。用户上传叶片图片，系统自动完成病害检测、环境感知、风险评估、知识检索，生成治疗建议和动态防治工作流。支持多轮对话记忆，同一用户可连续追问。

## 系统架构

```
用户（浏览器）
    │
    ▼
Flask Web App（10 个路由）
    │
    ├── 快速模式：直接函数调用 → YOLO → 风险引擎 → LLM 报告（<5s）
    │
    ├── Supervisor 模式：LangGraph 编排三个 ReAct Agent
    │   ├── Diagnosis Agent ──→ YOLO 检测 + 病害知识库
    │   ├── Risk Agent ──────→ 气象 API + 风险评分引擎
    │   └── Treatment Agent ─→ ChromaDB RAG + SOP + LLM 建议
    │
    └── StateGraph 模式：原生 StateGraph + Checkpointer
        START → detect → disease_info → weather → risk → treatment → update_history → END
                                      ↓ (healthy)
                                     END
```

### 三种运行模式

| 模式 | 实现方式 | 响应时间 | 特点 |
|------|---------|----------|------|
| **快速模式** | 直接函数调用 + LLM 报告 | < 5s | 默认模式，单次 LLM 调用，性能优先 |
| **Supervisor 模式** | `langgraph_supervisor` 编排三个 ReAct Agent | ~15s | LLM 自主决策工具调用顺序，完整 Function Calling 链路 |
| **StateGraph 模式** | 原生 `StateGraph` + `Checkpointer` | ~10s | 开发者定义图结构，条件边分支 + 多轮对话记忆 |

### 多轮对话

基于 LangGraph Checkpointer 实现用户级状态持久化：

- 通过 `thread_id` 关联同一用户的多次诊断（Flask session 自动管理）
- 每轮诊断完成后 `update_history_node` 自动追加摘要到 `conversation_history`
- LLM 生成建议时注入历史上下文，支持"上次那个病再详细说说"等连续交互
- `MemorySaver` 内存级持久化，重启后清空

## 技术栈

| 层级 | 技术 | 用途 |
|------|------|------|
| Agent 框架 | LangGraph（StateGraph / Supervisor / Checkpointer） | Multi-Agent 编排、状态持久化、条件分支 |
| Agent 模式 | ReAct Agent + Function Calling（7 个 @tool） | LLM 自主决策工具调用 |
| 大语言模型 | DeepSeek Chat（OpenAI 兼容接口） | 诊断建议生成、工作流动态决策 |
| 向量数据库 | ChromaDB | 农业知识语义检索（potato_knowledge 集合） |
| Embedding | BAAI/bge-small-zh-v1.5（HuggingFace） | 中文文本向量化 |
| 目标检测 | YOLOv8n（Ultralytics） | 叶片病斑检测（早疫病/晚疫病） |
| Web 框架 | Flask + Jinja2 | 后端路由、模板渲染 |
| 前端 | 自定义 CSS + Chart.js | 响应式 UI、数据可视化 |
| 外部 API | OpenWeatherMap | 实时气象数据（温度/湿度/降雨） |

## 快速开始

### 1. 安装依赖

```bash
pip install flask ultralytics langchain langchain-openai langgraph langgraph-checkpoint chromadb sentence-transformers requests python-dotenv
```

### 2. 配置 API Key

创建 `.env` 文件：

```env
DEEPSEEK_API_KEY=your_deepseek_api_key
DEEPSEEK_BASE_URL=https://api.deepseek.com
OPENWEATHER_API_KEY=your_openweather_api_key
```

### 3. 初始化向量数据库（可选）

```bash
python -m rag.ingest
```

首次运行自动下载 Embedding 模型（约 100MB），将知识库数据写入 ChromaDB（`chroma_db/` 目录）。快速模式不依赖此步骤。

### 4. 启动应用

```bash
python app.py
```

浏览器访问 `http://localhost:5000`。

## 效果展示

### 数据看板

首页展示今日诊断数、累计诊断、高风险数量、平均评分、主要病害分布、风险等级分布等统计指标。

![数据看板](docs/screenshots/数据看板.png)

### 病害知识库

浏览早疫病、晚疫病的详细信息，包括病原菌、叶片/茎秆/块茎症状、发病环境条件、推荐农药（成分、施药方式、浓度、间隔、安全提示）。

![病害知识库](docs/screenshots/病害知识库.png)

### 快速模式诊断

上传叶片图片后，系统依次完成 YOLO 检测（标注病斑框）、风险评分（多因子加权）、AI 诊断报告生成，全流程 < 5 秒。

| YOLO 检测结果 | 风险分析 + 检测详情 | AI 诊断报告 |
|:---:|:---:|:---:|
| ![检测结果](docs/screenshots/快速模式_1.png) | ![风险分析](docs/screenshots/快速模式_2.png) | ![诊断报告](docs/screenshots/快速模式_3.png) |

### Multi-Agent 协作诊断

Supervisor 协调器将任务分派给三个专业 Agent：诊断 Agent（YOLO + 知识库）、风险 Agent（气象 + 评分）、治疗 Agent（RAG + SOP + LLM），前端实时展示协作流程。

| Supervisor 流程编排 | Agent 详细执行步骤 | 最终诊断报告 |
|:---:|:---:|:---:|
| ![流程编排](docs/screenshots/Multi-Agent_1.png) | ![执行步骤](docs/screenshots/Multi-Agent_2.png) | ![诊断报告](docs/screenshots/Multi-Agent_3.png) |

### StateGraph 诊断

原生 LangGraph StateGraph 实现，6 个节点依次执行，支持条件边（健康叶片跳过风险评估和治疗），前端可视化展示节点执行流程。

| StateGraph 流程可视化 | 检测详情 + 风险分析 |
|:---:|:---:|
| ![StateGraph流程](docs/screenshots/StateGraph_1.png) | ![风险分析](docs/screenshots/StateGraph_2.png) |

### 防治工作流

基于 SOP 标准流程的动态防治工作流。农户每完成一步可反馈执行效果，LLM 根据反馈动态调整下一步方案：效果明显则进阶，无改善则升级措施，恶化则启动紧急方案。

| SOP 标准流程 | LLM 动态调整 | 执行反馈与迭代 |
|:---:|:---:|:---:|
| ![SOP流程](docs/screenshots/防治工作流_1.png) | ![动态调整](docs/screenshots/防治工作流_2.png) | ![执行反馈](docs/screenshots/防治工作流_3.png) |

## 核心模块详解

### 风险评分引擎

`engine/decision_engine.py` — 多因子加权评分（0-100 分），四维度叠加：

| 因子 | 权重上限 | 评分规则 |
|------|---------|---------|
| 病斑数量 | +40 | 20+处: +40, 10-19处: +25, 5-9处: +15 |
| 平均置信度 | +20 | ≥80%: +20, ≥60%: +10 |
| 环境条件 | +45 | 湿度≥85%: +25, 降雨: +20, 病害适温: +15~20 |
| 生长期 | +15 | 块茎期: +15, 生长期: +10 |

风险等级：≥70 高风险，40-69 中风险，<40 低风险。每个因子附带可读的风险原因。

### RAG 知识检索

`rag/` 目录 — ChromaDB + bge-small-zh-v1.5 中文 Embedding：

- **数据入库**（`rag/ingest.py`）：将病害信息、农药数据、SOP 流程三类知识写入 ChromaDB，每条文档附带 metadata（`disease_id`、`type`）
- **语义检索**（`rag/retriever.py`）：`search_knowledge_base(query, doc_type, disease_id, top_k)` 支持自然语言查询 + metadata 过滤
- **集合**：`potato_knowledge`，持久化到 `chroma_db/` 目录

### 工具调用（Function Calling）

`agents/tools.py` — 7 个 `@tool` 函数，供 ReAct Agent 自主调用：

| 工具 | 功能 |
|------|------|
| `detect_disease` | YOLO 检测，返回病斑坐标、置信度、标注图 |
| `get_disease_info` | 查询病害知识库（病原菌、症状、防治策略） |
| `get_weather` | 调用 OpenWeatherMap API 获取实时气象 |
| `compute_risk_score` | 多因子风险评分 |
| `search_knowledge_base` | ChromaDB 语义检索 |
| `get_sop` | 获取标准防治 SOP 步骤 |
| `generate_treatment_advice` | RAG + LLM 生成治疗建议 |

### 动态防治工作流

`engine/workflow_engine.py` — SOP 静态流程 + LLM 动态调整：

1. 从 `sop_db` 获取标准 SOP 步骤（按病害 + 风险等级）
2. 农户逐步执行并反馈效果（效果明显 / 无改善 / 恶化 / 遇到困难）
3. LLM 根据反馈动态生成下一步方案：
   - 效果明显 → 进阶步骤
   - 无改善 → 升级更强措施
   - 恶化 → 紧急方案
   - 遇到困难 → 替代方案
   - 全部完成 → `is_final: true`

### 知识库

`knowledge/` 目录 — 纯 Python dict 实现，无数据库依赖：

| 文件 | 内容 |
|------|------|
| `disease_db.py` | 2 种病害（早疫病/晚疫病）的病原菌、症状、发病环境、推荐农药 |
| `pesticide_db.py` | 6 种农药的成分、施药方式、浓度、间隔、安全提示 |
| `sop_db.py` | 按病害 × 风险等级的 SOP 步骤（低/中/高各 1-4 步） |
| `disease_normalizer.py` | YOLO 标签 → 标准病害 ID 映射（支持中文别名） |

### Token 监控面板

`/token_dashboard` — 追踪 LLM 调用的 token 消耗：

- 每次 LLM 调用自动记录到 `logs/token_log.csv`（时间戳、调用方式、病害、prompt/completion/total tokens、耗时）
- Chart.js 可视化：token 趋势折线图、prompt vs completion 对比、各方式平均 token 柱状图

## 页面路由

| 路由 | 方法 | 功能 |
|------|------|------|
| `/dashboard` | GET | 数据看板：今日诊断、累计统计、病害分布、风险分布 |
| `/diagnosis` | GET/POST | 病害诊断：图片上传 + 三模式切换 |
| `/api/agent_diagnosis` | POST | Multi-Agent 诊断 API（返回 JSON + 流程追踪） |
| `/api/langgraph_diagnosis` | POST | StateGraph 诊断 API（返回 JSON，支持多轮对话） |
| `/workflow` | GET | 防治工作流：SOP 步骤展示 + 动态调整 |
| `/next_task` | POST | 动态任务生成 API（LLM 根据反馈生成下一步） |
| `/history` | GET | 诊断历史：按病害/风险等级筛选 |
| `/knowledge` | GET | 病害知识库浏览 |
| `/analytics` | GET | 数据分析：趋势图、分布统计 |
| `/token_dashboard` | GET | LLM Token 使用统计 |

## 项目结构

```
potato_disease_project/
├── app.py                          # Flask 应用入口（10 个路由）
├── train.py                        # YOLOv8 训练脚本
├── xml2yolo.py                     # XML → YOLO 标签格式转换
├── data.yaml                       # YOLO 数据集配置
│
├── agents/                         # Multi-Agent 模块
│   ├── supervisor.py               # Supervisor 编排器 + 快速模式入口
│   ├── langgraph_diagnosis.py      # 原生 StateGraph（Checkpointer + 多轮对话）
│   ├── diagnosis_agent.py          # 诊断 Agent（ReAct）
│   ├── risk_agent.py               # 风险评估 Agent（ReAct）
│   ├── treatment_agent.py          # 治疗 Agent（ReAct）
│   └── tools.py                    # 7 个 @tool 工具函数
│
├── ai/                             # LLM 集成
│   ├── llm_agent.py                # DeepSeek 调用（主用，含 RAG + 环境 + 历史上下文）
│   ├── agent.py                    # DeepSeek 调用（备用，简化 prompt）
│   └── rag_retriever.py            # 快速模式字典检索
│
├── rag/                            # RAG 向量检索
│   ├── vectorstore.py              # ChromaDB 初始化 + bge-small-zh Embedding
│   ├── retriever.py                # 语义检索接口（支持 metadata 过滤）
│   └── ingest.py                   # 数据入库脚本
│
├── knowledge/                      # 知识库（纯 Python dict）
│   ├── disease_db.py               # 病害信息（早疫病/晚疫病）
│   ├── pesticide_db.py             # 农药数据（6 种）
│   ├── sop_db.py                   # SOP 标准流程
│   └── disease_normalizer.py       # 标签标准化映射
│
├── engine/                         # 业务引擎
│   ├── decision_engine.py          # 风险评分引擎（四因子加权）
│   └── workflow_engine.py          # 动态工作流引擎（SOP + LLM 自适应）
│
├── yolo/                           # YOLO 检测
│   └── predict.py                  # 推理接口（加载 best.pt，返回标注图）
│
├── utils/                          # 工具
│   └── weather_api.py              # OpenWeatherMap API 封装
│
├── templates/                      # Jinja2 模板（9 个页面）
│   ├── base.html                   # 基础布局（导航栏 + 侧边栏）
│   ├── dashboard.html              # 数据看板
│   ├── diagnosis.html              # 病害诊断（三模式切换）
│   ├── workflow.html               # 防治工作流
│   ├── history.html                # 诊断历史
│   ├── knowledge.html              # 病害知识库
│   ├── analytics.html              # 数据分析
│   ├── token_dashboard.html        # Token 统计
│   └── settings.html               # 设置
│
├── static/                         # 静态资源（CSS / 上传 / 检测结果）
├── models/                         # YOLO 模型权重（best.pt / yolov8n.pt）
├── dataset/                        # 训练数据集（522 训练 + 132 验证）
│   ├── images/train/ + val/
│   └── labels/train/ + val/
├── logs/                           # 运行日志（diagnosis_history.json / token_log.csv）
├── docs/                           # 项目文档 + 截图
└── .env                            # API 密钥（不提交到 Git）
```

## YOLO 模型训练

```bash
python train.py
```

| 参数 | 值 |
|------|------|
| 基座模型 | YOLOv8n（预训练） |
| 训练轮数 | 100 epochs |
| 输入尺寸 | 640 × 640 |
| Batch Size | 8 |
| 早停 | patience=20 |
| 训练集 | 522 张图片 |
| 验证集 | 132 张图片 |
| 类别 | early_blight（早疫病）、late_blight（晚疫病） |

数据标注使用 Pascal VOC XML 格式，通过 `xml2yolo.py` 转换为 YOLO txt 格式。

## 扩展指南

### 添加新病害

1. `knowledge/disease_db.py` — 添加病害信息（病原菌、症状、环境条件）
2. `knowledge/pesticide_db.py` — 添加对应农药
3. `knowledge/sop_db.py` — 添加 SOP 流程（低/中/高风险各一套）
4. `knowledge/disease_normalizer.py` — 添加标签映射
5. `python -m rag.ingest` — 更新向量数据库
6. 如需新 YOLO 类别：`dataset/` 添加标注数据，修改 `dataset/data.yaml`，重新训练

Agent 层面无需修改，工具是通用的。

### 添加新页面

1. `templates/` 下新建 Jinja2 模板，继承 `base.html`
2. `app.py` 添加路由函数

## License

本项目仅供学习和研究使用。
