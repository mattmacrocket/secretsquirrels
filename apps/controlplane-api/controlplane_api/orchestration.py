from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
import json
import subprocess
from typing import Any

import yaml

from .config import ControlPlaneSettings


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _load_yaml(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    raw = path.read_text(encoding="utf-8")
    payload = yaml.safe_load(raw)
    if not isinstance(payload, dict):
        return {}
    return payload


def _git_output(path: Path, *args: str) -> str:
    completed = subprocess.run(
        ["git", "-C", str(path), *args],
        capture_output=True,
        text=True,
        check=False,
    )
    if completed.returncode != 0:
        raise RuntimeError((completed.stderr or completed.stdout or "git command failed").strip())
    return (completed.stdout or "").strip()


def repo_status(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {"present": False, "path": str(path), "git": False}
    if not (path / ".git").exists():
        return {"present": True, "path": str(path), "git": False}

    try:
        branch = _git_output(path, "rev-parse", "--abbrev-ref", "HEAD")
        commit = _git_output(path, "rev-parse", "HEAD")
        committed_at = _git_output(path, "show", "-s", "--format=%cI", "HEAD")
        dirty = bool(_git_output(path, "status", "--porcelain"))
        return {
            "present": True,
            "path": str(path),
            "git": True,
            "branch": branch,
            "commit": commit,
            "committed_at": committed_at,
            "dirty": dirty,
        }
    except Exception as exc:
        return {
            "present": True,
            "path": str(path),
            "git": True,
            "error": str(exc),
        }


def _load_action_state(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {"bootstrap": None, "smoke": None, "update": None}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {"bootstrap": None, "smoke": None, "update": None}
    if not isinstance(payload, dict):
        return {"bootstrap": None, "smoke": None, "update": None}
    return {
        "bootstrap": payload.get("bootstrap"),
        "smoke": payload.get("smoke"),
        "update": payload.get("update"),
    }


def _save_action_state(path: Path, state: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(state, indent=2), encoding="utf-8")


def _trim_output(stdout: str, stderr: str, *, limit_chars: int = 12000) -> str:
    combined = "\n".join(part for part in (stdout.strip(), stderr.strip()) if part)
    if len(combined) <= limit_chars:
        return combined
    return f"{combined[:limit_chars]}\n... (truncated)"


def run_action(
    *,
    action_name: str,
    script_path: Path,
    base_dir: Path,
    timeout_seconds: int,
    state_path: Path,
) -> dict[str, Any]:
    started_at = _now_iso()
    command = ["bash", str(script_path), str(base_dir)]

    if not script_path.is_file():
        result = {
            "action": action_name,
            "ok": False,
            "started_at": started_at,
            "finished_at": _now_iso(),
            "exit_code": 127,
            "command": command,
            "output": f"missing script: {script_path}",
        }
    else:
        try:
            completed = subprocess.run(
                command,
                cwd=str(script_path.parent.parent),
                capture_output=True,
                text=True,
                timeout=timeout_seconds,
                check=False,
            )
            result = {
                "action": action_name,
                "ok": completed.returncode == 0,
                "started_at": started_at,
                "finished_at": _now_iso(),
                "exit_code": completed.returncode,
                "command": command,
                "output": _trim_output(completed.stdout, completed.stderr),
            }
        except subprocess.TimeoutExpired as exc:
            result = {
                "action": action_name,
                "ok": False,
                "started_at": started_at,
                "finished_at": _now_iso(),
                "exit_code": 124,
                "command": command,
                "output": f"action timed out after {timeout_seconds}s: {exc}",
            }

    state = _load_action_state(state_path)
    state[action_name] = result
    _save_action_state(state_path, state)
    return result


def build_projects_summary(settings: ControlPlaneSettings) -> list[dict[str, Any]]:
    projects_payload = _load_yaml(settings.projects_config_path)
    raw_projects = projects_payload.get("projects")
    if not isinstance(raw_projects, list):
        return []

    output: list[dict[str, Any]] = []
    for entry in raw_projects:
        if not isinstance(entry, dict):
            continue
        name = str(entry.get("name") or "").strip()
        if not name:
            continue

        local_path_raw = entry.get("local_path")
        if isinstance(local_path_raw, str) and local_path_raw.strip():
            local_path = Path(local_path_raw).expanduser()
        else:
            local_path = settings.workspace_root / name

        output.append(
            {
                "name": name,
                "role": str(entry.get("role") or ""),
                "repo": str(entry.get("repo") or ""),
                "verification_key": str(entry.get("verification_key") or ""),
                "dashboard": entry.get("dashboard") if isinstance(entry.get("dashboard"), dict) else {},
                "capabilities": entry.get("capabilities") if isinstance(entry.get("capabilities"), dict) else {},
                "local_path": str(local_path),
                "status": repo_status(local_path),
            }
        )

    return output


def build_orchestration_summary(settings: ControlPlaneSettings) -> dict[str, Any]:
    projects = build_projects_summary(settings)
    dirty_repos = [project["name"] for project in projects if bool(project.get("status", {}).get("dirty"))]
    missing_repos = [project["name"] for project in projects if not bool(project.get("status", {}).get("present"))]
    action_state = _load_action_state(settings.orchestration_state_path)

    return {
        "generated_at": _now_iso(),
        "projects": projects,
        "project_count": len(projects),
        "dirty_repo_count": len(dirty_repos),
        "dirty_repos": dirty_repos,
        "missing_repo_count": len(missing_repos),
        "missing_repos": missing_repos,
        "last_actions": action_state,
        "commands": {
            "bootstrap": ["bash", str(settings.bootstrap_script_path), str(settings.workspace_root)],
            "smoke": ["bash", str(settings.smoke_script_path), str(settings.workspace_root)],
            "update": ["bash", str(settings.update_script_path), str(settings.workspace_root)],
        },
    }
