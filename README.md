# QWEN Code Evaluator

AI-powered code review, scoring, and analysis engine built with **FastAPI**, **Ollama**, and **Qwen 2.5 Coder 7B**.

## Key Features

- **Dual-Pass Evaluation Pipeline**:
  - **Pass 1 — Language Detection**: Validates code against expected target language (e.g. Java). Returns 0.0 zero-scores immediately on mismatch.
  - **Pass 2 — In-Depth Review**: Evaluates completeness, code quality, and approach taken (scored out of 10) with actionable recommendations.
- **Glassmorphism Web Interface**: Responsive Apple macOS/Vision Pro styled UI (`index.html`) with Dark/Light modes, SVG radial progress meters, and interactive popup detail modals.
- **Execution Metrics**: Real-time performance tracking (`/api/metrics`) for processed request count and running average response time.
- **Optimized Performance**: Model persistence (`keep_alive: 5m`) for ~10s consecutive inference, request timeout safety (`300s`), and thread-safe metrics locks.

## Tech Stack

- **Python 3.x** / FastAPI / Pydantic v2
- **Ollama** — local LLM runtime
- **Qwen 2.5 Coder 7B** — code evaluation model

## Setup

```bash
python -m venv venv
.\venv\Scripts\activate          # Windows
pip install -r requirements.txt
```

Ensure Ollama is running with the model pulled:

```bash
ollama pull qwen2.5-coder:7b-instruct
```

## Run

```bash
uvicorn main:app --reload --port 8000
```

## Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/` | Responsive Web Interface |
| `POST` | `/review` | Dual-pass code review & scoring API |
| `GET` | `/api/metrics` | Execution stats (total requests & running average time) |
| `GET` | `/docs` | Swagger UI interactive API documentation |

## Project Structure

```
├── main.py           # FastAPI app, routes, Ollama client, metrics
├── schemas.py        # Pydantic request/response models & validation
├── prompts.py        # Language detection & evaluation prompt builders
├── templates/
│   └── index.html    # Glassmorphic responsive frontend UI
├── app.log           # Application runtime & execution log
├── .env              # Environment configuration
└── requirements.txt
```

## Environment Config (.env)

| Variable | Default | Description |
|----------|---------|-------------|
| `OLLAMA_MODEL` | `qwen2.5-coder:7b-instruct` | Ollama model name |
| `LLM_TEMPERATURE` | `0.1` | Sampling temperature |
| `LLM_TIMEOUT_SECONDS` | `300` | Request timeout limit |
| `DEFAULT_TARGET_LANGUAGE` | `Java` | Target programming language |
