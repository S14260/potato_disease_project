from knowledge.sop_db import get_sop
from ai.llm_agent import generate_workflow_step


# =====================================
# 生成初始任务
# =====================================

def generate_initial_task(
        disease,
        risk_level
):

    sop = get_sop(
        disease,
        risk_level
    )

    if not sop:
        return None

    return {
        "current_step": 0,
        "task": sop[0],
        "completed": [],
        "total_steps": len(sop)
    }


# =====================================
# 动态生成下一任务（LLM驱动）
# =====================================

def generate_next_task(
        disease,
        risk_level,
        current_step,
        feedback,
        environment,
        completed_steps=None
):

    if completed_steps is None:
        completed_steps = []

    # 构造历史记录
    history = []
    for step in completed_steps:
        history.append({
            "title": step.get("title", ""),
            "feedback": step.get("feedback", "")
        })

    # 调用LLM生成下一步
    llm_result = generate_workflow_step(
        disease,
        risk_level,
        environment,
        feedback,
        history
    )

    # 判断是否完成
    if llm_result.get("is_final", False):
        return {
            "finished": True,
            "message": llm_result.get("content", "当前农业流程已完成")
        }

    # 返回动态生成的任务
    return {
        "dynamic": True,
        "task": {
            "step": current_step + 1,
            "title": llm_result.get("title", "下一步"),
            "content": llm_result.get("content", ""),
            "tips": llm_result.get("tips", []),
            "reasoning": llm_result.get("reasoning", "")
        }
    }
