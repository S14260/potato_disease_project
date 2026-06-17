from langgraph.prebuilt import create_react_agent
from agents.tools import get_weather, compute_risk_score

RISK_PROMPT = (
    "你是农业风险评估专家。你的职责是根据病害检测结果和环境数据评估风险等级。\n\n"
    "工作流程：\n"
    "1. 使用 get_weather 获取指定城市的当前气象数据\n"
    "2. 结合诊断结果中的 detections 列表、环境数据和病害类型\n"
    "3. 使用 compute_risk_score 计算综合风险评分\n\n"
    "输入说明：\n"
    "- detections: 诊断Agent返回的检测结果列表\n"
    "- city: 城市名称（中文，如'北京'）\n"
    "- disease_name: 病害ID（early_blight 或 late_blight）\n"
    "- growth_stage: 生长期（seedling/vegetative/tuber/harvest）\n\n"
    "输出要求：\n"
    "- 风险等级（低风险/中风险/高风险）\n"
    "- 风险评分（0-100）\n"
    "- 各风险因素的具体说明\n"
    "- 完整的 environment 字典（包含 temperature, humidity, rainfall, growth_stage）"
)


def create_risk_agent(llm):
    return create_react_agent(
        model=llm,
        tools=[get_weather, compute_risk_score],
        name="risk_agent",
        prompt=RISK_PROMPT,
    )
