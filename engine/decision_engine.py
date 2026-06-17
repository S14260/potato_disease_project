# =====================================
# 农业风险决策引擎
# =====================================

def compute_risk_score(
        detections,
        environment,
        disease_name
):

    score = 0

    reasons = []

    # =====================================
    # 1. 病斑数量评分
    # =====================================

    disease_count = len(detections)

    if disease_count >= 20:

        score += 40

        reasons.append(
            f"检测到大量病斑（{disease_count}处）"
        )

    elif disease_count >= 10:

        score += 25

        reasons.append(
            f"检测到较多病斑（{disease_count}处）"
        )

    elif disease_count >= 5:

        score += 15

        reasons.append(
            f"检测到少量病斑（{disease_count}处）"
        )

    # =====================================
    # 2. 平均置信度评分
    # =====================================

    if detections:

        avg_conf = sum(
            d["confidence"]
            for d in detections
        ) / disease_count

        # confidence是百分比
        if avg_conf >= 80:

            score += 20

            reasons.append(
                "病害识别置信度高"
            )

        elif avg_conf >= 60:

            score += 10

            reasons.append(
                "病害识别较可信"
            )

    # =====================================
    # 3. 环境评分
    # =====================================

    humidity = environment["humidity"]

    temperature = environment["temperature"]

    rainfall = environment["rainfall"]

    # ===== 湿度 =====

    if humidity >= 85:

        score += 25

        reasons.append(
            "空气湿度高，利于病害扩散"
        )

    elif humidity >= 70:

        score += 15

        reasons.append(
            "空气湿度偏高"
        )

    # ===== 降雨 =====

    if rainfall:

        score += 20

        reasons.append(
            "当前存在降雨条件"
        )

    # ===== 温度 =====

    # 早疫病适宜温度
    if disease_name == "early_blight":

        if 20 <= temperature <= 30:

            score += 15

            reasons.append(
                "当前温度适宜早疫病发展"
            )

    # 晚疫病适宜环境
    elif disease_name == "late_blight":

        if 15 <= temperature <= 22:

            score += 20

            reasons.append(
                "当前温度适宜晚疫病传播"
            )

    # =====================================
    # 4. 生长期评分
    # =====================================

    stage = environment["growth_stage"]

    if stage == "tuber":

        score += 15

        reasons.append(
            "块茎形成期抗病能力下降"
        )

    elif stage == "vegetative":

        score += 10

        reasons.append(
            "植株生长期存在传播风险"
        )

    # =====================================
    # 5. 最终风险等级
    # =====================================

    if score >= 70:

        risk_level = "高风险"

    elif score >= 40:

        risk_level = "中风险"

    else:

        risk_level = "低风险"

    return {

        "score": score,

        "risk_level": risk_level,

        "reasons": reasons

    }