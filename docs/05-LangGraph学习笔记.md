# LangGraph 学习笔记 — 马铃薯病害诊断系统改造

> 本文档记录了将马铃薯病害诊断系统从 `langgraph_supervisor` 改造为原生 LangGraph `StateGraph` 的完整过程，包含核心概念、代码解析和面试话术。

---

## 1. 为什么要改造？

### 改造前 vs 改造后

| 维度 | 改造前 (langgraph_supervisor) | 改造后 (StateGraph) |
|------|-------------------------------|---------------------|
| 编排方式 | `create_supervisor()` 封装 | 手写 `StateGraph` |
| 数据传递 | Supervisor 自动路由 | 显式 State 定义 |
| 流程控制 | 黑盒，LLM 决定调用谁 | 白盒，开发者定义边和条件 |
| 并行执行 | 不支持 | 支持 fan-out/fan-in |
| 状态持久化 | 无 | Checkpointer |
| 面试展示 | "用了第三方库" | "手写 StateGraph" |

### 核心差异

```python
# ❌ 改造前：黑盒封装，面试官问细节你答不上来
from langgraph_supervisor import create_supervisor
supervisor = create_supervisor(agents=[...], model=llm, prompt="...")

# ✅ 改造后：白盒实现，每个概念都能讲清楚
graph = StateGraph(DiagnosisState)
graph.add_node("detect", detect_node)
graph.add_edge(START, "detect")
graph.add_conditional_edges("detect", route_fn, {...})
```

---

## 2. 核心概念详解

### 2.1 State（状态）

**是什么**：所有节点共享的数据结构，用 `TypedDict` 定义。

**为什么重要**：State 是 LangGraph 的数据总线。节点不直接通信，而是通过读写 State 间接协作。

```python
class DiagnosisState(TypedDict):
    # 输入字段
    image_path: str
    city: str
    growth_stage: str

    # 中间结果
    detections: list[dict]
    disease_label: str
    weather: dict
    environment: dict
    risk_result: dict

    # 输出
    treatment_advice: str

    # 对话消息（reducer：自动追加，不覆盖）
    messages: Annotated[list, add_messages]
```

**关键点**：
- 普通字段：节点返回 `{field: value}` 时直接覆盖
- `Annotated[list, add_messages]`：reducer 模式，返回的消息会追加到列表末尾
- State 是不可变的：每次节点执行后，LangGraph 创建新的 State 对象

**面试话术**：
> "我用 TypedDict 定义诊断流程的全局状态，每个节点从 State 读取输入、返回部分更新。对于对话消息字段，使用 Annotated + add_messages reducer 实现追加语义，避免覆盖历史消息。"

### 2.2 Node（节点）

**是什么**：普通 Python 函数，接收 State，返回部分 State。

```python
def detect_node(state: DiagnosisState) -> dict:
    """YOLO 检测节点"""
    result = predict_image(state["image_path"])  # 从 state 读取
    return {"detections": result["detections"]}  # 返回要更新的字段
```

**设计原则**：
- 单一职责：每个节点只做一件事
- 纯函数倾向：相同输入产生相同输出（除 LLM 调用外）
- 返回 dict：只返回要更新的字段，未返回的字段保持不变

**面试话术**：
> "每个节点是单一职责的函数，从共享 State 读取所需数据，返回要更新的字段。比如 detect_node 只负责 YOLO 检测，weather_node 只负责获取天气数据。节点之间不直接调用，通过 State 解耦。"

### 2.3 Edge（边）

**是什么**：节点之间的连接关系，定义执行顺序。

**三种类型**：

```python
# 1. 直接边：固定跳转
graph.add_edge(START, "detect")      # START → detect
graph.add_edge("risk", "treatment")  # risk → treatment
graph.add_edge("treatment", END)     # treatment → END

# 2. 条件边：根据状态动态决定下一步
def should_continue(state: DiagnosisState) -> str:
    if state["disease_label"] == "healthy":
        return "end"
    return "continue"

graph.add_conditional_edges(
    "detect",           # 源节点
    should_continue,    # 路由函数
    {                   # 返回值 → 目标节点映射
        "continue": "risk",
        "end": END,
    },
)

# 3. 并行边（通过 fan-out 实现）
# 多个节点不互相依赖时，LangGraph 自动并行执行
```

**面试话术**：
> "我用条件边实现了分支逻辑：检测到健康叶片时直接结束，检测到病害时继续风险评估。路由函数根据 State 中的 disease_label 字段决定走哪条路径。"

### 2.4 Checkpointer（检查点）

