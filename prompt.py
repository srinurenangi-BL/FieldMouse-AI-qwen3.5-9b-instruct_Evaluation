from __future__ import annotations

import json
from typing import Any


def build_master_prompt(
    language: str,
    question: str,
    student_code: str
) -> str:
    return f"""You are a strict code evaluator. You will be given a PROBLEM STATEMENT and a STUDENT CODE SUBMISSION in {language}. Evaluate the code carefully against the checklist below. Do not give marks or scores — only give findings.

IMPORTANT: Base every single finding purely on your own reading and reasoning about the exact code shown below. Do not use any fixed rule list, external tool, or memorized answer for this kind of problem. Do not assume anything about the code that is not actually visible in it. If you are unsure whether something is an issue, say so explicitly rather than guessing.

EXPECTED_LANGUAGE: {language}

PROBLEM STATEMENT:
{question}

STUDENT CODE:
{student_code}

Evaluate the code under EXACTLY these categories, in this order. For each category, output:
- Status: OK / MINOR ISSUE / MAJOR ISSUE / NOT APPLICABLE
- Findings: 1-3 short bullet points (be specific, quote line numbers or code snippets if possible)

CATEGORIES:
1. Syntax — compilation/parsing errors, incorrect language usage, deprecated syntax
2. Correctness — does it solve the stated problem? Does it handle edge cases (empty input, zero, negative, large, duplicate)?
3. Logic and Algorithm Choice — is the approach appropriate and not needlessly complex?
4. Efficiency — time complexity and space complexity concerns
5. Code Structure — modularity, function decomposition, repeated/duplicated code
6. Naming — variable/function name clarity and consistency
7. Formatting and Readability — indentation, spacing, line length
8. Error Handling — input validation, handling of invalid/unexpected input, crash safety
9. Security — hardcoded secrets, unsafe functions, injection risks (if applicable)
10. Memory Management — leaks, dangling references (only for C/C++ or manual memory languages, else write NOT APPLICABLE)
11. Constraint Adherence — did the code follow any explicit rules from the problem statement?
12. Comments and Documentation — are non-obvious parts explained? Not over/under-commented?
13. Testing — are there test cases included? Do they cover edge cases?

After the 13 categories, output a final section:

OVERALL SUMMARY:
- Top 3 strengths (bullet points)
- Top 3 problems that must be fixed (bullet points)

Do not skip any category. Do not add extra commentary outside this format. Do not assign a numeric score or grade."""


# ── SPLIT PIPELINE PROMPT BUILDERS ─────────────────────────────────────────

def build_stage1_syntax_correctness_prompt(
    language: str,
    question: str,
    student_code: str
) -> str:
    return f"""You are a code evaluator. Look ONLY at SYNTAX and CORRECTNESS. Ignore style, efficiency, and everything else. Base every finding purely on your own reading of the exact code below — do not use any external tool, fixed rule list, or memorized answer.

EXPECTED_LANGUAGE: {language}

PROBLEM STATEMENT:
{question}

STUDENT CODE:
{student_code}

Answer in this exact format:

SYNTAX:
- Status: OK / MINOR ISSUE / MAJOR ISSUE
- Findings: Perform a strict Language Match Audit. First, check structural signatures, imports, headers, and syntax in STUDENT CODE against EXPECTED_LANGUAGE: {language}. If STUDENT CODE is written in a different programming language than EXPECTED_LANGUAGE: {language}, mark Status as MAJOR ISSUE and explicitly state: 'LANGUAGE MISMATCH: Submitted code is written in another programming language, not {language}.' List any syntax errors or missing constructs with line references.

CORRECTNESS:
- Status: OK / MINOR ISSUE / MAJOR ISSUE
- Does it solve the problem as stated? (Yes/No/Partially)
- Edge cases checked: empty input, zero, negative numbers, large input, duplicates — for each, state whether the code would handle it correctly or fail.

Do not comment on anything outside syntax and correctness."""


