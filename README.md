# 马铃薯病害多Agent智能诊断系统

基于 LangGraph Multi-Agent 架构的马铃薯病害智能诊断平台。用户上传叶片图片，系统自动完成病害检测、环境感知、风险评估、知识检索，生成治疗建议和动态防治工作流。支持多轮对话记忆，同一用户可连续追问。

## 系统架构

```
用户（浏览器）
    │
    ▼
Flask Web App（7 个页面路由 + API）
    │
    ├── 快速模式：直接函数调用 → YOLO → 风险引擎 → LLM 报告（<5s）
    │
    ├── Supervisor 模式：LangGraph 编排三个 ReAct Agent
    │   ├── Diagnosis Agent ──→ YOLO 检测 + 病害知识库
    │   ├── Risk Agent ──────→ 气象 API + 风险评分引擎
    │   └── Treatment Agent ─→ ChromaDB RAG + SOP + LLM 建议
    │
    └── StateGraph 模式：原生 StateGraph + Checkpointer
        START → detect → [disease_info, weather] → risk → treatment → update_history → END
                                      ↓ (healthy)
                                     END
```

### 三种运行模式

| 模式 | 实现方式 | 响应时间 | 特点 |
|------|---------|----------|------|
| **快速模式** | 直接函数调用 + LLM 报告 | < 5s | 默认模式，性能优先 |
| **Supervisor 模式** | `langgraph_supervisor` 编排三个 ReAct Agent | ~15s | 完整 Tool Calling 链路 |
| **StateGraph 模式** | 原生 `StateGraph` + `Checkpointer` | ~10s | 条件边分支 + 多轮对话记忆 |

### 多轮对话

基于 LangGraph Checkpointer 实现用户级状态持久化：

- 通过 `thread_id` 关联同一用户的多次诊断
- 每轮诊断完成后自动保存摘要到 `conversation_history`
- LLM 生成建议时注入历史上下文，支持"上次那个病再详细说说"等连续交互
- Flask session 自动管理 `thread_id`，同一浏览器无需手动传参

## 技术栈

| 层级 | 技术 | 用途 |
|------|------|------|
| Agent 框架 | LangGraph（StateGraph / Supervisor / Checkpointer） | Multi-Agent 编排、状态持久化、条件分支 |
| Agent 模式 | ReAct Agent + Function Calling | LLM 自主决策工具调用 |
| 大语言模型 | mimo-v2.5-pro（小米 MiMo） | 诊断建议生成、工作流动态决策 |
| 向量数据库 | ChromaDB | 农业知识语义检索 |
| Embedding | BAAI/bge-small-zh-v1.5（HuggingFace） | 中文文本向量化（512 维） |
| 目标检测 | YOLOv8n（Ultralytics） | 叶片病斑检测（早疫病/晚疫病） |
| Web 框架 | Flask + Jinja2 | 后端路由、模板渲染 |
| 前端 | 自定义 CSS + Chart.js + Lucide Icons | 响应式 UI、数据可视化 |
| 外部 API | OpenWeatherMap | 实时气象数据（温度/湿度/降雨） |

## 快速开始

### 1. 安装依赖

```bash
pip install flask ultralytics langchain langchain-openai langgraph langgraph-checkpoint chromadb sentence-transformers requests markdown
```

### 2. 配置 API Key

在以下文件中替换 API Key：

- `ai/llm_agent.py` — mimo-v2.5-pro API Key
- `utils/weather_api.py` — OpenWeatherMap API Key

### 3. 初始化向量数据库

```bash
python rag/ingest.py
```

首次运行会自动下载 Embedding 模型（约 100MB），后续启动无需重复下载。

### 4. 启动应用

```bash
python app.py
```

浏览器访问 `http://localhost:5000`。

## 项目结构