**是什么**：状态持久化机制，支持多轮对话和断点恢复。

```python
from langgraph.checkpoint.memory import MemorySaver

# 编译时启用
checkpointer = MemorySaver()
app = graph.compile(checkpointer=checkpointer)

# 执行时通过 thread_id 关联会话
config = {"configurable": {"thread_id": "user-123"}}
result = app.invoke({"image_path": "leaf.jpg"}, config=config)

# 同一 thread_id 的后续调用会自动加载之前的状态
```

**用途**：
- **多轮对话**：同一 thread_id 的状态自动保留
- **Human-in-the-loop**：在某个节点暂停，等人工确认后继续
- **故障恢复**：进程崩溃后可从最近的 checkpoint 继续
- **时间旅行**：回溯到任意 checkpoint 查看历史状态

**Checkpointer 类型**：
| 类型 | 存储位置 | 适用场景 |
|------|---------|---------|
| `MemorySaver` | 内存 | 开发/演示 |
| `SqliteSaver` | SQLite 文件 | 单机持久化 |
| `PostgresSaver` | PostgreSQL | 生产环境 |

**面试话术**：
> "我用 MemorySaver 作为 Checkpointer，编译图时注入，执行时通过 thread_id 关联会话。同一用户的多次诊断请求共享同一个 thread_id，State 自动持久化，支持多轮对话和上下文记忆。生产环境可以替换为 PostgresSaver。"

### 2.5 图的编译与执行

```python
# 构建
graph = StateGraph(DiagnosisState)
graph.add_node("detect", detect_node)
graph.add_edge(START, "detect")
# ...

# 编译（可选传入 checkpointer）
app = graph.compile(checkpointer=MemorySaver())

# 执行
result = app.invoke(
    {"image_path": "leaf.jpg", "city": "Beijing"},
    config={"configurable": {"thread_id": "user-1"}},
)
```

**`invoke` vs `stream`**：
- `invoke`：一次性执行完，返回最终 State
- `stream`：逐步返回每个节点的输出，适合实时展示

```python
# 流式执行（展示每个节点的输出）
for event in app.stream(inputs, config=config):
    for node_name, output in event.items():
        print(f"[{node_name}] → {output}")
```

---

## 3. 代码逐行解析

### 3.1 State 定义

```python
class DiagnosisState(TypedDict):
    image_path: str                                    # 输入：图片路径
    city: str                                          # 输入：城市
    growth_stage: str                                  # 输入：生长期
    detections: list[dict]                             # YOLO 检测结果
    disease_label: str                                 # 标准化病害 ID
    result_image: str                                  # 标注后的图片路径
    disease_count: int                                 # 病斑数量
    disease_info: dict                                 # 病害知识库信息
    weather: dict                                      # 原始天气数据
    environment: dict                                  # 环境字典（含 growth_stage）
    risk_result: dict                                  # 风险评分结果
    treatment_advice: str                              # LLM 生成的治疗建议
    messages: Annotated[list, add_messages]            # 对话消息（reducer）
```

**设计考量**：
- `detections` 是 list[dict] 而非单个 dict，因为一张图可能检测到多个病斑
- `weather` 和 `environment` 分开：weather 是原始 API 返回，environment 是加工后的结构化数据
- `messages` 使用 reducer，因为对话消息需要追加而非覆盖

### 3.2 节点实现

```python
def detect_node(state: DiagnosisState) -> dict:
    """YOLO 检测 + 病害标准化"""
    from yolo.predict import predict_image
    from knowledge.disease_normalizer import normalize_disease

    # 从 state 读取输入
    result = predict_image(state["image_path"])
    detections = result["detections"]

    # 标准化病害标签
    if detections:
        raw_label = detections[0]["label"]
        disease_label = normalize_disease(raw_label)
    else:
        disease_label = "healthy"

    # 返回要更新的字段（只返回变化的部分）
    return {
        "detections": detections,
        "disease_label": disease_label,
        "result_image": result["image"],
        "disease_count": result["disease_count"],
    }
```

**注意**：节点函数使用 lazy import（函数内 import），避免模块加载时的循环依赖和重量级依赖加载。

### 3.3 条件边

```python
def should_continue_to_risk(state: DiagnosisState) -> str:
    """检测到健康叶片时跳过风险评估和治疗。"""
    if state["disease_label"] == "healthy":
        return "end"
    return "risk"

# 注册条件边
graph.add_conditional_edges(
    "detect",                    # 源节点：detect 执行完后
    should_continue_to_risk,     # 路由函数
    {
        "risk": "disease_info",  # 返回 "risk" → 执行 disease_info
        "end": END,              # 返回 "end" → 流程结束
    },
)
```

