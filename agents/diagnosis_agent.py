from langgraph.prebuilt import create_react_agent
from agents.tools import detect_disease, get_disease_info

DIAGNOSIS_PROMPT = (
    "你是马铃薯病害诊断专家。你的职责是从叶片图像中识别病害并查询病害详细信息。\n\n"
    "工作流程：\n"
    "1. 使用 detect_disease 工具分析上传的叶片图像\n"
    "2. 从检测结果中获取主要病害标签\n"
    "3. 使用 get_disease_info 查询该病害的详细信息\n\n"
    "输出要求：\n"
    "- 病害名称（中文）\n"
    "- 检测到的病斑数量和平均置信度\n"
    "- 病原体信息\n"
    "- 主要症状描述\n"
    "- 检测结果的原始数据（detections 列表）供后续风险评估使用"
)


def create_diagnosis_agent(llm):
    return create_react_agent(
        model=llm,
        tools=[detect_disease, get_disease_info],
        name="diagnosis_agent",
        prompt=DIAGNOSIS_PROMPT,
    )
