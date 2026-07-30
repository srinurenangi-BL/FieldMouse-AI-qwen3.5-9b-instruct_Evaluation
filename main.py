from __future__ import annotations

import asyncio
import httpx
from pathlib import Path
from typing import List, Optional, Union

from fastapi import FastAPI, HTTPException, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse

from config import TEMPLATES_DIR
from schemas import (
    CodeSubmission,
    CodeReviewRequest,
    IndividualReview,
    SummaryReview,
    PromptDrivenCodeReviewResponse,
    ScoreBreakdown
)
from prompt import (
    build_stage1_syntax_correctness_prompt,
    build_stage2_algorithm_efficiency_prompt,
    build_stage3_structure_naming_prompt,
    build_stage4_error_security_prompt,
    build_stage5_constraints_testing_prompt,
    build_stage6_aggregator_prompt
)
from llm_client import send_prompt, LLMClientError
from response_validator import parse_and_validate_llm_json, JSONValidationError


app = FastAPI(
    title="LMS Code Evaluator & Quality Review API",
    description="Production-grade AI Code Evaluation REST API backed by Qwen 2.5 Coder 7B 6-Stage Split Pipeline.",
    version="6.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/", response_class=HTMLResponse)
async def serve_ui():
    """Serves the frontend manual check UI from templates/index.html."""
    index_path = TEMPLATES_DIR / "index.html"
    if not index_path.exists():
        raise HTTPException(404, "Frontend templates/index.html not found.")
    return index_path.read_text(encoding="utf-8")


async def evaluate_single_submission(
    language: str,
    submission: CodeSubmission
) -> IndividualReview:
    """Evaluates a single code submission through the 6-stage LLM split pipeline."""
    full_q = (
        f"{submission.question_text}\n\nSPECIFIC_INSTRUCTIONS: {submission.specific_instructions}"
        if submission.specific_instructions
        else submission.question_text
    )

    # ──── STAGES 1 to 5: Concurrent Category Evaluations ────
    p1 = build_stage1_syntax_correctness_prompt(language, full_q, submission.code)
    p2 = build_stage2_algorithm_efficiency_prompt(language, full_q, submission.code)
    p3 = build_stage3_structure_naming_prompt(language, full_q, submission.code)
    p4 = build_stage4_error_security_prompt(language, full_q, submission.code)
    p5 = build_stage5_constraints_testing_prompt(language, full_q, submission.code)

    s1_out, s2_out, s3_out, s4_out, s5_out = await asyncio.gather(
        send_prompt(p1, is_json_format=False),
        send_prompt(p2, is_json_format=False),
        send_prompt(p3, is_json_format=False),
        send_prompt(p4, is_json_format=False),
        send_prompt(p5, is_json_format=False)
    )

    # ──── STAGE 6: Aggregator & Reference Code Synthesis ────
    p6 = build_stage6_aggregator_prompt(
        language=language,
        question=full_q,
        student_code=submission.code,
        stage1_out=s1_out,
        stage2_out=s2_out,
        stage3_out=s3_out,
        stage4_out=s4_out,
        stage5_out=s5_out
    )

    raw_aggregator_text = await send_prompt(p6, is_json_format=True)
    parsed_json = parse_and_validate_llm_json(raw_aggregator_text)

    ind_list = parsed_json.get("individual_reviews", [])
    if ind_list and isinstance(ind_list, list) and isinstance(ind_list[0], dict):
        item = ind_list[0]
        scores_raw = item.get("scores", {}) if isinstance(item.get("scores"), dict) else {}
        return IndividualReview(
            question_text=submission.question_text,
            correctness_feedback=str(item.get("correctness_feedback", "")),
            common_errors=str(item.get("common_errors", "None")),
            strengths=str(item.get("strengths", "None")),
            weaknesses=str(item.get("weaknesses", "None")),
            recommendations=str(item.get("recommendations", "None")),
            scores=ScoreBreakdown(
                completeness_score=float(scores_raw.get("completeness_score", 0.0)),
                code_quality_score=float(scores_raw.get("code_quality_score", 0.0)),
                approach_taken_score=float(scores_raw.get("approach_taken_score", 0.0)),
                overall_score=float(scores_raw.get("overall_score", 0.0))
            ),
            corrected_code=item.get("corrected_code")
        )
    else:
        scores_raw = parsed_json.get("scores", {}) if isinstance(parsed_json.get("scores"), dict) else {}
        return IndividualReview(
            question_text=submission.question_text,
            correctness_feedback=str(parsed_json.get("correctness_feedback", "")),
            common_errors=str(parsed_json.get("common_errors", "None")),
            strengths=str(parsed_json.get("strengths", "None")),
            weaknesses=str(parsed_json.get("weaknesses", "None")),
            recommendations=str(parsed_json.get("recommendations", "None")),
            scores=ScoreBreakdown(
                completeness_score=float(scores_raw.get("completeness_score", 0.0)),
                code_quality_score=float(scores_raw.get("code_quality_score", 0.0)),
                approach_taken_score=float(scores_raw.get("approach_taken_score", 0.0)),
                overall_score=float(scores_raw.get("overall_score", 0.0))
            ),
            corrected_code=parsed_json.get("corrected_code")
        )


@app.post("/review", response_model=PromptDrivenCodeReviewResponse)
@app.post("/api/v1/review", response_model=PromptDrivenCodeReviewResponse)
async def review_code(request: CodeReviewRequest):
    """Main POST endpoint to review code submissions using the LLM evaluation pipeline."""
    if not request.submissions:
        raise HTTPException(status_code=400, detail="At least one submission must be provided in the request.")

    try:
        reviews: List[IndividualReview] = []
        for sub in request.submissions:
            rev = await evaluate_single_submission(request.language, sub)
            reviews.append(rev)

        summary_rev: Optional[Union[SummaryReview, str]] = None
        if len(reviews) > 1:
            total_avg = round(sum(r.scores.overall_score for r in reviews) / len(reviews), 1)
            label = "Excellent" if total_avg >= 8.5 else ("Good" if total_avg >= 7.0 else ("Average" if total_avg >= 5.0 else "Critical"))
            summary_rev = SummaryReview(
                overall_average_score=total_avg,
                overall_quality_label=label,
                common_errors="; ".join(r.common_errors for r in reviews if r.common_errors != "None"),
                strengths="; ".join(r.strengths for r in reviews if r.strengths != "None"),
                weaknesses="; ".join(r.weaknesses for r in reviews if r.weaknesses != "None"),
                recommendations="; ".join(r.recommendations for r in reviews if r.recommendations != "None")
            )

        return PromptDrivenCodeReviewResponse(
            individual_reviews=reviews,
            summary_review=summary_rev
        )

    except LLMClientError as exc:
        raise HTTPException(status_code=503, detail=f"LLM communication error: {exc}")
    except JSONValidationError as exc:
        raise HTTPException(status_code=422, detail=f"LLM output validation error: {exc}")
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Internal evaluation error: {exc}")


@app.get("/api/v1/health")
async def health():
    """Health check endpoint to verify API and LLM connectivity."""
    try:
        async with httpx.AsyncClient(timeout=3.0) as client:
            from config import OLLAMA_BASE_URL
            r = await client.get(f"{OLLAMA_BASE_URL}/api/tags")
            return {"status": "healthy", "ollama": "connected" if r.status_code == 200 else "error"}
    except Exception:
        return {"status": "healthy", "ollama": "unreachable"}