**为什么用条件边而不是 if/else**：
- 条件边是声明式的，图结构清晰可见
- 支持可视化（LangGraph Studio 可以画出完整流程图）
- 便于测试和调试

### 3.4 图结构

```python
graph = StateGraph(DiagnosisState)

# 添加 5 个节点
graph.add_node("detect", detect_node)
graph.add_node("disease_info", disease_info_node)
graph.add_node("weather", weather_node)
graph.add_node("risk", risk_node)
graph.add_node("treatment", treatment_node)

# 连接边
graph.add_edge(START, "detect")
graph.add_conditional_edges("detect", should_continue_to_risk, {...})
graph.add_edge("disease_info", "weather")
graph.add_edge("weather", "risk")
graph.add_edge("risk", "treatment")
graph.add_edge("treatment", END)
```

**执行流程**：
```
START
  ↓
detect (YOLO 检测)
  ↓ (条件判断)
  ├─ healthy → END
  └─ 病害 → disease_info → weather → risk → treatment → END
```

### 3.5 编译与执行

```python
def create_diagnosis_app(checkpointer=None):
    graph = build_diagnosis_graph()
    return graph.compile(checkpointer=checkpointer)

def run_langgraph_diagnosis(image_path, city, growth_stage, thread_id):
    app = get_diagnosis_app()
    config = {"configurable": {"thread_id": thread_id}}
    result = app.invoke(
        {"image_path": image_path, "city": city, "growth_stage": growth_stage},
        config=config,
    )
    return format_result(result)
```

---

## 4. 面试高频问题

### Q1: LangGraph 和 LangChain 的关系？

> LangChain 提供了 LLM 调用、工具定义、RAG 等基础组件。LangGraph 在其之上提供了图编排能力，用于构建有状态、多步骤的 AI 应用。可以理解为：LangChain 是零件，LangGraph 是装配线。

### Q2: StateGraph 的 State 怎么设计？

> 用 TypedDict 定义，包含输入、中间结果、输出三类字段。对于需要追加的数据（如对话消息），用 Annotated + reducer（如 add_messages）实现追加语义。设计原则是：每个节点只读取它需要的字段，只返回它要更新的字段。

### Q3: 条件边和直接边有什么区别？

> 直接边是固定的执行顺序，A 执行完一定执行 B。条件边需要一个路由函数，根据当前 State 决定下一步执行哪个节点。比如检测到健康叶片时直接结束，检测到病害时继续风险评估。

### Q4: Checkpointer 有什么用？

> Checkpointer 实现状态持久化。每次节点执行后，State 会自动保存到 Checkpointer。通过 thread_id 关联会话，同一用户的后续请求可以加载之前的 State。用途包括：多轮对话、Human-in-the-loop、故障恢复、时间旅行调试。

### Q5: 怎么实现并行执行？

> 当多个节点之间没有依赖关系时，LangGraph 自动并行执行。比如 disease_info_node 和 weather_node 互不依赖，可以同时运行。通过 fan-out（一个节点输出到多个节点）和 fan-in（多个节点汇入一个节点）实现。

### Q6: invoke 和 stream 的区别？

> invoke 一次性执行完返回最终结果。stream 逐步返回每个节点的输出，适合实时展示给用户。比如诊断过程中，用户可以先看到检测结果，再看到风险评估，最后看到治疗建议。

### Q7: 生产环境怎么部署 Checkpointer？

> 开发环境用 MemorySaver（内存），生产环境用 PostgresSaver（PostgreSQL）。Checkpointer 是可插拔的接口，切换只需要换一个实例，不需要改业务代码。还可以用 Redis 实现分布式 Checkpointer。

### Q8: 怎么处理节点执行失败？

> LangGraph 支持重试机制，可以在节点上配置 max_retries。也可以用条件边实现 fallback 逻辑：主节点失败时路由到备用节点。比如 LLM 调用失败时，路由到一个返回静态建议的 fallback 节点。

### Q9: 多轮对话怎么实现？

> 三个关键机制配合：①State 中定义 `conversation_history` 字段存储历史诊断摘要；②每轮诊断结束后，`update_history_node` 将摘要追加到 history；③Checkpointer 通过 thread_id 自动持久化 State，同一用户的后续请求自动加载历史。LLM 生成建议时，将 history 注入 prompt，让它知道"上一轮诊断了什么"。

