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
    specific_instructions: Optional[str] = Field(None, description="Optional extra constraints or approach guidelines")


class CodeReviewRequest(BaseModel):
    target_language: str = Field(default=DEFAULT_TARGET_LANGUAGE, description="Target programming language")
    submissions: List[CodeSubmission] = Field(default_factory=list, description="List of submissions to evaluate")

    @model_validator(mode="before")
    @classmethod
    def normalize_flat_payload(cls, data: Any) -> Any:
        if isinstance(data, dict) and not data.get("submissions"):
            question_text = data.get("question_text") or data.get("problem")
            submitted_code = data.get("code")
            optional_constraints = data.get("specific_instructions") or data.get("instructions") or data.get("constraints")
            if question_text and submitted_code:
                data = dict(data)
                data["submissions"] = [
                    {
                        "question_text": str(question_text),
                        "code": str(submitted_code),
                        "specific_instructions": str(optional_constraints).strip() if optional_constraints else None,
                    }
                ]
        return data


def sanitize_numerical_score(raw_score_value: Any) -> float:
    if raw_score_value is None:
        return 0.0
    if isinstance(raw_score_value, (int, float)):
        numeric_score = float(raw_score_value)
        if 10.0 < numeric_score <= 100.0:
            numeric_score = numeric_score / 10.0
        return max(0.0, min(10.0, numeric_score))

    score_text = str(raw_score_value).strip()
    regex_match = re.search(r"(\d+(?:\.\d+)?)", score_text)
    if regex_match:
        try:
            parsed_score = float(regex_match.group(1))
            if "/100" in score_text or (10.0 < parsed_score <= 100.0):
                parsed_score = parsed_score / 10.0
            return max(0.0, min(10.0, parsed_score))
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
            completeness = sanitize_numerical_score(data.get("completeness_score", 0.0))
            code_quality = sanitize_numerical_score(data.get("code_quality_score", 0.0))
            approach_taken = sanitize_numerical_score(data.get("approach_taken_score", 0.0))
            overall = data.get("overall_score")
            if overall is None or overall == "" or str(overall).strip().lower() == "none":
                overall = round((0.5 * completeness) + (0.3 * code_quality) + (0.2 * approach_taken), 2)
            else:
                overall = sanitize_numerical_score(overall)
            return {
                "completeness_score": completeness,
                "code_quality_score": code_quality,
                "approach_taken_score": approach_taken,
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
            question_text = str(data.get("question_text") or data.get("question") or "")
            feedback_text = str(data.get("correctness_feedback") or data.get("feedback") or "")
            scores_dict = data.get("scores")
            if not isinstance(scores_dict, dict):
                scores_dict = {}
            return {
                "question_text": question_text,
                "correctness_feedback": feedback_text,
                "scores": scores_dict,
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
            average_score = sanitize_numerical_score(data.get("overall_average_score", 0.0))
            quality_label = str(data.get("overall_quality_label") or "").strip()
            if not quality_label:
                if average_score >= 9.0:
                    quality_label = "Excellent"
                elif average_score >= 7.5:
                    quality_label = "Good"
                elif average_score >= 6.0:
                    quality_label = "Average"
                elif average_score >= 4.0:
                    quality_label = "Poor"
                else:
                    quality_label = "Critical"

            return {
                "overall_average_score": average_score,
                "overall_quality_label": quality_label,
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
            reviews_list = data.get("individual_reviews")
            if isinstance(reviews_list, dict):
                reviews_list = list(reviews_list.values())
            elif not isinstance(reviews_list, list):
                reviews_list = []
            data["individual_reviews"] = reviews_list
        return data