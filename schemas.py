import os
import re
from typing import Any, List, Optional, Union
from dotenv import load_dotenv
from pydantic import BaseModel, Field, model_validator

load_dotenv()
DEFAULT_TARGET_LANGUAGE = os.getenv("DEFAULT_TARGET_LANGUAGE", "Java")


class CodeSubmission(BaseModel):
    question_text: str = Field(..., description="The problem statement or question")
    code: str = Field(..., description="The student's submitted source code")
    specific_instructions: Optional[str] = Field(None, description="Optional extra constraints for this question")


class CodeReviewRequest(BaseModel):
    target_language: str = Field(default=DEFAULT_TARGET_LANGUAGE, description="Programming language of the submitted code")
    submissions: List[CodeSubmission] = Field(default_factory=list, description="List of question + code submissions to evaluate")

    @model_validator(mode="before")
    @classmethod
    def normalize_flat_payload(cls, data: Any) -> Any:
        if isinstance(data, dict) and not data.get("submissions"):
            question_text = data.get("question_text") or data.get("problem")
            code = data.get("code")
            instructions = data.get("specific_instructions") or data.get("instructions") or data.get("constraints")
            if question_text and code:
                data = dict(data)
                data["submissions"] = [
                    {
                        "question_text": str(question_text),
                        "code": str(code),
                        "specific_instructions": str(instructions).strip() if instructions else None,
                    }
                ]
        return data


def _clean_score(val: Any) -> float:
    if val is None:
        return 0.0
    if isinstance(val, (int, float)):
        score = float(val)
        if 10.0 < score <= 100.0:
            score = score / 10.0
        return max(0.0, min(10.0, score))
    val_str = str(val).strip()
    match = re.search(r"(\d+(?:\.\d+)?)", val_str)
    if match:
        try:
            score = float(match.group(1))
            if "/100" in val_str or (10.0 < score <= 100.0):
                score = score / 10.0
            return max(0.0, min(10.0, score))
        except (ValueError, TypeError):
            pass
    return 0.0


class ScoreBreakdown(BaseModel):
    completeness_score: float = Field(0.0, ge=0.0, le=10.0)
    code_quality_score: float = Field(0.0, ge=0.0, le=10.0)
    approach_taken_score: float = Field(0.0, ge=0.0, le=10.0)
    overall_score: float = Field(0.0, ge=0.0, le=10.0)

    @model_validator(mode="before")
    @classmethod
    def normalize_scores(cls, data: Any) -> Any:
        if isinstance(data, dict):
            comp = _clean_score(data.get("completeness_score", 0.0))
            qual = _clean_score(data.get("code_quality_score", 0.0))
            appr = _clean_score(data.get("approach_taken_score", 0.0))
            overall = data.get("overall_score")
            if overall is None or overall == "" or str(overall).strip().lower() == "none":
                overall = round((0.5 * comp) + (0.3 * qual) + (0.2 * appr), 2)
            else:
                overall = _clean_score(overall)
            return {
                "completeness_score": comp,
                "code_quality_score": qual,
                "approach_taken_score": appr,
                "overall_score": overall,
            }
        return data


class IndividualReview(BaseModel):
    question_text: str = ""
    correctness_feedback: str = ""
    scores: ScoreBreakdown = Field(default_factory=ScoreBreakdown)

    @model_validator(mode="before")
    @classmethod
    def normalize_review(cls, data: Any) -> Any:
        if isinstance(data, dict):
            q_text = str(data.get("question_text") or data.get("question") or "")
            feedback = str(data.get("correctness_feedback") or data.get("feedback") or "")
            scores = data.get("scores")
            if not isinstance(scores, dict):
                scores = {}
            return {
                "question_text": q_text,
                "correctness_feedback": feedback,
                "scores": scores,
            }
        return data


class SummaryReview(BaseModel):
    overall_average_score: float = 0.0
    overall_quality_label: str = "Critical"
    executive_feedback: Optional[str] = ""
    common_errors: str = ""
    strengths: str = ""
    weaknesses: str = ""
    recommendations: str = ""

    @model_validator(mode="before")
    @classmethod
    def normalize_summary(cls, data: Any) -> Any:
        if isinstance(data, dict):
            score = _clean_score(data.get("overall_average_score", 0.0))
            label = str(data.get("overall_quality_label") or "")
            if not label:
                if score >= 9.0:
                    label = "Excellent"
                elif score >= 7.5:
                    label = "Good"
                elif score >= 6.0:
                    label = "Average"
                elif score >= 4.0:
                    label = "Poor"
                else:
                    label = "Critical"

            return {
                "overall_average_score": score,
                "overall_quality_label": label,
                "executive_feedback": str(data.get("executive_feedback") or ""),
                "common_errors": str(data.get("common_errors") or data.get("common_mistakes") or data.get("mistakes") or ""),
                "strengths": str(data.get("strengths") or ""),
                "weaknesses": str(data.get("weaknesses") or ""),
                "recommendations": str(data.get("recommendations") or ""),
            }
        return data


class ExecutionMetrics(BaseModel):
    request_duration_seconds: float = 0.0
    lang_detection_duration_seconds: float = 0.0
    code_eval_duration_seconds: float = 0.0
    total_requests_processed: int = 0
    running_average_duration_seconds: float = 0.0


class PromptDrivenCodeReviewResponse(BaseModel):
    individual_reviews: List[IndividualReview] = Field(default_factory=list)
    summary_review: Optional[Union[SummaryReview, str]] = None
    execution_metrics: Optional[ExecutionMetrics] = None

    @model_validator(mode="before")
    @classmethod
    def normalize_response(cls, data: Any) -> Any:
        if isinstance(data, dict):
            reviews = data.get("individual_reviews")
            if isinstance(reviews, dict):
                reviews = list(reviews.values())
            elif not isinstance(reviews, list):
                reviews = []
            data["individual_reviews"] = reviews
        return data