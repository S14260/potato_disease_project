import json
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage


def create_llm():
    return ChatOpenAI(
        model="mimo-v2.5-pro",
        base_url="https://token-plan-cn.xiaomimimo.com/v1",
        api_key="tp-c2rtlxwsq7sgmt1r32ijnuswqgvoof4gurdjh8qwtufcbmjo",
        temperature=0.7,
        max_tokens=2000,
    )


# ============================================================
# 快速模式（默认）：直接调用各模块 + LLM 生成建议
# 避免 YOLO 重复调用，速度快
# ============================================================

def run_diagnosis_pipeline(
    image_path: str,
    location: str,
    growth_stage: str,
):
    from yolo.predict import predict_image
    from knowledge.disease_normalizer import normalize_disease
    from knowledge.disease_db import get_disease_info
    from knowledge.sop_db import get_sop
    from utils.weather_api import get_weather
    from engine.decision_engine import compute_risk_score

    # Step 1: YOLO detection
    predict_result = predict_image(image_path)
    detections = predict_result["detections"]
    result_image = predict_result["image"]
    disease_count = predict_result["disease_count"]

    # Step 2: Normalize label
    if detections:
        raw_label = detections[0]["label"]
        main_label = normalize_disease(raw_label)
    else:
        main_label = "healthy"

    # Step 3: Disease info
    info = get_disease_info(main_label)
    if not info:
        info = {
            "name": "未知病害",
            "symptom": {"info": "暂无数据"},
            "treatment": {"info": "建议人工复核"},
        }

    # Step 4: Environment
    weather_data = get_weather(location)
    environment = {
        "temperature": weather_data["temperature"],
        "humidity": weather_data["humidity"],
        "weather": weather_data["weather"],
        "rainfall": weather_data["rainfall"],
        "location": location,
        "growth_stage": growth_stage,
    }
    if growth_stage == "seedling":
        environment["risk_bias"] = "low"
    elif growth_stage == "vegetative":
        environment["risk_bias"] = "medium"
    elif growth_stage == "tuber":
        environment["risk_bias"] = "high"
    elif growth_stage == "harvest":
        environment["risk_bias"] = "medium"

    # Step 5: Risk scoring
    risk_result = compute_risk_score(detections, environment, main_label)
    risk_level = risk_result["risk_level"]
    risk_score = risk_result["score"]
    risk_reasons = risk_result["reasons"]

    # Step 6: Initial task
    current_task = get_sop(main_label, risk_level)
    if current_task:
        current_task = {
            "current_step": 0,
            "task": current_task[0],
            "completed": [],
            "total_steps": len(current_task),
        }

    # Step 7: LLM advice (single call, no sub-agents)
    advice = _generate_llm_advice(
        main_label, environment, risk_level, risk_score,
        detections, info, location,
    )

    return {
        "image": result_image,
        "detections": detections,
        "disease_count": disease_count,
        "risk_level": risk_level,
        "risk_score": risk_score,
        "risk_reasons": risk_reasons,
        "info": info,
        "advice": advice,
        "environment": environment,
        "location": location,
        "growth_stage": growth_stage,
        "current_task": current_task,
        "disease": main_label,
    }


def _generate_llm_advice(
    disease_id, environment, risk_level, risk_score,
    detections, info, location,
):
    from knowledge.pesticide_db import pesticide_db
    from ai.llm_agent import normalize_label, build_environment_text, calculate_risk

    products = pesticide_db.get(disease_id, [])
    product_text = ""
    for p in products[:3]:
        product_text += (
            f"- {p['name']}({p['ingredient']}): "
            f"{p['dosage']}, {p['interval']}, {p['method']}, {p['safety']}\n"
        )

    env_text = build_environment_text(environment)
    disease_name = info.get("name", disease_id)
    pathogen = info.get("pathogen", "未知")
    symptoms = info.get("symptom", {})

    prompt = f"""你是农业植保专家，请根据以下信息生成诊断报告。

【病害信息】
- 病害: {disease_name} ({disease_id})
- 病原: {pathogen}
- 叶片症状: {symptoms.get('leaf', '暂无')}
- 检测病斑数: {len(detections)}

【环境信息】
- 城市: {location}
{env_text}

【风险评估】
- 风险等级: {risk_level}
- 风险评分: {risk_score}/100

【推荐药剂】
{product_text}

请输出完整的诊断报告（使用Markdown格式），包含：
1. 病害识别结果（表格形式）
2. 风险评估结果（表格形式）
3. 治疗方案（药剂表格 + SOP步骤）
4. 环境分析
5. 诊断结论与建议

要求：结构化、数据化、专业，不要大段纯文本。使用表格和列表。"""

    try:
        llm = create_llm()
        response = llm.invoke([
            SystemMessage(content="你是农业植保专家，输出专业的诊断报告。"),
            HumanMessage(content=prompt),
        ])
        return response.content
    except Exception as e:
        print(f"LLM error: {e}")
        return _fallback_advice(disease_name, risk_level, products)


