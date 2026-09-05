"""
Security and Path Traversal Protection Tests for spline-dose-response-meta-engine.
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import pytest
from cli import _resolve_safe_path as cli_resolve_safe_path
from doseresponse_meta import _resolve_safe_path as doseresponse_resolve_safe_path, process_batch, calculate_metrics
from agents.base import PHIGuard, SecurityException, AuditTrail


class TestPathTraversalProtection:
    """Tests for path traversal prevention in CLI and batch processing."""

    def test_safe_path_within_cwd(self, tmp_path, monkeypatch):
        """Valid paths within working directory should resolve correctly."""
        monkeypatch.chdir(tmp_path)
        test_file = tmp_path / "test.csv"
        test_file.write_text("data")
        result = cli_resolve_safe_path("test.csv", must_exist=True)
        assert result == test_file.resolve()

    def test_safe_path_traversal_blocked(self, tmp_path, monkeypatch):
        """Paths outside working directory should be blocked."""
        monkeypatch.chdir(tmp_path)
        with pytest.raises(ValueError, match="Path traversal blocked"):
            cli_resolve_safe_path("../etc/passwd")

    def test_safe_path_absolute_traversal_blocked(self, tmp_path, monkeypatch):
        """Absolute paths outside working directory should be blocked."""
        monkeypatch.chdir(tmp_path)
        with pytest.raises(ValueError, match="Path traversal blocked"):
            cli_resolve_safe_path("/etc/passwd")

    def test_safe_path_nonexistent_input_blocked(self, tmp_path, monkeypatch):
        """Non-existent input files should raise FileNotFoundError."""
        monkeypatch.chdir(tmp_path)
        with pytest.raises(FileNotFoundError):
            cli_resolve_safe_path("nonexistent.csv", must_exist=True)

    def test_doseresponse_safe_path_traversal_blocked(self, tmp_path, monkeypatch):
        """Path traversal protection in doseresponse_meta should block traversal."""
        monkeypatch.chdir(tmp_path)
        with pytest.raises(ValueError, match="Path traversal blocked"):
            doseresponse_resolve_safe_path("../../etc/passwd")

    def test_batch_processing_path_traversal_blocked(self, tmp_path, monkeypatch):
        """Batch processing should reject traversal paths."""
        monkeypatch.chdir(tmp_path)
        with pytest.raises(ValueError, match="Path traversal blocked"):
            process_batch("../evil.csv", "out.csv")

    def test_batch_processing_output_traversal_blocked(self, tmp_path, monkeypatch):
        """Batch processing should reject traversal output paths."""
        monkeypatch.chdir(tmp_path)
        input_file = tmp_path / "in.csv"
        input_file.write_text("Patient_ID,v1,v2,v3\nPT-001,1.0,2.0,3.0\n")
        with pytest.raises(ValueError, match="Path traversal blocked"):
            process_batch(str(input_file), "../evil/out.csv")


class TestPHIGuardEnforcement:
    """Tests for PHI detection and blocking."""

    def test_mrn_detected(self):
        with pytest.raises(SecurityException):
            PHIGuard.assert_no_phi("Patient MRN-12345678")

    def test_ssn_detected(self):
        with pytest.raises(SecurityException):
            PHIGuard.assert_no_phi("SSN: 123-45-6789")

    def test_phone_detected(self):
        with pytest.raises(SecurityException):
            PHIGuard.assert_no_phi("Call 555-123-4567")

    def test_email_detected(self):
        with pytest.raises(SecurityException):
            PHIGuard.assert_no_phi("Email: patient@example.com")

    def test_clean_text_passes(self):
        PHIGuard.assert_no_phi("Analytical assay specimen KEY-001 optimal")

    def test_redact_phi(self):
        result = PHIGuard.redact_phi("Patient MRN-12345678 has SSN 123-45-6789")
        assert "REDACTED_IDENTIFIER" in result
        assert "MRN" not in result
        assert "123-45-6789" not in result


class TestAuditTrailIntegrity:
    """Tests for HMAC-SHA256 audit trail."""

    def test_audit_trail_chaining(self):
        trail = AuditTrail(secret_key="test-key-123")
        trail.log("actor1", "tier1", "EVENT_A", {"data": "value1"})
        trail.log("actor2", "tier2", "EVENT_B", {"data": "value2"})
        assert trail.verify_integrity() is True
        assert len(trail.get_trail()) == 2

    def test_audit_trail_tamper_detection(self):
        trail = AuditTrail(secret_key="test-key-456")
        trail.log("actor1", "tier1", "EVENT_A", {"data": "value1"})
        # Tamper with the trail
        trail.logs[0]["current_hash"] = "tampered_hash"
        assert trail.verify_integrity() is False


class TestCalculateMetrics:
    """Tests for core dose-response calculation."""

    def test_basic_calculation(self):
        result = calculate_metrics(v1=10.0, v2=5.0)
        assert result["score"] == 12.5  # 10 + 5/2
        assert result["classification"] in ["Low / Standard", "Moderate / Intermediate", "High / Severe"]

    def test_single_value(self):
        result = calculate_metrics(v1=8.0)
        assert result["score"] == 8.0
        assert result["classification"] == "Low / Standard"

    def test_moderate_classification(self):
        result = calculate_metrics(v1=15.0)
        assert result["classification"] == "Moderate / Intermediate"

    def test_high_classification(self):
        result = calculate_metrics(v1=30.0)
        assert result["classification"] == "High / Severe"

    def test_string_values_ignored(self):
        result = calculate_metrics(v1=10.0, label="test")
        assert result["score"] == 10.0

    def test_empty_input(self):
        result = calculate_metrics()
        assert result["score"] == 1.0  # Default primary_val
