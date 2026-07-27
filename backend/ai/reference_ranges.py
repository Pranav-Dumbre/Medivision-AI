"""
Medical laboratory reference ranges for 50+ common tests.

Covers: CBC, Lipid Profile, Kidney Function Test, Liver Function Test,
Thyroid Panel, Diabetes, Vitamins, Uric Acid, Electrolytes, and more.

All ranges are for **adults** and are approximate clinical guidelines.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


@dataclass
class ReferenceRange:
    """Reference range for a single lab parameter."""
    test_name: str
    unit: str
    low: float
    high: float
    critical_low: Optional[float] = None
    critical_high: Optional[float] = None
    category: str = "General"
    aliases: tuple[str, ...] = ()

    def get_status(self, value: float) -> str:
        """Return status string for a given numeric value."""
        if self.critical_low is not None and value <= self.critical_low:
            return "Critical Low"
        if self.critical_high is not None and value >= self.critical_high:
            return "Critical High"
        if value < self.low:
            return "Low"
        if value > self.high:
            return "High"
        return "Normal"


# ──────────────────────────────────────────────────────────────
# Complete Blood Count (CBC)
# ──────────────────────────────────────────────────────────────
CBC = [
    ReferenceRange(
        "Hemoglobin", "g/dL", 12.0, 17.5, critical_low=7.0, critical_high=20.0,
        category="CBC",
        aliases=("Hb", "HGB", "Haemoglobin"),
    ),
    ReferenceRange(
        "RBC Count", "million/µL", 4.0, 5.5, critical_low=2.5, critical_high=7.5,
        category="CBC",
        aliases=("Red Blood Cells", "RBC", "Erythrocytes"),
    ),
    ReferenceRange(
        "WBC Count", "×10³/µL", 4.0, 11.0, critical_low=2.0, critical_high=30.0,
        category="CBC",
        aliases=("White Blood Cells", "WBC", "Leukocytes", "Total WBC Count", "TLC"),
    ),
    ReferenceRange(
        "Platelet Count", "×10³/µL", 150.0, 400.0, critical_low=50.0, critical_high=1000.0,
        category="CBC",
        aliases=("Platelets", "PLT", "Thrombocytes"),
    ),
    ReferenceRange(
        "Hematocrit", "%", 36.0, 54.0, critical_low=20.0, critical_high=60.0,
        category="CBC",
        aliases=("HCT", "PCV", "Packed Cell Volume"),
    ),
    ReferenceRange(
        "MCV", "fL", 80.0, 100.0,
        category="CBC",
        aliases=("Mean Corpuscular Volume",),
    ),
    ReferenceRange(
        "MCH", "pg", 27.0, 33.0,
        category="CBC",
        aliases=("Mean Corpuscular Hemoglobin",),
    ),
    ReferenceRange(
        "MCHC", "g/dL", 32.0, 36.0,
        category="CBC",
        aliases=("Mean Corpuscular Hemoglobin Concentration",),
    ),
    ReferenceRange(
        "RDW", "%", 11.5, 14.5,
        category="CBC",
        aliases=("Red Cell Distribution Width", "RDW-CV"),
    ),
    ReferenceRange(
        "MPV", "fL", 7.5, 11.5,
        category="CBC",
        aliases=("Mean Platelet Volume",),
    ),
    ReferenceRange(
        "Neutrophils", "%", 40.0, 70.0,
        category="CBC",
        aliases=("Neutrophil %", "Segmented Neutrophils"),
    ),
    ReferenceRange(
        "Lymphocytes", "%", 20.0, 45.0,
        category="CBC",
        aliases=("Lymphocyte %",),
    ),
    ReferenceRange(
        "Monocytes", "%", 2.0, 10.0,
        category="CBC",
        aliases=("Monocyte %",),
    ),
    ReferenceRange(
        "Eosinophils", "%", 1.0, 6.0,
        category="CBC",
        aliases=("Eosinophil %",),
    ),
    ReferenceRange(
        "Basophils", "%", 0.0, 2.0,
        category="CBC",
        aliases=("Basophil %",),
    ),
    ReferenceRange(
        "ESR", "mm/hr", 0.0, 20.0,
        category="CBC",
        aliases=("Erythrocyte Sedimentation Rate", "Sed Rate"),
    ),
]

# ──────────────────────────────────────────────────────────────
# Lipid Profile
# ──────────────────────────────────────────────────────────────
LIPID_PROFILE = [
    ReferenceRange(
        "Total Cholesterol", "mg/dL", 0.0, 200.0, critical_high=300.0,
        category="Lipid Profile",
        aliases=("Cholesterol", "TC", "Total Chol"),
    ),
    ReferenceRange(
        "HDL Cholesterol", "mg/dL", 40.0, 60.0,
        category="Lipid Profile",
        aliases=("HDL", "Good Cholesterol", "HDL-C"),
    ),
    ReferenceRange(
        "LDL Cholesterol", "mg/dL", 0.0, 100.0, critical_high=190.0,
        category="Lipid Profile",
        aliases=("LDL", "Bad Cholesterol", "LDL-C"),
    ),
    ReferenceRange(
        "Triglycerides", "mg/dL", 0.0, 150.0, critical_high=500.0,
        category="Lipid Profile",
        aliases=("TG", "Trigs"),
    ),
    ReferenceRange(
        "VLDL Cholesterol", "mg/dL", 5.0, 40.0,
        category="Lipid Profile",
        aliases=("VLDL", "VLDL-C"),
    ),
    ReferenceRange(
        "Total Cholesterol/HDL Ratio", "", 0.0, 5.0,
        category="Lipid Profile",
        aliases=("TC/HDL Ratio", "Cholesterol Ratio"),
    ),
]

# ──────────────────────────────────────────────────────────────
# Kidney Function Test (KFT / RFT)
# ──────────────────────────────────────────────────────────────
KFT = [
    ReferenceRange(
        "Blood Urea", "mg/dL", 7.0, 20.0, critical_high=100.0,
        category="Kidney Function",
        aliases=("Urea", "BUN", "Blood Urea Nitrogen"),
    ),
    ReferenceRange(
        "Creatinine", "mg/dL", 0.6, 1.2, critical_high=10.0,
        category="Kidney Function",
        aliases=("Serum Creatinine", "S. Creatinine", "Creat"),
    ),
    ReferenceRange(
        "Uric Acid", "mg/dL", 3.5, 7.2, critical_high=12.0,
        category="Kidney Function",
        aliases=("Serum Uric Acid", "S. Uric Acid"),
    ),
    ReferenceRange(
        "eGFR", "mL/min/1.73m²", 90.0, 120.0, critical_low=15.0,
        category="Kidney Function",
        aliases=("Estimated GFR", "Glomerular Filtration Rate"),
    ),
    ReferenceRange(
        "Calcium", "mg/dL", 8.5, 10.5, critical_low=6.0, critical_high=13.0,
        category="Kidney Function",
        aliases=("Serum Calcium", "Ca", "Total Calcium"),
    ),
    ReferenceRange(
        "Phosphorus", "mg/dL", 2.5, 4.5,
        category="Kidney Function",
        aliases=("Serum Phosphorus", "Phosphate", "Inorganic Phosphorus"),
    ),
]

# ──────────────────────────────────────────────────────────────
# Liver Function Test (LFT)
# ──────────────────────────────────────────────────────────────
LFT = [
    ReferenceRange(
        "Total Bilirubin", "mg/dL", 0.1, 1.2, critical_high=15.0,
        category="Liver Function",
        aliases=("Bilirubin Total", "T. Bilirubin", "S. Bilirubin"),
    ),
    ReferenceRange(
        "Direct Bilirubin", "mg/dL", 0.0, 0.3, critical_high=10.0,
        category="Liver Function",
        aliases=("Conjugated Bilirubin", "D. Bilirubin"),
    ),
    ReferenceRange(
        "Indirect Bilirubin", "mg/dL", 0.1, 1.0,
        category="Liver Function",
        aliases=("Unconjugated Bilirubin",),
    ),
    ReferenceRange(
        "SGOT", "U/L", 5.0, 40.0, critical_high=1000.0,
        category="Liver Function",
        aliases=("AST", "Aspartate Aminotransferase", "SGOT (AST)"),
    ),
    ReferenceRange(
        "SGPT", "U/L", 7.0, 56.0, critical_high=1000.0,
        category="Liver Function",
        aliases=("ALT", "Alanine Aminotransferase", "SGPT (ALT)"),
    ),
    ReferenceRange(
        "Alkaline Phosphatase", "U/L", 44.0, 147.0,
        category="Liver Function",
        aliases=("ALP", "Alk Phos"),
    ),
    ReferenceRange(
        "GGT", "U/L", 9.0, 48.0,
        category="Liver Function",
        aliases=("Gamma-GT", "Gamma Glutamyl Transferase", "GGTP"),
    ),
    ReferenceRange(
        "Total Protein", "g/dL", 6.0, 8.3,
        category="Liver Function",
        aliases=("Serum Total Protein", "TP"),
    ),
    ReferenceRange(
        "Albumin", "g/dL", 3.5, 5.5,
        category="Liver Function",
        aliases=("Serum Albumin", "Alb"),
    ),
    ReferenceRange(
        "Globulin", "g/dL", 2.0, 3.5,
        category="Liver Function",
        aliases=("Serum Globulin",),
    ),
    ReferenceRange(
        "A/G Ratio", "", 1.0, 2.1,
        category="Liver Function",
        aliases=("Albumin/Globulin Ratio", "AG Ratio"),
    ),
]

# ──────────────────────────────────────────────────────────────
# Thyroid Panel
# ──────────────────────────────────────────────────────────────
THYROID = [
    ReferenceRange(
        "TSH", "µIU/mL", 0.4, 4.0, critical_low=0.01, critical_high=100.0,
        category="Thyroid",
        aliases=("Thyroid Stimulating Hormone", "Serum TSH", "S. TSH"),
    ),
    ReferenceRange(
        "T3 Total", "ng/dL", 80.0, 200.0,
        category="Thyroid",
        aliases=("Triiodothyronine", "Total T3", "T3"),
    ),
    ReferenceRange(
        "T4 Total", "µg/dL", 5.1, 14.1,
        category="Thyroid",
        aliases=("Thyroxine", "Total T4", "T4"),
    ),
    ReferenceRange(
        "Free T3", "pg/mL", 2.0, 4.4,
        category="Thyroid",
        aliases=("FT3",),
    ),
    ReferenceRange(
        "Free T4", "ng/dL", 0.93, 1.7,
        category="Thyroid",
        aliases=("FT4",),
    ),
]

# ──────────────────────────────────────────────────────────────
# Diabetes Panel
# ──────────────────────────────────────────────────────────────
DIABETES = [
    ReferenceRange(
        "Fasting Blood Sugar", "mg/dL", 70.0, 100.0, critical_low=40.0, critical_high=400.0,
        category="Diabetes",
        aliases=("FBS", "Fasting Glucose", "Fasting Blood Glucose", "FBG"),
    ),
    ReferenceRange(
        "Post Prandial Blood Sugar", "mg/dL", 70.0, 140.0, critical_high=400.0,
        category="Diabetes",
        aliases=("PPBS", "PP Blood Sugar", "Post Meal Glucose", "PP Glucose"),
    ),
    ReferenceRange(
        "Random Blood Sugar", "mg/dL", 70.0, 140.0, critical_low=40.0, critical_high=500.0,
        category="Diabetes",
        aliases=("RBS", "Random Glucose"),
    ),
    ReferenceRange(
        "HbA1c", "%", 4.0, 5.6, critical_high=14.0,
        category="Diabetes",
        aliases=(
            "Glycated Hemoglobin", "Glycosylated Hemoglobin",
            "A1C", "Hemoglobin A1c",
        ),
    ),
]

# ──────────────────────────────────────────────────────────────
# Vitamins & Minerals
# ──────────────────────────────────────────────────────────────
VITAMINS = [
    ReferenceRange(
        "Vitamin D", "ng/mL", 30.0, 100.0, critical_low=10.0,
        category="Vitamins",
        aliases=(
            "25-OH Vitamin D", "Vitamin D Total", "Vit D",
            "25-Hydroxy Vitamin D",
        ),
    ),
    ReferenceRange(
        "Vitamin B12", "pg/mL", 200.0, 900.0, critical_low=100.0,
        category="Vitamins",
        aliases=("Cobalamin", "Vit B12", "Cyanocobalamin"),
    ),
    ReferenceRange(
        "Iron", "µg/dL", 60.0, 170.0, critical_low=30.0,
        category="Vitamins",
        aliases=("Serum Iron", "S. Iron", "Fe"),
    ),
    ReferenceRange(
        "Ferritin", "ng/mL", 12.0, 300.0, critical_low=5.0,
        category="Vitamins",
        aliases=("Serum Ferritin", "S. Ferritin"),
    ),
    ReferenceRange(
        "Folic Acid", "ng/mL", 3.0, 17.0,
        category="Vitamins",
        aliases=("Folate", "Vitamin B9", "Serum Folate"),
    ),
    ReferenceRange(
        "TIBC", "µg/dL", 250.0, 370.0,
        category="Vitamins",
        aliases=("Total Iron Binding Capacity",),
    ),
]

# ──────────────────────────────────────────────────────────────
# Electrolytes
# ──────────────────────────────────────────────────────────────
ELECTROLYTES = [
    ReferenceRange(
        "Sodium", "mEq/L", 136.0, 145.0, critical_low=120.0, critical_high=160.0,
        category="Electrolytes",
        aliases=("Na", "Serum Sodium", "Na+"),
    ),
    ReferenceRange(
        "Potassium", "mEq/L", 3.5, 5.1, critical_low=2.5, critical_high=6.5,
        category="Electrolytes",
        aliases=("K", "Serum Potassium", "K+"),
    ),
    ReferenceRange(
        "Chloride", "mEq/L", 98.0, 106.0, critical_low=80.0, critical_high=120.0,
        category="Electrolytes",
        aliases=("Cl", "Serum Chloride", "Cl-"),
    ),
]


# ══════════════════════════════════════════════════════════════
# Master lookup
# ══════════════════════════════════════════════════════════════

ALL_RANGES: list[ReferenceRange] = (
    CBC + LIPID_PROFILE + KFT + LFT + THYROID + DIABETES + VITAMINS + ELECTROLYTES
)


def _build_lookup() -> dict[str, ReferenceRange]:
    """Build a case-insensitive lookup dict mapping all names + aliases → range."""
    lookup: dict[str, ReferenceRange] = {}
    for ref in ALL_RANGES:
        lookup[ref.test_name.lower()] = ref
        for alias in ref.aliases:
            lookup[alias.lower()] = ref
    return lookup


_LOOKUP = _build_lookup()


def find_reference(test_name: str) -> Optional[ReferenceRange]:
    """Find a reference range by test name or alias (case-insensitive)."""
    return _LOOKUP.get(test_name.strip().lower())


def get_all_test_names() -> list[str]:
    """Return a list of all known test names (primary names only)."""
    return [r.test_name for r in ALL_RANGES]


def get_categories() -> list[str]:
    """Return sorted unique categories."""
    return sorted({r.category for r in ALL_RANGES})
