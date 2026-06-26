"""
LangGraph StateGraph 实现 — 马铃薯病害诊断工作流

用原生 LangGraph 替代 langgraph_supervisor，展示 StateGraph 核心概念：
- TypedDict 定义共享状态
- 节点函数读写状态
- 条件边实现分支逻辑
- MemorySaver 支持多轮对话
"""

from typing import TypedDict, Annotated
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages
from langgraph.checkpoint.memory import MemorySaver


# =============================================
# 1. State 定义 — 所有节点共享的数据结构
# =============================================

class DiagnosisState(TypedDict):
    """诊断流程的全局状态。

    每个节点从 state 读取所需字段，返回要更新的字段。
    LangGraph 自动合并返回值到 state 中。
    """
    # 输入
    image_path: str
    city: str
    growth_stage: str

    # YOLO 检测结果
    detections: list[dict]
    disease_label: str
    result_image: str
    disease_count: int

    # 病害知识
    disease_info: dict

    # 环境数据
    weather: dict
    environment: dict

    # 风险评估
    risk_result: dict

    # 治疗方案
    treatment_advice: str

    # 对话消息（add_messages reducer 自动追加，不覆盖）
    messages: Annotated[list, add_messages]

    # 多轮对话历史（Checkpointer 自动持久化）
    # 每轮诊断完成后追加摘要，下轮 LLM 可引用上下文
    conversation_history: list[dict]


# =============================================
# 2. 节点函数 — 每个节点负责一个原子操作
# =============================================

def detect_node(state: DiagnosisState) -> dict:
    """YOLO 检测 + 病害标准化。

    读取: image_path
    写入: detections, disease_label, result_image, disease_count
    """
    from yolo.predict import predict_image
    from knowledge.disease_normalizer import normalize_disease

    result = predict_image(state["image_path"])
    detections = result["detections"]

    if detections:
        raw_label = detections[0]["label"]
        disease_label = normalize_disease(raw_label)
    else:
        disease_label = "healthy"

    return {
        "detections": detections,
        "disease_label": disease_label,
        "result_image": result["image"],
        "disease_count": result["disease_count"],
    }


def disease_info_node(state: DiagnosisState) -> dict:
    """查询病害知识库。

    读取: disease_label
    写入: disease_info
    """
    from knowledge.disease_db import get_disease_info

    info = get_disease_info(state["disease_label"])
    if not info:
        info = {"name": "未知病害", "symptom": {"info": "暂无数据"}}
    return {"disease_info": info}


def weather_node(state: DiagnosisState) -> dict:
    """获取天气数据并构造环境字典。

    读取: city, growth_stage
    写入: weather, environment
    """
    from utils.weather_api import get_weather

    weather_data = get_weather(state["city"])
    growth_stage = state["growth_stage"]

    environment = {
        "temperature": weather_data["temperature"],
        "humidity": weather_data["humidity"],
        "weather": weather_data["weather"],
        "rainfall": weather_data["rainfall"],
        "location": state["city"],
        "growth_stage": growth_stage,
    }

    return {"weather": weather_data, "environment": environment}


def risk_node(state: DiagnosisState) -> dict:
    """风险评分。

    读取: detections, environment, disease_label
    写入: risk_result
    """
    from engine.decision_engine import compute_risk_score

    risk_result = compute_risk_score(
        state["detections"],
        state["environment"],
        state["disease_label"],
    )
    return {"risk_result": risk_result}


def treatment_node(state: DiagnosisState) -> dict:
    """生成治疗建议（调用 LLM + RAG）。

    读取: disease_label, environment, conversation_history
    写入: treatment_advice
    """
    from ai.llm_agent import generate_advice

    history = state.get("conversation_history", [])
    advice = generate_advice(
        state["disease_label"],
        state["environment"],
        history=history,
    )
    return {"treatment_advice": advice}


