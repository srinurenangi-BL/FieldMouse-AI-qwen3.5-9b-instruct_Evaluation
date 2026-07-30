# Main Workflow / Process Flow

This describes the end-to-end flow of the code evaluation API — from the moment
a request hits the endpoint to the moment a response leaves it. Use this as the
reference when wiring the actual backend together.

---

## High-Level Flow

```
CLIENT
  |
  |  POST /review
  |  { language, problem(s), code(s), specific_instructions? }
  v
[1] INPUT VALIDATION
  - Required fields present? (language, problem, code)
  - Non-empty strings?
  - language is a supported value?
  - If batch: each item validated the same way
  |
  |  invalid -> return 400 with a clear error, STOP HERE
  v
[2] PROMPT CONSTRUCTION
  - Call build_review_prompt(language, ques_ans_content_with_inst, summary_gen_flag)
  - This assembles the fixed instructions + rubrics + the dynamic
    problem/code content into the final prompt string
  |
  v
[3] LLM CALL
  - Send prompt to the model (Qwen2.5-Coder-7B-Instruct, local/hosted endpoint)
  - Use low temperature (0.1-0.3) for consistency
  - Use structured/JSON-constrained decoding if the inference server supports it
  - Set a timeout (LLM calls can hang or run long)
  |
  |  timeout / connection error -> return 502/504, STOP HERE
  v
[4] RESPONSE VALIDATION
  - Attempt json.loads() on the raw model output
  - If parsing fails:
      -> strip anything before first '{' and after last '}', retry parse once
      -> if still invalid, retry the LLM call once (models occasionally
         glitch on a single call)
      -> if still invalid after retry, return 502 with a clear
         "evaluation service returned malformed output" error
  - If parsing succeeds, validate the schema:
      -> all required keys present?
      -> scores are numbers between 0-10?
      -> array fields are actually arrays?
      -> corrected_code is either a string or null, never missing?
  - If schema is invalid, treat the same as a parse failure (retry once, then error)
  |
  v
[5] POST-PROCESSING (optional, deterministic — not evaluation logic)
  - Compute overall_average_score across individual_reviews if not
    reliably returned by the model
  - Round/clamp scores defensively (e.g. clamp to 0-10 in case the model
    slightly overshoots)
  - Attach request metadata (timestamp, request_id) for logging/audit
  - NOTE: this step must only do arithmetic/formatting on what the model
    already decided — it must never inject or override a judgment
    (see the "no hardcoding" principle from the evaluation prompt)
  |
  v
[6] RESPONSE TO CLIENT
  - Return 200 with the validated JSON
  - Log the request/response pair for later review (helps you spot when
    the model is drifting or being inconsistent)
  |
  v
CLIENT receives structured review
```

---

## Component Responsibilities (keep these separate — one job each)

| Component | Responsibility | Should NOT do |
|---|---|---|
| `api/routes.py` | Receive HTTP request, call validation, call service layer, return HTTP response | Should not build prompts or call the LLM directly |
| `schemas.py` | Define request/response Pydantic models | Should not contain business logic |
| `prompt_builder.py` | Build the exact prompt string sent to the LLM | Should not make any evaluative judgment itself |
| `llm_client.py` | Send prompt to the model, handle timeouts/retries, return raw text | Should not parse or interpret the content — just transport |
| `response_validator.py` | Parse JSON, validate schema, clamp/round scores | Should not decide right/wrong on the code — only checks structure |
| `main.py` | Wire the app together, start the server | Should not contain evaluation or parsing logic |

Keeping these separate means: if the model output format changes, you only touch
`response_validator.py`. If you swap models, you only touch `llm_client.py`. If
you change scoring rubrics, you only touch `prompt_builder.py`.

---

## Error Handling Summary

| Failure point | HTTP status | Behavior |
|---|---|---|
| Missing/invalid input fields | 400 | Return specific field errors, no LLM call made |
| LLM unreachable / timeout | 502 or 504 | Return error, do not retry indefinitely — cap retries (e.g. 1 retry) |
| LLM returns invalid JSON | 502 (after 1 retry) | Log the raw output for debugging |
| LLM returns valid JSON but wrong schema | 502 (after 1 retry) | Log the raw output for debugging |
| Everything succeeds | 200 | Return the validated response |

---

## Batch vs. Single Submission

- If the client sends one question+code pair, `summary_gen_flag` can be `False`
  (no need for a cross-question summary).
- If the client sends multiple question+code pairs in one request, set
  `summary_gen_flag = True` so the model also produces `summary_review`.
- Either way, `individual_reviews` is always a list — even a single-item
  request should still return a list with one entry, so the client-side
  parsing logic doesn't need two different code paths.