def build_stage2_algorithm_efficiency_prompt(
    language: str,
    question: str,
    student_code: str
) -> str:
    return f"""You are a code evaluator. Look ONLY at ALGORITHM CHOICE and EFFICIENCY. Ignore syntax, correctness, and style. Base every finding purely on your own reading of the exact code below — do not use any external tool, fixed rule list, or memorized answer.

EXPECTED_LANGUAGE: {language}

PROBLEM STATEMENT:
{question}

STUDENT CODE:
{student_code}

Answer in this exact format:

ALGORITHM CHOICE:
- Status: OK / MINOR ISSUE / MAJOR ISSUE
- Is the approach appropriate for the problem? Explain briefly.
- Is it needlessly complex or a brute-force where a better-known method exists?

EFFICIENCY:
- Status: OK / MINOR ISSUE / MAJOR ISSUE
- Estimated time complexity (Big-O) and why
- Estimated space complexity (Big-O) and why
- Any obvious inefficiencies (nested loops, redundant recomputation, unnecessary data structures)

Do not comment on anything outside algorithm choice and efficiency."""


def build_stage3_structure_naming_prompt(
    language: str,
    question: str,
    student_code: str
) -> str:
    return f"""You are a code evaluator. Look ONLY at CODE STRUCTURE, NAMING, and READABILITY. Ignore correctness and efficiency. Base every finding purely on your own reading of the exact code below — do not use any external tool, fixed rule list, or memorized answer.

EXPECTED_LANGUAGE: {language}

STUDENT CODE:
{student_code}

Answer in this exact format:

STRUCTURE:
- Status: OK / MINOR ISSUE / MAJOR ISSUE
- Is logic broken into functions/classes appropriately?
- Any duplicated code blocks that should be reusable functions?

NAMING:
- Status: OK / MINOR ISSUE / MAJOR ISSUE
- Are variable/function names meaningful and consistent?

READABILITY & FORMATTING:
- Status: OK / MINOR ISSUE / MAJOR ISSUE
- Indentation, spacing, line length issues

Do not comment on anything outside these three areas."""


def build_stage4_error_security_prompt(
    language: str,
    question: str,
    student_code: str
) -> str:
    return f"""You are a code evaluator. Look ONLY at ERROR HANDLING, SECURITY, MEMORY MANAGEMENT, and DOCUMENTATION. Base every finding purely on your own reading of the exact code below — do not use any external tool, fixed rule list, or memorized answer.

EXPECTED_LANGUAGE: {language}

STUDENT CODE:
{student_code}

Answer in this exact format:

ERROR HANDLING:
- Status: OK / MINOR ISSUE / MAJOR ISSUE
- Does the code validate input and handle invalid/unexpected cases without crashing?

SECURITY:
- Status: OK / MINOR ISSUE / MAJOR ISSUE / NOT APPLICABLE
- Any hardcoded secrets, unsafe functions, or injection risks?

MEMORY MANAGEMENT:
- Status: OK / MINOR ISSUE / MAJOR ISSUE / NOT APPLICABLE
- (Only relevant for C/C++ or manual-memory languages — else write NOT APPLICABLE)

COMMENTS & DOCUMENTATION:
- Status: OK / MINOR ISSUE / MAJOR ISSUE
- Are non-obvious parts explained? Is commenting excessive or insufficient?

Do not comment on anything outside these four areas."""


def build_stage5_constraints_testing_prompt(
    language: str,
    question: str,
    student_code: str
) -> str:
    return f"""You are a code evaluator. Look ONLY at CONSTRAINT ADHERENCE and TESTING. Base every finding purely on your own reading of the exact code below — do not use any external tool, fixed rule list, or memorized answer.

EXPECTED_LANGUAGE: {language}

PROBLEM STATEMENT:
{question}

STUDENT CODE:
{student_code}

Answer in this exact format:

CONSTRAINT ADHERENCE:
- Status: OK / MINOR ISSUE / MAJOR ISSUE / NOT APPLICABLE
- Explicit Mandated Method Check: Check if the PROBLEM STATEMENT explicitly requires using specific classes, methods, or techniques. If the student used a different approach instead of the mandated method, mark Status as MAJOR ISSUE and explicitly state what mandated method was ignored.
- Did the code follow all explicit constraints stated in the problem statement?

TESTING:
- Status: OK / MINOR ISSUE / MAJOR ISSUE / NOT APPLICABLE
- Are test cases present? Do they cover edge cases, or only the happy path?

Do not comment on anything outside these two areas."""


