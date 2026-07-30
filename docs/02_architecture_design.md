# Architecture & Design Specification — LLM Code Reviewer API

This document serves as the architectural spec and guidelines for the backend API project evaluating code submissions using Qwen2.5-Coder-7B-Instruct.

---

## 1. Project Layout (Flat Structure)

```
LLM_With_FASTAPI/
  AGENTS.md             - Workspace rules for agent sessions
  docs/
    01_workflow_process.md   - Workflow & request lifecycle spec
    02_architecture_design.md - Architecture design spec (this file)
  main.py               - FastAPI app entry point & route definitions
  prompt.py              - Evaluation prompts & rubrics (Stage 1-6 builders)
  llm_client.py          - HTTP client for LLM endpoint transport
  response_validator.py  - Parsers, JSON sanitization, score clamping
  schemas.py             - Pydantic models for request & response shapes
  config.py              - Environment settings loader via python-dotenv
  templates/
    index.html          - Simple UI for manual testing
  test_pipeline_e2e.py   - End-to-end integration test suite
  scratch_seq_test.py    - Scratch file (do not touch)
  test_syntax_fix.py     - Scratch file (do not touch)
  .env                   - Local environment configuration
  requirements.txt       - Dependencies
```

---

## 2. API Contract Specification

### Endpoint: `POST /review` (and alias `POST /api/v1/review`)

#### Request Shape (JSON):
```json
{
  "language": "Java",
  "submissions": [
    {
      "question_text": "Write a Java program to add two numbers.",
      "code": "public class Main { ... }",
      "specific_instructions": "Optional constraints"
    }
  ]
}
```

#### Response Shape (JSON):
```json
{
  "individual_reviews": [
    {
      "question_text": "Write a Java program to add two numbers.",
      "correctness_feedback": "Detailed correctness feedback...",
      "common_errors": "None",
      "strengths": "Clean main method...",
      "weaknesses": "None",
      "recommendations": "Add user input handling...",
      "scores": {
        "completeness_score": 10.0,
        "code_quality_score": 9.0,
        "approach_taken_score": 9.5,
        "overall_score": 9.5
      },
      "corrected_code": "public class Main { ... }"
    }
  ],
  "summary_review": {
    "overall_average_score": 9.5,
    "overall_quality_label": "Excellent",
    "common_errors": "None",
    "strengths": "Good structure",
    "weaknesses": "None",
    "recommendations": "Keep up the clean code"
  }
}
```
*(Note: `summary_review` is included when `len(submissions) > 1`; omitted or `null` for a single submission).*

---

## 3. Core Component Responsibilities

| File | Primary Responsibility | Constraints & Exclusions |
|---|---|---|
| `main.py` | FastAPI app creation, `/review` route definition, pipeline orchestration | No prompt text, rubrics, or HTTP transport code directly inline. |
| `prompt.py` | Constructs prompt strings for Stage 1-6 pipeline | No HTTP requests or LLM execution calls. |
| `llm_client.py` | Sends prompt to LLM endpoint, handles timeout & retries, returns raw text | No JSON parsing or rubric interpretation logic. |
| `response_validator.py` | Parses raw text, extracts JSON, validates schema, clamps scores to `[0, 10]` | Never alters LLM judgment or injects rule-based score heuristics. |
| `schemas.py` | Pydantic model definitions for API shapes | Data shapes only; no business logic. |
| `config.py` | Reads environment variables from `.env` | No business logic. |

---

## 4. Code Quality & Non-Negotiable Rules

1. **Type hints everywhere** using Pydantic models across boundaries.
2. **Single Responsibility**: Every function does one clearly named thing.
3. **No hardcoded evaluation logic**: All scores and quality judgments come strictly from the LLM.
4. **No bare `except:` blocks**: Catch specific exceptions.
5. **Flat layout**: Do not create `app/`, `services/`, or `repositories/` subdirectories.
6. **Scratch Protection**: Do not modify `scratch_seq_test.py` or `test_syntax_fix.py`.
7. **End-to-End Verification**: Run `test_pipeline_e2e.py` after any multi-file modification.
