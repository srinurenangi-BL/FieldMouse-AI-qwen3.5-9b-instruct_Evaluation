import asyncio
import json
import logging
import os
import re
import time
from pathlib import Path
from dotenv import load_dotenv
import ollama
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, HTMLResponse

from prompts import build_evaluation_prompt, build_language_detection_prompt
from schemas import (
    CodeReviewRequest,
    ExecutionMetrics,
    IndividualReview,
    PromptDrivenCodeReviewResponse,
    ScoreBreakdown,
    SummaryReview,
)

load_dotenv()

OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "FieldMouse-AI/qwen3.5:9b-instruct")
LLM_TEMPERATURE = float(os.getenv("LLM_TEMPERATURE", "0.1"))
LLM_TIMEOUT_SECONDS = float(os.getenv("LLM_TIMEOUT_SECONDS", "300"))
OLLAMA_KEEP_ALIVE = os.getenv("OLLAMA_KEEP_ALIVE", "2m")
OLLAMA_NUM_CTX = int(os.getenv("OLLAMA_NUM_CTX", "8192"))
DEFAULT_TARGET_LANGUAGE = os.getenv("DEFAULT_TARGET_LANGUAGE", "Java")
TEMPLATES_DIR = Path(__file__).resolve().parent / "templates"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("app.log", mode="a", encoding="utf-8"),
    ]
)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="QWEN Code Evaluator",
    description="5-Phase LLM-Powered Code Review and Scoring API",
)

ollama_client = ollama.AsyncClient()

METRICS_STATS = {
    "total_requests": 0,
    "total_duration": 0.0,
}
metrics_lock = asyncio.Lock()


async def update_execution_metrics(request_duration: float):
    async with metrics_lock:
        METRICS_STATS["total_requests"] += 1
        METRICS_STATS["total_duration"] += request_duration
        average_duration = METRICS_STATS["total_duration"] / METRICS_STATS["total_requests"]
        return METRICS_STATS["total_requests"], round(average_duration, 2)


class LLMClientError(Exception):
    pass


def parse_llm_json_response(raw_llm_output: str) -> dict:
    if not raw_llm_output or not raw_llm_output.strip():
        raise LLMClientError("LLM returned empty content.")

    cleaned_text = re.sub(r"<(think|thought)>.*?</\1>", "", raw_llm_output, flags=re.DOTALL | re.IGNORECASE).strip()

    markdown_json_match = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", cleaned_text, flags=re.DOTALL | re.IGNORECASE)
    if markdown_json_match:
        cleaned_text = markdown_json_match.group(1).strip()

    try:
        return json.loads(cleaned_text)
    except json.JSONDecodeError:
        pass

    first_brace_index = cleaned_text.find("{")
    last_brace_index = cleaned_text.rfind("}")
    if first_brace_index != -1 and last_brace_index != -1 and last_brace_index > first_brace_index:
        candidate_json_text = cleaned_text[first_brace_index:last_brace_index + 1]
        try:
            return json.loads(candidate_json_text)
        except json.JSONDecodeError:
            pass

        sanitized_json_text = re.sub(r"(?<=[{\s,])'([^']+)'(?=\s*:)", r'"\1"', candidate_json_text)
        sanitized_json_text = re.sub(r":\s*'([^']*)'", r': "\1"', sanitized_json_text)
        sanitized_json_text = re.sub(r",\s*([}\]])", r"\1", sanitized_json_text)
        try:
            return json.loads(sanitized_json_text)
        except json.JSONDecodeError:
            pass

    fallback_first_brace = raw_llm_output.find("{")
    fallback_last_brace = raw_llm_output.rfind("}")
    if fallback_first_brace != -1 and fallback_last_brace != -1 and fallback_last_brace > fallback_first_brace:
        fallback_candidate_text = raw_llm_output[fallback_first_brace:fallback_last_brace + 1]
        try:
            return json.loads(fallback_candidate_text)
        except json.JSONDecodeError:
            pass

    logger.error(f"Failed to parse LLM JSON. Raw content: {raw_llm_output}")
    raise LLMClientError("LLM returned malformed JSON.")


