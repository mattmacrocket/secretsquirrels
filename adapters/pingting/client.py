from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import json
import shutil
import sqlite3
import subprocess
import time
from typing import Any


@dataclass(frozen=True)
class PingTingStatusSnapshot:
    payload: dict[str, Any]
    source: str
    age_seconds: float | None


def _safe_int(value: Any) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return 0


def _extract_json_payload(raw: str) -> dict[str, Any]:
    text = raw.strip()
    if not text:
        raise ValueError("empty status payload")
    try:
        payload = json.loads(text)
    except json.JSONDecodeError:
        start = text.find("{")
        end = text.rfind("}")
        if start == -1 or end <= start:
            raise
        payload = json.loads(text[start : end + 1])
    if not isinstance(payload, dict):
        raise ValueError("status payload must be a JSON object")
    return payload


def _safe_json_loads(raw: Any, default: Any) -> Any:
    if not isinstance(raw, str) or raw.strip() == "":
        return default
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return default


class PingTingAdapter:
    """Loads PingTing status from status.json or CLI fallback."""

    def __init__(
        self,
        *,
        repo_path: Path,
        status_path: Path,
        config_path: Path,
        max_age_seconds: int = 120,
        python_bin: str | None = None,
        command_timeout_seconds: int = 20,
    ) -> None:
        self.repo_path = repo_path
        self.status_path = status_path
        self.config_path = config_path
        self.max_age_seconds = max_age_seconds
        self.python_bin = python_bin
        self.command_timeout_seconds = command_timeout_seconds

    def _resolve_python_bin(self) -> str:
        if self.python_bin:
            return self.python_bin

        venv_python = self.repo_path / ".venv" / "bin" / "python"
        if venv_python.exists():
            return str(venv_python)

        for candidate in ("python3", "python"):
            if shutil.which(candidate):
                return candidate

        return "python3"

    def _read_status_file(self) -> PingTingStatusSnapshot | None:
        if not self.status_path.is_file():
            return None

        try:
            raw = self.status_path.read_text(encoding="utf-8")
            payload = _extract_json_payload(raw)
        except Exception:
            return None

        try:
            mtime = self.status_path.stat().st_mtime
            age_seconds = max(0.0, time.time() - mtime)
        except OSError:
            age_seconds = None

        return PingTingStatusSnapshot(payload=payload, source="file", age_seconds=age_seconds)

    def _run_status_cli(self) -> PingTingStatusSnapshot:
        cmd = [
            self._resolve_python_bin(),
            "-m",
            "pingting",
            "--config",
            str(self.config_path),
            "status",
            "--json",
        ]

        completed = subprocess.run(
            cmd,
            cwd=str(self.repo_path),
            capture_output=True,
            text=True,
            timeout=self.command_timeout_seconds,
            check=False,
        )

        if completed.returncode != 0:
            stderr = (completed.stderr or "").strip()
            stdout = (completed.stdout or "").strip()
            detail = stderr or stdout or f"exit={completed.returncode}"
            raise RuntimeError(f"pingting status command failed: {detail}")

        payload = _extract_json_payload(completed.stdout)
        return PingTingStatusSnapshot(payload=payload, source="cli", age_seconds=0.0)

    def _highlights(self, payload: dict[str, Any]) -> dict[str, Any]:
        findings_24h = payload.get("findings_24h")
        if not isinstance(findings_24h, dict):
            findings_24h = {}

        learning = payload.get("learning")
        if not isinstance(learning, dict):
            learning = {}

        agent_status = payload.get("agent_status")
        if not isinstance(agent_status, dict):
            agent_status = {}

        enabled_agents = sorted(
            name
            for name, details in agent_status.items()
            if isinstance(details, dict) and bool(details.get("enabled"))
        )

        alert_channels = payload.get("alert_channels")
        if not isinstance(alert_channels, list):
            alert_channels = []

        return {
            "findings_total": _safe_int(payload.get("findings_total")),
            "findings_pending": _safe_int(payload.get("findings_pending")),
            "devices_total": _safe_int(payload.get("devices_total")),
            "devices_unknown": _safe_int(payload.get("devices_unknown")),
            "alert_delivery_failures_24h": _safe_int(payload.get("alert_delivery_failures_24h")),
            "learning_status": str(learning.get("status") or "unknown"),
            "enabled_agents": enabled_agents,
            "alert_channel_count": len(alert_channels),
            "findings_24h": {
                "critical": _safe_int(findings_24h.get("critical")),
                "high": _safe_int(findings_24h.get("high")),
                "medium": _safe_int(findings_24h.get("medium")),
                "low": _safe_int(findings_24h.get("low")),
            },
        }

    def load_recent_findings(
        self,
        *,
        limit: int = 30,
        severity: str | None = None,
        include_acknowledged: bool = True,
        include_learning: bool = True,
    ) -> dict[str, Any]:
        normalized_limit = max(1, min(int(limit), 200))
        where_clauses = ["false_positive = 0"]
        params: list[Any] = []

        normalized_severity = (severity or "").strip().lower()
        if normalized_severity:
            if normalized_severity not in {"low", "medium", "high", "critical"}:
                return {
                    "ok": False,
                    "count": 0,
                    "findings": [],
                    "errors": [f"invalid severity: {normalized_severity}"],
                }
            where_clauses.append("severity = ?")
            params.append(normalized_severity)

        if not include_acknowledged:
            where_clauses.append("acknowledged = 0")
        if not include_learning:
            where_clauses.append("during_learning = 0")

        query = (
            "SELECT id, created_at, severity, agent, title, description, device_ip, device_mac, "
            "acknowledged, false_positive, during_learning "
            "FROM findings "
            f"WHERE {' AND '.join(where_clauses)} "
            "ORDER BY created_at DESC LIMIT ?"
        )
        params.append(normalized_limit)

        db_path = self.repo_path / "data" / "pingting.db"
        if not db_path.is_file():
            return {
                "ok": False,
                "count": 0,
                "findings": [],
                "errors": [f"missing database file: {db_path}"],
            }

        connection: sqlite3.Connection | None = None
        try:
            connection = sqlite3.connect(str(db_path))
            connection.row_factory = sqlite3.Row
            cursor = connection.execute(query, tuple(params))
            rows = cursor.fetchall()
        except Exception as exc:
            return {
                "ok": False,
                "count": 0,
                "findings": [],
                "errors": [f"failed reading pingting findings: {exc}"],
            }
        finally:
            try:
                if connection is not None:
                    connection.close()
            except Exception:
                pass

        findings: list[dict[str, Any]] = []
        for row in rows:
            findings.append(
                {
                    "id": int(row["id"]),
                    "created_at": str(row["created_at"]),
                    "severity": str(row["severity"]),
                    "agent": str(row["agent"]),
                    "title": str(row["title"]),
                    "description": str(row["description"] or ""),
                    "device_ip": str(row["device_ip"] or ""),
                    "device_mac": str(row["device_mac"] or ""),
                    "acknowledged": bool(row["acknowledged"]),
                    "false_positive": bool(row["false_positive"]),
                    "during_learning": bool(row["during_learning"]),
                }
            )

        return {
            "ok": True,
            "count": len(findings),
            "limit": normalized_limit,
            "findings": findings,
            "errors": [],
        }

    def load_recent_agent_runs(
        self,
        *,
        limit: int = 30,
        agent: str | None = None,
        status: str | None = None,
    ) -> dict[str, Any]:
        normalized_limit = max(1, min(int(limit), 200))
        where_clauses: list[str] = []
        params: list[Any] = []

        normalized_agent = (agent or "").strip()
        if normalized_agent:
            where_clauses.append("agent = ?")
            params.append(normalized_agent)

        normalized_status = (status or "").strip().lower()
        if normalized_status:
            where_clauses.append("status = ?")
            params.append(normalized_status)

        query = (
            "SELECT id, agent, started_at, completed_at, status, findings_count, raw_data_summary, error_message "
            "FROM agent_runs "
        )
        if where_clauses:
            query += f"WHERE {' AND '.join(where_clauses)} "
        query += "ORDER BY started_at DESC LIMIT ?"
        params.append(normalized_limit)

        db_path = self.repo_path / "data" / "pingting.db"
        if not db_path.is_file():
            return {
                "ok": False,
                "count": 0,
                "runs": [],
                "errors": [f"missing database file: {db_path}"],
            }

        connection: sqlite3.Connection | None = None
        try:
            connection = sqlite3.connect(str(db_path))
            connection.row_factory = sqlite3.Row
            cursor = connection.execute(query, tuple(params))
            rows = cursor.fetchall()
        except Exception as exc:
            return {
                "ok": False,
                "count": 0,
                "runs": [],
                "errors": [f"failed reading pingting agent runs: {exc}"],
            }
        finally:
            try:
                if connection is not None:
                    connection.close()
            except Exception:
                pass

        runs: list[dict[str, Any]] = []
        for row in rows:
            runs.append(
                {
                    "id": int(row["id"]),
                    "agent": str(row["agent"]),
                    "started_at": str(row["started_at"]),
                    "completed_at": str(row["completed_at"] or ""),
                    "status": str(row["status"]),
                    "findings_count": _safe_int(row["findings_count"]),
                    "raw_data_summary": _safe_json_loads(row["raw_data_summary"], default={}),
                    "error_message": str(row["error_message"] or ""),
                }
            )

        return {
            "ok": True,
            "count": len(runs),
            "limit": normalized_limit,
            "runs": runs,
            "errors": [],
        }

    def load_status_summary(
        self,
        *,
        refresh_if_stale: bool = True,
        force_cli_refresh: bool = False,
    ) -> dict[str, Any]:
        errors: list[str] = []
        snapshot = self._read_status_file()

        stale = snapshot is not None and snapshot.age_seconds is not None and snapshot.age_seconds > self.max_age_seconds

        if force_cli_refresh:
            try:
                snapshot = self._run_status_cli()
            except Exception as exc:
                errors.append(str(exc))
                if snapshot is None:
                    snapshot = self._read_status_file()
        elif snapshot is None:
            try:
                snapshot = self._run_status_cli()
            except Exception as exc:
                errors.append(str(exc))
        elif stale and refresh_if_stale:
            try:
                snapshot = self._run_status_cli()
            except Exception as exc:
                errors.append(str(exc))
                snapshot = PingTingStatusSnapshot(
                    payload=snapshot.payload,
                    source="file_stale",
                    age_seconds=snapshot.age_seconds,
                )

        if snapshot is None:
            return {
                "ok": False,
                "source": "unavailable",
                "stale": True,
                "status_age_seconds": None,
                "errors": errors or ["unable to load pingting status"],
                "highlights": {},
                "snapshot": {},
            }

        computed_stale = snapshot.age_seconds is not None and snapshot.age_seconds > self.max_age_seconds
        return {
            "ok": True,
            "source": snapshot.source,
            "stale": computed_stale,
            "status_age_seconds": snapshot.age_seconds,
            "errors": errors,
            "highlights": self._highlights(snapshot.payload),
            "snapshot": snapshot.payload,
        }
