from langgraph.prebuilt import create_react_agent
from agents.tools import (
    search_knowledge_base,
    get_sop,
    generate_treatment_advice,
)

TREATMENT_PROMPT = (
    "你是植物保护和治疗方案专家。你的职责是根据诊断结果和风险等级制定治疗方案。\n\n"
    "工作流程：\n"
    "1. 使用 search_knowledge_base 搜索相关病害和农药信息\n"
    "2. 使用 get_sop 获取对应风险等级的标准操作流程\n"
    "3. 使用 generate_treatment_advice 生成AI增强的治疗建议\n\n"
    "输入说明：\n"
    "- disease: 病害ID（early_blight 或 late_blight）\n"
    "- risk_level: 风险等级（低风险/中风险/高风险）\n"
    "- environment: 环境数据字典\n\n"
    "输出要求：\n"
    "- 推荐药剂名称、成分、浓度、施药间隔\n"
    "- SOP标准操作流程步骤\n"
    "- AI生成的综合治疗建议\n"
    "- 安全用药注意事项"
)


def create_treatment_agent(llm):
    return create_react_agent(
        model=llm,
        tools=[search_knowledge_base, get_sop, generate_treatment_advice],
        name="treatment_agent",
        prompt=TREATMENT_PROMPT,
    )
