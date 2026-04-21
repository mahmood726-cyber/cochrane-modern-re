"""Heuristic mapping: free-text Cochrane Analysis.name → MID lookup key.

Coverage is intentionally narrow (matches the 15 outcomes in
`data/mid_lookup.yaml`). Any analysis-name that doesn't match returns
the sentinel 'unknown_outcome' — that MA then gets tier3_mid_flip = NA,
which is how the v0.1 paper reports Tier 3 as "MID-available subset".

Patterns are case-insensitive substring matches with word boundaries.
Order matters: more specific patterns first (e.g., cv_mortality before
all_cause_mortality).
"""
from __future__ import annotations

import re

# (compiled pattern, outcome_code) — evaluated in order; first match wins.
_PATTERNS: list[tuple[re.Pattern[str], str]] = [
    # More specific mortality causes FIRST
    (re.compile(r"\bcardiovascular\s+mortal|\bCV[-\s]mortal|\bcardiac\s+death", re.I),
     "cv_mortality"),
    (re.compile(r"\bmajor\s+adverse\s+cardiac|\bMACE\b", re.I),
     "mace"),
    (re.compile(r"\bmyocardial\s+infarct", re.I),
     "myocardial_infarction"),
    (re.compile(r"\bstroke\b", re.I),
     "stroke"),

    # Heart failure hospitalisation specifically
    (re.compile(r"(?:heart\s+failure|HF)[-\s]+hospital", re.I),
     "hf_hospitalisation"),

    # All-cause mortality (after specific-cause mortality)
    (re.compile(r"(?:all[-\s]?cause\s+|overall\s+)?mortal(?:ity|ities)|death\s*(?:from\s+any|all\s+causes)|\bdeath\b", re.I),
     "all_cause_mortality"),

    # Hospitalisation (after HF hospitalisation)
    (re.compile(r"\bhospitali[sz]ation", re.I),
     "all_cause_hospitalisation"),

    # QoL instruments
    (re.compile(r"\bKCCQ", re.I),
     "kccq_overall_summary"),
    (re.compile(r"\bSF[-]?36\b.*(?:physical|PCS)|\bPCS\b", re.I),
     "sf36_pcs"),
    (re.compile(r"\bSF[-]?36\b.*(?:mental|MCS)|\bMCS\b", re.I),
     "sf36_mcs"),

    # Functional
    (re.compile(r"\b6[-\s]?minute\s+walk|\b6[-\s]?MWD|\bsix[-\s]minute\s+walk", re.I),
     "six_minute_walk_distance_m"),

    # Physiologic
    (re.compile(r"\bLDL[-\s]?C?\b|\blow[-\s]density\s+lipoprotein", re.I),
     "ldl_c_mg_dl"),
    (re.compile(r"\bsystolic\s+(?:blood\s+)?pressure|\bSBP\b", re.I),
     "systolic_bp_mmhg"),
    (re.compile(r"\bHbA1c|\bhaemoglobin\s+A1c|\bhemoglobin\s+A1c|\bglycat(?:ed|ion)\s+haemoglobin", re.I),
     "hba1c_percent"),
]


def map_outcome(analysis_name: str | None) -> str:
    """Return an outcome_code for a Cochrane Analysis.name, or 'unknown_outcome'.

    The 'unknown_outcome' return is an explicit typed sentinel, not a silent
    failure: downstream flip_classifier explicitly checks
    `outcome_code not in mid_table` and returns tier3_mid_flip = None (NA),
    which the aggregator reports as the 'MID-available subset' denominator.
    """
    if not analysis_name:
        return "unknown_outcome"  # sentinel:skip-line P1-silent-failure-sentinel
    text = str(analysis_name).strip()
    if not text:
        return "unknown_outcome"  # sentinel:skip-line P1-silent-failure-sentinel
    for pattern, code in _PATTERNS:
        if pattern.search(text):
            return code
    return "unknown_outcome"  # sentinel:skip-line P1-silent-failure-sentinel


def mapping_stats(analysis_names: list[str | None]) -> dict[str, int]:
    """Count how many names map to each outcome_code. Useful for reports."""
    from collections import Counter
    return dict(Counter(map_outcome(n) for n in analysis_names))
