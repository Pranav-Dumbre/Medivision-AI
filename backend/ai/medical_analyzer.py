"""
AI Medical Analyzer — LLM-based report analysis via Ollama.

Uses MedGemma or BioMistral (via Ollama local API) to analyze
extracted OCR text and produce structured medical analysis.
"""
from __future__ import annotations

import json
import logging
import re
from typing import Optional

import requests

from backend.models.schemas import (
    AnalysisResult,
    ParameterResult,
    ParameterStatus,
    PatientInfo,
    RiskLevel,
)
from backend.ai.reference_ranges import find_reference

logger = logging.getLogger(__name__)

# Ollama API configuration
OLLAMA_BASE_URL = "http://localhost:11434"
DEFAULT_MODEL = "medgemma"
FALLBACK_MODELS = ["biomistral", "mistral", "llama3.2", "gemma2"]
REQUEST_TIMEOUT = 300  # 5 minutes for large reports


SYSTEM_PROMPT = """You are a medical laboratory report analyzer. Your task is to analyze medical lab reports and extract structured information.

IMPORTANT RULES:
1. You are NOT providing a medical diagnosis. You are explaining lab values in simple language.
2. Always include that this is for informational purposes only.
3. Never prescribe medications.
4. Only provide general health recommendations.

Analyze the following medical report text and return a JSON object with EXACTLY this structure:

{
  "patient_info": {
    "name": "patient name or Not Available",
    "age": "age or Not Available",
    "gender": "gender or Not Available",
    "report_date": "date or Not Available",
    "lab_name": "laboratory name or Not Available",
    "ref_number": "reference number or Not Available"
  },
  "parameters": [
    {
      "test_name": "Name of the test",
      "patient_value": "The value from the report",
      "unit": "unit of measurement",
      "normal_range": "normal reference range",
      "status": "Normal OR Low OR High OR Critical Low OR Critical High",
      "explanation": "Simple explanation of what this value means for the patient's health in 2-3 sentences",
      "possible_causes": ["cause1", "cause2"],
      "health_implications": ["implication1", "implication2"]
    }
  ],
  "summary": "A comprehensive but simple-language summary of the overall report in 3-5 sentences. Mention which values are normal and which are abnormal. Explain what the abnormalities might indicate.",
  "risk_level": "Low Risk OR Moderate Risk OR High Risk OR Unknown",
  "key_findings": ["finding1", "finding2", "finding3"],
  "recommendations": ["recommendation1", "recommendation2", "recommendation3"]
}

Return ONLY valid JSON. No markdown, no code fences, no extra text."""


def check_ollama_available() -> tuple[bool, str]:
    """
    Check if Ollama is running and a suitable model is available.

    Returns:
        (available: bool, model_name: str)
    """
    try:
        resp = requests.get(f"{OLLAMA_BASE_URL}/api/tags", timeout=5)
        if resp.status_code != 200:
            return False, ""

        models = resp.json().get("models", [])
        model_names = [m["name"].split(":")[0] for m in models]

        # Check preferred models in order
        for preferred in [DEFAULT_MODEL] + FALLBACK_MODELS:
            if preferred in model_names:
                logger.info(f"Ollama model found: {preferred}")
                return True, preferred

        if model_names:
            logger.warning(
                f"No medical model found. Available: {model_names}. "
                f"Using first available: {model_names[0]}"
            )
            return True, model_names[0].split(":")[0]

        return False, ""
    except requests.ConnectionError:
        logger.warning("Ollama is not running at localhost:11434")
        return False, ""
    except Exception as e:
        logger.warning(f"Ollama check failed: {e}")
        return False, ""


def _call_ollama(prompt: str, model: str) -> str:
    """Send a prompt to Ollama and return the response text."""
    payload = {
        "model": model,
        "prompt": prompt,
        "system": SYSTEM_PROMPT,
        "stream": False,
        "options": {
            "temperature": 0.1,
            "top_p": 0.9,
            "num_predict": 4096,
        },
    }

    resp = requests.post(
        f"{OLLAMA_BASE_URL}/api/generate",
        json=payload,
        timeout=REQUEST_TIMEOUT,
    )
    resp.raise_for_status()
    return resp.json().get("response", "")


def _extract_json(text: str) -> dict:
    """Extract JSON from LLM response, handling markdown fences."""
    # Try direct parse first
    text = text.strip()

    # Remove markdown code fences if present
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*\n?", "", text)
        text = re.sub(r"\n?```\s*$", "", text)

    # Try to find JSON object in the text
    json_match = re.search(r"\{[\s\S]*\}", text)
    if json_match:
        try:
            return json.loads(json_match.group())
        except json.JSONDecodeError:
            pass

    # Last resort: try the whole text
    try:
        return json.loads(text)
    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse LLM JSON response: {e}")
        logger.debug(f"Raw response: {text[:500]}")
        return {}


