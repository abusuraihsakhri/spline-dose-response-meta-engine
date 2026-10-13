"""Authenticated FastAPI adapter for the legacy deterministic task-audit workflow.

The scientific linear dose-response model is separately available in dose_response.py.
"""
import hmac
import os

from fastapi import Depends, FastAPI, Header, HTTPException, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from .base import AuditLogger, SecurityException
from .models import SystemTaskPayload
from .supervisor import SystemSupervisor

supervisor = SystemSupervisor(model_provider="mock")
app = FastAPI(
    title="Spline Dose Response Meta Engine API",
    description="Legacy deterministic rules engine; not a clinical decision support service",
    version="3.1.0",
)


def require_api_key(x_api_key: str | None = Header(default=None)):
    expected = os.environ.get("SPLINE_API_KEY")
    if not expected or len(expected) < 24:
        raise HTTPException(status_code=503, detail="API authentication is not configured")
    if not x_api_key or not hmac.compare_digest(expected, x_api_key):
        raise HTTPException(status_code=401, detail="Invalid or missing API key")


@app.exception_handler(SecurityException)
async def security_exception_handler(request: Request, exc: SecurityException):
    return JSONResponse(status_code=422, content={"detail": "Potential identifier detected; request rejected"})


class ChatRequest(BaseModel):
    query: str


@app.get("/health")
def health():
    return {"status": "HEALTHY", "service": "spline-dose-response-meta-engine",
            "version": "3.1.0", "clinical_validation": False}


@app.get("/metrics", dependencies=[Depends(require_api_key)])
def metrics():
    return {
        "dossiers_processed_total": len(supervisor.dossier_registry),
        "audit_blocks_total": len(AuditLogger.get_trail()),
    }


@app.post("/api/audit", dependencies=[Depends(require_api_key)])
def api_audit(payload: SystemTaskPayload):
    return supervisor.process_task(payload).to_dict()


@app.post("/api/chat", dependencies=[Depends(require_api_key)])
def api_chat(req: ChatRequest):
    return {"response": supervisor.query_supervisory_chat(req.query)}


@app.get("/api/audit/logs", dependencies=[Depends(require_api_key)])
def api_audit_logs():
    return {"audit_trail": AuditLogger.get_trail(),
            "verified": AuditLogger.verify_integrity()}
