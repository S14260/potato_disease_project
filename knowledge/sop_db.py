# knowledge/sop_db.py

sop_db = {

    # =====================================
    # 马铃薯早疫病
    # =====================================

    "early_blight": {

        "低风险": [

            {
                "step": 1,
                "title": "田间巡查",
                "content": "定期观察叶片是否出现褐色病斑。"
            },

            {
                "step": 2,
                "title": "环境管理",
                "content": "保持田间通风，降低湿度。"
            }

        ],

        "中风险": [

            {
                "step": 1,
                "title": "病叶处理",
                "content": "及时清除受感染叶片。"
            },

            {
                "step": 2,
                "title": "保护性施药",
                "content": "喷施代森锰锌等保护性药剂。"
            },

            {
                "step": 3,
                "title": "持续监测",
                "content": "7天后重新巡田观察。"
            }

        ],

        "高风险": [

            {
                "step": 1,
                "title": "紧急处理",
                "content": "立即清除严重病株。"
            },

            {
                "step": 2,
                "title": "联合施药",
                "content": "联合使用保护性和治疗性药剂。"
            },

            {
                "step": 3,
                "title": "缩短施药周期",
                "content": "根据病害扩散情况缩短施药间隔。"
            },

            {
                "step": 4,
                "title": "动态复查",
                "content": "3~5天后重新巡田评估风险。"
            }

        ]

    },

    # =====================================
    # 马铃薯晚疫病
    # =====================================

    "late_blight": {

        "低风险": [

            {
                "step": 1,
                "title": "环境监测",
                "content": "关注低温高湿环境变化。"
            }

        ],

        "中风险": [

            {
                "step": 1,
                "title": "病株检查",
                "content": "重点检查叶片水浸状病斑。"
            },

            {
                "step": 2,
                "title": "预防施药",
                "content": "喷施保护性药剂预防扩散。"
            }

        ],

        "高风险": [

            {
                "step": 1,
                "title": "中心病株隔离",
                "content": "立即拔除中心病株。"
            },

            {
                "step": 2,
                "title": "治疗性施药",
                "content": "喷施甲霜灵锰锌、霜脲氰。"
            },

            {
                "step": 3,
                "title": "降低湿度",
                "content": "及时排水并加强通风。"
            },

            {
                "step": 4,
                "title": "连续监测",
                "content": "连续监测病斑扩散情况。"
            }

        ]

    }

}


# =====================================
# 获取SOP流程
# =====================================

def get_sop(label, risk_level):

    disease_sop = sop_db.get(label)

    if not disease_sop:

        return []

    return disease_sop.get(risk_level, [])