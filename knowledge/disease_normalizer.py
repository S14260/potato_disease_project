# =========================
# 统一病害ID层（核心修复）
# =========================

DISEASE_MAP = {

    "early_blight": {
        "cn": "马铃薯早疫病",
        "aliases": ["早疫病", "early blight", "Alternaria solani"]
    },

    "late_blight": {
        "cn": "马铃薯晚疫病",
        "aliases": ["晚疫病", "late blight", "Phytophthora infestans"]
    },

    "healthy": {
        "cn": "健康叶片",
        "aliases": ["healthy", "正常"]
    }
}


def normalize_disease(label: str) -> str:
    """
    YOLO输出 → 标准 disease_id
    """
    label = label.lower().strip()

    if label in DISEASE_MAP:
        return label

    # 反向匹配 alias
    for k, v in DISEASE_MAP.items():
        if label in v["aliases"]:
            return k

    return "unknown"