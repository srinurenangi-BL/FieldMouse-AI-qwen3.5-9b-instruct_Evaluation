from __future__ import annotations

from typing import Any, List, Optional, Union
from pydantic import BaseModel, Field, model_validator


# ──── Request Schemas ───────────────────────────────────────────────────

class CodeSubmission(BaseModel):
    question_text: str = Field(
        ...,
        description="The problem statement or question text for this submission",
        example="In an online ticket system..."
    )
    code: str = Field(
        ...,
        description="The student's submitted source code to be reviewed",
        example="import java.util.*;..."
    )
    specific_instructions: Optional[str] = Field(
        None,
        description="Optional extra constraints or instructions for this question"
    )


class CodeReviewRequest(BaseModel):
    language: str = Field(
        "Java",
        description="Programming language of the submitted code (e.g., Java, Python, C++, JavaScript)",
        example="Java"
    )
    submissions: List[CodeSubmission] = Field(
        default_factory=list,
        description="List of one or more question+code submissions to evaluate"
    )

    @model_validator(mode="before")
    @classmethod
    def normalize_submission_payload(cls, data: Any) -> Any:
        if isinstance(data, dict):
            # Normalize flat payload containing 'problem' or 'question_text' and 'code'
            if not data.get("submissions"):
                question_text = data.get("question_text") or data.get("problem")
                code = data.get("code")
                if question_text and code:
                    data = dict(data)
                    data["submissions"] = [
                        {
                            "question_text": str(question_text),
                            "code": str(code),
                            "specific_instructions": data.get("specific_instructions")
                        }
                    ]
        return data


# ──── Response Schemas ──────────────────────────────────────────────────

class ScoreBreakdown(BaseModel):
    completeness_score: float = Field(0.0, ge=0.0, le=10.0)
    code_quality_score: float = Field(0.0, ge=0.0, le=10.0)
    approach_taken_score: float = Field(0.0, ge=0.0, le=10.0)
    overall_score: float = Field(0.0, ge=0.0, le=10.0)


class IndividualReview(BaseModel):
    question_text: str = ""
    correctness_feedback: str = ""
    common_errors: str = "None"
    strengths: str = "None"
    weaknesses: str = "None"
    recommendations: str = "None"
    scores: ScoreBreakdown = Field(default_factory=ScoreBreakdown)
    corrected_code: Optional[str] = None


class SummaryReview(BaseModel):
    overall_average_score: float = 0.0
    overall_quality_label: str = "Critical"
    common_errors: str = ""
    strengths: str = ""
    weaknesses: str = ""
    recommendations: str = ""


class PromptDrivenCodeReviewResponse(BaseModel):
    individual_reviews: List[IndividualReview] = Field(default_factory=list)
    summary_review: Optional[Union[SummaryReview, str]] = None
