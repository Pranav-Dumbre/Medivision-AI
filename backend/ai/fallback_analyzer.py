"""
Fallback Analyzer — Rule-based medical report analysis.

Used when Ollama/LLM is not available. Extracts parameters from OCR text
using regex patterns and evaluates them against predefined reference ranges.
"""
from __future__ import annotations

import re
import logging
from typing import Optional

from backend.models.schemas import (
    AnalysisResult,
    ParameterResult,
    ParameterStatus,
    PatientInfo,
    RiskLevel,
)
from backend.ai.reference_ranges import ALL_RANGES, find_reference, ReferenceRange

logger = logging.getLogger(__name__)


# ──────────────────────────────────────────────────────────────
# Explanation templates for common abnormalities
# ──────────────────────────────────────────────────────────────
EXPLANATIONS = {
    "Hemoglobin": {
        "Low": {
            "explanation": (
                "Your hemoglobin level is below the normal range, which may "
                "indicate anemia. Low hemoglobin can reduce oxygen delivery "
                "throughout the body and may cause fatigue or weakness."
            ),
            "causes": [
                "Iron deficiency",
                "Vitamin B12 or folate deficiency",
                "Chronic blood loss",
                "Chronic diseases",
            ],
            "implications": [
                "Fatigue and weakness",
                "Shortness of breath",
                "Dizziness",
                "Pale skin",
            ],
        },
        "High": {
            "explanation": (
                "Your hemoglobin level is above the normal range. High hemoglobin "
                "can increase blood thickness and may be related to dehydration, "
                "lung disease, or other conditions."
            ),
            "causes": [
                "Dehydration",
                "Chronic lung disease",
                "Smoking",
                "Living at high altitude",
            ],
            "implications": [
                "Increased blood clotting risk",
                "Headaches",
                "Dizziness",
            ],
        },
    },
    "WBC Count": {
        "High": {
            "explanation": (
                "Your white blood cell count is elevated, which often indicates "
                "that your body is fighting an infection or inflammation."
            ),
            "causes": [
                "Bacterial or viral infection",
                "Inflammation",
                "Stress response",
                "Certain medications",
            ],
            "implications": [
                "Active infection or inflammation",
                "Immune system activation",
            ],
        },
        "Low": {
            "explanation": (
                "Your white blood cell count is below normal, which may indicate "
                "a weakened immune system or bone marrow issues."
            ),
            "causes": [
                "Viral infections",
                "Bone marrow disorders",
                "Autoimmune conditions",
                "Certain medications",
            ],
            "implications": [
                "Increased susceptibility to infections",
                "Weakened immune response",
            ],
        },
    },
    "Platelet Count": {
        "Low": {
            "explanation": (
                "Your platelet count is below normal, which may affect blood "
                "clotting and increase bleeding risk."
            ),
            "causes": [
                "Viral infections (e.g., dengue)",
                "Liver disease",
                "Autoimmune conditions",
                "Bone marrow disorders",
            ],
            "implications": [
                "Easy bruising",
                "Prolonged bleeding",
                "Risk of internal bleeding",
            ],
        },
        "High": {
            "explanation": (
                "Your platelet count is elevated, which may increase the risk "
                "of blood clots."
            ),
            "causes": [
                "Iron deficiency",
                "Chronic inflammation",
                "Infection recovery",
                "Post-surgery",
            ],
            "implications": [
                "Increased risk of blood clots",
                "Potential cardiovascular concern",
            ],
        },
    },
    "Total Cholesterol": {
        "High": {
            "explanation": (
                "Your total cholesterol is elevated, which increases the risk of "
                "heart disease and stroke over time."
            ),
            "causes": [
                "High-fat diet",
                "Sedentary lifestyle",
                "Genetic factors",
                "Obesity",
            ],
            "implications": [
                "Increased cardiovascular risk",
                "Arterial plaque buildup",
            ],
        },
    },
    "LDL Cholesterol": {
        "High": {
            "explanation": (
                "Your LDL (bad) cholesterol is elevated. High LDL can lead to "
                "plaque buildup in arteries, increasing heart disease risk."
            ),
            "causes": [
                "High saturated fat diet",
                "Lack of exercise",
                "Genetic predisposition",
                "Obesity",
            ],
            "implications": [
                "Atherosclerosis risk",
                "Heart attack and stroke risk",
            ],
        },
    },
    "Creatinine": {
        "High": {
            "explanation": (
                "Your creatinine level is elevated, which may indicate reduced "
                "kidney function. The kidneys normally filter creatinine from "
                "the blood."
            ),
            "causes": [
                "Reduced kidney function",
                "Dehydration",
                "High protein diet",
                "Intense exercise",
            ],
            "implications": [
                "Possible kidney impairment",
                "Need for kidney function monitoring",
            ],
        },
    },
    "Fasting Blood Sugar": {
        "High": {
            "explanation": (
                "Your fasting blood sugar is above the normal range, which may "
                "indicate prediabetes or diabetes. Consistently high blood sugar "
                "can damage organs over time."
            ),
            "causes": [
                "Insulin resistance",
                "Diabetes mellitus",
                "Stress",
                "Certain medications",
            ],
            "implications": [
                "Risk of diabetes",
                "Long-term organ damage if untreated",
                "Need for dietary management",
            ],
        },
    },
    "HbA1c": {
        "High": {
            "explanation": (
                "Your HbA1c level indicates that your average blood sugar over "
                "the past 2-3 months has been elevated. Values above 5.7% may "
                "indicate prediabetes; above 6.5% may indicate diabetes."
            ),
            "causes": [
                "Uncontrolled diabetes",
                "Insulin resistance",
                "Poor dietary habits",
            ],
            "implications": [
                "Risk of diabetic complications",
                "Need for blood sugar management",
            ],
        },
    },
    "TSH": {
        "High": {
            "explanation": (
                "Your TSH level is elevated, which typically indicates an "
                "underactive thyroid (hypothyroidism). The pituitary gland "
                "produces more TSH when thyroid hormone levels are low."
            ),
            "causes": [
                "Hypothyroidism",
                "Hashimoto's thyroiditis",
                "Iodine deficiency",
            ],
            "implications": [
                "Fatigue and weight gain",
                "Cold intolerance",
                "Slow metabolism",
            ],
        },
        "Low": {
            "explanation": (
                "Your TSH level is below normal, which may indicate an "
                "overactive thyroid (hyperthyroidism)."
            ),
            "causes": [
                "Hyperthyroidism",
                "Graves' disease",
                "Excessive thyroid medication",
            ],
            "implications": [
                "Rapid heartbeat",
                "Weight loss",
                "Anxiety and irritability",
            ],
        },
    },
    "Vitamin D": {
        "Low": {
            "explanation": (
                "Your vitamin D level is below the recommended range. Vitamin D "
                "is essential for bone health, immune function, and mood regulation."
            ),
            "causes": [
                "Insufficient sun exposure",
                "Poor dietary intake",
                "Malabsorption",
                "Darker skin pigmentation",
            ],
            "implications": [
                "Weak bones (osteopenia/osteoporosis)",
                "Increased fracture risk",
                "Fatigue",
                "Weakened immunity",
            ],
        },
    },
    "Vitamin B12": {
        "Low": {
            "explanation": (
                "Your vitamin B12 level is below normal. B12 is essential for "
                "nerve function, red blood cell formation, and DNA synthesis."
            ),
            "causes": [
                "Vegetarian/vegan diet",
                "Malabsorption (e.g., pernicious anemia)",
                "Certain medications",
                "Aging",
            ],
            "implications": [
                "Fatigue and weakness",
                "Numbness and tingling in hands/feet",
                "Memory problems",
                "Megaloblastic anemia",
            ],
        },
    },
    "Uric Acid": {
        "High": {
            "explanation": (
                "Your uric acid level is elevated, which can lead to crystal "
                "deposits in joints (gout) and may affect kidney function."
            ),
            "causes": [
                "High purine diet (red meat, seafood)",
                "Obesity",
                "Kidney dysfunction",
                "Alcohol consumption",
            ],
            "implications": [
                "Risk of gout attacks",
                "Kidney stone risk",
                "Joint inflammation",
            ],
        },
    },
    "SGPT": {
        "High": {
            "explanation": (
                "Your SGPT (ALT) liver enzyme is elevated, which may indicate "
                "liver stress or damage. This enzyme is released when liver "
                "cells are injured."
            ),
            "causes": [
                "Fatty liver disease",
                "Hepatitis",
                "Alcohol consumption",
                "Certain medications",
            ],
            "implications": [
                "Liver inflammation",
                "Need for liver function monitoring",
            ],
        },
    },
    "SGOT": {
        "High": {
            "explanation": (
                "Your SGOT (AST) enzyme is elevated. While primarily a liver "
                "enzyme, it's also found in heart and muscle tissue."
            ),
            "causes": [
                "Liver disease",
                "Heart conditions",
                "Muscle damage",
                "Certain medications",
            ],
            "implications": [
                "Liver or muscle inflammation",
                "Need for further investigation",
            ],
        },
    },
}