def update_history_node(state: DiagnosisState) -> dict:
    """诊断完成后，将本轮摘要追加到对话历史。

    读取: disease_label, risk_result, environment, conversation_history
    写入: conversation_history（追加）
    """
    risk = state.get("risk_result", {})
    history = state.get("conversation_history", [])

    summary = {
        "disease": state.get("disease_label", ""),
        "disease_name": state.get("disease_info", {}).get("name", ""),
        "risk_level": risk.get("risk_level", ""),
        "risk_score": risk.get("score", 0),
        "city": state.get("city", ""),
        "temperature": state.get("environment", {}).get("temperature", ""),
        "humidity": state.get("environment", {}).get("humidity", ""),
    }

    return {"conversation_history": history + [summary]}


# =============================================
# 3. 条件边 — 根据状态决定下一步
# =============================================

def should_continue_to_risk(state: DiagnosisState) -> str:
    """检测到健康叶片时跳过风险评估和治疗。"""
    if state["disease_label"] == "healthy":
        return "end"
    return "risk"


# =============================================
# 4. 构建 StateGraph
# =============================================

def build_diagnosis_graph() -> StateGraph:
    """构建完整的诊断工作流图。

    图结构:
        START → detect → [disease_info, weather]（并行）→ risk → treatment → update_history → END
                                    ↓ (healthy)
                                   END
    """
    graph = StateGraph(DiagnosisState)

    # 添加节点
    graph.add_node("detect", detect_node)
    graph.add_node("disease_info", disease_info_node)
    graph.add_node("weather", weather_node)
    graph.add_node("risk", risk_node)
    graph.add_node("treatment", treatment_node)
    graph.add_node("update_history", update_history_node)

    # 边：START → detect
    graph.add_edge(START, "detect")

    # 条件边：detect 之后判断是否继续
    graph.add_conditional_edges(
        "detect",
        should_continue_to_risk,
        {
            "risk": "disease_info",  # 继续 → 先查病害信息
            "end": END,              # 健康 → 直接结束
        },
    )

    # 并行：disease_info 完成后，risk 和 weather 同时执行
    graph.add_edge("disease_info", "weather")
    graph.add_edge("weather", "risk")

    # risk → treatment → update_history → END
    graph.add_edge("risk", "treatment")
    graph.add_edge("treatment", "update_history")
    graph.add_edge("update_history", END)

    return graph


# =============================================
# 5. 编译并导出
# =============================================

def create_diagnosis_app(checkpointer=None):
    """编译 StateGraph 为可执行应用。

    Args:
        checkpointer: 状态持久化后端。传入 MemorySaver 支持多轮对话。
    """
    graph = build_diagnosis_graph()
    return graph.compile(checkpointer=checkpointer)


# 全局单例（带 checkpointer 支持多轮对话）
_app = None


def get_diagnosis_app():
    """获取编译后的诊断图（单例）。"""
    global _app
    if _app is None:
        _app = create_diagnosis_app(checkpointer=MemorySaver())
    return _app


def run_langgraph_diagnosis(
    image_path: str,
    city: str = "Beijing",
    growth_stage: str = "vegetative",
    thread_id: str = "default",
) -> dict:
    """运行 LangGraph 诊断流程。

    Args:
        image_path: 叶片图片路径
        city: 城市名
        growth_stage: 生长期 (seedling/vegetative/tuber/harvest)
        thread_id: 会话 ID（用于 Checkpointer 多轮对话）

    Returns:
        诊断结果字典
    """
    app = get_diagnosis_app()

    config = {"configurable": {"thread_id": thread_id}}

    result = app.invoke(
        {
            "image_path": image_path,
            "city": city,
            "growth_stage": growth_stage,
            "conversation_history": [],
        },
        config=config,
    )

    # 构造返回格式（兼容现有 fast pipeline）
    risk = result.get("risk_result", {})
    return {
        "image": result.get("result_image", ""),
        "detections": result.get("detections", []),
        "disease_count": result.get("disease_count", 0),
        "disease": result.get("disease_label", ""),
        "info": result.get("disease_info", {}),
        "environment": result.get("environment", {}),
        "risk_level": risk.get("risk_level", "低风险"),
        "risk_score": risk.get("score", 0),
        "risk_reasons": risk.get("reasons", []),
        "advice": result.get("treatment_advice", ""),
        "location": city,
        "growth_stage": growth_stage,
    }