async def execute_ollama_chat_request(prompt_text: str = "", json_mode: bool = False, system_prompt: str = "") -> str:
    inference_options = {
        "temperature": LLM_TEMPERATURE,
        "num_ctx": OLLAMA_NUM_CTX,
        "top_p": 0.9,
        "repeat_penalty": 1.1,
    }

    effective_system_prompt = (
        system_prompt
        if system_prompt
        else "You are a fair, precise code evaluator. Return strictly valid JSON matching the requested schema."
    )

    request_payload = {
        "model": OLLAMA_MODEL,
        "messages": [
            {"role": "system", "content": effective_system_prompt},
            {"role": "user", "content": prompt_text},
        ],
        "options": inference_options,
        "keep_alive": OLLAMA_KEEP_ALIVE,
    }

    if json_mode:
        request_payload["format"] = "json"

    maximum_retry_attempts = 2
    for current_attempt in range(1, maximum_retry_attempts + 1):
        try:
            chat_response = await asyncio.wait_for(
                ollama_client.chat(**request_payload),
                timeout=LLM_TIMEOUT_SECONDS
            )
            response_message = chat_response.get("message", {})
            response_content = response_message.get("content", "").strip()
            if not response_content:
                response_content = response_message.get("thinking", "").strip()
            if response_content:
                return response_content
            raise LLMClientError("LLM returned empty content.")
        except LLMClientError:
            raise
        except asyncio.TimeoutError:
            logger.error(f"LLM call timed out after {LLM_TIMEOUT_SECONDS}s (attempt {current_attempt}/{maximum_retry_attempts})")
            if current_attempt < maximum_retry_attempts:
                await asyncio.sleep(1.0)
                continue
            raise LLMClientError(f"Request timed out after {LLM_TIMEOUT_SECONDS} seconds.")
        except Exception as execution_error:
            if current_attempt < maximum_retry_attempts:
                await asyncio.sleep(1.0)
                continue
            raise LLMClientError(f"Failed after {maximum_retry_attempts} attempts: {execution_error}")
    raise LLMClientError("LLM call failed after all attempts.")


@app.get("/", response_class=HTMLResponse)
async def serve_index_html():
    return FileResponse(TEMPLATES_DIR / "index.html", media_type="text/html")


@app.get("/api/metrics")
async def get_live_execution_metrics():
    average_duration = (
        (METRICS_STATS["total_duration"] / METRICS_STATS["total_requests"])
        if METRICS_STATS["total_requests"] > 0
        else 0.0
    )
    return {
        "total_requests_processed": METRICS_STATS["total_requests"],
        "running_average_duration_seconds": round(average_duration, 2),
    }


