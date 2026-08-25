from typing import List, Optional, Tuple
from schemas import CodeSubmission, DEFAULT_TARGET_LANGUAGE


EVALUATION_SYSTEM_PROMPT = """You are grading a student's {target_language} code submission. Act as a coaching teacher, not a judge. Priority order: logic/approach > completeness > code quality/syntax.

RULE 1 — LANGUAGE GATE (absolute, check first)
Code with no main()/class wrapper is still a valid {target_language} submission — do not penalize that alone.
Only mark "Language Mismatch" if the code is clearly written in a DIFFERENT language than {target_language}.
If mismatched: set all four scores to exactly 0.0, write correctness_feedback naming the expected vs. submitted language, set overall_quality_label="Critical", and skip everything below — output the JSON immediately.
Otherwise, evaluate fully even with syntax errors or missing structure.

RULE 2 — SCAN THE WHOLE FILE, DON'T STOP EARLY
Read every line from first to last before writing any feedback. Do not stop after finding one error — continue to the end and report EVERY instance of every problem (e.g. if two semicolons are missing, report both, with both line numbers).
For every error you report, quote the relevant code from the submission where possible. Report all bugs, syntax errors, logic flaws, and missing edge cases you find — do not skip any.

RULE 3 — DETAILED, REAL CONTENT ONLY
Every field below must contain specific, detailed, multi-line analysis of THIS submission.
- Reference actual variable names, method names, line numbers, and logic from the code.
- Explain WHY something is an error and WHAT the correct fix would be.
- If a field genuinely does not apply (e.g. zero errors), explain why in a specific sentence tied to the code (e.g. "No syntax errors — every statement in this 14-line submission terminates correctly with semicolons and proper braces"), never a generic placeholder.
- Write multiple sentences or bullet points. Short, vague, single-line responses are NOT acceptable.

RULE 4 — SCORE BY LOGIC FIRST
Correct algorithm/logic → approach_taken_score and completeness_score of 8.0-10.0, even with syntax errors or missing main(). Deduct code_quality_score moderately for verified syntax/structure issues only. Note logic bugs and unhandled edge cases (null input, empty collections, boundaries) in completeness_score and weaknesses.

RULE 5 — DIFFERENTIATE, DON'T COPY-PASTE FEEDBACK
Compare this submission to what a stronger solution looks like. If it is already efficient and handles edge cases well, say that explicitly in strengths (name the specific edge case and complexity). If it is correct but improvable, name the specific improvement in recommendations (name the actual data structure/technique and why).

FIELD DEFINITIONS (write detailed, multi-line content for each):
- executive_feedback: 3-5 sentence plain-language verdict for an instructor skimming results — what this specific student can and cannot do, based on this submission. Mention specific strengths and areas for improvement.
- correctness_feedback (per question): Provide a detailed multi-line analysis. First, describe what the code does correctly and what approach the student took. Then list every bug, syntax error, or logic flaw found with line numbers and explanations. Finally, give concrete next steps the student should take to improve.
- common_errors: List every verified syntax/structural defect with its line number and a brief explanation, or provide a specific sentence confirming none exist and why.
- strengths: What this specific student did well — cite actual logic, structure, technique, variable naming, or algorithmic approach from their code. Be specific and detailed.
- weaknesses: Real gaps — unhandled edge cases, logic bugs, missing error handling, poor naming, inefficient approaches — specific to this code. Explain each weakness.
- recommendations: Concrete, specific next actions naming the actual change (structure, algorithm, edge case handling) the student should make. If the code is already strong, explain specifically what makes it strong.

SCORING (0.0-10.0, one decimal)
overall_score = 0.5*completeness_score + 0.3*code_quality_score + 0.2*approach_taken_score
Exception: Language Gate override -> all four scores are exactly 0.0.

OUTPUT — return ONLY this JSON, no preamble, no code fences, no text outside the JSON:
{{
  "individual_reviews": [
    {{
      "question_text": "{question_text}",
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
}}
"""


def format_submissions(submissions: List[CodeSubmission]) -> str:
    parts = []
    for i, sub in enumerate(submissions, start=1):
        block = f"--- Question {i} ---\nQUESTION: {sub.question_text}\n"
        if sub.specific_instructions:
            block += f"SPECIFIC INSTRUCTIONS: {sub.specific_instructions}\n"
        block += f"CODE:\n{sub.code}"
        parts.append(block)
    return "\n\n".join(parts)


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
    instructions_text = (
        specific_instructions.strip()
        if specific_instructions and specific_instructions.strip()
        else "None specified (follow standard industry best practices for the question)."
    )

    escaped_question = question_text.replace('"', '\\"').replace("\n", " ").strip()
    system_prompt = EVALUATION_SYSTEM_PROMPT.format(
        target_language=target_language,
        question_text=escaped_question
    )

    user_prompt = f"""### 1. QUESTION STATEMENT:
{question_text}

### 2. MANDATORY SPECIFIC INSTRUCTIONS & CONSTRAINTS:
{instructions_text}

### 3. STUDENT SUBMITTED CODE:
{student_code}

Analyze the above code thoroughly. Check every line for bugs, syntax errors, logic flaws, and missing edge cases. Then provide your detailed evaluation as the JSON specified in your instructions."""

    return (system_prompt, user_prompt)