def _fallback_advice(disease_name, risk_level, products):
    product_lines = "\n".join(
        f"- {p['name']}({p['ingredient']}): {p['dosage']}, {p['interval']}"
        for p in products[:3]
    )
    return f"""## {disease_name} 诊断报告

**风险等级**: {risk_level}

### 推荐药剂
{product_lines}

### 建议
请及时采取防治措施，注意田间通风和湿度管理。"""


# ============================================================
# Agent 模式（可选）：完整的 Multi-Agent 协作
# 用于演示和测试，速度较慢
# ============================================================

def run_agent_pipeline(
    image_path: str,
    location: str,
    growth_stage: str,
):
    from agents.diagnosis_agent import create_diagnosis_agent
    from agents.risk_agent import create_risk_agent
    from agents.treatment_agent import create_treatment_agent
    from langgraph_supervisor import create_supervisor

    llm = create_llm()
    diagnosis = create_diagnosis_agent(llm)
    risk = create_risk_agent(llm)
    treatment = create_treatment_agent(llm)

    supervisor = create_supervisor(
        agents=[diagnosis, risk, treatment],
        model=llm,
        prompt=(
            "协调三个Agent完成诊断：\n"
            "1. diagnosis_agent - 病害检测\n"
            "2. risk_agent - 风险评估\n"
            "3. treatment_agent - 治疗方案"
        ),
    )
    app_graph = supervisor.compile()

    user_msg = (
        f"诊断马铃薯病害：\n"
        f"- 图片: {image_path}\n"
        f"- 城市: {location}\n"
        f"- 生长期: {growth_stage}"
    )
    result = app_graph.invoke(
        {"messages": [{"role": "user", "content": user_msg}]}
    )
    return _extract_advice(result)


def _extract_advice(supervisor_result):
    messages = supervisor_result.get("messages", [])
    for msg in reversed(messages):
        if hasattr(msg, "content") and msg.content:
            if hasattr(msg, "type") and msg.type == "ai":
                return msg.content
        elif isinstance(msg, dict):
            if msg.get("role") == "assistant" and msg.get("content"):
                return msg["content"]
    return "诊断系统已处理。"


# ============================================================
# Agent 模式 + Trace 可视化数据
# ============================================================

AGENT_DISPLAY = {
    "supervisor": {"name": "Supervisor 协调器", "icon": "brain", "color": "#8b5cf6"},
    "diagnosis_agent": {"name": "诊断 Agent", "icon": "search", "color": "#3b82f6"},
    "risk_agent": {"name": "风险 Agent", "icon": "alert-triangle", "color": "#f59e0b"},
    "treatment_agent": {"name": "治疗 Agent", "icon": "pill", "color": "#22c55e"},
}

TOOL_DISPLAY = {
    "detect_disease": "YOLO 病害检测",
    "get_disease_info": "查询病害知识库",
    "get_weather": "获取气象数据",
    "compute_risk_score": "计算风险评分",
    "search_knowledge_base": "检索知识库",
    "get_sop": "获取标准流程",
    "generate_treatment_advice": "生成治疗建议",
}