# ──────────────────────────────────────────────────────────────
# Default explanation templates for unknown parameters
# ──────────────────────────────────────────────────────────────
DEFAULT_EXPLANATIONS = {
    "Low": {
        "explanation": (
            "This value is below the normal reference range. "
            "Low values may indicate a deficiency or underlying condition. "
            "Please consult your healthcare provider for proper evaluation."
        ),
        "causes": ["Nutritional deficiency", "Underlying medical condition"],
        "implications": ["May require further investigation", "Follow-up recommended"],
    },
    "High": {
        "explanation": (
            "This value is above the normal reference range. "
            "Elevated values may indicate stress on a particular organ or system. "
            "Please consult your healthcare provider for proper evaluation."
        ),
        "causes": ["Dietary factors", "Underlying medical condition"],
        "implications": ["May require lifestyle changes", "Follow-up recommended"],
    },
    "Critical Low": {
        "explanation": (
            "This value is CRITICALLY below normal and may require urgent "
            "medical attention. Please consult your healthcare provider "
            "immediately."
        ),
        "causes": ["Severe deficiency", "Acute medical condition"],
        "implications": [
            "Urgent medical evaluation recommended",
            "Potential health emergency",
        ],
    },
    "Critical High": {
        "explanation": (
            "This value is CRITICALLY above normal and may require urgent "
            "medical attention. Please consult your healthcare provider "
            "immediately."
        ),
        "causes": ["Severe organ stress", "Acute medical condition"],
        "implications": [
            "Urgent medical evaluation recommended",
            "Potential health emergency",
        ],
    },
}


