# Spline Dose Response Meta Engine

Research utility for **two-stage linear dose–response meta-analysis**. It fits within-study log-relative-risk slopes by generalized least squares (GLS) using supplied covariance matrices, then pools slopes using fixed-effect inverse-variance or DerSimonian–Laird random-effects methods.

**Scope limitation:** This implementation does not reconstruct Greenland–Longnecker covariances from category counts, fit restricted cubic splines, or provide validated clinical decision thresholds. The repository name reflects its original planned scope.

## Browser application

The static interface in web/index.html runs the Python statistical module in the browser using Pyodide/WebAssembly. It accepts a JSON study dataset, reports pooled and per-study estimates, and exports results to JSON. The browser downloads Pyodide from a pinned jsDelivr version; it does **not upload study data or results** to an analysis server. Internet access is needed for the runtime. Do not enter identifiable patient data.

A GitHub Pages deployment workflow is configured in .github/workflows/pages.yml. Availability is subject to repository Pages settings and a successful deployment.

## Statistical method

For each study, supply nonreference dose levels, relative risks for those levels versus a common referent, and an n×n positive-definite covariance matrix of the **log-relative-risk contrasts**. The generalized least-squares model sets the referent log RR to zero; it is **not** included as an independent observation.

\[
\hat\beta=(x^\top V^{-1}x)^{-1}x^\top V^{-1}\log(RR),\qquad
\mathrm{Var}(\hat\beta)=(x^\top V^{-1}x)^{-1}.
\]

Here x is dose minus reference_dose. All studies must use consistent exposure units and effect-measure interpretation. Pooling provides Cochran Q, I² and (random effects) DerSimonian–Laird τ². The RR estimate is exp(beta) **per one unit of exposure**. Reported 95% confidence intervals use a normal approximation; the random-effects intervals can underestimate uncertainty with few studies. No nonlinear models, missing covariance estimation, publication-bias adjustments or causal inference are implemented.

## Input JSON

Synthetic example (covariances are illustrative, not inferred from study counts):

~~~json
{
  "model": "random",
  "studies": [
    {
      "study_id": "A",
      "reference_dose": 0,
      "doses": [1, 2, 3],
      "relative_risks": [1.10517, 1.22140, 1.34986],
      "covariance": [[0.04, 0.01, 0.01], [0.01, 0.04, 0.01], [0.01, 0.01, 0.04]]
    },
    {
      "study_id": "B",
      "reference_dose": 0,
      "doses": [1, 2, 3],
      "relative_risks": [1.05127, 1.10517, 1.16183],
      "covariance": [[0.05, 0.0125, 0.0125], [0.0125, 0.05, 0.0125], [0.0125, 0.0125, 0.05]]
    }
  ]
}
~~~

The covariance must be on the log-risk scale, not RR scale, and cannot be replaced by a matrix of raw standard errors. Random-effects pooling requires at least two studies.

## Local installation and tests

Requires Python 3.10+.

~~~bash
git clone https://github.com/abusuraihsakhri/spline-dose-response-meta-engine.git
cd spline-dose-response-meta-engine
python -m pip install -e ".[dev]"
python -m pytest -v

# Save the JSON example above as studies.json
spline-dose-response dose-response -i studies.json -o results.json
~~~

Python functions are available directly from dose_response.py: fit_study(study), pool_studies(studies, model="random") and analyze_json(text).

## Legacy demonstrations

The existing legacy CLI subcommands audit, batch, chat, verify-audit and serve remain available. The older doseresponse_meta.py single/batch commands are also retained for compatibility, but calculate_metrics() is an unrelated weighted-sum heuristic **without statistical or clinical validity**. The deterministic agent rules use arbitrary demonstration thresholds; they must not guide patient management. The chat command is mock-only and performs no inference.

## Optional API and Docker

Start the legacy FastAPI server with python cli.py serve (default localhost:8000). /health is public. Other application endpoints require an X-API-Key matching SPLINE_API_KEY (minimum 24 characters). Unconfigured authentication disables those endpoints.

For Docker Compose, create a local, ignored .env file containing **two independent strong random values** for AUDIT_SECRET_KEY and SPLINE_API_KEY:

~~~bash
cp .env.example .env
python -c "import secrets; print(secrets.token_hex(32))"
# Generate twice; paste one distinct value into each .env variable
docker compose up --build
~~~

Compose binds to 127.0.0.1:8000. HMAC audit logs exist only in process memory. Pattern-based identifier detection is limited and is **not a HIPAA de-identification guarantee**. Do not process identifiable patient data.

## Methodological references

- Greenland S, Longnecker MP. Methods for trend estimation from summarized dose–response data, with applications to meta-analysis. *Am J Epidemiol.* 1992;135:1301–1309. [PMID: 1626547](https://pubmed.ncbi.nlm.nih.gov/1626547/).
- Orsini N, Bellocco R, Greenland S. Generalized least squares for trend estimation of summarized dose–response data. *Stata J.* 2006;6:40–57. [doi:10.1177/1536867X0600600103](https://doi.org/10.1177/1536867X0600600103).

## Technology and license

Python standard library (statistical calculations); FastAPI/Pydantic/Uvicorn (optional server); Pyodide/WebAssembly (browser); pytest (testing). Browser support requires JavaScript, WebAssembly and access to the Pyodide CDN. Browser input is capped at 512 KiB. License: [MIT](LICENSE).