def _parse_agent_trace(messages):
    """Parse langgraph messages into a structured agent trace."""
    steps = []
    step_idx = 0

    for msg in messages:
        msg_type = getattr(msg, "type", None)
        msg_name = getattr(msg, "name", None) or ""
        msg_content = getattr(msg, "content", "") or ""
        tool_calls = getattr(msg, "tool_calls", []) or []

        # AI message with tool calls → agent is invoking tools
        if msg_type == "ai" and tool_calls:
            agent_key = msg_name if msg_name in AGENT_DISPLAY else "supervisor"
            for tc in tool_calls:
                tool_name = tc.get("name", "")
                tool_args = tc.get("args", {})
                detail = TOOL_DISPLAY.get(tool_name, tool_name)
                # Add context from args
                if "image_path" in tool_args:
                    detail += f" → {tool_args['image_path'].split('/')[-1]}"
                elif "city" in tool_args:
                    detail += f" → {tool_args['city']}"
                elif "disease_key" in tool_args:
                    detail += f" → {tool_args['disease_key']}"
                elif "query" in tool_args:
                    detail += f" → {tool_args['query'][:30]}"
                elif "disease" in tool_args:
                    detail += f" → {tool_args['disease']}"

                steps.append({
                    "idx": step_idx,
                    "agent": agent_key,
                    "agent_name": AGENT_DISPLAY.get(agent_key, {}).get("name", agent_key),
                    "agent_color": AGENT_DISPLAY.get(agent_key, {}).get("color", "#64748b"),
                    "action": "tool_call",
                    "tool": tool_name,
                    "detail": detail,
                    "status": "running",
                })
                step_idx += 1

        # Tool message → result of a tool call
        elif msg_type == "tool":
            tool_name = msg_name or ""
            # Truncate content for display
            summary = msg_content[:120] + "..." if len(msg_content) > 120 else msg_content
            # Find the matching step and update it
            for s in reversed(steps):
                if s.get("tool") == tool_name and s.get("status") == "running":
                    s["status"] = "done"
                    s["result_summary"] = summary
                    break

        # AI message with content (not just tool calls) → agent output
        elif msg_type == "ai" and msg_content and not tool_calls:
            agent_key = msg_name if msg_name in AGENT_DISPLAY else "supervisor"
            # Skip the supervisor's routing messages
            if agent_key != "supervisor":
                steps.append({
                    "idx": step_idx,
                    "agent": agent_key,
                    "agent_name": AGENT_DISPLAY.get(agent_key, {}).get("name", agent_key),
                    "agent_color": AGENT_DISPLAY.get(agent_key, {}).get("color", "#64748b"),
                    "action": "output",
                    "detail": f"{AGENT_DISPLAY.get(agent_key, {}).get('name', agent_key)} 输出结果",
                    "result_summary": msg_content[:200] + "..." if len(msg_content) > 200 else msg_content,
                    "status": "done",
                })
                step_idx += 1

    return steps


def run_agent_pipeline_with_trace(
    image_path: str,
    location: str,
    growth_stage: str,
):
    """Run multi-agent pipeline and return structured trace data."""
    from agents.diagnosis_agent import create_diagnosis_agent
    from agents.risk_agent import create_risk_agent
    from agents.treatment_agent import create_treatment_agent
    from langgraph_supervisor import create_supervisor

    llm = create_llm()
    diagnosis = create_diagnosis_agent(llm)
    risk = create_risk_agent(llm)
    treatment = create_treatment_agent(llm)

    supervisor = create_supervisor(
        agents=[diagnosis, risk, treatment],
        model=llm,
        prompt=(
            "协调三个Agent完成诊断：\n"
            "1. diagnosis_agent - 病害检测\n"
            "2. risk_agent - 风险评估\n"
            "3. treatment_agent - 治疗方案"
        ),
    )
    app_graph = supervisor.compile()

    user_msg = (
        f"诊断马铃薯病害：\n"
        f"- 图片: {image_path}\n"
        f"- 城市: {location}\n"
        f"- 生长期: {growth_stage}"
    )
    result = app_graph.invoke(
        {"messages": [{"role": "user", "content": user_msg}]}
    )

    messages = result.get("messages", [])
    advice = _extract_advice(result)
    trace_steps = _parse_agent_trace(messages)

    # Build agent flow summary
    agents_involved = []
    seen = set()
    for step in trace_steps:
        agent_key = step["agent"]
        if agent_key not in seen:
            seen.add(agent_key)
            agents_involved.append({
                "key": agent_key,
                "name": AGENT_DISPLAY.get(agent_key, {}).get("name", agent_key),
                "color": AGENT_DISPLAY.get(agent_key, {}).get("color", "#64748b"),
            })

    return {
        "advice": advice,
        "trace": {
            "steps": trace_steps,
            "agents_involved": agents_involved,
        },
    }


# ============================================================
# LangGraph StateGraph 模式：原生 StateGraph 实现
# 展示 LangGraph 核心概念，适合学习和面试
# ============================================================

def run_langgraph_pipeline(
    image_path: str,
    location: str,
    growth_stage: str,
    thread_id: str = "default",
):
    """运行 LangGraph StateGraph 诊断流程。

    与 run_diagnosis_pipeline 的区别：
    - 使用原生 StateGraph 而非手动编排
    - 支持 Checkpointer 状态持久化
    - 展示 Node / Edge / Conditional Edge 概念
    """
    from agents.langgraph_diagnosis import run_langgraph_diagnosis
    return run_langgraph_diagnosis(
        image_path=image_path,
        city=location,
        growth_stage=growth_stage,
        thread_id=thread_id,
    )
