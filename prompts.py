from typing import List, Optional, Tuple
from schemas import CodeSubmission, DEFAULT_TARGET_LANGUAGE


EVALUATION_SYSTEM_PROMPT = """You are an expert programming instructor and strict code evaluator.
Act as an expert coaching teacher, not a harsh judge.
Priority order: Logic & Approach > Completeness & Edge Cases > Code Quality & Syntax.
Follow all sequential phases and output strictly valid JSON matching the requested schema."""


def format_submissions(submissions: List[CodeSubmission]) -> str:
    formatted_parts = []
    for index, submission_item in enumerate(submissions, start=1):
        submission_block = f"--- Question {index} ---\nQUESTION: {submission_item.question_text}\n"
        if submission_item.specific_instructions:
            submission_block += f"SPECIFIC INSTRUCTIONS (Optional): {submission_item.specific_instructions}\n"
        submission_block += f"CODE:\n{submission_item.code}"
        formatted_parts.append(submission_block)
    return "\n\n".join(formatted_parts)


def build_language_detection_prompt(target_language: str, code: str) -> str:
    return f"""You are a programming language detector.
Identify what programming language the following code is written in,
and whether it matches the expected language.

EXPECTED LANGUAGE: {target_language}

CODE:
{code}

Reply with ONLY this JSON (no markdown, no explanation):
{{
    "match": true or false,
    "detected_language": "the actual language of the code"
}}

Rules:
- "match" is true ONLY if the code is written in {target_language}
- "match" is false if the code is in any other language
- Output ONLY valid JSON, nothing else"""


def build_evaluation_prompt(
    target_language: str = DEFAULT_TARGET_LANGUAGE,
    question_text: str = "",
    student_code: str = "",
    specific_instructions: Optional[str] = None,
    summary_gen_flag: bool = True,
) -> Tuple[str, str]:
    effective_instructions_text = (
        specific_instructions.strip()
        if specific_instructions and specific_instructions.strip()
        else "None specified (grade purely on the problem statement and standard software best practices)."
    )

    escaped_question = question_text.replace('"', '\\"').replace("\n", " ").strip()
    system_prompt = EVALUATION_SYSTEM_PROMPT

    numbered_code_lines = [
        f"Line {idx}: {line}" for idx, line in enumerate(student_code.splitlines(), start=1)
    ]
    formatted_numbered_code = "\n".join(numbered_code_lines) if numbered_code_lines else student_code

    user_prompt = f"""### 1. TARGET PROGRAMMING LANGUAGE:
{target_language}

### 2. PROBLEM STATEMENT / QUESTION:
{question_text}

### 3. SPECIFIC INSTRUCTIONS & CONSTRAINTS (Optional):
{effective_instructions_text}

### 4. STUDENT SUBMITTED CODE (with line numbers):
{formatted_numbered_code}

=============================================================================
EVALUATION PIPELINE — MANDATORY STEP-BY-STEP PROCESS
=============================================================================
Think step-by-step through the student's submission following this exact sequence:

PHASE 1 — LANGUAGE GATE (Absolute First Step)
Check whether the submitted code is written in {target_language}.
  - If the code is written in a DIFFERENT programming language than {target_language}:
      1. Immediately abort any further evaluation.
      2. Set all four scores (completeness, code_quality, approach_taken, overall) to exactly 0.0.
      3. In correctness_feedback, clearly explain the language mismatch
         (naming expected language vs. detected language).
      4. Set overall_quality_label="Critical" and return the JSON immediately.
  - Otherwise, proceed to Phase 2. Note: Standalone functions or snippets lacking
    formal boilerplate/class scaffolding are still valid {target_language} submissions.

PHASE 2 — CORE ALGORITHMIC LOGIC & PROBLEM INTENT
Understand the question statement thoroughly.
  - Specific instructions/constraints are OPTIONAL. If provided, verify compliance.
    If none are provided, grade purely against the problem intent and best practices.
  - Evaluate whether the student's algorithmic strategy correctly solves the problem.
  - A sound algorithmic approach should be rewarded with high approach_taken_score
    and completeness_score (8.0-10.0), even if minor syntax or formatting errors exist.

PHASE 3 — EDGE CASES, ROBUSTNESS & ERROR HANDLING
Examine whether the code handles critical boundaries and edge cases:
  - Null, None, empty collections, single-element collections.
  - Boundary values (zero, negative numbers, extreme ranges).
  - Resource lifecycle management (e.g., closing streams/scanners if applicable).
  - Note unhandled edge cases in completeness_score and weaknesses.

PHASE 4 — EXHAUSTIVE LINE-BY-LINE SYNTAX & STRUCTURAL AUDIT
Perform an exhaustive line-by-line scan from the very first line to the final token.
  - BRACE & SYNTAX VERIFICATION: Check literal braces '{' and '}' directly from the code above.
    If opening and closing braces exist in the code, NEVER claim they are missing.
  - STRICT GROUNDING MANDATE: Grade ONLY what is literally written in the
    STUDENT SUBMITTED CODE above. Never invent, imagine, or hallucinate syntax errors.
  - If the code compiles and has valid syntax: You MUST state in 'common_errors':
    "None. The code has zero syntax errors." and award a high code_quality_score (9.0-10.0).
  - VERBATIM QUOTE REQUIREMENT: For any real error reported, quote the EXACT
    verbatim line of code from the student's submission. If a line is already
    correctly written or fixed in this code, do NOT report it as an error.
  - ANTI-EARLY-STOPPING MANDATE: Do NOT stop scanning after finding the first 1 or 2 errors.
    Scan every subsequent line to the end and report 100% of verified syntax errors with line numbers.

PHASE 5 — BALANCED SCORING & STRUCTURED JSON OUTPUT
Calculate balanced scores on a 0.0 to 10.0 scale (one decimal place):
  - overall_score = 0.5 * completeness_score + 0.3 * code_quality_score + 0.2 * approach_taken_score
  - Exception: Language Gate failure overrides all scores to exactly 0.0.

FIELD DEFINITIONS (write detailed, multi-line content for each):
  - executive_feedback: 3-5 sentence plain-language summary for an instructor skimming results.
  - correctness_feedback (per question): Detailed multi-line analysis covering what works,
    every bug/syntax flaw with line numbers, and concrete next steps.
  - common_errors: List every verified syntax/structural defect with its line number
    and explanation, or provide a specific confirmation that none exist.
  - strengths: What this specific student did well — cite actual logic, data structures, or clean naming.
  - weaknesses: Real gaps — unhandled edge cases, logic bugs, inefficient approaches.
  - recommendations: Concrete, actionable next steps for the student.

OUTPUT — return ONLY this JSON, no preamble, no code fences, no text outside the JSON:
{{
  "individual_reviews": [
    {{
      "question_text": "{escaped_question}",
      "correctness_feedback": "<detailed multi-line analysis: what works, what is broken with line numbers, and concrete next steps>",
      "scores": {{"completeness_score": 0.0, "code_quality_score": 0.0, "approach_taken_score": 0.0, "overall_score": 0.0}}
    }}
  ],
  "summary_review": {{
    "overall_average_score": 0.0,
    "overall_quality_label": "Excellent / Good / Average / Poor / Critical",
    "executive_feedback": "<3-5 sentence instructor-facing verdict>",
    "common_errors": "<list of verified defects with line numbers, or specific confirmation of none>",
    "strengths": "<detailed, specific to this code>",
    "weaknesses": "<detailed, specific to this code>",
    "recommendations": "<specific actions or specific confirmation code is strong>"
  }}
}}"""

    return (system_prompt, user_prompt)