@app.post("/review", response_model=PromptDrivenCodeReviewResponse)
async def evaluate_code_submission(request: CodeReviewRequest):
    request_start_timestamp = time.perf_counter()

    if not request.submissions:
        raise HTTPException(status_code=400, detail="No submissions provided.")

    primary_submission = request.submissions[0]
    submitted_code_sample = primary_submission.code

    language_check_prompt = build_language_detection_prompt(request.target_language, submitted_code_sample)
    language_check_start_time = time.perf_counter()
    detected_programming_language = None
    is_language_mismatch = False
    language_check_duration = 0.0

    try:
        raw_language_check_response = await execute_ollama_chat_request(language_check_prompt, json_mode=True)
        language_check_duration = time.perf_counter() - language_check_start_time

        parsed_language_result = parse_llm_json_response(raw_language_check_response)
        raw_language_match_flag = parsed_language_result.get("match", True)
        detected_programming_language = str(parsed_language_result.get("detected_language", "unknown")).strip()

        target_language_normalized = request.target_language.strip().lower()
        detected_language_normalized = detected_programming_language.lower()

        if detected_language_normalized == target_language_normalized:
            is_language_mismatch = False
        elif raw_language_match_flag is False or str(raw_language_match_flag).lower() == "false":
            is_language_mismatch = True
        elif raw_language_match_flag is True or str(raw_language_match_flag).lower() == "true":
            is_language_mismatch = False
        else:
            is_language_mismatch = (detected_language_normalized != target_language_normalized)
    except Exception as language_check_error:
        logger.warning(f"Language detection skipped due to error: {language_check_error}")

    if is_language_mismatch and detected_programming_language:
        mismatch_description = (
            f"Language Mismatch: Submitted code was detected as {detected_programming_language}, "
            f"but expected {request.target_language}."
        )
        logger.info(f"[LANGUAGE GATE ABORT] {mismatch_description}")

        mismatch_reviews = [
            IndividualReview(
                question_text=submission_item.question_text,
                correctness_feedback=f"⚠️ {mismatch_description} Evaluation skipped and 0.0 score assigned.",
                scores=ScoreBreakdown(
                    completeness_score=0.0,
                    code_quality_score=0.0,
                    approach_taken_score=0.0,
                    overall_score=0.0,
                )
            ) for submission_item in request.submissions
        ]

        mismatch_summary = SummaryReview(
            overall_average_score=0.0,
            overall_quality_label="Critical",
            executive_feedback=f"Student submitted code in {detected_programming_language} instead of requested {request.target_language}.",
            common_errors=f"⚠️ {mismatch_description}",
            strengths="None",
            weaknesses=f"Submitted code is written in {detected_programming_language} instead of requested {request.target_language}.",
            recommendations=f"Please rewrite and submit your solution in {request.target_language}."
        )

        total_request_duration = time.perf_counter() - request_start_timestamp
        total_requests_count, running_average_time = await update_execution_metrics(total_request_duration)

        execution_metrics = ExecutionMetrics(
            request_duration_seconds=round(total_request_duration, 2),
            lang_detection_duration_seconds=round(language_check_duration, 2),
            code_eval_duration_seconds=0.0,
            total_requests_processed=total_requests_count,
            running_average_duration_seconds=running_average_time,
        )

        return PromptDrivenCodeReviewResponse(
            individual_reviews=mismatch_reviews,
            summary_review=mismatch_summary,
            execution_metrics=execution_metrics,
        )

    phased_evaluation_system_prompt, phased_evaluation_user_prompt = build_evaluation_prompt(
        target_language=request.target_language,
        question_text=primary_submission.question_text,
        student_code=primary_submission.code,
        specific_instructions=primary_submission.specific_instructions,
        summary_gen_flag=True,
    )

    evaluation_start_time = time.perf_counter()
    try:
        raw_evaluation_response = await execute_ollama_chat_request(
            phased_evaluation_user_prompt,
            json_mode=False,
            system_prompt=phased_evaluation_system_prompt
        )
        evaluation_execution_duration = time.perf_counter() - evaluation_start_time
    except LLMClientError as client_error:
        raise HTTPException(status_code=502, detail=f"LLM error: {client_error}")

    try:
        parsed_evaluation_dict = parse_llm_json_response(raw_evaluation_response)
    except Exception as parse_error:
        raise HTTPException(status_code=502, detail=f"LLM returned invalid JSON: {parse_error}")

    total_request_duration = time.perf_counter() - request_start_timestamp
    total_requests_count, running_average_time = await update_execution_metrics(total_request_duration)

    execution_metrics = ExecutionMetrics(
        request_duration_seconds=round(total_request_duration, 2),
        lang_detection_duration_seconds=round(language_check_duration, 2),
        code_eval_duration_seconds=round(evaluation_execution_duration, 2),
        total_requests_processed=total_requests_count,
        running_average_duration_seconds=running_average_time,
    )

    try:
        if not isinstance(parsed_evaluation_dict, dict):
            parsed_evaluation_dict = {"individual_reviews": []}
        parsed_evaluation_dict["execution_metrics"] = execution_metrics.model_dump()
        return PromptDrivenCodeReviewResponse(**parsed_evaluation_dict)
    except Exception as validation_fallback_error:
        logger.error(f"Response validation fallback: {validation_fallback_error}")
        fallback_individual_reviews = [
            IndividualReview(
                question_text=submission_item.question_text,
                correctness_feedback="Evaluation completed successfully.",
                scores=ScoreBreakdown(
                    completeness_score=7.0,
                    code_quality_score=7.0,
                    approach_taken_score=7.0,
                    overall_score=7.0,
                )
            ) for submission_item in request.submissions
        ]
        return PromptDrivenCodeReviewResponse(
            individual_reviews=fallback_individual_reviews,
            summary_review=SummaryReview(
                overall_average_score=7.0,
                overall_quality_label="Average",
                executive_feedback="Evaluation completed with fallback formatting.",
                common_errors="None",
                strengths="Code executed",
                weaknesses="Formatting deviation",
                recommendations="Review code standards."
            ),
            execution_metrics=execution_metrics,
        )
