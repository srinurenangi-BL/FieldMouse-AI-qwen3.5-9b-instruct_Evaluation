# AGENTS.md — Standing Rules for This Project

This file is read automatically by every agent session in this workspace.
Do not ask the user to repeat any of the below — treat it as already given.

## Project

A backend API service that evaluates student code submissions using an LLM
(Qwen2.5-Coder-7B-Instruct). Single endpoint: `POST /review`. Stateless,
no database.

## Current file structure (do not change this layout)

```
main.py                - entry point, defines POST /review, orchestrates
                          the flow below, no prompt text or LLM calls here
prompt.py               - builds the exact prompt string(s) sent to the
                          LLM, including scoring rubrics. Single source of
                          truth for evaluation criteria. No HTTP calls here.
llm_client.py           - sends the prompt to the LLM endpoint, handles
                          timeout, retries at most once, returns raw text.
                          No parsing or evaluation logic here.
response_validator.py   - parses the LLM's JSON output, validates required
                          fields/types, clamps scores to 0-10. Never
                          overrides or adds to the LLM's actual judgment.
schemas.py              - Pydantic (or dataclass) models for request and
                          response shapes. No business logic here.
config.py               - reads settings from .env. Nothing else.
templates/index.html    - simple manual-check UI, kept separate from
                          /review logic
scratch_seq_test.py     - scratch file, not part of the app, do not edit
                          unless explicitly asked
test_pipeline_e2e.py    - end-to-end test, run this after any change that
                          touches more than one file
test_syntax_fix.py      - scratch/test file, not part of the app, do not
                          edit unless explicitly asked
```

## Reference docs (read before larger changes)

- @docs/01_workflow_process.md — full request lifecycle: validation,
  prompt construction, LLM call, response validation/retry, error handling
- @docs/02_architecture_design.md — the original design spec this project
  was built from, including the request/response JSON shapes

## Non-negotiable rules

1. **No hardcoded evaluation logic in Python.** No regex, linter output, or
   rule-based checks that decide correctness, quality, or scores. All
   judgment comes from the LLM's JSON response, built in `prompt.py`.

2. **Keep the flat structure above.** No `app/` package, no `services/`,
   no `repositories/` folder. If a new concern comes up, add one file at
   the root with a clear single responsibility — do not restructure.

3. **No speculative extensibility.** No abstract base classes, plugin
   systems, or "future model swapping" scaffolding.

4. **No auth, rate limiting, caching, or database** unless explicitly
   requested.

5. **Retry the LLM call at most once** on malformed/invalid JSON output.
   Never retry indefinitely.

6. **Type hints everywhere. Pydantic models for all request/response
   shapes** — never raw dicts crossing a function boundary.

7. **One job per function.** If a function needs "and then it also does X"
   in its docstring, split it.

8. **No bare `except:` blocks** — catch specific exceptions.

9. **Never touch `scratch_seq_test.py` or `test_syntax_fix.py`** unless
   explicitly asked to.

10. After any change spanning more than one file, run
    `test_pipeline_e2e.py` before considering the task done.

## When editing the evaluation prompt itself

The prompt text in `prompt.py` is the single source of truth for scoring
rubrics and evaluation behavior. If asked to change how scoring or feedback
works, edit the prompt string there — do not add Python-side logic in
`response_validator.py` or `main.py` to compensate for or override what
the LLM decides.
