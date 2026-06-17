# Multi-Agent 设计详解

## 为什么选择 Multi-Agent 架构

### 传统单体管道的问题
- 所有逻辑写在一个 `app.py` 中（~500行），耦合度高
- LLM 只做文本生成，没有自主决策能力
- 新增功能需要修改主流程，扩展性差

### Multi-Agent 的优势
- **关注点分离**: 每个 Agent 只负责一个领域，prompt 更精准
- **自主决策**: LLM 通过 Function Calling 自主选择调用哪个工具
- **可扩展**: 新增 Agent（如灌溉建议）只需创建并注册到 Supervisor
- **可测试**: 每个 Agent 可独立测试

## 架构模式: Supervisor 协调

选择 LangGraph 的 `create_supervisor` 模式，而非纯顺序管道或完全自主对话。

### 三种模式对比

| 模式 | 描述 | 适用场景 |
|------|------|----------|
| 顺序管道 | 固定顺序调用，无 LLM 决策 | 流程固定、不需要灵活性 |
| Supervisor 协调 | LLM 决定调用顺序，有默认流程 | **本项目采用** |
| 完全自主对话 | Agent 之间自由通信 | 复杂协作，不确定性高 |

### Supervisor 工作原理

```python
# Supervisor 的核心是一个 LangGraph 状态图
# 节点 = 子 Agent，边 = Supervisor 的路由决策

supervisor = create_supervisor(
    agents=[diagnosis_agent, risk_agent, treatment_agent],
    model=llm,
    prompt=SUPERVISOR_PROMPT,  # 描述各 Agent 能力和执行顺序
)
```

Supervisor 的 LLM 接收用户请求后：
1. 分析请求内容
2. 决定调用哪个子 Agent
3. 将子 Agent 的输出作为上下文传给下一个 Agent
4. 整合所有输出生成最终报告

## 子 Agent 设计

### 每个 Agent 的结构

```
Agent = LLM + System Prompt + Tools
```

- **LLM**: mimo-v2.5-pro (via ChatOpenAI)
- **System Prompt**: 定义 Agent 的角色、工作流程、输出格式
- **Tools**: Agent 可以调用的函数（用 @tool 装饰器定义）

### Diagnosis Agent

**角色**: 病害诊断专家
**工具**: `detect_disease`, `get_disease_info`
**工作流**:
1. 调用 `detect_disease` 分析图像
2. 从结果中提取病害标签
3. 调用 `get_disease_info` 查询详情
4. 输出：病害名称、病斑数量、置信度、症状描述

### Risk Agent

**角色**: 风险评估专家
**工具**: `get_weather`, `compute_risk_score`
**工作流**:
1. 调用 `get_weather` 获取气象数据
2. 结合诊断结果和环境数据
3. 调用 `compute_risk_score` 计算评分
4. 输出：风险等级、评分、风险因素列表

### Treatment Agent

**角色**: 治疗方案专家
**工具**: `search_knowledge_base`, `get_sop`, `generate_treatment_advice`
**工作流**:
1. 调用 `search_knowledge_base` 语义检索相关知识
2. 调用 `get_sop` 获取标准操作流程
3. 调用 `generate_treatment_advice` 生成 AI 建议
4. 输出：推荐药剂、SOP 步骤、综合治疗建议

## Function Calling 机制

### 工具定义方式

使用 LangChain 的 `@tool` 装饰器，docstring 自动成为工具描述，type hints 自动定义输入 schema：

```python
@tool
def detect_disease(image_path: str) -> dict:
    """Detect potato leaf diseases using YOLO model.
    Returns detections with labels, confidence, and bbox."""
    from yolo.predict import predict_image
    return predict_image(image_path)
```

### 调用流程

```
用户消息 → LLM 分析 → 决定调用 tool_name(args)
    → 执行 Python 函数 → 结果返回 LLM
    → LLM 决定是否继续调用工具
    → 无更多工具调用 → 输出最终文本
```

## 错误处理与回退

- **Supervisor 失败**: 回退到直接调用 `generate_advice()`
- **工具执行失败**: 工具返回错误信息，LLM 尝试替代方案
- **LLM 超时**: 设置 max_rounds=10 防止无限循环

## 面试常见问题

**Q: 为什么不用单个 Agent 加所有工具？**
A: 单 Agent 的 system prompt 会很长，工具描述混杂，LLM 容易选错工具。分 Agent 后每个 prompt 聚焦一个领域，工具集更小，准确率更高。

**Q: Supervisor 怎么决定调用顺序？**
A: Supervisor 的 system prompt 描述了各 Agent 的能力和推荐顺序（诊断→风险→治疗）。LLM 根据 prompt 和用户请求自主决策，同时有默认顺序保底。

**Q: 和直接写 if-else 调用有什么区别？**
A: Agent 模式下 LLM 可以根据上下文灵活调整。例如 YOLO 没检测到病害时，Supervisor 可以跳过 Risk Agent 直接输出"健康"结论。if-else 无法处理这种语义级别的判断。
