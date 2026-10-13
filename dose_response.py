"""Two-stage linear dose-response meta-analysis with supplied log-risk covariance.

The caller must provide the within-study covariance of nonreference log-relative-risk
contrasts. This module does not reconstruct Greenland--Longnecker covariance from
category counts, and does not implement nonlinear restricted cubic splines.
"""
import json
import math
from typing import Any

Z95 = 1.959963984540054
MAX_STUDIES = 200
MAX_DOSES = 50


def _finite(value: Any, label: str) -> float:
    if isinstance(value, bool):
        raise ValueError(f"{label} must be a finite number")
    try:
        num = float(value)
    except (ValueError, TypeError, OverflowError) as exc:
        raise ValueError(f"{label} must be a finite number") from exc
    if not math.isfinite(num):
        raise ValueError(f"{label} must be a finite number")
    return num


def _cholesky(matrix: list[list[float]]) -> list[list[float]]:
    n = len(matrix)
    lower = [[0.0] * n for _ in range(n)]
    for i in range(n):
        for j in range(i + 1):
            val = matrix[i][j] - sum(lower[i][k] * lower[j][k] for k in range(j))
            if i == j:
                if val <= 0 or not math.isfinite(val):
                    raise ValueError("Covariance must be symmetric positive definite")
                lower[i][j] = math.sqrt(val)
            else:
                lower[i][j] = val / lower[j][j]
    return lower


def _solve_cholesky(lower: list[list[float]], rhs: list[float]) -> list[float]:
    n = len(rhs)
    y = [0.0] * n
    for i in range(n):
        y[i] = (rhs[i] - sum(lower[i][j] * y[j] for j in range(i))) / lower[i][i]
    x = [0.0] * n
    for i in range(n - 1, -1, -1):
        x[i] = (y[i] - sum(lower[j][i] * x[j] for j in range(i + 1, n))) / lower[i][i]
    return x


def _exp(value: float) -> float:
    try:
        result = math.exp(value)
    except OverflowError as exc:
        raise ValueError("Estimated relative risk is outside representable range") from exc
    if not math.isfinite(result):
        raise ValueError("Estimated relative risk is nonfinite")
    return result


def fit_study(study: dict[str, Any]) -> dict[str, Any]:
    """GLS with referent log RR constrained to zero; model has no intercept."""
    if not isinstance(study, dict):
        raise ValueError("Each study must be an object")
    sid = str(study.get("study_id", "(unnamed)"))[:120]
    doses = study.get("doses")
    risks = study.get("relative_risks")
    cov = study.get("covariance")
    if not isinstance(doses, list) or not 1 <= len(doses) <= MAX_DOSES:
        raise ValueError(f"{sid}: doses must contain 1 to {MAX_DOSES} nonreference levels")
    n = len(doses)
    if not isinstance(risks, list) or len(risks) != n:
        raise ValueError(f"{sid}: relative_risks must match doses")
    if not isinstance(cov, list) or len(cov) != n or any(not isinstance(r, list) or len(r) != n for r in cov):
        raise ValueError(f"{sid}: covariance must be an {n}x{n} matrix on log-risk scale")
    ref = _finite(study.get("reference_dose", 0), f"{sid} reference_dose")
    x = [_finite(d, "dose") - ref for d in doses]
    if any(d == 0 for d in x) or len(set(x)) != n:
        raise ValueError(f"{sid}: nonreference doses must be distinct and differ from reference")
    rr = [_finite(r, "relative risk") for r in risks]
    if any(r <= 0 for r in rr):
        raise ValueError(f"{sid}: all relative risks must be positive")
    y = [math.log(r) for r in rr]
    v = [[_finite(cell, "covariance element") for cell in row] for row in cov]
    for i in range(n):
        for j in range(i):
            if not math.isclose(v[i][j], v[j][i], abs_tol=1e-10, rel_tol=1e-10):
                raise ValueError(f"{sid}: covariance must be symmetric")
    lower = _cholesky(v)
    vinvx = _solve_cholesky(lower, x)
    vinvy = _solve_cholesky(lower, y)
    info = sum(a * b for a, b in zip(x, vinvx))
    if info <= 0 or not math.isfinite(info):
        raise ValueError(f"{sid}: invalid model information")
    beta = sum(a * b for a, b in zip(x, vinvy)) / info
    variance = 1.0 / info
    if not all(math.isfinite(a) for a in (beta, variance)):
        raise ValueError(f"{sid}: nonfinite regression result")
    se = math.sqrt(variance)
    return {"study_id": sid, "log_rr_per_dose": beta, "standard_error": se,
            "variance": variance, "rr_per_dose": _exp(beta),
            "rr_ci95": [_exp(beta - Z95 * se), _exp(beta + Z95 * se)],
            "n_nonreference_categories": n}


def pool_studies(studies: list[dict[str, Any]], model: str = "random") -> dict[str, Any]:
    """Fixed inverse-variance or DerSimonian-Laird random-effects linear pooling."""
    if model not in {"fixed", "random"}:
        raise ValueError("model must be 'fixed' or 'random'")
    if not isinstance(studies, list) or not 1 <= len(studies) <= MAX_STUDIES:
        raise ValueError(f"studies must contain 1 to {MAX_STUDIES} objects")
    if model == "random" and len(studies) < 2:
        raise ValueError("Random-effects pooling requires at least two studies")
    per_study = [fit_study(s) for s in studies]
    ids = [s["study_id"] for s in per_study]
    if len(set(ids)) != len(ids):
        raise ValueError("study_id must be unique")
    betas = [s["log_rr_per_dose"] for s in per_study]
    w = [1.0 / s["variance"] for s in per_study]
    wsum = sum(w)
    fixed_beta = sum(a * b for a, b in zip(w, betas)) / wsum
    q = sum(wi * (bi - fixed_beta) ** 2 for wi, bi in zip(w, betas))
    df = len(studies) - 1
    c = wsum - sum(wi ** 2 for wi in w) / wsum
    tau2 = max(0.0, (q - df) / c) if c > 0 else 0.0
    weights = [1.0 / (s["variance"] + (tau2 if model == "random" else 0.0)) for s in per_study]
    total = sum(weights)
    beta = sum(wi * bi for wi, bi in zip(weights, betas)) / total
    se = math.sqrt(1.0 / total)
    return {"method": f"two-stage GLS, {model}-effect inverse-variance pooling" + (" (DerSimonian-Laird tau²)" if model == "random" else ""),
            "model": model, "number_of_studies": len(per_study), "studies": per_study,
            "pooled_log_rr_per_dose": beta, "pooled_se": se, "pooled_rr_per_dose": _exp(beta),
            "pooled_rr_ci95": [_exp(beta - Z95 * se), _exp(beta + Z95 * se)],
            "q": q, "q_df": df,
            "i_squared_percent": 100 * max(0.0, (q - df) / q) if q > 0 else 0.0,
            "tau_squared": tau2 if model == "random" else 0.0,
            "limitations": "Requires supplied within-study covariance of nonreference log-risk contrasts. No covariance reconstruction, nonlinear spline model, publication-bias adjustment, or clinical guidance. Normal-approximation CIs; DerSimonian-Laird may underestimate uncertainty with few studies."}


def analyze_json(text: str) -> str:
    """JSON-in/JSON-out entrypoint for CLI and Pyodide browser execution."""
    payload = json.loads(text)
    if not isinstance(payload, dict):
        raise ValueError("Input must be a JSON object")
    return json.dumps(pool_studies(payload.get("studies"), payload.get("model", "random")), allow_nan=False)