# ──────────────────────────────────────────────────────────────
# Default recommendations
# ──────────────────────────────────────────────────────────────
DEFAULT_RECOMMENDATIONS = [
    "Stay well hydrated — drink 8-10 glasses of water daily",
    "Eat a balanced diet rich in fruits, vegetables, and whole grains",
    "Exercise regularly — aim for at least 30 minutes of moderate activity daily",
    "Get adequate sleep — 7-8 hours per night",
    "Reduce excess salt, sugar, and processed foods",
    "Avoid smoking and excessive alcohol consumption",
    "Follow up with your healthcare provider to discuss these results",
    "Take prescribed medications as directed by your doctor",
    "Manage stress through relaxation techniques or counseling",
    "Schedule regular health check-ups as recommended",
]


# ──────────────────────────────────────────────────────────────
# Regex-based parameter extraction
# ──────────────────────────────────────────────────────────────

def _extract_patient_info(text: str) -> PatientInfo:
    """Extract patient info from OCR text using regex patterns."""
    info = PatientInfo()

    # Name patterns
    name_patterns = [
        r"(?:patient\s*name|name\s*of\s*patient|name)\s*[:\-]?\s*([A-Za-z\s\.]+)",
        r"(?:mr|mrs|ms|dr)\.?\s+([A-Za-z\s]+)",
    ]
    for pat in name_patterns:
        m = re.search(pat, text, re.IGNORECASE)
        if m:
            name = m.group(1).strip()
            if len(name) > 2 and not any(
                kw in name.lower()
                for kw in ["test", "report", "lab", "hospital", "clinic"]
            ):
                info.name = name
                break

    # Age
    age_match = re.search(
        r"(?:age|years?)\s*[:\-]?\s*(\d{1,3})\s*(?:years?|yrs?|y)?",
        text,
        re.IGNORECASE,
    )
    if age_match:
        info.age = age_match.group(1) + " years"

    # Gender
    gender_match = re.search(
        r"(?:sex|gender)\s*[:\-]?\s*(male|female|m|f)",
        text,
        re.IGNORECASE,
    )
    if gender_match:
        g = gender_match.group(1).strip().lower()
        info.gender = "Male" if g in ("male", "m") else "Female"

    # Date
    date_match = re.search(
        r"(?:date|collected|reported)\s*[:\-]?\s*(\d{1,2}[/\-]\d{1,2}[/\-]\d{2,4})",
        text,
        re.IGNORECASE,
    )
    if date_match:
        info.report_date = date_match.group(1)

    return info


