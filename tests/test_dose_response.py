"""Reference-value and malformed-input regression tests for covariance-aware GLS."""
import json
import math
import pytest
from dose_response import Z95, fit_study, pool_studies, analyze_json


def study(name="A", beta=0.2, variance=0.04):
    return {
        "study_id": name, "reference_dose": 0, "doses": [1, 2, 3],
        "relative_risks": [math.exp(beta * x) for x in [1, 2, 3]],
        "covariance": [[variance if i == j else variance * 0.25
                        for j in range(3)] for i in range(3)],
    }


def test_correlated_gls_recovers_known_slope():
    result = fit_study(study())
    assert result["log_rr_per_dose"] == pytest.approx(0.2)
    assert result["variance"] == pytest.approx(0.00375)
    assert result["rr_per_dose"] == pytest.approx(math.exp(0.2))


def test_fixed_effect_pool_se_and_ci():
    result = pool_studies([study("A"), study("B")], model="fixed")
    assert result["pooled_log_rr_per_dose"] == pytest.approx(.2)
    assert result["pooled_se"] == pytest.approx(math.sqrt(.00375 / 2))
    assert result["tau_squared"] == 0
    assert result["i_squared_percent"] == 0
    assert result["pooled_rr_ci95"][0] == pytest.approx(
        math.exp(.2 - Z95 * math.sqrt(.00375 / 2)))


def test_random_effect_heterogeneity():
    result = pool_studies([study("A", -.1), study("B", .5)], "random")
    assert result["tau_squared"] > 0
    assert result["i_squared_percent"] > 0
    assert result["pooled_log_rr_per_dose"] == pytest.approx(.2)
    assert result["pooled_se"] > pool_studies(
        [study("A", -.1), study("B", .5)], "fixed")["pooled_se"]


def test_json_roundtrip():
    value = analyze_json(json.dumps(
        {"studies": [study("A"), study("B")], "model": "random"}))
    assert json.loads(value)["number_of_studies"] == 2


@pytest.mark.parametrize("bad", [
    {"doses": [0, 1, 2]},
    {"relative_risks": [1, 0, 1]},
    {"relative_risks": [1, -1, 1]},
    {"relative_risks": [1, "nan", 1]},
    {"covariance": [[.04, 0, 0], [0, -1, 0], [0, 0, .04]]},
    {"covariance": [[.04, .06, 0], [.06, .04, 0], [0, 0, .04]]},
    {"covariance": [[.04, .02, 0], [0, .04, 0], [0, 0, .04]]},
    {"doses": [1, 1, 3]},
])
def test_invalid_studies_rejected(bad):
    data = study()
    data.update(bad)
    with pytest.raises(ValueError):
        fit_study(data)


def test_random_one_study_rejected():
    with pytest.raises(ValueError):
        pool_studies([study()], "random")


def test_empty_rejected():
    with pytest.raises(ValueError):
        pool_studies([], "fixed")
