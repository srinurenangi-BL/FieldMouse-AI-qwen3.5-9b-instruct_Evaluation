from __future__ import annotations

import json
import re
from typing import Any, Dict


class JSONValidationError(Exception):
    """Raised when LLM response output cannot be parsed or validated against required schema."""
    pass


def parse_and_validate_llm_json(raw_text: str) -> Dict[str, Any]:
    """Parses raw text returned by LLM into JSON dict.
    
    If parsing fails, strips markdown codeblocks or substring before '{' and after '}',
    and retries parsing once. Defensively clamps numerical scores to [0.0, 10.0].
    """
    text = raw_text.strip()
    parsed_data: Dict[str, Any] | None = None

    # First attempt: Direct JSON parsing
    try:
        parsed_data = json.loads(text, strict=False)
    except Exception:
        parsed_data = None

    # Second attempt: Substring extraction between first '{' and last '}'
    if parsed_data is None:
        if "```" in text:
            match = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", text)
            if match:
                text = match.group(1).strip()
            else:
                text = text.replace("```", "").strip()

        start = text.find("{")
        end = text.rfind("}")
        if start != -1 and end > start:
            clean_text = text[start:end + 1]
            clean_text = re.sub(r",\s*}", "}", clean_text)
            try:
                parsed_data = json.loads(clean_text, strict=False)
            except Exception:
                parsed_data = None

    if not isinstance(parsed_data, dict):
        raise JSONValidationError("Failed to parse LLM response as a valid JSON object.")

    # Defensive score clamping (arithmetic bounds enforcement)
    ind_reviews = parsed_data.get("individual_reviews")
    if isinstance(ind_reviews, list):
        for review in ind_reviews:
            if isinstance(review, dict):
                scores = review.get("scores")
                if isinstance(scores, dict):
                    for key in ["completeness_score", "code_quality_score", "approach_taken_score", "overall_score"]:
                        if key in scores:
                            try:
                                val = float(scores[key])
                                scores[key] = round(max(0.0, min(10.0, val)), 1)
                            except (ValueError, TypeError):
                                scores[key] = 0.0

    return parsed_data
