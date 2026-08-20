from typing import List, Optional
from schemas import CodeSubmission, DEFAULT_TARGET_LANGUAGE


def format_submissions(submissions: List[CodeSubmission]) -> str:
    parts = []
    for i, sub in enumerate(submissions, start=1):
        block = f"--- Question {i} ---\n"
        block += f"QUESTION: {sub.question_text}\n"
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
) -> str:
    instructions_text = (
        specific_instructions.strip()
        if specific_instructions and specific_instructions.strip()
        else "None specified (follow standard industry best practices for the question)."
    )

    INDIVIDUAL_PART = f"""The expected programming language is: {target_language}

### 1. QUESTION STATEMENT:
{question_text}

### 2. MANDATORY SPECIFIC INSTRUCTIONS & CONSTRAINTS:
{instructions_text}

### 3. STUDENT SUBMITTED CODE:
{student_code}

Instructions for Evaluation:
1. LANGUAGE VERIFICATION:
- If submitted code is NOT written in {target_language}:
  - Assign 0.0 to all scores.
  - Set correctness_feedback to: "⚠️ Language Mismatch: Submitted code was detected as [detected_language], but expected {target_language}. Evaluation skipped and 0.0 score assigned."
  - In summary_review, set overall_average_score: 0.0, overall_quality_label: "Critical", common_errors: "⚠️ Language Mismatch", strengths: "None", weaknesses: "Code written in another language", recommendations: "Please rewrite and submit in {target_language}."

2. IN-DEPTH EVALUATION & MANDATORY INSTRUCTION COMPLIANCE (If language matches {target_language}):
- MANDATORY INSTRUCTIONS ARE STRICT REQUIREMENTS: Verify full adherence to the 'MANDATORY SPECIFIC INSTRUCTIONS & CONSTRAINTS' listed above.
  - If any constraint or instruction is violated or ignored (e.g. required data structure, algorithm approach, prohibited operator, or edge-case handling):
    - Heavily penalize completeness_score and approach_taken_score.
    - Explicitly state the missed constraint / rule violation in correctness_feedback and weaknesses.
- Check functional correctness, bugs, logic flaws, time/space efficiency, readability, and syntax.
- Merge correctness assessment AND improvement suggestions into correctness_feedback as exactly 2 sentences:
  - Sentence 1: assess correctness and mandatory instruction compliance.
  - Sentence 2: provide a genuine improvement suggestion, or confirm the code is optimal. Do NOT invent unnecessary suggestions.
- Do NOT output improvement_suggestions as a separate key.

Scoring (ALL SCORES MUST BE OUT OF 10):
- completeness_score (0.0–10.0): degree to which problem requirements and all mandatory instructions are satisfied.
- code_quality_score (0.0–10.0): syntax, naming, formatting, structure, and clean coding standards.
- approach_taken_score (0.0–10.0): algorithm design, efficiency, and compliance with the requested approach.
- overall_score formula:
  overall_score = (0.5 * completeness_score) + (0.3 * code_quality_score) + (0.2 * approach_taken_score)"""

    SUMMARY_PART = """

------------------------------------------------------------
SUMMARY REVIEW
------------------------------------------------------------
Provide:
- overall_quality_label (9–10: Excellent, 7.5–8.9: Good, 6–7.4: Average, 4–5.9: Poor, below 4: Critical)
- common_errors: key errors or constraint violations found
- strengths: highlights of good practices and compliance
- weaknesses: bugs, missed constraints, or unhandled edge cases
- recommendations: clear steps for optimization or correction"""

    SCORE_PART = """

------------------------------------------------------------
OUTPUT FORMAT
------------------------------------------------------------
Output ONLY the following JSON object directly starting with '{'. Do NOT write 'Thinking Process:', preamble, or markdown notes outside the JSON:
{
    "individual_reviews": [
        {
            "question_text": "",
            "correctness_feedback": "",
            "scores": {
                "completeness_score": 0.0,
                "code_quality_score": 0.0,
                "approach_taken_score": 0.0,
                "overall_score": 0.0
            }
        }
    ],
    "summary_review": {
        "overall_average_score": 0.0,
        "overall_quality_label": "",
        "common_errors": "",
        "strengths": "",
        "weaknesses": "",
        "recommendations": ""
    }
}"""

    SCORE_WITHOUT_SUMM_PART = """

------------------------------------------------------------
OUTPUT FORMAT
------------------------------------------------------------
Output ONLY the following JSON object directly starting with '{'. Do NOT write 'Thinking Process:', preamble, or markdown notes outside the JSON:
{
    "individual_reviews": [
        {
            "question_text": "",
            "correctness_feedback": "",
            "scores": {
                "completeness_score": 0.0,
                "code_quality_score": 0.0,
                "approach_taken_score": 0.0,
                "overall_score": 0.0
            }
        }
    ],
    "summary_review": "None"
}"""

    if summary_gen_flag:
        return INDIVIDUAL_PART + SUMMARY_PART + SCORE_PART
    else:
        return INDIVIDUAL_PART + SCORE_WITHOUT_SUMM_PART