"""Outcome-mapper tests — pattern specificity + coverage."""
from __future__ import annotations

from src.outcome_mapper import map_outcome


def test_none_and_empty_return_unknown() -> None:
    assert map_outcome(None) == "unknown_outcome"
    assert map_outcome("") == "unknown_outcome"
    assert map_outcome("   ") == "unknown_outcome"


def test_all_cause_mortality_variants() -> None:
    for label in (
        "All-cause mortality",
        "all cause mortality",
        "Overall mortality",
        "Mortality at 30 days",
        "Death from any cause",
        "Mortality at any time up to 28 days or discharge from hospital",
    ):
        assert map_outcome(label) == "all_cause_mortality", f"failed on: {label!r}"


def test_cardiovascular_mortality_beats_all_cause() -> None:
    for label in (
        "Cardiovascular mortality",
        "CV mortality",
        "Cardiac death",
        "Cardiovascular mortality and morbidity",
    ):
        assert map_outcome(label) == "cv_mortality", f"failed on: {label!r}"


def test_mace_specific() -> None:
    assert map_outcome("MACE") == "mace"
    assert map_outcome("Major adverse cardiac events") == "mace"


def test_myocardial_infarction() -> None:
    assert map_outcome("Myocardial infarction") == "myocardial_infarction"
    assert map_outcome("Non-fatal myocardial infarction") == "myocardial_infarction"


def test_stroke() -> None:
    assert map_outcome("Stroke") == "stroke"
    assert map_outcome("Ischaemic stroke") == "stroke"


def test_hf_hospitalisation_beats_generic_hospitalisation() -> None:
    assert map_outcome("Heart failure hospitalisation") == "hf_hospitalisation"
    assert map_outcome("HF-hospitalization") == "hf_hospitalisation"


def test_generic_hospitalisation() -> None:
    assert map_outcome("All-cause hospitalisation") == "all_cause_hospitalisation"
    assert map_outcome("Hospitalization") == "all_cause_hospitalisation"


def test_kccq() -> None:
    assert map_outcome("KCCQ overall summary score") == "kccq_overall_summary"
    assert map_outcome("KCCQ-OSS") == "kccq_overall_summary"


def test_sf36_pcs_and_mcs() -> None:
    assert map_outcome("SF-36 Physical Component Summary") == "sf36_pcs"
    assert map_outcome("SF36 PCS") == "sf36_pcs"
    assert map_outcome("SF-36 Mental Component Summary") == "sf36_mcs"
    assert map_outcome("PCS") == "sf36_pcs"
    assert map_outcome("MCS") == "sf36_mcs"


def test_six_minute_walk() -> None:
    assert map_outcome("6-minute walk distance") == "six_minute_walk_distance_m"
    assert map_outcome("Six-minute walk test") == "six_minute_walk_distance_m"
    assert map_outcome("6MWD") == "six_minute_walk_distance_m"


def test_ldl_c() -> None:
    assert map_outcome("LDL-C") == "ldl_c_mg_dl"
    assert map_outcome("Low-density lipoprotein cholesterol") == "ldl_c_mg_dl"


def test_systolic_bp() -> None:
    assert map_outcome("Systolic blood pressure") == "systolic_bp_mmhg"
    assert map_outcome("SBP change from baseline") == "systolic_bp_mmhg"
    assert map_outcome("Systolic pressure") == "systolic_bp_mmhg"


def test_hba1c() -> None:
    assert map_outcome("HbA1c") == "hba1c_percent"
    assert map_outcome("Haemoglobin A1c") == "hba1c_percent"
    assert map_outcome("Glycated haemoglobin") == "hba1c_percent"


def test_unknown_outcomes() -> None:
    """Outcomes not in any pattern return 'unknown_outcome'."""
    for label in (
        "Adverse effects",
        "Withdrawal due to adverse effects",
        "Oestradiol at 6 months (pmol/L)",
        "Bronchopulmonary dysplasia",
        "Abnormal tympanometry",
        "Quit attempts",
    ):
        assert map_outcome(label) == "unknown_outcome", f"unexpectedly mapped: {label!r}"


def test_specificity_order_cv_mortality_not_all_cause() -> None:
    """Specific CV-mortality patterns must win over the broader mortality regex."""
    # Even though the label contains 'mortality', CV-specific prefix should win.
    assert map_outcome("Cardiovascular mortality") == "cv_mortality"
    assert map_outcome("CV mortality") == "cv_mortality"


def test_specificity_order_hf_hospitalisation_not_generic() -> None:
    """Heart-failure hospitalisation wins over generic hospitalisation."""
    assert map_outcome("Heart failure hospitalisation") == "hf_hospitalisation"
