"""API auth, sanitization and CSV parsing regressions."""
import json

from fastapi.testclient import TestClient
from agents.api import app
from cli import main, _parse_bool
from agents.models import SystemTaskPayload

client = TestClient(app)


def test_api_requires_configured_secret(monkeypatch):
    monkeypatch.delenv("SPLINE_API_KEY", raising=False)
    assert client.post("/api/audit", json={"task_id":"T1","target_identifier":"K1","primary_metric":5}).status_code == 503
    assert client.get("/api/audit/logs").status_code == 503
    assert client.get("/health").status_code == 200


def test_api_rejects_missing_and_invalid_key(monkeypatch):
    monkeypatch.setenv("SPLINE_API_KEY", "a" * 32)
    payload={"task_id":"T1","target_identifier":"K1","primary_metric":5}
    assert client.post("/api/audit",json=payload).status_code == 401
    assert client.post("/api/audit",json=payload,headers={"X-API-Key":"wrong"}).status_code == 401


def test_api_valid_key_and_phi_rejection(monkeypatch):
    monkeypatch.setenv("SPLINE_API_KEY", "a" * 32)
    h={"X-API-Key":"a" * 32}
    payload={"task_id":"T1","target_identifier":"K1","primary_metric":5}
    assert client.post("/api/audit",json=payload,headers=h).status_code == 200
    payload["attributes"]={"nested":{"patient":"MRN-12345678"}}
    response=client.post("/api/audit",json=payload,headers=h)
    assert response.status_code == 422
    assert "MRN" not in response.text


def test_nonfinite_task_rejected():
    import pytest
    from pydantic import ValidationError
    with pytest.raises(ValidationError):
        SystemTaskPayload(task_id="T",target_identifier="K",primary_metric=float("nan"))


def test_batch_false_is_false(tmp_path,monkeypatch):
    monkeypatch.chdir(tmp_path)
    (tmp_path/"input.csv").write_text(
      "task_id,target_identifier,primary_metric,is_critical_flag\\n"
      "T-1,K-1,2,False\\n",encoding="utf-8"
    )
    assert main(["batch","-i","input.csv","-o","output.csv"]) == 0
    result=(tmp_path/"output.csv").read_text()
    assert "CRITICAL_STAT_PANIC" not in result
    assert _parse_bool("False") is False
    assert _parse_bool("true") is True