```
potato_disease_project/
├── app.py                          # Flask 应用入口
├── train.py                        # YOLOv8 训练脚本
│
├── agents/                         # Multi-Agent 模块
│   ├── supervisor.py               # Supervisor 编排器 + 快速模式入口
│   ├── langgraph_diagnosis.py      # 原生 StateGraph 实现（Checkpointer + 多轮对话）
│   ├── diagnosis_agent.py          # 诊断 Agent（ReAct）
│   ├── risk_agent.py               # 风险评估 Agent（ReAct）
│   ├── treatment_agent.py          # 治疗 Agent（ReAct）
│   └── tools.py                    # 7 个 @tool 工具函数
│
├── ai/                             # LLM 集成
│   ├── llm_agent.py                # mimo-v2.5-pro 调用（主用）
│   ├── agent.py                    # DeepSeek 调用（备用）
│   └── rag_retriever.py            # 快速模式字典检索
│
├── rag/                            # RAG 向量检索
│   ├── vectorstore.py              # ChromaDB 初始化 + Embedding 模型
│   ├── retriever.py                # 语义检索接口（支持 metadata 过滤）
│   └── ingest.py                   # 数据入库脚本
│
├── knowledge/                      # 知识库
│   ├── disease_db.py               # 病害信息
│   ├── pesticide_db.py             # 农药数据
│   ├── sop_db.py                   # SOP 标准流程
│   └── disease_normalizer.py       # 标签标准化
│
├── engine/                         # 业务引擎
│   ├── decision_engine.py          # 风险评分引擎（多因子规则）
│   └── workflow_engine.py          # 动态工作流引擎（LLM 驱动）
│
├── yolo/                           # YOLO 检测
│   └── predict.py                  # 推理接口
│
├── utils/                          # 工具
│   └── weather_api.py              # 气象 API 封装
│
├── templates/                      # Jinja2 模板
├── static/                         # 静态资源（CSS / 上传 / 检测结果）
├── models/                         # YOLO 模型权重
├── dataset/                        # 训练数据集
├── logs/                           # 运行日志
└── docs/                           # 项目文档
```

## 功能模块

### 1. 病害检测

- 基于 YOLOv8n 目标检测，自行采集并标注数据集
- 支持早疫病（Early Blight）和晚疫病（Late Blight）两种病害
- 输出检测框、置信度、病斑数量

### 2. 风险评估

- 多因子规则引擎：病斑数量、置信度、温度、湿度、降雨、生长期
- 三级风险等级：低风险（<40）、中风险（40-69）、高风险（≥70）

### 3. RAG 知识检索

- ChromaDB 向量数据库 + bge-small-zh 中文 Embedding
- 支持自然语言语义检索（如"叶子长斑用什么药"）
- 支持 metadata 过滤（按病害类型、文档类型筛选）
- 涵盖病害信息、农药数据、SOP 流程三类知识

### 4. Multi-Agent 协作

- LangGraph Supervisor 模式编排三个 ReAct Agent
- 每个 Agent 拥有专属 prompt 和 2-3 个工具
- LLM 通过 Function Calling 自主决策调用顺序和参数

### 5. 原生 StateGraph

- 用 TypedDict 定义共享 State，节点函数读写状态
- 条件边实现分支逻辑（健康叶片跳过风险评估和治疗）
- Checkpointer（MemorySaver）实现状态持久化

### 6. 多轮对话

- `conversation_history` 字段存储历史诊断摘要
- `update_history_node` 每轮诊断完成后追加记录
- LLM 生成建议时注入历史上下文
- Flask session 自动管理 thread_id

### 7. 动态防治工作流

- SOP 标准流程 + LLM 动态调整
- 根据农户反馈（效果明显/无改善/恶化）自适应生成下一步方案
- 支持插入动态任务应对突发天气变化

## 效果展示

### YOLO 模型训练

训练曲线（mAP50、Precision、Recall 随 Epoch 变化）：

![训练曲线](runs/detect/potato_disease2/results.png)

混淆矩阵：

![混淆矩阵](runs/detect/potato_disease2/confusion_matrix.png)

### 检测效果示例

| 早疫病检测 | 晚疫病检测 |
|:---:|:---:|
| ![早疫病检测](static/results/result_1780989541.jpg) | ![晚疫病检测](static/results/result_1780990542.jpg) |

### 系统界面

| Dashboard 数据看板 | 病害诊断页面 |
|:---:|:---:|
| ![Dashboard](docs/screenshots/dashboard.png) | ![诊断页面](docs/screenshots/diagnosis.png) |

| Multi-Agent 协作流程 | 防治工作流 |
|:---:|:---:|
| ![Agent 流程](docs/screenshots/agent_flow.png) | ![工作流](docs/screenshots/workflow.png) |

## YOLO 模型训练

```bash
python train.py
```

训练参数：YOLOv8n 预训练基座，100 epochs，输入尺寸 640×640，batch_size=8。

训练数据：自行采集并标注的马铃薯叶片图片，包含 early_blight 和 late_blight 两个类别。

## 扩展指南

### 添加新病害

1. 在 `knowledge/disease_db.py` 添加病害信息
2. 在 `knowledge/pesticide_db.py` 添加对应农药
3. 在 `knowledge/sop_db.py` 添加 SOP 流程
4. 运行 `python rag/ingest.py` 更新向量数据库
5. 如需新 YOLO 类别，在 `dataset/` 添加标注数据并重新训练模型

Agent 层面无需修改，工具是通用的。

## License

本项目仅供学习和研究使用。
