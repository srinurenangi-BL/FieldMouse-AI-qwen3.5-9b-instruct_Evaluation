# QWEN Code Evaluator

AI-powered code review and scoring API using Qwen 2.5 Coder via Ollama + FastAPI.

## Tech Stack

- **Python 3.x** / FastAPI / Pydantic v2
- **Ollama** — local LLM runtime
- **Qwen 2.5 Coder 7B** — evaluation model

## Setup

```bash
python -m venv venv
.\venv\Scripts\activate          # Windows
pip install -r requirements.txt
```

Make sure Ollama is running with the model pulled:

```bash
ollama pull qwen2.5-coder:7b-instruct
```

## Run

```bash
uvicorn main:app --reload --port 8000
```

- **UI** → http://localhost:8000
- **Swagger docs** → http://localhost:8000/docs
- **POST** `/review` — submit code for evaluation

## Project Structure

```
├── main.py           # FastAPI app, routes, LLM client
├── schemas.py        # Pydantic request/response models
├── prompts.py        # Prompt builders (language detection + evaluation)
├── templates/
│   └── index.html    # Frontend UI
├── .env              # Config (model, temperature, language)
└── requirements.txt
```

## Config (.env)

| Variable | Default | Description |
|----------|---------|-------------|
| `OLLAMA_MODEL` | `qwen2.5-coder:7b-instruct` | Ollama model name |
| `LLM_TEMPERATURE` | `0.1` | LLM sampling temperature |
| `LLM_TIMEOUT_SECONDS` | `300` | Request timeout |
| `DEFAULT_TARGET_LANGUAGE` | `Java` | Expected code language |
