from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import os


def _parse_int_env(name: str, default: int) -> int:
    raw = os.getenv(name)
    if raw is None:
        return default
    try:
        return int(raw)
    except ValueError:
        return default


def _parse_origins(raw: str) -> list[str]:
    items = [item.strip() for item in raw.split(",")]
    return [item for item in items if item]


@dataclass(frozen=True)
class ControlPlaneSettings:
    repo_root: Path
    workspace_root: Path
    projects_config_path: Path
    clownpeanuts_api_base: str
    clownpeanuts_api_token: str
    clownpeanuts_ws_events_url: str
    clownpeanuts_ws_theater_url: str
    clownpeanuts_ws_token: str
    pingting_repo_path: Path
    pingting_status_path: Path
    pingting_config_path: Path
    pingting_python_bin: str | None
    pingting_status_max_age_seconds: int
    pingting_command_timeout_seconds: int
    orchestration_state_path: Path
    orchestration_action_timeout_seconds: int
    bootstrap_script_path: Path
    smoke_script_path: Path
    update_script_path: Path
    cors_allow_origins: list[str]
    api_auth_token: str


def load_settings() -> ControlPlaneSettings:
    repo_root = Path(__file__).resolve().parents[3]
    workspace_root = Path(os.getenv("CONTROLPLANE_WORKSPACE_ROOT", "/Users/matt/code")).expanduser()
    pingting_repo = Path(os.getenv("PINGTING_REPO_PATH", str(workspace_root / "pingting"))).expanduser()

    return ControlPlaneSettings(
        repo_root=repo_root,
        workspace_root=workspace_root,
        projects_config_path=Path(
            os.getenv("CONTROLPLANE_PROJECTS_CONFIG", str(repo_root / "config" / "projects.yaml"))
        ).expanduser(),
        clownpeanuts_api_base=os.getenv("CLOWNPEANUTS_API_BASE", "http://127.0.0.1:8099").strip(),
        clownpeanuts_api_token=os.getenv("CLOWNPEANUTS_API_TOKEN", "").strip(),
        clownpeanuts_ws_events_url=os.getenv(
            "CLOWNPEANUTS_WS_EVENTS_URL",
            "ws://127.0.0.1:8099/ws/events",
        ).strip(),
        clownpeanuts_ws_theater_url=os.getenv(
            "CLOWNPEANUTS_WS_THEATER_URL",
            "ws://127.0.0.1:8099/ws/theater/live",
        ).strip(),
        clownpeanuts_ws_token=(
            os.getenv("CLOWNPEANUTS_WS_TOKEN", "").strip()
            or os.getenv("CLOWNPEANUTS_API_TOKEN", "").strip()
        ),
        pingting_repo_path=pingting_repo,
        pingting_status_path=Path(
            os.getenv("PINGTING_STATUS_PATH", str(pingting_repo / "data" / "status.json"))
        ).expanduser(),
        pingting_config_path=Path(
            os.getenv("PINGTING_CONFIG_PATH", str(pingting_repo / "config" / "pingting.yaml"))
        ).expanduser(),
        pingting_python_bin=(os.getenv("PINGTING_PYTHON_BIN") or "").strip() or None,
        pingting_status_max_age_seconds=_parse_int_env("PINGTING_STATUS_MAX_AGE_SECONDS", 120),
        pingting_command_timeout_seconds=_parse_int_env("PINGTING_STATUS_TIMEOUT_SECONDS", 20),
        orchestration_state_path=Path(
            os.getenv(
                "CONTROLPANE_ACTION_STATE_PATH",
                str(repo_root / "data" / "controlplane" / "actions-state.json"),
            )
        ).expanduser(),
        orchestration_action_timeout_seconds=_parse_int_env("CONTROLPANE_ACTION_TIMEOUT_SECONDS", 900),
        bootstrap_script_path=Path(
            os.getenv("CONTROLPANE_BOOTSTRAP_SCRIPT_PATH", str(repo_root / "scripts" / "bootstrap_repos.sh"))
        ).expanduser(),
        smoke_script_path=Path(
            os.getenv("CONTROLPANE_SMOKE_SCRIPT_PATH", str(repo_root / "harness" / "smoke.sh"))
        ).expanduser(),
        update_script_path=Path(
            os.getenv("CONTROLPANE_UPDATE_SCRIPT_PATH", str(repo_root / "scripts" / "update_repos.sh"))
        ).expanduser(),
        cors_allow_origins=_parse_origins(
            os.getenv(
                "CONTROLPANE_CORS_ALLOW_ORIGINS",
                "http://127.0.0.1:4317,http://localhost:4317,http://127.0.0.1:3001,http://localhost:3001,http://127.0.0.1:3000,http://localhost:3000",
            )
        ),
        api_auth_token=os.getenv("CONTROLPANE_API_AUTH_TOKEN", "").strip(),
    )
