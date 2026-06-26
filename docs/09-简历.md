# 马铃薯病害多Agent智能诊断系统

## 项目信息

- **项目周期**：2026.03 - 2026.06
- **项目类型**：个人项目（研究生课题方向）
- **项目链接**：本地部署 Flask Web 应用

---

## 技术栈

| 层级 | 技术 | 用途 |
|------|------|------|
| **Agent 框架** | LangGraph + LangChain | Multi-Agent 编排、ReAct Agent、工具调用 |
| **大语言模型** | mimo-v2.5-pro（小米 MiMo） | 诊断建议生成、工作流动态决策 |
| **工具调用** | OpenAI Function Calling + @tool 装饰器 | 7 个自定义工具，LLM 自主选择调用 |
| **目标检测** | YOLOv8n（Ultralytics） | 叶片病斑检测（早疫病/晚疫病） |
| **向量数据库** | ChromaDB | 农业知识语义检索 |
| **Embedding** | BAAI/bge-small-zh-v1.5（HuggingFace） | 中文文本向量化 |
| **Web 框架** | Flask + Jinja2 | 后端路由、模板渲染 |
| **前端** | 自定义 CSS + Chart.js + Lucide Icons | 响应式 UI、数据可视化 |
| **外部 API** | OpenWeatherMap | 实时气象数据（温度/湿度/降雨） |
| **开发语言** | Python 3.10+ | 全栈开发 |

---

## 项目描述

面向马铃薯病害防治场景，基于 LangGraph Multi-Agent 架构构建智能诊断平台。系统实现「图像检测 → 环境感知 → 风险评估 → 知识检索 → 方案生成 → 动态干预」全链路闭环，将传统单体管道拆分为诊断、风险、治疗三个专业化 Agent，通过 Supervisor 编排协作，LLM 自主决策工具调用。

---

## 核心工作

### 1. Multi-Agent 协作架构设计

- 基于 LangGraph `create_supervisor` + `create_react_agent` 实现 Supervisor 模式
- 将系统拆分为 **诊断 Agent**、**风险评估 Agent**、**治疗 Agent** 三个独立单元
- 每个 Agent 拥有专属 system prompt 和 2-3 个工具，降低单 Agent 工具选择复杂度
- Supervisor 根据上下文自主决策调用顺序，支持并行执行和错误回退

### 2. Tool Calling 工具框架

- 基于 `langchain_core.tools.@tool` 装饰器从零构建 7 个工具函数
- 工具涵盖：YOLO 检测、病害信息查询、气象数据获取、风险评分计算、RAG 知识检索、SOP 流程获取、治疗建议生成
- LLM 通过 Function Calling 协议自主决定调用时机和参数，无需硬编码调用逻辑
- 工具函数内置参数校验和错误处理，返回结构化 JSON

### 3. RAG 知识增强检索

- 构建 ChromaDB 向量数据库，将病害信息、农药数据、SOP 流程向量化存储
- 使用 `BAAI/bge-small-zh-v1.5` 中文 Embedding 模型，支持农业术语语义理解
- 实现带 metadata 过滤的语义检索（按病害类型、文档类型过滤）
- 替代原有字典精确匹配方案，支持自然语言模糊查询

### 4. 动态防治工作流

- 基于 SOP 标准流程定义防治步骤序列
- 结合农户反馈和环境数据，LLM 动态生成下一阶段防治方案
- 支持插入动态任务（如排水、补喷）应对突发天气变化
- 实现病害管理流程闭环，从发现到防治的完整追踪

### 5. 企业级前端产品化

- 自定义 CSS 设计系统（CSS 变量、组件库、响应式布局）
- 7 个功能页面：Dashboard 数据看板、病害诊断、防治工作流、历史记录、病害知识库、数据分析、系统设置
- Chart.js 数据可视化：病害分布饼图、风险等级柱状图、趋势折线图
- 诊断历史持久化（JSON），支持筛选过滤和统计分析

---

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

---

## 项目亮点（简历用）

> **多Agent协作架构**：基于LangGraph实现Supervisor模式，将诊断、风险、治疗三个领域解耦为独立Agent，每个Agent拥有专属prompt和工具集，LLM自主决策调用顺序，降低单Agent工具选择复杂度
>
> **RAG知识增强**：构建ChromaDB向量数据库，对病害、农药、SOP数据向量化，使用bge-small-zh中文Embedding模型实现语义检索，替代字典精确匹配
>
> **Function Calling工具框架**：基于@tool装饰器封装7个领域工具，LLM通过OpenAI Function Calling协议自主选择调用，无需硬编码逻辑
>
> **动态决策闭环**：SOP标准流程 + LLM动态调整，根据农户反馈和环境变化自动生成个性化防治方案

---

## 面试高频问题

### Q: 为什么用 Multi-Agent 而不是单 Agent 加所有工具？

单 Agent 的 system prompt 需要描述所有工具的使用场景，工具集过大会导致 LLM 选择准确率下降。分 Agent 后每个 prompt 聚焦一个领域，工具集更小（2-3个），LLM 决策更准确。另外分 Agent 后可以独立测试和优化每个领域的 prompt。

### Q: RAG 检索和直接查字典有什么区别？

字典只能精确匹配 key，不支持模糊查询。ChromaDB 是向量数据库，支持语义搜索——用户问"叶子长斑用什么药"能匹配到"早疫病"的相关信息。新增病害只需添加文档，不改代码，扩展性更好。

### Q: Function Calling 怎么保证 LLM 不调错工具？

三层防御：(1) 每个 Agent 的 system prompt 限定工具使用场景；(2) 工具函数内部参数校验，返回结构化错误；(3) Supervisor 有 max_rounds 限制防止循环调用，超时回退到直接函数调用。

### Q: 怎么扩展到更多病害？

三步：(1) `knowledge/*.py` 添加新病害数据；(2) 运行 `python rag/ingest.py` 更新向量数据库；(3) 如需新 YOLO 类别，重新训练模型。Agent 层面零修改。

---

## 项目成果

- 完成端到端的 Multi-Agent 农业病害诊断系统，支持早疫病、晚疫病两种病害识别
- 实现从图像检测到动态防治的完整业务闭环
- 系统具备良好的扩展性，新增病害无需修改 Agent 代码
- 前端 Dashboard 可视化诊断数据，支持历史趋势分析