def build_stage6_aggregator_prompt(
    language: str,
    question: str,
    student_code: str,
    stage1_out: str,
    stage2_out: str,
    stage3_out: str,
    stage4_out: str,
    stage5_out: str
) -> str:
    return f"""You are Stage 6 (Aggregator) of a Code Evaluator Pipeline.
You will be given evaluation notes from 5 separate reviews of the same code submission in {language}.
Combine them into a single clean JSON report. Do not re-evaluate the code — only reorganize and summarize what is given to you in the 5 stage outputs below.

EXPECTED_LANGUAGE: {language}

PROBLEM STATEMENT:
{question}

STUDENT CODE:
{student_code}

STAGE 1 OUTPUT (Syntax & Correctness):
{stage1_out}

STAGE 2 OUTPUT (Algorithm & Efficiency):
{stage2_out}

STAGE 3 OUTPUT (Structure, Naming, Readability):
{stage3_out}

STAGE 4 OUTPUT (Error Handling, Security, Documentation):
{stage4_out}

STAGE 5 OUTPUT (Constraints & Testing):
{stage5_out}

SCORING & SYNTHESIS RULES:
1. Gatekeeper checks & Language Mismatch Rule:
   - If STUDENT CODE is empty or placeholder ("N/A", "TODO"): completeness_score=0.0, code_quality_score=0.0, approach_taken_score=0.0, overall_score=0.0.
   - If Stage 1 reports LANGUAGE MISMATCH (student code is written in a different programming language than EXPECTED_LANGUAGE):
     * MUST set ALL scores (completeness_score, code_quality_score, approach_taken_score, overall_score) to 0.0.
     * MUST set correctness_feedback to: "Language Mismatch Error. The submitted code is written in a different programming language than expected."
     * MUST set common_errors to: "Language Mismatch: Submitted code does not match EXPECTED_LANGUAGE."
     * MUST set weaknesses to: "Submitted code is written in an incorrect programming language."
     * MUST provide a 100% correct reference solution in EXPECTED_LANGUAGE under corrected_code.
2. Mandated Method & Constraint Compliance Rule:
   - Check Stage 5 output carefully: If Stage 5 notes that the student ignored an explicitly mandated class/method:
     * MUST set approach_taken_score to 4.0 - 5.0.
     * MUST include under common_errors the specific mandated approach that was ignored.
     * MUST include under weaknesses the failed mandate.
     * MUST include under recommendations actionable advice to refactor using the mandated method.
3. Score derivation:
   - completeness_score: 9.0–10.0 if correct and solves problem; 5.0–6.5 if syntax/compilation errors or incorrect logic.
   - approach_taken_score: 9.0–10.0 if all problem constraints followed; 4.0–5.0 if mandated method ignored or forbidden operator used.
   - code_quality_score: 9.0–10.0 if clean/idiomatic; 6.0–7.5 if minor style issues; 3.0–6.0 if syntax/compilation errors exist.
   - overall_score = round((0.5 * completeness_score) + (0.3 * code_quality_score) + (0.2 * approach_taken_score), 1).
4. Synthesize fields:
   - correctness_feedback: EXACTLY 2 sentences detailing functional accuracy, syntax validity, and requirement compliance based strictly on Stage 1 findings.
   - common_errors: List specific syntax errors, missing semicolons, or constraint violations from Stage 1 and Stage 5 findings. Write "None" if clean.
   - strengths: Bulleted top 3 strengths derived strictly from Stage 1–5 findings.
   - weaknesses: Bulleted top 3 problems that must be fixed derived strictly from Stage 1–5 findings. Write "None" if optimal.
   - recommendations: Actionable step-by-step recommendations for fixing errors and improving code.
   - corrected_code: A complete, valid reference solution in {language} satisfying ALL question requirements and best practices.

OUTPUT FORMAT — Return ONLY this JSON object:
{{
  "individual_reviews": [
    {{
      "question_text": "{question}",
      "correctness_feedback": "<EXACTLY 2 sentences based on Stage 1>",
      "common_errors": "<Specific line errors, constraint violations, or 'None'>",
      "strengths": "<Top 3 strengths as bullet points from Stage 1–5 findings>",
      "weaknesses": "<Top 3 problems to fix as bullet points from Stage 1–5 findings, or 'None'>",
      "recommendations": "<Actionable recommendations based on Stage 1–5 findings>",
      "scores": {{
        "completeness_score": 0.0,
        "code_quality_score": 0.0,
        "approach_taken_score": 0.0,
        "overall_score": 0.0
      }},
      "corrected_code": "<Complete valid reference solution in {language}>"
    }}
  ]
}}"""


def build_evaluation_prompt(
    language: str,
    question: str,
    student_code: str,
    specific_instructions: str = "",
    summary_gen_flag: bool = False
) -> str:
    full_q = f"{question}\n\nSPECIFIC_INSTRUCTIONS: {specific_instructions}" if specific_instructions else question
    return build_master_prompt(language, full_q, student_code)