from flask import (
    Flask,
    render_template,
    request,
    jsonify,
    redirect,
    url_for
)

import os
import json
import csv
import markdown
from datetime import datetime

from werkzeug.utils import secure_filename

from agents.supervisor import run_diagnosis_pipeline, run_agent_pipeline_with_trace
from engine.workflow_engine import generate_next_task
from knowledge.disease_db import disease_db
from knowledge.pesticide_db import pesticide_db
from knowledge.sop_db import get_sop

app = Flask(__name__)

UPLOAD_FOLDER = "static/uploads"
RESULTS_FOLDER = "static/results"
HISTORY_FILE = "logs/diagnosis_history.json"

app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER

os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(RESULTS_FOLDER, exist_ok=True)
os.makedirs("logs", exist_ok=True)


# =====================================
# Jinja2 Filters
# =====================================

@app.template_filter("markdown")
def markdown_filter(text):
    if not text:
        return ""
    return markdown.markdown(text, extensions=["tables", "fenced_code"])


# =====================================
# History helpers
# =====================================

def load_history():
    try:
        with open(HISTORY_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return []


def save_history(records):
    with open(HISTORY_FILE, "w", encoding="utf-8") as f:
        json.dump(records, f, ensure_ascii=False, indent=2)


def append_history(record):
    records = load_history()
    records.append(record)
    save_history(records)


# =====================================
# 根路由 → 重定向到 Dashboard
# =====================================

@app.route("/")
def root():
    return redirect(url_for("dashboard"))


# =====================================
# Dashboard 首页
# =====================================

@app.route("/dashboard")
def dashboard():
    records = load_history()
    now = datetime.now()
    today_str = now.strftime("%Y-%m-%d")

    today_count = sum(1 for r in records if r.get("time", "").startswith(today_str))
    total_count = len(records)
    high_count = sum(1 for r in records if r.get("risk_level") == "高风险")

    # 平均风险评分
    scores = [r.get("risk_score", 0) for r in records]
    avg_score = round(sum(scores) / len(scores), 1) if scores else 0

    # 主要病害
    from collections import Counter
    disease_counter = Counter(r.get("disease_name", "") for r in records)
    main_disease = disease_counter.most_common(1)[0][0] if disease_counter else None

    stats = {
        "today": today_count,
        "total": total_count,
        "high_risk": high_count,
        "pending": 0,
        "main_disease": main_disease,
        "avg_score": avg_score,
    }

    # 图表数据 - 病害类型分布
    disease_labels = list(disease_counter.keys()) or ["暂无数据"]
    disease_counts = list(disease_counter.values()) or [0]

    # 图表数据 - 风险等级分布
    low_count = sum(1 for r in records if r.get("risk_level") == "低风险")
    mid_count = sum(1 for r in records if r.get("risk_level") == "中风险")
    high_count_chart = sum(1 for r in records if r.get("risk_level") == "高风险")
    risk_counts = [low_count, mid_count, high_count_chart]

    # 最近 5 条记录
    recent = []
    for r in records[-5:]:
        recent.append({
            "time": r.get("time", ""),
            "disease_name": r.get("disease_name", ""),
            "risk_level": r.get("risk_level", ""),
            "risk_class": _risk_class(r.get("risk_level", "")),
            "risk_score": r.get("risk_score", 0),
            "detection_count": r.get("detection_count", 0),
        })
    recent.reverse()

    return render_template(
        "dashboard.html",
        active_page="dashboard",
        stats=stats,
        recent_records=recent,
        disease_labels=disease_labels,
        disease_counts=disease_counts,
        risk_counts=risk_counts,
    )


# =====================================
# 病害诊断页
# =====================================

@app.route("/diagnosis", methods=["GET", "POST"])
def diagnosis():
    result = None
    error = None

    if request.method == "POST":
        file = request.files.get("file")
        if not file or file.filename == "":
            error = "请上传图片"
            return render_template("diagnosis.html", active_page="diagnosis", result=None, error=error)

        try:
            location = request.form.get("location")
            growth_stage = request.form.get("growth_stage")

            filename = secure_filename(file.filename)
            upload_path = os.path.join(app.config["UPLOAD_FOLDER"], filename)
            file.save(upload_path)

            result = run_diagnosis_pipeline(
                image_path=upload_path,
                location=location,
                growth_stage=growth_stage,
            )

            # 保存诊断历史
            env = result.get("environment", {})
            info = result.get("info", {})
            record = {
                "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "disease": result.get("disease", ""),
                "disease_name": info.get("name", result.get("disease", "")),
                "risk_level": result.get("risk_level", ""),
                "risk_score": result.get("risk_score", 0),
                "detection_count": len(result.get("detections", [])),
                "location": location,
                "growth_stage": growth_stage,
                "temperature": env.get("temperature", ""),
                "humidity": env.get("humidity", ""),
            }
            append_history(record)

        except Exception as e:
            print("ERROR:", e)
            error = f"系统错误: {str(e)}"
            result = None

    now = datetime.now()
    return render_template("diagnosis.html", active_page="diagnosis", result=result, error=error)


@app.route("/api/agent_diagnosis", methods=["POST"])
def agent_diagnosis():
    """Multi-Agent diagnosis API endpoint."""
    file = request.files.get("file")
    if not file or file.filename == "":
        return jsonify({"error": "请上传图片"}), 400

    try:
        location = request.form.get("location", "Beijing")
        growth_stage = request.form.get("growth_stage", "vegetative")

        filename = secure_filename(file.filename)
        upload_path = os.path.join(app.config["UPLOAD_FOLDER"], filename)
        file.save(upload_path)

        agent_result = run_agent_pipeline_with_trace(
            image_path=upload_path,
            location=location,
            growth_stage=growth_stage,
        )

        # Also run fast pipeline for structured data (detections, risk, etc.)
        fast_result = run_diagnosis_pipeline(
            image_path=upload_path,
            location=location,
            growth_stage=growth_stage,
        )

        # Save history
        env = fast_result.get("environment", {})
        info = fast_result.get("info", {})
        record = {
            "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "disease": fast_result.get("disease", ""),
            "disease_name": info.get("name", fast_result.get("disease", "")),
            "risk_level": fast_result.get("risk_level", ""),
            "risk_score": fast_result.get("risk_score", 0),
            "detection_count": len(fast_result.get("detections", [])),
            "location": location,
            "growth_stage": growth_stage,
            "temperature": env.get("temperature", ""),
            "humidity": env.get("humidity", ""),
            "mode": "agent",
        }
        append_history(record)

        return jsonify({
            "success": True,
            "result": {
                "image": fast_result.get("image", ""),
                "detections": fast_result.get("detections", []),
                "disease_count": fast_result.get("disease_count", 0),
                "risk_level": fast_result.get("risk_level", ""),
                "risk_score": fast_result.get("risk_score", 0),
                "risk_reasons": fast_result.get("risk_reasons", []),
                "info": fast_result.get("info", {}),
                "environment": fast_result.get("environment", {}),
                "disease": fast_result.get("disease", ""),
                "current_task": fast_result.get("current_task"),
            },
            "agent_report": agent_result.get("advice", ""),
            "trace": agent_result.get("trace", {}),
        })

    except Exception as e:
        print("Agent diagnosis error:", e)
        return jsonify({"error": f"系统错误: {str(e)}"}), 500


# =====================================
# 防治工作流
# =====================================

@app.route("/workflow")
def workflow():
    disease = request.args.get("disease")
    risk_level = request.args.get("risk_level")
    location = request.args.get("location", "Beijing")

    if not disease or not risk_level:
        return render_template(
            "workflow.html",
            active_page="workflow",
            disease=None,
            risk_level=None,
            environment={},
            sop_steps=[],
        )

    sop_steps = get_sop(disease, risk_level)
    # 标准化步骤格式
    steps = []
    for i, s in enumerate(sop_steps):
        steps.append({
            "step": i + 1,
            "title": s.get("title", f"步骤 {i+1}"),
            "content": s.get("content", ""),
            "tips": s.get("tips", []),
        })

    from utils.weather_api import get_weather
    weather = get_weather(location)
    environment = {
        "temperature": weather.get("temperature", 20),
        "humidity": weather.get("humidity", 70),
        "rainfall": weather.get("rainfall", False),
        "growth_stage": request.args.get("growth_stage", "vegetative"),
    }

    return render_template(
        "workflow.html",
        active_page="workflow",
        disease=disease,
        risk_level=risk_level,
        environment=environment,
        sop_steps=steps,
    )


# =====================================
# 历史记录
# =====================================

@app.route("/history")
def history():
    records = load_history()
    filter_disease = request.args.get("disease", "")
    filter_risk = request.args.get("risk", "")

    filtered = []
    for r in records:
        if filter_disease and r.get("disease") != filter_disease:
            continue
        if filter_risk and r.get("risk_level") != filter_risk:
            continue
        filtered.append({
            "time": r.get("time", ""),
            "disease_name": r.get("disease_name", ""),
            "risk_level": r.get("risk_level", ""),
            "risk_class": _risk_class(r.get("risk_level", "")),
            "risk_score": r.get("risk_score", 0),
            "detection_count": r.get("detection_count", 0),
            "location": r.get("location", ""),
        })
    filtered.reverse()

    return render_template(
        "history.html",
        active_page="history",
        records=filtered,
        filter_disease=filter_disease,
        filter_risk=filter_risk,
    )


# =====================================
# 病害知识库
# =====================================

@app.route("/knowledge")
def knowledge():
    selected_disease = request.args.get("disease", "early_blight")
    selected_info = disease_db.get(selected_disease)

    # 获取对应药剂
    all_pesticides = []
    for disease_id, plist in pesticide_db.items():
        for p in plist:
            all_pesticides.append({**p, "disease_id": disease_id})

    return render_template(
        "knowledge.html",
        active_page="knowledge",
        diseases=disease_db,
        selected_disease=selected_disease,
        selected_info=selected_info,
        pesticides=all_pesticides,
    )


# =====================================
# 数据分析
# =====================================

@app.route("/analytics")
def analytics():
    records = load_history()
    total = len(records)

    early_count = sum(1 for r in records if r.get("disease") == "early_blight")
    late_count = sum(1 for r in records if r.get("disease") == "late_blight")

    early_pct = round(early_count / total * 100) if total > 0 else 0
    late_pct = round(late_count / total * 100) if total > 0 else 0

    low_count = sum(1 for r in records if r.get("risk_level") == "低风险")
    mid_count = sum(1 for r in records if r.get("risk_level") == "中风险")
    high_count = sum(1 for r in records if r.get("risk_level") == "高风险")

    scores = [r.get("risk_score", 0) for r in records]
    avg_score = round(sum(scores) / len(scores), 1) if scores else 0

    # 趋势数据（最近 20 条）
    recent_20 = records[-20:]
    trend_labels = [r.get("time", "")[-8:] for r in recent_20]  # HH:MM:SS
    trend_scores = [r.get("risk_score", 0) for r in recent_20]

    # 详细记录
    detail_records = []
    for r in records[-30:]:
        detail_records.append({
            "time": r.get("time", ""),
            "disease_name": r.get("disease_name", ""),
            "risk_level": r.get("risk_level", ""),
            "risk_class": _risk_class(r.get("risk_level", "")),
            "risk_score": r.get("risk_score", 0),
            "temperature": r.get("temperature", "-"),
            "humidity": r.get("humidity", "-"),
        })
    detail_records.reverse()

    stats = {
        "total": total,
        "early_pct": early_pct,
        "late_pct": late_pct,
        "early_count": early_count,
        "late_count": late_count,
        "low_count": low_count,
        "mid_count": mid_count,
        "high_count": high_count,
        "avg_score": avg_score,
    }

    return render_template(
        "analytics.html",
        active_page="analytics",
        stats=stats,
        trend_labels=trend_labels,
        trend_scores=trend_scores,
        records=detail_records,
    )


# =====================================
# 系统设置
# =====================================

@app.route("/settings")
def settings():
    return render_template("settings.html", active_page="settings")


# =====================================
# 动态生成下一任务
# =====================================

@app.route("/next_task", methods=["POST"])
def next_task():
    data = request.json
    disease = data["disease"]
    risk_level = data["risk_level"]
    current_step = data["current_step"]
    feedback = data["feedback"]
    environment = data["environment"]
    completed_steps = data.get("completed_steps", [])

    next_task_data = generate_next_task(
        disease,
        risk_level,
        current_step,
        feedback,
        environment,
        completed_steps,
    )

    return jsonify(next_task_data)


# =====================================
# Token 统计面板（保留兼容）
# =====================================

@app.route("/token_dashboard")
def token_dashboard():
    token_data = []
    try:
        with open("logs/token_log.csv", "r", encoding="utf-8") as f:
            reader = csv.reader(f)
            for row in reader:
                token_data.append(row)
    except Exception:
        pass

    return render_template("token_dashboard.html", data=token_data)


# =====================================
# Helpers
# =====================================

def _risk_class(risk_level):
    if risk_level == "高风险":
        return "tag-red"
    elif risk_level == "中风险":
        return "tag-orange"
    return "tag-green"


# =====================================
# 启动
# =====================================

if __name__ == "__main__":
    app.run(debug=True)
