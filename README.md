# QWEN Code Evaluator with FastAPI 🚀

[![FastAPI](https://img.shields.io/badge/FastAPI-0.100+-009688.svg?style=flat&logo=fastapi)](https://fastapi.tiangolo.com/)
[![Ollama](https://img.shields.io/badge/Ollama-Qwen_2.5_Coder_7B-black.svg?style=flat)](https://ollama.ai/)
[![Python](https://img.shields.io/badge/Python-3.10+-3776AB.svg?style=flat&logo=python)](https://www.python.org/)
[![UI](https://img.shields.io/badge/UI-Apple_Glassmorphism-0071E3.svg?style=flat&logo=apple)](http://localhost:8000)

A production-grade, prompt-driven AI Code Evaluation engine and interactive review platform powered by **FastAPI** and local **Qwen 2.5 Coder 7B** via **Ollama**.

---

## 🌟 Overview

The **QWEN Code Evaluator** evaluates student programming submissions dynamically based on question statements, explicit constraints, and target language requirements. Built without hardcoded evaluation rules or heuristic regex checks, all judgment and scoring are derived through a multi-stage LLM evaluation pipeline.

### 🍏 Frontend — Apple Studio Glass Edition
Included out of the box is an **Apple macOS Sequoia-inspired UI** featuring:
- **Interactive Segregated Response Blocks**: Modular cards for Executive Feedback, Errors, Strengths, Weaknesses, Recommendations, and Reference Solutions.
- **Apple Vision Pro Style Popup Modals**: Deep glassmorphism modals with spring physics, scale-up entrance, and one-click code copy.
- **Apple Watch Activity Score Gauge**: SVG radial meter with smooth count-up score animations.
- **Dark & Light Mode**: Seamless theme switching tailored with SF Pro design tokens.

---

## 🏗 Architecture & Pipeline Design

```
                     ┌────────────────────────┐
                     │   User / LMS Client    │
                     └───────────┬────────────┘
                                 │
                     ┌───────────▼────────────┐
                     │  FastAPI (main.py)     │
                     └───────────┬────────────┘
                                 │
          ┌──────────────────────┴──────────────────────┐
          │ Concurrent 5-Stage LLM Evaluation Pipeline  │
          └──────────────────────┬──────────────────────┘
                                 │
     ┌───────────────────────────┼───────────────────────────┐
     │                           │                           │
┌────▼────┐                 ┌────▼────┐                 ┌────▼────┐
│ Stage 1 │                 │ Stage 2 │                 │ Stage 3 │
│ Syntax  │                 │ Algorithm│                │ Structure│
└────┬────┘                 └────┬────┘                 └────┬────┘
     │                           │                           │
     └───────────────────────────┼───────────────────────────┘
                                 │
                     ┌───────────▼────────────┐
                     │   Stage 6 Aggregator   │
                     │  (JSON Synthesis)      │
                     └───────────┬────────────┘
                                 │
                     ┌───────────▼────────────┐
                     │ Response Validator     │
                     └───────────┬────────────┘
                                 │
                     ┌───────────▼────────────┐
                     │ Validated JSON Report  │
                     └────────────────────────┘
```

The evaluation relies on a 6-stage split pipeline:
1. **Stage 1 (Syntax & Correctness)**: Verifies compilation syntax and functional correctness.
2. **Stage 2 (Algorithm & Efficiency)**: Evaluates time/space complexity ($O(N)$) and algorithmic choices.
3. **Stage 3 (Structure & Readability)**: Inspects modularity, variable naming, and formatting.
4. **Stage 4 (Error Handling & Security)**: Checks input validation, crash safety, and security risks.
5. **Stage 5 (Constraint Adherence & Testing)**: Audits explicit technique mandates and test coverage.
6. **Stage 6 (Aggregator & Synthesis)**: Consolidates all stage notes into a structured JSON report with normalized 0–10 score breakdowns.

---

## 📁 Repository Structure

```
├── main.py                # FastAPI entry point & route orchestration
├── prompt.py              # 6-Stage split pipeline prompt builders (Single source of truth)
├── llm_client.py          # HTTP client for Ollama API with timeout & retry logic
├── response_validator.py  # JSON validation and score normalization layer
├── schemas.py             # Pydantic request & response models
├── config.py              # Environment configuration loader (.env)
├── templates/
│   └── index.html         # Interactive Apple-grade UI frontend
├── requirements.txt       # Python package dependencies
├── .env                   # Environment configuration settings
└── .gitignore             # Workspace file exclusion rules
```

---

## ⚙️ Prerequisites & Setup

### 1. Requirements
- **Python**: Version `3.10` or higher
- **Ollama**: Installed and running locally ([ollama.ai](https://ollama.ai))

### 2. Pull Qwen 2.5 Coder Model
Ensure Ollama is running, then pull the model:
```bash
ollama pull qwen2.5-coder:7b-instruct
```

### 3. Environment Configuration (`.env`)
Create a `.env` file in the root directory (or use default fallbacks):
```env
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=qwen2.5-coder:7b-instruct
LLM_ENDPOINT_URL=http://localhost:11434/api/chat
LLM_TIMEOUT_SECONDS=300.0
LLM_TEMPERATURE=0.1
DEFAULT_TARGET_LANGUAGE=Java
```

### 4. Installation & Server Execution
Create virtual environment and install dependencies:
```bash
# Windows
python -m venv venv
.\venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Launch FastAPI development server
uvicorn main:app --reload
```

Once started, access:
- **Interactive UI**: [http://127.0.0.1:8000](http://127.0.0.1:8000)
- **API Documentation**: [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)

---

## 📡 API Specification

### POST `/api/v1/review` (or `/review`)

Reviews code submissions against problem statements and constraints.

#### Request Body
```json
{
  "language": "Java",
  "submissions": [
    {
      "question_text": "In an online ticket system, combine city code and sequence number without using + operator for string concatenation.",
      "code": "import java.util.*;\npublic class BookingID {\n    public static void main(String[] args) {\n        Scanner sc = new Scanner(System.in);\n        String city = sc.next();\n        String seq = sc.next();\n        StringBuilder sb = new StringBuilder();\n        sb.append(city).append(seq);\n        System.out.println(sb.toString());\n    }\n}",
      "specific_instructions": "Must use StringBuilder append chain or String.concat."
    }
  ]
}
```

#### Response JSON
```json
{
  "individual_reviews": [
    {
      "question_text": "In an online ticket system...",
      "correctness_feedback": "The program correctly reads inputs and concatenates them using StringBuilder without using the + operator. Output format aligns with all requirements.",
      "common_errors": "None",
      "strengths": "- Used StringBuilder.append as explicitly requested.\n- Correct logic and string handling.\n- Clean syntax and execution flow.",
      "weaknesses": "None",
      "recommendations": "Consider adding input validation for empty input strings.",
      "scores": {
        "completeness_score": 10.0,
        "code_quality_score": 9.5,
        "approach_taken_score": 10.0,
        "overall_score": 9.8
      },
      "corrected_code": "import java.util.*;\n..."
    }
  ],
  "summary_review": null
}
```

---

## 🛠 Configuration & Customization

- **Language Settings**: You can change the default target language across the backend by setting `DEFAULT_TARGET_LANGUAGE` in `.env` (e.g. `C++`, `Python`, `Java`, `JavaScript`).
- **Timeout & Retries**: `LLM_TIMEOUT_SECONDS` configures HTTP client timeout duration (default: `300.0` seconds).

---

## 📜 License

Distributed under the MIT License.
