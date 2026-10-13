"""
Command Line Interface for Spline Dose Response Meta Engine.
"""
import argparse
import csv
import json
import os
import sys
from pathlib import Path
from agents.models import SystemTaskPayload
from agents.supervisor import SystemSupervisor
from agents.base import AuditLogger
from dose_response import analyze_json

supervisor = SystemSupervisor(model_provider="mock")


def _resolve_safe_path(path_str: str, must_exist: bool = False) -> Path:
    """Resolve a path safely, preventing directory traversal outside cwd."""
    cwd = Path.cwd().resolve()
    p = Path(path_str).resolve()
    try:
        p.relative_to(cwd)
    except ValueError:
        raise ValueError(f"Path traversal blocked: '{path_str}' must reside within the working directory.")
    if must_exist and not p.exists():
        raise FileNotFoundError(f"Input file not found: {path_str}")
    return p


def _parse_bool(value: str) -> bool:
    if isinstance(value, bool):
        return value
    val = str(value).strip().lower()
    if val in {"1", "true", "yes", "y"}:
        return True
    if val in {"0", "false", "no", "n", ""}:
        return False
    raise ValueError(f"Invalid boolean value: {value!r}")


def main(argv=None):
    parser = argparse.ArgumentParser(prog="spline-dose-response-meta-engine", description="Spline Dose Response Meta Engine")
    subparsers = parser.add_subparsers(dest="command", required=True)

    # Audit
    p_audit = subparsers.add_parser("audit", help="Run single task evaluation")
    p_audit.add_argument("--task-id", default="TASK-2026-001")
    p_audit.add_argument("--target", default="KEY-TARGET-01")
    p_audit.add_argument("--primary", type=float, default=28.5)
    p_audit.add_argument("--secondary", type=float, default=14.2)
    p_audit.add_argument("--critical", action="store_true")
    p_audit.add_argument("--status", default="DISCORDANT")

    # Chat
    p_chat = subparsers.add_parser("chat", help="System configuration query")
    p_chat.add_argument("query", nargs="+")

    # Batch
    p_batch = subparsers.add_parser("batch", help="Batch process CSV records")
    p_batch.add_argument("-i", "--input", required=True)
    p_batch.add_argument("-o", "--output", default="results.csv")

    # Covariance-aware linear dose-response analysis
    p_gls = subparsers.add_parser("dose-response", help="Fit two-stage linear GLS from JSON")
    p_gls.add_argument("-i", "--input", required=True, help="Input JSON containing studies and covariance")
    p_gls.add_argument("-o", "--output", help="Save results JSON; print to stdout if omitted")

    # Verify Audit
    subparsers.add_parser("verify-audit", help="Verify HMAC audit trail integrity")

    # Serve
    p_serve = subparsers.add_parser("serve", help="Launch FastAPI REST server")
    p_serve.add_argument("--host", default="127.0.0.1")
    p_serve.add_argument("--port", type=int, default=8000)

    args = parser.parse_args(argv)

    if args.command == "audit":
        payload = SystemTaskPayload(
            task_id=args.task_id,
            target_identifier=args.target,
            primary_metric=args.primary,
            secondary_metric=args.secondary,
            status_descriptor=args.status,
            is_critical_flag=args.critical,
        )
        dossier = supervisor.process_task(payload)
        print("=" * 80)
        print(f"  SPLINE DOSE RESPONSE META ENGINE")
        print(f"  Domain: Clinical & Biomedical AI | Standard: CAP / CLSI / ISO Standards")
        print(f"  Dossier ID: {dossier.dossier_id} | Urgency: [{dossier.overall_urgency.value}]")
        print("=" * 80)
        for a in dossier.alerts:
            print(f"\n  [{a.urgency.value}] from {a.origin_worker}:")
            print(f"  Summary: {a.summary}")
            print(f"  Details: {a.technical_details}")
            print(f"  Action:  {a.actionable_remediation}")
        print(f"\n  HMAC-SHA256 Audit Hash: {dossier.audit_hash}")
        print("=" * 80)
        return 0

    if args.command == "chat":
        ans = supervisor.query_supervisory_chat(" ".join(args.query))
        print(f"\n[Spline Dose Response Meta Engine Supervisor]:\n{ans}\n")
        return 0

    if args.command == "verify-audit":
        trail = AuditLogger.get_trail()
        valid = AuditLogger.verify_integrity()
        print(f"Audit Trail Blocks: {len(trail)} | Cryptographic Integrity Verified: {valid}")
        return 0

    if args.command == "dose-response":
        in_path = _resolve_safe_path(args.input, must_exist=True)
        output = analyze_json(in_path.read_text(encoding="utf-8"))
        if args.output:
            out_path = _resolve_safe_path(args.output)
            out_path.write_text(json.dumps(json.loads(output), indent=2) + "\n", encoding="utf-8")
            print(f"Saved analysis -> {out_path}")
        else:
            print(json.dumps(json.loads(output), indent=2))
        return 0

    if args.command == "batch":
        in_path = _resolve_safe_path(args.input, must_exist=True)
        out_path = _resolve_safe_path(args.output)
        with open(in_path, mode="r", encoding="utf-8-sig") as f:
            reader = csv.DictReader(f)
            fieldnames = list(reader.fieldnames or [])
            rows = list(reader)

        required = {"task_id", "target_identifier", "primary_metric"}
        if not required.issubset(fieldnames):
            raise ValueError(f"Batch CSV must include: {', '.join(sorted(required))}")
        out_fields = list(dict.fromkeys(fieldnames + ["overall_urgency", "integrity_status", "total_alerts", "audit_hash"]))
        out_rows = []
        for r in rows:
            payload = SystemTaskPayload(
                task_id=r["task_id"],
                target_identifier=r["target_identifier"],
                primary_metric=float(r["primary_metric"]),
                secondary_metric=float(r.get("secondary_metric", 5.0)),
                status_descriptor=r.get("status_descriptor", "NOMINAL"),
                is_critical_flag=_parse_bool(r.get("is_critical_flag", "false")),
            )
            dossier = supervisor.process_task(payload)
            row_dict = dict(r)
            row_dict["overall_urgency"] = dossier.overall_urgency.value
            row_dict["integrity_status"] = dossier.integrity_status.value
            row_dict["total_alerts"] = dossier.total_alerts
            row_dict["audit_hash"] = dossier.audit_hash
            out_rows.append(row_dict)

        with open(out_path, mode="w", encoding="utf-8", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=out_fields)
            writer.writeheader()
            writer.writerows(out_rows)
        print(f"Processed {len(out_rows)} records -> {out_path}")
        return 0

    if args.command == "serve":
        import uvicorn
        from agents.api import app
        print(f"Starting Spline Dose Response Meta Engine API server on http://{args.host}:{args.port}")
        uvicorn.run(app, host=args.host, port=args.port)
        return 0

    return 0


if __name__ == "__main__":
    sys.exit(main())
