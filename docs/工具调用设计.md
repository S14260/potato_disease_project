# Tool Calling 机制详解

## 什么是 Tool Calling

Tool Calling（函数调用）是 LLM 的一项能力：模型不仅能生成文本，还能决定调用哪个函数、传入什么参数。这是 Agent 系统的核心机制。

## 工作原理

```
用户消息 + 工具定义列表
        │
        ▼
   LLM 分析请求
        │
        ├── 不需要工具 → 直接返回文本
        │
        └── 需要工具 → 返回 tool_calls:
             [
               {
                 "function": {
                   "name": "detect_disease",
                   "arguments": "{\"image_path\": \"/uploads/leaf.jpg\"}"
                 }
               }
             ]
                    │
                    ▼
            执行 Python 函数
                    │
                    ▼
            将结果作为 tool role 消息返回给 LLM
                    │
                    ▼
            LLM 继续推理（可能再次调用工具）
                    │
                    ▼
            最终输出文本回复
```

## 本项目中的工具定义

使用 LangChain 的 `@tool` 装饰器，自动生成 OpenAI Function Calling Schema：

```python
from langchain_core.tools import tool

@tool
def detect_disease(image_path: str) -> dict:
    """Detect potato leaf diseases using YOLO model.
    Returns detections with labels, confidence, and bbox."""
    from yolo.predict import predict_image
    return predict_image(image_path)
```

自动生成的 Schema:
```json
{
  "type": "function",
  "function": {
    "name": "detect_disease",
    "description": "Detect potato leaf diseases using YOLO model...",
    "parameters": {
      "type": "object",
      "properties": {
        "image_path": {
          "type": "string",
          "description": ""
        }
      },
      "required": ["image_path"]
    }
  }
}
```

## 工具列表

| 工具名 | 所属 Agent | 功能 | 底层调用 |
|--------|-----------|------|----------|
| `detect_disease` | Diagnosis | YOLO 病害检测 | `yolo.predict.predict_image()` |
| `get_disease_info` | Diagnosis | 查询病害详情 | `knowledge.disease_db.get_disease_info()` |
| `get_weather` | Risk | 获取气象数据 | `utils.weather_api.get_weather()` |
| `compute_risk_score` | Risk | 计算风险评分 | `engine.decision_engine.compute_risk_score()` |
| `search_knowledge_base` | Treatment | 语义检索知识库 | `rag.retriever.search_knowledge_base()` |
| `get_sop` | Treatment | 获取 SOP 流程 | `knowledge.sop_db.get_sop()` |
| `generate_treatment_advice` | Treatment | 生成 AI 治疗建议 | `ai.llm_agent.generate_advice()` |

## Agent 的 ReAct 循环

每个子 Agent 使用 LangGraph 的 `create_react_agent`，实现 ReAct (Reasoning + Acting) 模式：

```python
from langgraph.prebuilt import create_react_agent

agent = create_react_agent(
    model=llm,                    # mimo-v2.5-pro
    tools=[tool1, tool2],         # 该 Agent 可用的工具
    name="diagnosis_agent",
    prompt="You are a disease diagnosis specialist...",
)
```

ReAct 循环：
1. **Reason**: LLM 分析当前状态，决定下一步
2. **Act**: 调用一个工具
3. **Observe**: 获取工具返回结果
4. **Repeat**: 回到步骤 1，直到无需更多工具调用

## Supervisor 的路由机制

Supervisor 本身也是一个 Agent，它的 "工具" 是三个子 Agent：

```python
supervisor = create_supervisor(
    agents=[diagnosis_agent, risk_agent, treatment_agent],
    model=llm,
    prompt="Coordinate: diagnosis → risk → treatment...",
)
```

Supervisor 的 LLM 看到的工具列表是三个子 Agent 的名称和描述。它根据用户请求决定调用哪个子 Agent，子 Agent 的输出作为 Supervisor 的 tool result。

## 与直接调用的区别

| 方面 | 直接调用 | Agent Tool Calling |
|------|---------|-------------------|
| 决策者 | 程序员写死的 if-else | LLM 自主决定 |
| 灵活性 | 固定流程 | 可根据上下文调整 |
| 错误处理 | 需要预写所有分支 | LLM 可动态选择替代方案 |
| 可扩展性 | 修改主流程 | 只需注册新工具 |

## 面试常见问题

**Q: Function Calling 和普通的 API 调用有什么区别？**
A: 普通 API 调用是程序员决定调什么、传什么参数。Function Calling 是 LLM 根据用户意图自主决定调用哪个函数、传什么参数。程序员只需定义工具列表和描述，LLM 负责决策。

**Q: 如果 LLM 调用了错误的工具怎么办？**
A: 三种防御措施：(1) 每个 Agent 的 prompt 限制了工具使用场景；(2) 工具函数内部有参数校验；(3) Supervisor 有 max_rounds 限制防止循环调用。

**Q: @tool 装饰器做了什么？**
A: 它读取函数的 docstring 作为工具描述，读取 type hints 生成 JSON Schema，然后包装成 LangChain 的 BaseTool 对象。LLM 看到的是 OpenAI Function Calling 标准格式的工具定义。
