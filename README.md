# 马铃薯病害多Agent智能诊断系统

基于 LangGraph Multi-Agent 架构的马铃薯病害智能诊断平台。用户上传叶片图片，系统自动完成病害检测、环境感知、风险评估、知识检索，生成治疗建议和动态防治工作流。

## 系统架构

```
用户（浏览器）
    │
    ▼
Flask Web App（7 个页面路由 + API）
    │
    ▼
Supervisor Agent（LangGraph 编排）
    ├── Diagnosis Agent ──→ YOLO 检测 + 病害知识库
    ├── Risk Agent ──────→ 气象 API + 风险评分引擎
    └── Treatment Agent ─→ ChromaDB RAG + SOP + LLM 建议
    │
    ▼
前端渲染（Jinja2 + Chart.js）
```

### 双模式架构

| 模式 | 流程 | 响应时间 | 适用场景 |
|------|------|----------|----------|
| **快速模式**（默认） | YOLO → 标准化 → 字典查知识 → 天气API → 风险引擎 → LLM报告 | < 5s | 日常使用 |
| **Agent 模式** | Supervisor 编排三个子 Agent，LLM 通过 Function Calling 自主调用工具 | ~15s | 演示 Multi-Agent 能力 |

## 技术栈

| 层级 | 技术 | 用途 |
|------|------|------|
| Agent 框架 | LangGraph + LangChain | Multi-Agent 编排、ReAct Agent、工具调用 |
| 大语言模型 | mimo-v2.5-pro（小米 MiMo） | 诊断建议生成、工作流动态决策 |
| 工具调用 | OpenAI Function Calling + @tool 装饰器 | 7 个自定义工具，LLM 自主选择调用 |
| 目标检测 | YOLOv8n（Ultralytics） | 叶片病斑检测（早疫病/晚疫病） |
| 向量数据库 | ChromaDB | 农业知识语义检索 |
| Embedding | BAAI/bge-small-zh-v1.5（HuggingFace） | 中文文本向量化 |
| Web 框架 | Flask + Jinja2 | 后端路由、模板渲染 |
| 前端 | 自定义 CSS + Chart.js + Lucide Icons | 响应式 UI、数据可视化 |
| 外部 API | OpenWeatherMap | 实时气象数据（温度/湿度/降雨） |

## 快速开始

### 1. 安装依赖

```bash
pip install flask ultralytics langchain langchain-openai langgraph chromadb sentence-transformers requests markdown
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
├── app.py                      # Flask 应用入口
├── train.py                    # YOLOv8 训练脚本
│
├── agents/                     # Multi-Agent 模块
│   ├── supervisor.py           # Supervisor 编排器
│   ├── diagnosis_agent.py      # 诊断 Agent
│   ├── risk_agent.py           # 风险评估 Agent
│   ├── treatment_agent.py      # 治疗 Agent
│   └── tools.py                # 7 个 @tool 工具函数
│
├── ai/                         # LLM 集成
│   ├── llm_agent.py            # mimo-v2.5-pro 调用（主用）
│   ├── agent.py                # DeepSeek 调用（备用）
│   └── rag_retriever.py        # 快速模式字典检索
│
├── rag/                        # RAG 向量检索
│   ├── vectorstore.py          # ChromaDB 初始化
│   ├── retriever.py            # 语义检索接口
│   └── ingest.py               # 数据入库脚本
│
├── knowledge/                  # 知识库
│   ├── disease_db.py           # 病害信息
│   ├── pesticide_db.py         # 农药数据
│   ├── sop_db.py               # SOP 标准流程
│   └── disease_normalizer.py   # 标签标准化
│
├── engine/                     # 业务引擎
│   ├── decision_engine.py      # 风险评分引擎
│   └── workflow_engine.py      # 动态工作流引擎
│
├── yolo/                       # YOLO 检测
│   └── predict.py              # 推理接口
│
├── utils/                      # 工具
│   └── weather_api.py          # 气象 API 封装
│
├── templates/                  # Jinja2 模板
│   ├── base.html               # 基础布局
│   ├── index.html              # 首页
│   ├── diagnosis.html          # 病害诊断
│   ├── dashboard.html          # 数据看板
│   ├── workflow.html           # 防治工作流
│   ├── history.html            # 历史记录
│   ├── knowledge.html          # 病害知识库
│   ├── analytics.html          # 数据分析
│   └── settings.html           # 系统设置
│
├── static/                     # 静态资源
│   ├── css/main.css            # 自定义 CSS 设计系统
│   ├── uploads/                # 用户上传图片
│   └── results/                # YOLO 检测结果图
│
├── models/                     # YOLO 模型权重
│   ├── best.pt                 # 训练好的检测模型
│   └── yolov8n.pt              # 预训练基座模型
│
├── dataset/                    # 训练数据集
│   ├── data.yaml               # 数据集配置
│   ├── train/                  # 训练集
│   └── valid/                  # 验证集
│
├── logs/                       # 运行日志
│   └── diagnosis_history.json  # 诊断历史记录
│
└── docs/                       # 项目文档
```

## 效果展示

### YOLO 模型训练

训练曲线（mAP50、Precision、Recall 随 Epoch 变化）：

![训练曲线](runs/detect/potato_disease2/results.png)

混淆矩阵：

![混淆矩阵](runs/detect/potato_disease2/confusion_matrix.png)

F1 曲线：

![F1曲线](runs/detect/potato_disease2/BoxF1_curve.png)

PR 曲线：

![PR曲线](runs/detect/potato_disease2/BoxPR_curve.png)

### 检测效果示例

<!-- TODO: 替换为实际检测效果图 -->

| 早疫病检测 | 晚疫病检测 |
|:---:|:---:|
| ![早疫病检测](static/results/result_1780989541.jpg) | ![晚疫病检测](static/results/result_1780990542.jpg) |

### 系统界面

<!-- TODO: 替换为实际界面截图 -->

| Dashboard 数据看板 | 病害诊断页面 |
|:---:|:---:|
| ![Dashboard](docs/screenshots/dashboard.png) | ![诊断页面](docs/screenshots/diagnosis.png) |

| Multi-Agent 协作流程 | 防治工作流 |
|:---:|:---:|
| ![Agent 流程](docs/screenshots/agent_flow.png) | ![工作流](docs/screenshots/workflow.png) |

> 注：系统界面截图需要手动截取后放入 `docs/screenshots/` 目录。

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
- 涵盖病害信息、农药数据、SOP 流程三类知识

### 4. Multi-Agent 协作

- LangGraph Supervisor 模式编排三个子 Agent
- 每个 Agent 拥有专属 prompt 和 2-3 个工具
- LLM 通过 Function Calling 自主决策调用顺序和参数

### 5. 动态防治工作流

- SOP 标准流程 + LLM 动态调整
- 根据农户反馈（效果明显/无改善/恶化）自适应生成下一步方案
- 支持插入动态任务应对突发天气变化

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
