import ollama
import os
import json
import asyncio
import logging
import time
from pathlib import Path
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse, FileResponse

from schemas import (
    CodeReviewRequest,
    PromptDrivenCodeReviewResponse,
    IndividualReview,
    SummaryReview,
    ScoreBreakdown,
    ExecutionMetrics
)
from prompts import format_submissions, build_language_detection_prompt, build_evaluation_prompt

load_dotenv()

OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "qwen2.5-coder:7b-instruct")
LLM_TEMPERATURE = float(os.getenv("LLM_TEMPERATURE", "0.1"))
LLM_TIMEOUT_SECONDS = float(os.getenv("LLM_TIMEOUT_SECONDS", "300"))
DEFAULT_TARGET_LANGUAGE = os.getenv("DEFAULT_TARGET_LANGUAGE", "Java")
TEMPLATES_DIR = Path(__file__).resolve().parent / "templates"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("app.log", mode="a", encoding="utf-8")
    ]
)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="QWEN Code Evaluator",
    description="LLM-powered code review and scoring API",
)

ollama_client = ollama.AsyncClient()

METRICS_STATS = {
    "total_requests": 0,
    "total_duration": 0.0
}
metrics_lock = asyncio.Lock()


async def record_metrics(req_duration: float):
    async with metrics_lock:
        METRICS_STATS["total_requests"] += 1
        METRICS_STATS["total_duration"] += req_duration
        avg = METRICS_STATS["total_duration"] / METRICS_STATS["total_requests"]
        return METRICS_STATS["total_requests"], round(avg, 2)


class LLMClientError(Exception):
    pass


async def send_prompt(prompt_text: str = "", json_mode: bool = False) -> str:
    options = {"temperature": LLM_TEMPERATURE}
    kwargs = {
        "model": OLLAMA_MODEL,
        "messages": [
            {"role": "system", "content": "You are a fair, precise code evaluator. Return strictly what was requested."},
            {"role": "user", "content": prompt_text},
        ],
        "options": options,
        "keep_alive": "5m",
    }

    if json_mode:
        kwargs["format"] = "json"

    max_attempts = 2
    for attempt in range(1, max_attempts + 1):
        try:
            response = await asyncio.wait_for(
                ollama_client.chat(**kwargs),
                timeout=LLM_TIMEOUT_SECONDS
            )
            content = response["message"]["content"]
            if content:
                return content.strip()
            raise LLMClientError("LLM returned empty content.")
        except LLMClientError:
            raise
        except asyncio.TimeoutError:
            logger.error(f"[TIMEOUT] LLM call timed out after {LLM_TIMEOUT_SECONDS}s (attempt {attempt}/{max_attempts})")
            if attempt < max_attempts:
                await asyncio.sleep(1.0)
                continue
            raise LLMClientError(f"Request timed out after {LLM_TIMEOUT_SECONDS} seconds.")
        except Exception as e:
            if attempt < max_attempts:
                await asyncio.sleep(1.0)
                continue
            raise LLMClientError(f"Failed after {max_attempts} attempts: {e}")
    raise LLMClientError("LLM call failed after all attempts.")


@app.get("/", response_class=HTMLResponse)
async def home():
    return FileResponse(TEMPLATES_DIR / "index.html", media_type="text/html")


@app.get("/api/metrics")
async def get_metrics():
    avg = (METRICS_STATS["total_duration"] / METRICS_STATS["total_requests"]) if METRICS_STATS["total_requests"] > 0 else 0.0
    return {
        "total_requests_processed": METRICS_STATS["total_requests"],
        "running_average_duration_seconds": round(avg, 2)
    }


