from openai import OpenAI
import os

# 从 .env 加载环境变量
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass


# ===============================
# DeepSeek API
# ===============================
client = OpenAI(
    api_key=os.getenv("DEEPSEEK_API_KEY"),
    base_url=os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com"),
)


# ===============================
# LLM生成农业建议
# ===============================
def generate_advice(disease, info):

    prompt = f"""
你是一名农业植保专家，请根据以下病害信息为农户提供专业建议。

病害名称: {info['name']}

症状:
{info['symptom']}

病因:
{info['cause']}

防治方法:
{info['treatment']}

预防措施:
{info['prevention']}

请按以下结构输出：

1. 病害分析
2. 防治策略
3. 农业管理建议
"""

    response = client.chat.completions.create(
        model="deepseek-chat",
        messages=[
            {"role": "system", "content": "你是一名农业植保专家"},
            {"role": "user", "content": prompt}
        ],
        temperature=0.7
    )

    advice = response.choices[0].message.content

    return advice