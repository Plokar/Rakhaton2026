"""Deterministická pravidla RECIST 1.1 a extrakce součtů SLD (T-304)."""
import pytest

from services.rules.recist import evaluate_sld


def measurements(*values):
    return [
        {"date": f"2026-0{i + 1}-01", "sld_mm": value, "citation": f"P03-img0{i + 1}"}
        for i, value in enumerate(values)
    ]


@pytest.mark.parametrize(("values", "expected"), [
    ((100, 70), "PR"),       # pokles alespoň o 30 % proti baseline
    ((100, 80), "SD"),       # nedosahuje PR
    ((100, 70, 85), "PD"),   # nárůst ≥20 % a ≥5 mm proti nadiru
    ((100, 70, 74), "SD"),   # relativní nárůst nedosahuje 20 %
    ((100, 0), "CR"),
])
def test_evaluate_sld(values, expected):
    result = evaluate_sld(measurements(*values))
    assert result["response"] == expected


def test_evaluate_sld_requires_two_measurements():
    assert evaluate_sld(measurements(83)) is None


def test_evaluate_sld_rejects_zero_baseline():
    assert evaluate_sld(measurements(0, 20)) is None


def test_new_lesion_is_progression_regardless_of_sld():
    assert evaluate_sld(measurements(100, 46), new_lesions=True)["response"] == "PD"