def _extract_parameters(text: str) -> list[ParameterResult]:
    """
    Extract lab parameter values from OCR text using regex matching
    against known test names and aliases.
    """
    parameters: list[ParameterResult] = []
    found_names: set[str] = set()

    for ref in ALL_RANGES:
        # Build regex pattern from test name and aliases
        all_names = [ref.test_name] + list(ref.aliases)
        for name in all_names:
            # Escape special regex characters in the name
            escaped = re.escape(name)
            # Pattern: test_name followed by value (with optional unit)
            patterns = [
                # "Test Name : 10.2 g/dL" or "Test Name 10.2"
                rf"{escaped}\s*[:\-]?\s*([\d]+\.?\d*)\s*({re.escape(ref.unit)})?",
                # "Test Name ... 10.2 ... 12-16"
                rf"{escaped}[^\n]*([\d]+\.?\d*)\s*{re.escape(ref.unit)}?",
            ]

            for pattern in patterns:
                match = re.search(pattern, text, re.IGNORECASE)
                if match and ref.test_name not in found_names:
                    try:
                        value = float(match.group(1))
                    except (ValueError, IndexError):
                        continue

                    # Skip unreasonably large/small values (likely OCR errors)
                    if value > 50000 or value < 0:
                        continue

                    status_str = ref.get_status(value)
                    status = _parse_status_str(status_str)

                    # Get explanation
                    expl_data = _get_explanation(ref.test_name, status_str)

                    param = ParameterResult(
                        test_name=ref.test_name,
                        patient_value=str(value),
                        unit=ref.unit,
                        normal_range=f"{ref.low} - {ref.high} {ref.unit}",
                        status=status,
                        explanation=expl_data["explanation"],
                        possible_causes=expl_data["causes"],
                        health_implications=expl_data["implications"],
                    )
                    parameters.append(param)
                    found_names.add(ref.test_name)
                    break  # Move to next reference

            if ref.test_name in found_names:
                break  # Already found this test

    return parameters


def _parse_status_str(status: str) -> ParameterStatus:
    """Convert string status to enum."""
    mapping = {
        "Normal": ParameterStatus.NORMAL,
        "Low": ParameterStatus.LOW,
        "High": ParameterStatus.HIGH,
        "Critical Low": ParameterStatus.CRITICAL_LOW,
        "Critical High": ParameterStatus.CRITICAL_HIGH,
    }
    return mapping.get(status, ParameterStatus.UNKNOWN)


def _get_explanation(test_name: str, status: str) -> dict:
    """Get explanation for a parameter's abnormal status."""
    if status == "Normal":
        return {
            "explanation": (
                f"Your {test_name} is within the normal range. "
                "This is a healthy finding."
            ),
            "causes": [],
            "implications": [],
        }

    # Check specific explanations
    base_status = "High" if "High" in status else "Low" if "Low" in status else status
    if test_name in EXPLANATIONS and base_status in EXPLANATIONS[test_name]:
        data = EXPLANATIONS[test_name][base_status]
        return {
            "explanation": data["explanation"],
            "causes": data.get("causes", []),
            "implications": data.get("implications", []),
        }

    # Use default templates
    if status in DEFAULT_EXPLANATIONS:
        data = DEFAULT_EXPLANATIONS[status]
        explanation = data["explanation"].replace("This value", f"Your {test_name}")
        return {
            "explanation": explanation,
            "causes": data["causes"],
            "implications": data["implications"],
        }

    return {
        "explanation": f"Your {test_name} value requires attention.",
        "causes": ["Please consult your healthcare provider"],
        "implications": ["Further evaluation recommended"],
    }


def _assess_risk(parameters: list[ParameterResult]) -> RiskLevel:
    """Determine overall risk level based on parameter statuses."""
    if not parameters:
        return RiskLevel.UNKNOWN

    critical_count = sum(
        1
        for p in parameters
        if p.status in (ParameterStatus.CRITICAL_LOW, ParameterStatus.CRITICAL_HIGH)
    )
    abnormal_count = sum(
        1
        for p in parameters
        if p.status not in (ParameterStatus.NORMAL, ParameterStatus.UNKNOWN)
    )
    total = len(parameters)

    if critical_count > 0:
        return RiskLevel.HIGH
    if abnormal_count > total * 0.4:
        return RiskLevel.HIGH
    if abnormal_count > total * 0.2:
        return RiskLevel.MODERATE
    if abnormal_count > 0:
        return RiskLevel.MODERATE
    return RiskLevel.LOW