```
第 1 次诊断 (thread_id="user-123"):
  State: {conversation_history: []}
  → detect → risk → treatment → update_history
  State: {conversation_history: [{disease: "early_blight", risk: "高风险"}]}

第 2 次诊断 (同一 thread_id):
  Checkpointer 自动加载上轮 State
  State: {conversation_history: [{disease: "early_blight", risk: "高风险"}]}
  → treatment_node 读取 history，注入 LLM prompt
  → LLM: "上次诊断为早疫病高风险，本次检测到..."
```

---

## 5. 多轮对话实现详解

### 5.1 设计思路

多轮对话的核心问题：**怎么让 LLM 知道"上一轮发生了什么"？**

方案：
1. **State 层**：`conversation_history: list[dict]` 存储历史诊断摘要
2. **持久化层**：MemorySaver Checkpointer + thread_id 自动保存/加载
3. **LLM 层**：将 history 格式化后注入 prompt

### 5.2 State 设计

```python
class DiagnosisState(TypedDict):
    # ... 其他字段 ...
    conversation_history: list[dict]  # 历史诊断摘要
```

每条历史记录：
```python
{
    "disease": "early_blight",
    "disease_name": "马铃薯早疫病",
    "risk_level": "高风险",
    "risk_score": 75,
    "city": "Beijing",
    "temperature": 28,
    "humidity": 85,
}
```

### 5.3 update_history_node

```python
def update_history_node(state: DiagnosisState) -> dict:
    risk = state.get("risk_result", {})
    history = state.get("conversation_history", [])
    summary = {
        "disease": state.get("disease_label", ""),
        "disease_name": state.get("disease_info", {}).get("name", ""),
        "risk_level": risk.get("risk_level", ""),
        "risk_score": risk.get("score", 0),
        "city": state.get("city", ""),
    }
    return {"conversation_history": history + [summary]}
```

### 5.4 LLM 注入历史

```python
def generate_advice(label, environment, history=None):
    history_text = ""
    if history:
        history_text = "\n\n【历史诊断记录】\n"
        for i, h in enumerate(history):
            history_text += f"第{i+1}次: {h['disease_name']} | 风险: {h['risk_level']}\n"
        history_text += "请在回答中参考历史诊断，注意病情变化趋势。"

    prompt = f"作物病害：{disease_id}\n...\n{history_text}"
```

### 5.5 Flask Session 管理

```python
# 同一浏览器自动关联同一个 thread_id
if "thread_id" not in session:
    session["thread_id] = f"session-{uuid.uuid4().hex[:8]}"
thread_id = session["thread_id"]
```

---

## 6. 学习资源

### 官方文档
- LangGraph 概念: https://langchain-ai.github.io/langgraph/concepts/
- LangGraph 教程: https://langchain-ai.github.io/langgraph/tutorials/
- LangGraph GitHub: https://github.com/langchain-ai/langgraph

### 推荐学习路径
1. 先看官方 Quick Start，跑通第一个 StateGraph
2. 理解 State / Node / Edge 三个核心抽象
3. 学习条件边和并行执行
4. 掌握 Checkpointer 和 Human-in-the-loop
5. 尝试流式输出（stream）和可视化（LangGraph Studio）

### 关键 API 速查

```python
from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph.message import add_messages

# 构建
graph = StateGraph(MyState)
graph.add_node("name", func)
graph.add_edge("a", "b")
graph.add_conditional_edges("a", router, mapping)
graph.add_edge(START, "first")
graph.add_edge("last", END)

# 编译
app = graph.compile(checkpointer=MemorySaver())

# 执行
result = app.invoke(inputs, config={"configurable": {"thread_id": "1"}})

# 流式
for event in app.stream(inputs):
    print(event)
```

---

## 6. 改造总结

### 改造前的架构
```
User → Supervisor (langgraph_supervisor.create_supervisor)
         ├→ diagnosis_agent (ReAct)
         ├→ risk_agent (ReAct)
         └→ treatment_agent (ReAct)
```

### 改造后的架构
```
User → StateGraph
         ├→ detect_node (YOLO)
         ├→ disease_info_node (知识库)  ─┐
         ├→ weather_node (天气 API)     ─┤ 并行
         ├→ risk_node (规则引擎)
         └→ treatment_node (LLM + RAG)
```

### 收获
1. **理解了 StateGraph 的核心抽象**：State、Node、Edge
2. **掌握了条件边和并行执行**：比 supervisor 的黑盒路由更灵活
3. **学会了 Checkpointer**：支持多轮对话和状态持久化
4. **面试有话可说**：不再是"用了第三方库"，而是能讲清楚每个设计决策
