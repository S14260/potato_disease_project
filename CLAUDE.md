# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Potato disease detection and diagnosis system. Users upload leaf photos via a Flask web app; a YOLO model detects diseases (early_blight, late_blight), then a risk engine, knowledge base, and LLM generate treatment advice with dynamic task workflows.

## Commands

```bash
# Run the web app (Flask, debug mode)
python app.py

# Train YOLO model (requires GPU, uses ultralytics)
python train.py

# Run prediction on a single image (CLI)
python -c "from yolo.predict import predict_image; print(predict_image('test.jpg'))"
```

No test suite, linter, or CI is configured.

## Architecture

### Request Flow

`app.py` (Flask) orchestrates the full pipeline on image upload:

1. **YOLO Detection** (`yolo/predict.py`) — loads `models/best.pt`, returns detections with labels/confidence/bbox, saves annotated image to `static/results/`
2. **Disease Normalization** (`knowledge/disease_normalizer.py`) — maps raw YOLO labels to canonical IDs (`early_blight`, `late_blight`, `healthy`)
3. **Knowledge Lookup** (`knowledge/disease_db.py`) — static dict of disease info (symptoms, risk environments, treatment strategies)
4. **Weather** (`utils/weather_api.py`) — OpenWeatherMap API call by city name, returns temperature/humidity/rainfall
5. **Risk Scoring** (`engine/decision_engine.py`) — rule-based score from detection count, confidence, weather, and growth stage (seedling/vegetative/tuber/harvest). Thresholds: <40 low, 40-69 medium, >=70 high
6. **LLM Advice** (`ai/llm_agent.py`) — RAG-augmented LLM call using mimo-v2.5-pro model. Retrieves pesticide data from `knowledge/pesticide_db.py` via `ai/rag_retriever.py`, then generates structured treatment advice
7. **Dynamic Workflow** (`engine/workflow_engine.py`) — SOP-based task sequence from `knowledge/sop_db.py`, can insert dynamic tasks (drainage, re-spray) based on weather/feedback

### Key Design Decisions

- **Two LLM files exist**: `ai/agent.py` (DeepSeek, simpler prompt) and `ai/llm_agent.py` (mimo model with RAG). The app uses `llm_agent.py`. `ai/agent.py` appears to be an earlier/alternative implementation.
- **Knowledge base is entirely in Python dicts** — no database. All disease info, pesticides, and SOPs are hardcoded in `knowledge/*.py`.
- **Disease labels must match exactly** across `disease_normalizer.py`, `disease_db.py`, `pesticide_db.py`, `sop_db.py`, and `data.yaml`. When adding a new disease, update all of them.

### Module Map

| Directory | Purpose |
|-----------|---------|
| `yolo/` | YOLO model inference and visualization |
| `ai/` | LLM integration (two providers) and RAG retriever |
| `knowledge/` | Static knowledge bases: diseases, pesticides, SOPs, normalization |
| `engine/` | Risk scoring and dynamic workflow engine |
| `utils/` | Weather API wrapper |
| `templates/` | Jinja2 HTML templates (index.html, token_dashboard.html) |
| `static/` | Uploaded images and result images |
| `models/` | YOLO weights (best.pt for inference, yolov8n.pt for training base) |
| `dataset/` | Training data with data.yaml config (classes: early_blight, late_blight) |

## Environment Variables & API Keys

API keys are currently hardcoded in source files (not env vars):
- `ai/llm_agent.py` — mimo API key
- `ai/agent.py` — DeepSeek API key
- `utils/weather_api.py` — OpenWeatherMap API key

## YOLO Training

Dataset config at `data.yaml` and `dataset/data.yaml`. Training uses ultralytics YOLOv8n as base, 100 epochs, imgsz=640, batch=8. Output goes to `runs/detect/`.
