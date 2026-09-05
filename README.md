# Spline Dose Response Meta Engine

> **Domain:** Clinical Decision Support & Biomedical Computing  
> **Reference Guidelines & Standards:** CAP / CLSI / ISO Standards

<div align="center">

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
![Python](https://img.shields.io/badge/Python-3.10%20%7C%203.11%20%7C%203.12-3776AB.svg?logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-0.111-009688.svg?logo=fastapi&logoColor=white)
![Audit Trail](https://img.shields.io/badge/Audit-HMAC--SHA256_Tamper--Evident-brightgreen.svg)
![Zero-PHI Guard](https://img.shields.io/badge/Guard-Zero--PHI_Outbound-blue.svg)
![Docker](https://img.shields.io/badge/Docker-Ready-2496ED.svg?logo=docker&logoColor=white)

</div>

---

## Overview

Greenland-Longnecker Dose-Response Meta-Analysis Engine that estimates linear and log-linear trend slopes from correlated relative risks across non-zero exposure levels. Provides enterprise-grade security with zero-PHI outbound protection and tamper-evident HMAC-SHA256 audit trails.

Author: Dr. Abu Suraih Sakhri  
License: MIT

---

## Features

### Core Analytical Engine
- **`calculate_metrics()`**: Core domain algorithm for dose-response meta-analysis
- **`process_single()`**: Evaluate single case with configurable parameters
- **`process_batch()`**: Batch process CSV records with path traversal protection

### Enterprise Security
- **Zero-PHI Outbound Interceptor**: AST and regex inspection blocking SSNs, MRNs, phone numbers, and patient identifiers
- **Tamper-Evident HMAC-SHA256 Audit Trail**: Chained, cryptographically signed logs for every evaluation
- **Path Traversal Protection**: All file I/O operations are validated to prevent directory traversal attacks

### Multi-Agent Architecture
- **InvariantQCWorker**: Primary mathematical and protocol boundary auditor
- **SafetyEscalationWorker**: Safety boundary and emergency interlock detection
- **ProtocolConformanceWorker**: Spec conformance and anomaly triage

### API & Observability
- **FastAPI REST API**: OpenAPI 3.1 endpoints for task processing
- **Prometheus Metrics**: Operational telemetry export
- **WebSocket Telemetry**: Real-time event streaming

---

## Installation

```bash
# Clone the repository
git clone https://github.com/abusuraihsakhri/spline-dose-response-meta-engine.git
cd spline-dose-response-meta-engine

# Install dependencies
pip install fastapi uvicorn pydantic

# For development (includes pytest)
pip install -e ".[dev]"
```

---

## Usage

### Command Line Interface

#### Single Case Evaluation
```bash
python cli.py audit --task-id TASK-001 --target TARGET-01 --primary 28.5 --secondary 14.2
```

#### Batch Processing
```bash
python cli.py batch -i sample.csv -o results.csv
```

#### Interactive Chat
```bash
python cli.py chat "Explain the analysis parameters"
```

#### Verify Audit Trail
```bash
python cli.py verify-audit
```

#### Start API Server
```bash
python cli.py serve --host 127.0.0.1 --port 8000
```

### Direct Python API
```python
from doseresponse_meta import calculate_metrics, process_batch

# Single evaluation
result = calculate_metrics(v1=12.0, v2=4.0, v3=2.0)
print(result)
# {'tool': 'spline-dose-response-meta-engine', 'score': 14.0, ...}

# Batch processing
process_batch("input.csv", "output.csv")
```

### FastAPI Server
```bash
# Start the server
python cli.py serve

# Check health
curl http://localhost:8000/health

# Process a task
curl -X POST http://localhost:8000/api/audit \
  -H "Content-Type: application/json" \
  -d '{"task_id": "T1", "target_identifier": "K1", "primary_metric": 25.0}'

# Get Prometheus metrics
curl http://localhost:8000/metrics
```

---

## Input Data Schema

### CSV Batch Format
| Field | Description | Requirement |
|:------|:------------|:------------|
| `Patient_ID` | Patient identifier | Required |
| `v1` | Primary parameter | Required |
| `v2` | Secondary parameter | Required |
| `v3` | Tertiary parameter | Required |

### JSON API Payload
```json
{
  "task_id": "TASK-001",
  "target_identifier": "SPECIMEN-01",
  "primary_metric": 28.5,
  "secondary_metric": 14.2,
  "status_descriptor": "NOMINAL",
  "is_critical_flag": false
}
```

---

## Security Configuration

### Audit Secret Key
Set the `AUDIT_SECRET_KEY` environment variable for persistent audit integrity:
```bash
export AUDIT_SECRET_KEY=$(python -c "import secrets; print(secrets.token_hex(32))")
```

If not set, an ephemeral key will be generated (with a warning) for each session.

---

## Testing

```bash
# Run all tests
pytest -v

# Run with coverage
pytest -v --cov=agents --cov=doseresponse_meta

# Run high-throughput simulation
python simulator.py --tasks 1000
```

---

## Docker Deployment

```bash
docker build -t spline-dose-response-meta-engine .
docker run -p 8000:8000 spline-dose-response-meta-engine
```

---

## Project Structure

```
spline-dose-response-meta-engine/
├── agents/                 # Multi-agent architecture
│   ├── api.py             # FastAPI REST server
│   ├── base.py            # Security, PHI guard, audit trail
│   ├── learning.py        # Bayesian calibration engine
│   ├── llm_factory.py     # LLM provider abstraction
│   ├── metrics.py         # Prometheus metrics exporter
│   ├── models.py          # Pydantic data models
│   ├── streamer.py        # WebSocket telemetry
│   ├── supervisor.py      # Master orchestrator
│   └── workers.py         # Specialized worker agents
├── tests/                 # Test suite
├── web/                   # Operations console UI
├── cli.py                 # Command line interface
├── doseresponse_meta.py   # Core dose-response engine
├── enrichment.py          # Feature enrichment modules
├── simulator.py           # High-throughput simulator
├── pyproject.toml         # Project metadata and dependencies
└── Dockerfile             # Container configuration
```

---

## License

MIT License - see [LICENSE](LICENSE) for details.
