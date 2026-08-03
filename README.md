# QWEN Code Evaluator API 🔒

A proprietary, AI-powered Code Evaluation Engine & Learning Management System (LMS) Automated Review Service.

> **CONFIDENTIAL & PROPRIETARY**: This repository contains internal enterprise code for the automated code evaluation platform. Unauthorized distribution or copying is strictly prohibited.

---

## 📌 Overview

The **QWEN Code Evaluator Engine** evaluates student code submissions against problem statements and strict execution constraints. Built on **FastAPI** and local **Qwen 2.5 Coder 7B**, the service provides deterministic scoring, detailed line-by-line feedback, and reference code generation without hardcoded rule sets or regex heuristics.

---

## 🍏 Internal Studio Console UI

Included for manual verification and testing is an enterprise web console featuring:
- **Modular Diagnostic Blocks**: Segregated feedback cards for Executive Findings, Syntax Errors, Strengths, Weaknesses, Recommendations, and Reference Code.
- **Glassmorphic Detail Modals**: Interactive detail cards with spring physics and one-click code copy.
- **Activity Score Gauges**: SVG radial activity meters with smooth score count-up animations.
- **Adaptive Appearance**: Built-in Dark and Light visual themes.

---

## 🏗 Architecture & Pipeline Design

```
                     ┌────────────────────────┐
                     │   Enterprise Client    │
                     └───────────┬────────────┘
                                 │
                     ┌───────────▼────────────┐
                     │  FastAPI Gateway       │
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

The evaluation process relies on a 6-stage split pipeline:
1. **Stage 1 (Syntax & Correctness)**: Verifies syntax validity and language matching.
2. **Stage 2 (Algorithm & Efficiency)**: Evaluates time and space complexity ($O(N)$).
3. **Stage 3 (Structure & Readability)**: Inspects code decomposition, variable naming, and formatting.
4. **Stage 4 (Error Handling & Security)**: Audits input validation, crash safety, and security.
5. **Stage 5 (Constraint Adherence & Testing)**: Checks adherence to explicit problem constraints.
6. **Stage 6 (Aggregator & Synthesis)**: Synthesizes findings into a unified report with 0–10 score breakdowns.

---

## 📁 Repository Layout

```
├── main.py                # FastAPI route handlers & orchestration
├── prompt.py              # 6-Stage split pipeline prompt definitions
├── llm_client.py          # LLM communication layer with timeout & retry logic
├── response_validator.py  # Response validation & score normalization
├── schemas.py             # Pydantic request & response schemas
├── config.py              # Environment configuration loader
├── templates/
│   └── index.html         # Internal Studio Web Console UI
├── requirements.txt       # Python dependencies
├── .env                   # Environment settings
└── .gitignore             # Git exclusion rules
```

---

## ⚙️ Environment Setup & Deployment

### 1. Prerequisites
- **Python**: Version `3.10+`
- **Ollama**: Service running locally with model `qwen2.5-coder:7b-instruct`

### 2. Environment Variables (`.env`)
Configure application settings in `.env`:
```env
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=qwen2.5-coder:7b-instruct
LLM_ENDPOINT_URL=http://localhost:11434/api/chat
LLM_TIMEOUT_SECONDS=300.0
LLM_TEMPERATURE=0.1
DEFAULT_TARGET_LANGUAGE=Java
```

### 3. Server Startup
```bash
# Activate virtual environment
.\venv\Scripts\activate

# Install requirements
pip install -r requirements.txt

# Start production server
uvicorn main:app --reload
```

---

## 📡 API Reference

### `POST /api/v1/review`

Evaluates code submissions against problem statements and constraints.

#### Request Payload
```json
{
  "language": "Java",
  "submissions": [
    {
      "question_text": "Read city code and sequence number, combine into a booking ID without using + operator.",
      "code": "import java.util.*;\npublic class BookingID {\n    public static void main(String[] args) {\n        Scanner sc = new Scanner(System.in);\n        String city = sc.next();\n        String seq = sc.next();\n        StringBuilder sb = new StringBuilder();\n        sb.append(city).append(seq);\n        System.out.println(sb.toString());\n    }\n}"
    }
  ]
}
```

#### Response Structure
```json
{
  "individual_reviews": [
    {
      "question_text": "Read city code and sequence number...",
      "correctness_feedback": "The program correctly reads inputs and concatenates them using StringBuilder without using the + operator.",
      "common_errors": "None",
      "strengths": "- Used StringBuilder.append as requested.\n- Correct string handling.",
      "weaknesses": "None",
      "recommendations": "Add input validation for empty input scenarios.",
      "scores": {
        "completeness_score": 10.0,
        "code_quality_score": 9.5,
        "approach_taken_score": 10.0,
        "overall_score": 9.8
      },
      "corrected_code": "import java.util.*;\n..."
    }
  ]
}
```

---

## 🔒 Confidentiality Notice

This software is confidential property. All rights reserved.
