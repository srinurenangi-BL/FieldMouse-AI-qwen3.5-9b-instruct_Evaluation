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
    ques_ans_content_with_inst: str = "",
    summary_gen_flag: bool = False,
    language: Optional[str] = None
) -> str:
    if language:
        target_language = language

    INDIVIDUAL_PART = f"""
            The submitted programming language is:

            {target_language}

            Below are the question-answer pairs submitted by the user.

            Each item may optionally contain SPECIFIC INSTRUCTIONS.
            These instructions represent additional constraints,
            expected approaches, edge cases, evaluation criteria,
            or implementation requirements for that particular question.

            While evaluating each answer:
            - Carefully follow the SPECIFIC INSTRUCTIONS if present
            - Evaluate whether the submitted answer satisfies them
            - Include violations or missed requirements in the feedback

            Submitted Question–Answer Data:

            {ques_ans_content_with_inst}

            Tasks:

            ------------------------------------------------------------
            1. REVIEW EACH QUESTION–ANSWER INDIVIDUALLY
            ------------------------------------------------------------

            For each item:

            - Analyze correctness
            - Identify bugs
            - Evaluate readability
            - Evaluate efficiency
            - Validate adherence to SPECIFIC INSTRUCTIONS (if present)
            - Merge correctness assessment AND improvement suggestions into
              correctness_feedback as exactly 2 sentences.
              Sentence 1: assess correctness.
              Sentence 2: a genuine improvement if one exists, or confirm the
              code is optimal. Do not invent suggestions.
            - Do NOT output improvement_suggestions as a separate key.

            Scoring (ALL SCORES MUST BE OUT OF 10):
            - completeness_score
            - code_quality_score
            - approach_taken_score
            - overall_score

            overall_score formula:
            (0.5 * completeness_score)
            + (0.3 * code_quality_score)
            + (0.2 * approach_taken_score)"""

    SUMMARY_PART = """------------------------------------------------------------
        2. SUMMARY REVIEW
        ------------------------------------------------------------

        Provide:
        - overall_quality_label
        - common mistakes
        - strengths
        - weaknesses
        - recommendations

        overall_quality_label mapping:
        - 9–10 → Excellent
        - 7.5–8.9 → Good
        - 6–7.4 → Average
        - 4–5.9 → Poor
        - below 4 → Critical"""

    SCORE_PART = """------------------------------------------------------------
        3. OUTPUT FORMAT
        ------------------------------------------------------------

        Return this exact JSON schema:

        {{
            "individual_reviews": [
                {{
                    "question_text": "",
                    "correctness_feedback": "",
                    "scores": {{
                        "completeness_score":0.0,
                        "code_quality_score": 0.0,
                        "approach_taken_score": 0.0,
                        "overall_score": 0.0
                    }}
                }}
            ],
            "summary_review": {{
                "overall_average_score": 0.0,
                "overall_quality_label": "",
                "common_errors": "",
                "strengths": "",
                "weaknesses": "",
                "recommendations": ""
            }}
        }}

        Rules:
        - All scores must be between 0 and 10
        - Output ONLY valid JSON
        - Do not include markdown
        - Do not include explanations outside JSON
        - Base analysis strictly on the submitted code
        """

    SCORE_WITHOUT_SUMM_PART = """------------------------------------------------------------
        3. OUTPUT FORMAT
        ------------------------------------------------------------

        Return this exact JSON schema:

        {{
            "individual_reviews": [
                {{
                    "question_text": "",
                    "correctness_feedback": "",
                    "scores": {{
                        "completeness_score":0.0,
                        "code_quality_score": 0.0,
                        "approach_taken_score": 0.0,
                        "overall_score": 0.0
                    }}
                }}
            ],
            "summary_review":"None"
        }}

        Rules:
        - All scores must be between 0 and 10
        - Output ONLY valid JSON
        - Do not include markdown
        - Do not include explanations outside JSON
        - Do not include improvement_suggestions in the output
        - Base analysis strictly on the submitted code
        """

    if summary_gen_flag:
        return INDIVIDUAL_PART + SUMMARY_PART + SCORE_PART
    else:
        return INDIVIDUAL_PART + SCORE_WITHOUT_SUMM_PART