def _parse_status(status_str: str) -> ParameterStatus:
    """Convert status string to ParameterStatus enum."""
    s = status_str.strip().lower()
    mapping = {
        "normal": ParameterStatus.NORMAL,
        "low": ParameterStatus.LOW,
        "high": ParameterStatus.HIGH,
        "critical low": ParameterStatus.CRITICAL_LOW,
        "critical high": ParameterStatus.CRITICAL_HIGH,
    }
    return mapping.get(s, ParameterStatus.UNKNOWN)


def _parse_risk(risk_str: str) -> RiskLevel:
    """Convert risk string to RiskLevel enum."""
    s = risk_str.strip().lower()
    if "high" in s:
        return RiskLevel.HIGH
    if "moderate" in s or "medium" in s:
        return RiskLevel.MODERATE
    if "low" in s:
        return RiskLevel.LOW
    return RiskLevel.UNKNOWN


def _validate_with_references(params: list[ParameterResult]) -> list[ParameterResult]:
    """Cross-validate LLM output against our reference ranges."""
    for param in params:
        ref = find_reference(param.test_name)
        if ref is None:
            continue

        # Try to parse numeric value
        try:
            numeric_val = float(
                re.sub(r"[^\d.]", "", param.patient_value.split()[0])
            )
        except (ValueError, IndexError):
            continue

        # Validate and potentially correct the status
        correct_status = ref.get_status(numeric_val)
        correct_status_enum = _parse_status(correct_status)

        if param.status != correct_status_enum:
            logger.info(
                f"Correcting {param.test_name} status from "
                f"{param.status.value} to {correct_status}"
            )
            param.status = correct_status_enum

        # Fill in unit/range if missing
        if not param.unit:
            param.unit = ref.unit
        if not param.normal_range:
            param.normal_range = f"{ref.low} - {ref.high} {ref.unit}"

    return params


def analyze_with_llm(
    ocr_text: str,
    model: Optional[str] = None,
) -> AnalysisResult:
    """
    Analyze medical report text using a local LLM via Ollama.

    Args:
        ocr_text: Extracted text from the medical report.
        model: Ollama model name (auto-detected if None).

    Returns:
        AnalysisResult with all fields populated.
    """
    # Auto-detect model if not specified
    if model is None:
        available, model = check_ollama_available()
        if not available:
            raise ConnectionError(
                "Ollama is not available. Please start Ollama or use fallback mode."
            )

    logger.info(f"Analyzing report with model: {model}")

    user_prompt = f"""Analyze this medical laboratory report and return structured JSON:

--- REPORT START ---
{ocr_text}
--- REPORT END ---

Extract ALL test parameters you can find. For each parameter:
- Identify the test name, value, unit, and normal range
- Determine if the value is Normal, Low, High, Critical Low, or Critical High
- Explain in simple language what this means
- List possible causes if abnormal
- List health implications if abnormal

Also provide an overall summary, risk level, key findings, and general recommendations.
Remember: Return ONLY valid JSON."""

    # Call the LLM
    raw_response = _call_ollama(user_prompt, model)
    parsed = _extract_json(raw_response)

    if not parsed:
        raise ValueError("LLM returned invalid/empty response.")

    # Build the result
    result = AnalysisResult(analysis_mode="ai")

    # Patient info
    pi = parsed.get("patient_info", {})
    result.patient_info = PatientInfo(
        name=pi.get("name", "Not Available"),
        age=pi.get("age", "Not Available"),
        gender=pi.get("gender", "Not Available"),
        report_date=pi.get("report_date", "Not Available"),
        lab_name=pi.get("lab_name", "Not Available"),
        ref_number=pi.get("ref_number", "Not Available"),
    )

    # Parameters
    for p in parsed.get("parameters", []):
        param = ParameterResult(
            test_name=p.get("test_name", "Unknown"),
            patient_value=str(p.get("patient_value", "")),
            unit=p.get("unit", ""),
            normal_range=p.get("normal_range", ""),
            status=_parse_status(p.get("status", "Unknown")),
            explanation=p.get("explanation", ""),
            possible_causes=p.get("possible_causes", []),
            health_implications=p.get("health_implications", []),
        )
        result.parameters.append(param)

    # Validate against reference ranges
    result.parameters = _validate_with_references(result.parameters)

    # Summary, risk, findings, recommendations
    result.summary = parsed.get("summary", "Analysis completed.")
    result.risk_level = _parse_risk(parsed.get("risk_level", "Unknown"))
    result.key_findings = parsed.get("key_findings", [])
    result.recommendations = parsed.get("recommendations", [])
    result.raw_ocr_text = ocr_text

    # Compute stats
    result.compute_stats()

    return result
