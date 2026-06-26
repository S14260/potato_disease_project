from openai import OpenAI
import time
import csv
from ai.rag_retriever import retrieve_pesticide
import os

client = OpenAI(
    api_key="tp-c2rtlxwsq7sgmt1r32ijnuswqgvoof4gurdjh8qwtufcbmjo",
    base_url="https://token-plan-cn.xiaomimimo.com/v1"
)


# =========================
# 1. 统一标签（关键修复）
# =========================
def normalize_label(label):

    mapping = {
        "early_blight": "early_blight",
        "late_blight": "late_blight",
        "healthy": "healthy"
    }

    return mapping.get(label.lower(), label.lower())


# =========================
# 2. 环境文本
# =========================
def build_environment_text(env):

    rain = "有降雨" if env.get("rainfall") else "无降雨"

    return f"""
环境信息：
- 温度：{env.get('temperature')}℃
- 湿度：{env.get('humidity')}%
- 天气：{rain}
"""


# =========================
# 3. 风险等级
# =========================
def calculate_risk(env):

    temp = env.get("temperature", 20)
    hum = env.get("humidity", 60)
    rain = env.get("rainfall", False)

    if hum > 85 and temp < 20 and rain:
        return "高"
    elif hum > 70:
        return "中"
    return "低"


# =========================
# 4. 主函数
# =========================
def generate_advice(label, environment=None, history=None):

    start = time.time()

    if environment is None:
        environment = {
            "temperature": 20,
            "humidity": 60,
            "rainfall": False
        }

    # ===== 标准化 =====
    disease_id = normalize_label(label)

    print("当前病害：", label)
    print("RAG检索病害：", disease_id)

    # ===== RAG =====
    products = retrieve_pesticide(disease_id)

    print("RAG检索结果：", products)

    # ===== ❗关键修复：允许无数据，但不直接退出 =====
    if not products:
        return "⚠️ 未检索到农药数据，请检查知识库匹配关系（RAG为空）"

    # ===== 构造农药文本 =====
    product_text = ""
    for p in products[:3]:
        product_text += f"""
名称：{p.get('name')}
成分：{p.get('ingredient')}
方式：{p.get('method')}
浓度：{p.get('dosage')}
间隔：{p.get('interval')}
说明：{p.get('note')}
"""

    env_text = build_environment_text(environment)
    risk = calculate_risk(environment)

    # ===== 构造历史上下文 =====
    history_text = ""
    if history:
        history_text = "\n\n【历史诊断记录】\n"
        for i, h in enumerate(history):
            history_text += (
                f"第{i+1}次: {h.get('disease_name', h.get('disease', '未知'))} "
                f"| 风险: {h.get('risk_level', '未知')} "
                f"| 城市: {h.get('city', '未知')} "
                f"| 温度: {h.get('temperature', '?')}℃ "
                f"| 湿度: {h.get('humidity', '?')}%\n"
            )
        history_text += "请在回答中参考历史诊断，注意病情变化趋势。"

    prompt = f"""
作物病害：{disease_id}

{env_text}

风险等级：{risk}

农药信息：
{product_text}
{history_text}

请生成规范防治建议：

【风险等级】{risk}
【推荐用药】必须使用提供药剂
【施药方式】结合天气
【施药间隔】简洁说明

限制：
- 不要编造药剂
- 不超过180字
"""

    response = client.chat.completions.create(
        model="mimo-v2.5-pro",
        messages=[
            {"role": "system", "content": "农业植保专家"},
            {"role": "user", "content": prompt}
        ],
        max_tokens=2000
    )

    advice = response.choices[0].message.content

    # ===== log路径修复 =====
    log_path = "logs/token_log.csv"
    os.makedirs("logs", exist_ok=True)

    with open(log_path, "a", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow([
            time.strftime("%Y-%m-%d %H:%M:%S"),
            "rag+env+risk",
            label,
            response.usage.prompt_tokens,
            response.usage.completion_tokens,
            response.usage.total_tokens,
            round(time.time() - start, 2)
        ])

    return advice


# =========================
# 5. 动态工作流步骤生成
# =========================
def generate_workflow_step(
    disease,
    risk_level,
    environment,
    feedback,
    history
):

    start = time.time()

    disease_id = normalize_label(disease)
    env_text = build_environment_text(environment)
    risk = calculate_risk(environment)

    # 构造历史文本
    history_text = ""
    if history:
        for i, h in enumerate(history):
            history_text += f"\n步骤{i+1}: {h.get('title', '未知')} - 农户反馈: {h.get('feedback', '无')}"
    else:
        history_text = "无历史记录"

    prompt = f"""指导农户治疗马铃薯{disease_id}。
{env_text}风险等级：{risk_level}
历史：{history_text}
反馈：{feedback}

根据反馈生成下一步。规则：
- 效果明显→进阶步骤
- 无改善→更强措施
- 恶化→紧急方案
- 遇到困难→替代方案
- 全部完成→is_final设true

只返回JSON：
{{"title":"标题","content":"50-100字操作说明","tips":["提示1","提示2"],"reasoning":"30字分析","is_final":false}}"""

    try:
        response = client.chat.completions.create(
            model="mimo-v2.5-pro",
            messages=[
                {"role": "system", "content": "你是农业植保专家。你必须只返回一个合法的JSON对象，不要返回任何其他文字、解释或markdown格式。"},
                {"role": "user", "content": prompt}
            ],
            max_tokens=2000,
            temperature=0.3
        )

        content = response.choices[0].message.content.strip()

        print("LLM原始返回:", content)

        # 提取JSON
        import json
        import re

        # 去掉markdown代码块标记
        cleaned = content
        if "```" in cleaned:
            cleaned = re.sub(r'```json\s*', '', cleaned)
            cleaned = re.sub(r'```\s*', '', cleaned)
            cleaned = cleaned.strip()

        # 尝试直接解析
        result = None
        try:
            result = json.loads(cleaned)
        except json.JSONDecodeError:
            pass

        # 尝试提取第一个完整的JSON对象（支持嵌套）
        if result is None:
            try:
                # 找到第一个 { 的位置
                start = cleaned.find('{')
                if start != -1:
                    # 从 { 开始，逐字符匹配括号深度
                    depth = 0
                    for i in range(start, len(cleaned)):
                        if cleaned[i] == '{':
                            depth += 1
                        elif cleaned[i] == '}':
                            depth -= 1
                        if depth == 0:
                            json_str = cleaned[start:i+1]
                            result = json.loads(json_str)
                            break
            except (json.JSONDecodeError, ValueError):
                pass

        if result is None:
            raise ValueError(f"无法解析LLM返回的JSON: {content[:200]}")

        # 记录token
        log_path = "logs/token_log.csv"
        os.makedirs("logs", exist_ok=True)
        with open(log_path, "a", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow([
                time.strftime("%Y-%m-%d %H:%M:%S"),
                "workflow_step",
                disease_id,
                response.usage.prompt_tokens,
                response.usage.completion_tokens,
                response.usage.total_tokens,
                round(time.time() - start, 2)
            ])

        return result

    except Exception as e:
        print("❌ 工作流LLM错误:", e)
        return {
            "title": "继续执行",
            "content": f"请继续按照之前的指导执行。如有问题请联系农技人员。({str(e)[:50]})",
            "tips": ["保持田间通风", "定期观察病斑变化"],
            "reasoning": "系统暂时无法生成个性化建议",
            "is_final": False
        }