def _generate_summary(
    parameters: list[ParameterResult],
    risk: RiskLevel,
) -> str:
    """Generate a plain-language summary of the analysis."""
    total = len(parameters)
    normal = sum(1 for p in parameters if p.status == ParameterStatus.NORMAL)
    abnormal_params = [
        p for p in parameters if p.status != ParameterStatus.NORMAL
    ]

    if total == 0:
        return (
            "No laboratory parameters could be extracted from this report. "
            "Please ensure the report image is clear and try again."
        )

    summary_parts = [
        f"This report contains {total} laboratory parameters. "
    ]

    if normal == total:
        summary_parts.append(
            "All values are within the normal range. "
            "This is a positive finding."
        )
    elif abnormal_params:
        summary_parts.append(
            f"{normal} values are within the normal range. "
            f"However, {len(abnormal_params)} parameter(s) show abnormalities: "
        )
        abnormal_names = [
            f"{p.test_name} is {p.status.value.lower()}"
            for p in abnormal_params[:5]
        ]
        summary_parts.append(", ".join(abnormal_names) + ". ")

        if risk == RiskLevel.HIGH:
            summary_parts.append(
                "Some values are significantly outside normal ranges. "
                "Please consult your healthcare provider promptly for proper evaluation."
            )
        elif risk == RiskLevel.MODERATE:
            summary_parts.append(
                "These findings may warrant attention. "
                "Please discuss these results with your healthcare provider."
            )
        else:
            summary_parts.append(
                "Minor deviations from normal ranges were noted. "
                "Consider discussing these results during your next check-up."
            )

    return "".join(summary_parts)


def _generate_key_findings(parameters: list[ParameterResult]) -> list[str]:
    """Extract the key findings from the analysis."""
    findings = []
    for p in parameters:
        if p.status in (ParameterStatus.CRITICAL_LOW, ParameterStatus.CRITICAL_HIGH):
            findings.append(
                f"⚠️ CRITICAL: {p.test_name} is {p.patient_value} {p.unit} "
                f"(Normal: {p.normal_range}) — {p.status.value}"
            )
        elif p.status in (ParameterStatus.HIGH, ParameterStatus.LOW):
            icon = "🔴" if p.status == ParameterStatus.HIGH else "🟡"
            findings.append(
                f"{icon} {p.test_name}: {p.patient_value} {p.unit} — {p.status.value}"
            )
    return findings[:10]  # Limit to top 10


def analyze_fallback(ocr_text: str) -> AnalysisResult:
    """
    Analyze medical report text using rule-based logic.

    This is the fallback when no LLM is available.

    Args:
        ocr_text: Extracted text from the medical report.

    Returns:
        AnalysisResult with all fields populated.
    """
    logger.info("Running fallback (rule-based) analysis...")

    result = AnalysisResult(analysis_mode="fallback")

    # Extract patient info
    result.patient_info = _extract_patient_info(ocr_text)

    # Extract and evaluate parameters
    result.parameters = _extract_parameters(ocr_text)

    # Risk assessment
    result.risk_level = _assess_risk(result.parameters)

    # Summary
    result.summary = _generate_summary(result.parameters, result.risk_level)

    # Key findings
    result.key_findings = _generate_key_findings(result.parameters)

    # Recommendations (select relevant ones)
    result.recommendations = DEFAULT_RECOMMENDATIONS[:7]

    # Add specific recommendations based on findings
    abnormal_categories = {
        find_reference(p.test_name).category
        for p in result.parameters
        if p.status != ParameterStatus.NORMAL and find_reference(p.test_name)
    }
    if "Diabetes" in abnormal_categories:
        result.recommendations.insert(0, "Monitor your blood sugar levels regularly")
    if "Lipid Profile" in abnormal_categories:
        result.recommendations.insert(0, "Limit intake of saturated and trans fats")
    if "Kidney Function" in abnormal_categories:
        result.recommendations.insert(0, "Stay well hydrated and limit protein if advised")

    result.raw_ocr_text = ocr_text
    result.compute_stats()

    return result
