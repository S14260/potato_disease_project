from langchain_core.tools import tool


@tool
def detect_disease(image_path: str) -> dict:
    """Detect potato leaf diseases from an image using YOLO model.
    Returns detections with labels, confidence scores, bounding boxes,
    disease counts, and annotated result image path."""
    from yolo.predict import predict_image
    return predict_image(image_path)


@tool
def get_disease_info(disease_key: str) -> dict:
    """Look up detailed disease information by disease ID.
    Valid keys: early_blight, late_blight.
    Returns name, type, pathogen, symptoms, risk environment, treatment strategy."""
    from knowledge.disease_db import get_disease_info as _get
    result = _get(disease_key)
    return result or {"error": f"Unknown disease: {disease_key}"}


@tool
def get_weather(city: str) -> dict:
    """Get current weather data (temperature, humidity, rainfall) for a city.
    Returns temperature in Celsius, humidity percentage, weather description, and rainfall boolean."""
    from utils.weather_api import get_weather as _get
    return _get(city)


@tool
def compute_risk_score(
    detections: list,
    environment: dict,
    disease_name: str,
) -> dict:
    """Compute agricultural risk score (0-100) based on YOLO detections,
    environment data (temperature, humidity, rainfall, growth_stage),
    and disease name (early_blight or late_blight).
    Returns score, risk_level, and contributing reasons."""
    from engine.decision_engine import compute_risk_score as _compute
    return _compute(detections, environment, disease_name)


@tool
def search_knowledge_base(query: str) -> list:
    """Search the potato disease knowledge base using semantic search.
    Returns relevant documents about diseases, pesticides, SOPs, and treatments.
    Use natural language queries like 'early blight pesticide' or '晚疫病防治'."""
    from rag.retriever import search_knowledge_base as _search
    return _search(query, top_k=5)


@tool
def get_sop(disease: str, risk_level: str) -> list:
    """Get Standard Operating Procedure steps for a disease at a given risk level.
    disease: early_blight or late_blight.
    risk_level: 低风险, 中风险, or 高风险."""
    from knowledge.sop_db import get_sop as _get
    return _get(disease, risk_level)


@tool
def generate_treatment_advice(disease_key: str, environment: dict) -> str:
    """Generate AI-powered treatment advice by combining disease info,
    environment data, and RAG-retrieved pesticide knowledge via LLM.
    Use after diagnosis and risk assessment are complete."""
    from ai.llm_agent import generate_advice
    return generate_advice(disease_key, environment)