@app.post("/review", response_model=PromptDrivenCodeReviewResponse)
async def review_code(request: CodeReviewRequest):
    req_start_time = time.perf_counter()
    logger.info("=== [PROCESS STARTED] Code Evaluation Request Received ===")

    if not request.submissions:
        logger.error("[REJECTED] No code submissions provided in request payload.")
        raise HTTPException(status_code=400, detail="No submissions provided.")

    logger.info(f"[INPUT RECEIVED] Target Language: {request.target_language} | Total Submissions: {len(request.submissions)}")

    logger.info("[STEP 1/5] Initiating Language Detection check...")
    first_code = request.submissions[0].code
    lang_prompt = build_language_detection_prompt(request.target_language, first_code)

    lang_start = time.perf_counter()
    logger.info(f"[LLM INPUT SENT] Sending Language Detection prompt to model '{OLLAMA_MODEL}'...")
    detected_lang = None
    is_mismatch = False
    lang_duration = 0.0

    try:
        lang_raw = await send_prompt(lang_prompt, json_mode=True)
        lang_duration = time.perf_counter() - lang_start
        logger.info(f"[LLM RESPONSE RECEIVED] Language Detection completed by LLM in {lang_duration:.2f} seconds.")

        lang_result = json.loads(lang_raw)
        raw_match = lang_result.get("match", True)
        detected_lang = str(lang_result.get("detected_language", "unknown")).strip()

        target_clean = request.target_language.strip().lower()
        detected_clean = detected_lang.lower()

        if detected_clean == target_clean:
            is_mismatch = False
        elif raw_match is False or str(raw_match).lower() == "false":
            is_mismatch = True
        elif raw_match is True or str(raw_match).lower() == "true":
            is_mismatch = False
        else:
            is_mismatch = (detected_clean != target_clean)

        if is_mismatch:
            logger.warning(f"[LANGUAGE MISMATCH] Expected '{request.target_language}', but detected '{detected_lang}'. Assigning 0.0 scores and returning explanation.")
        else:
            logger.info(f"[SUCCESS] Language check passed. Submitted code matches expected target language '{request.target_language}'.")
    except Exception as e:
        logger.warning(f"[WARNING] Language detection skipped due to error: {e}")

    if is_mismatch and detected_lang:
        mismatch_msg = f"⚠️ Language Mismatch: Submitted code was detected as {detected_lang}, but expected {request.target_language}."

        reviews = []
        for sub in request.submissions:
            reviews.append(
                IndividualReview(
                    question_text=sub.question_text,
                    correctness_feedback=f"{mismatch_msg} Evaluation skipped and 0.0 score assigned.",
                    scores=ScoreBreakdown(
                        completeness_score=0.0,
                        code_quality_score=0.0,
                        approach_taken_score=0.0,
                        overall_score=0.0
                    )
                )
            )

        summary = SummaryReview(
            overall_average_score=0.0,
            overall_quality_label="Critical",
            common_errors=f"{mismatch_msg}",
            strengths="None",
            weaknesses=f"Submitted code is written in {detected_lang} instead of requested {request.target_language}.",
            recommendations=f"Please rewrite and submit your solution in {request.target_language}."
        )

        total_duration = time.perf_counter() - req_start_time
        total_reqs, running_avg = await record_metrics(total_duration)

        metrics = ExecutionMetrics(
            request_duration_seconds=round(total_duration, 2),
            lang_detection_duration_seconds=round(lang_duration, 2),
            code_eval_duration_seconds=0.0,
            total_requests_processed=total_reqs,
            running_average_duration_seconds=running_avg
        )

        logger.info(f"=== [PROCESS COMPLETED - LANGUAGE MISMATCH ZERO SCORE] Total Request Time: {total_duration:.2f}s (Language Detection: {lang_duration:.2f}s) | Total Requests Processed: {total_reqs} | Running Average Response Time: {running_avg:.2f}s ===")

        return PromptDrivenCodeReviewResponse(
            individual_reviews=reviews,
            summary_review=summary,
            execution_metrics=metrics
        )

    logger.info("[STEP 2/5] Formatting code submissions...")
    formatted = format_submissions(request.submissions)

    logger.info("[STEP 3/5] Building evaluation prompt...")
    eval_prompt = build_evaluation_prompt(
        target_language=request.target_language,
        ques_ans_content_with_inst=formatted,
        summary_gen_flag=True,
    )

    logger.info(f"[STEP 4/5] Sending main evaluation prompt ({len(eval_prompt)} characters) to LLM model '{OLLAMA_MODEL}'...")
    eval_start = time.perf_counter()
    try:
        raw_response = await send_prompt(eval_prompt, json_mode=True)
        eval_duration = time.perf_counter() - eval_start
        logger.info(f"[LLM RESPONSE RECEIVED] Code Evaluation completed by LLM in {eval_duration:.2f} seconds.")
    except LLMClientError as e:
        logger.error(f"[ERROR] LLM evaluation call failed after {time.perf_counter() - eval_start:.2f}s: {e}")
        raise HTTPException(status_code=502, detail=f"LLM error: {e}")

    logger.info("[STEP 5/5] Parsing LLM response into structured output...")
    try:
        result = json.loads(raw_response)
    except json.JSONDecodeError as e:
        logger.error(f"[ERROR] Failed to parse JSON response from LLM: {e}")
        raise HTTPException(status_code=502, detail=f"LLM returned invalid JSON: {e}")

    total_duration = time.perf_counter() - req_start_time
    total_llm_time = lang_duration + eval_duration
    total_reqs, running_avg = await record_metrics(total_duration)

    metrics = ExecutionMetrics(
        request_duration_seconds=round(total_duration, 2),
        lang_detection_duration_seconds=round(lang_duration, 2),
        code_eval_duration_seconds=round(eval_duration, 2),
        total_requests_processed=total_reqs,
        running_average_duration_seconds=running_avg
    )

    logger.info(f"=== [PROCESS COMPLETED] Total Request Time: {total_duration:.2f}s | Total LLM Time: {total_llm_time:.2f}s (Language Detection: {lang_duration:.2f}s, Code Evaluation: {eval_duration:.2f}s) | Total Requests Processed: {total_reqs} | Running Average Response Time: {running_avg:.2f}s ===")

    result["execution_metrics"] = metrics.model_dump()
    return PromptDrivenCodeReviewResponse(**result)
