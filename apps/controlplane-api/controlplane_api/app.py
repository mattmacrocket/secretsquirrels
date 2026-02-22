from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from pathlib import Path
import sys
from typing import Any
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from fastapi import FastAPI, HTTPException, Query, Request, Response, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import websockets
from websockets.exceptions import ConnectionClosed

REPO_ROOT = Path(__file__).resolve().parents[3]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from adapters.clownpeanuts import ClownPeanutsAdapter
from adapters.pingting import PingTingAdapter
from .config import ControlPlaneSettings, load_settings
from .orchestration import build_orchestration_summary, run_action


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _extract_bearer_token(raw_value: str | None) -> str | None:
    if raw_value is None:
        return None
    value = raw_value.strip()
    if not value:
        return None
    parts = value.split()
    if len(parts) != 2 or parts[0].lower() != "bearer":
        return None
    token = parts[1].strip()
    return token or None


def _resolve_request_token(request: Request) -> str | None:
    bearer = _extract_bearer_token(request.headers.get("authorization"))
    if bearer:
        return bearer
    api_key = request.headers.get("x-api-key")
    if api_key:
        token = api_key.strip()
        if token:
            return token
    token_query = request.query_params.get("token")
    if token_query:
        token = token_query.strip()
        if token:
            return token
    return None


def _resolve_websocket_token(websocket: WebSocket) -> str | None:
    bearer = _extract_bearer_token(websocket.headers.get("authorization"))
    if bearer:
        return bearer
    api_key = websocket.headers.get("x-api-key")
    if api_key:
        token = api_key.strip()
        if token:
            return token
    for query_key in ("token", "api_key", "access_token"):
        token_query = websocket.query_params.get(query_key)
        if token_query:
            token = token_query.strip()
            if token:
                return token
    return None


def _with_token_query(url: str, token: str) -> str:
    if not token:
        return url
    split = urlsplit(url)
    query = dict(parse_qsl(split.query, keep_blank_values=True))
    if any(key in query for key in ("token", "api_key", "access_token")):
        return url
    query["token"] = token
    return urlunsplit((split.scheme, split.netloc, split.path, urlencode(query), split.fragment))


def create_app(settings: ControlPlaneSettings | None = None) -> FastAPI:
    settings = settings or load_settings()
    clownpeanuts = ClownPeanutsAdapter(
        base_url=settings.clownpeanuts_api_base,
        api_token=settings.clownpeanuts_api_token,
    )
    pingting = PingTingAdapter(
        repo_path=settings.pingting_repo_path,
        status_path=settings.pingting_status_path,
        config_path=settings.pingting_config_path,
        python_bin=settings.pingting_python_bin,
        max_age_seconds=settings.pingting_status_max_age_seconds,
        command_timeout_seconds=settings.pingting_command_timeout_seconds,
    )

    app = FastAPI(
        title="SquirrelOps Control Plane API",
        version="0.1.0",
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
    )

    if settings.cors_allow_origins:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=settings.cors_allow_origins,
            allow_credentials=False,
            allow_methods=["*"],
            allow_headers=["*"],
        )

    async def relay_deception_websocket(*, websocket: WebSocket, upstream_url: str) -> None:
        if settings.api_auth_token and _resolve_websocket_token(websocket) != settings.api_auth_token:
            await websocket.close(code=4401, reason="authentication required")
            return

        await websocket.accept()
        upstream_token = settings.clownpeanuts_ws_token
        resolved_upstream_url = _with_token_query(upstream_url, upstream_token)
        upstream_headers: dict[str, str] = {}
        if upstream_token:
            upstream_headers["Authorization"] = f"Bearer {upstream_token}"

        try:
            async with websockets.connect(
                resolved_upstream_url,
                additional_headers=upstream_headers or None,
            ) as upstream:
                while True:
                    message = await upstream.recv()
                    if isinstance(message, bytes):
                        await websocket.send_bytes(message)
                    else:
                        await websocket.send_text(message)
        except WebSocketDisconnect:
            return
        except ConnectionClosed:
            return
        except Exception:
            try:
                await websocket.close(code=1011, reason="upstream websocket unavailable")
            except Exception:
                return

    @app.middleware("http")
    async def auth_middleware(request: Request, call_next: Any) -> Response:
        if not settings.api_auth_token:
            return await call_next(request)
        if request.method.upper() == "OPTIONS":
            return await call_next(request)
        if request.url.path == "/health":
            return await call_next(request)
        token = _resolve_request_token(request)
        if token != settings.api_auth_token:
            return JSONResponse(
                status_code=401,
                content={"detail": "authentication required"},
                headers={"WWW-Authenticate": "Bearer"},
            )
        return await call_next(request)

    @app.get("/health")
    def health() -> dict[str, Any]:
        return {
            "status": "ok",
            "service": "controlplane-api",
            "generated_at": _now_iso(),
        }

    @app.get("/overview/summary")
    async def overview_summary() -> dict[str, Any]:
        deception: dict[str, Any]
        try:
            deception_status = await clownpeanuts.status()
            deception = {"ok": True, "status": deception_status}
        except Exception as exc:
            deception = {"ok": False, "status": {}, "error": str(exc)}

        sentry = pingting.load_status_summary(refresh_if_stale=True)
        sentry_findings = pingting.load_recent_findings(
            limit=5,
            include_acknowledged=False,
            include_learning=True,
        )
        if not bool(sentry_findings.get("ok")):
            sentry_findings = {
                "ok": False,
                "count": 0,
                "findings": [],
                "errors": sentry_findings.get("errors", []),
            }
        orchestration = build_orchestration_summary(settings)

        overall_ok = bool(deception.get("ok")) and bool(sentry.get("ok")) and orchestration.get("missing_repo_count", 0) == 0

        return {
            "generated_at": _now_iso(),
            "overall_ok": overall_ok,
            "deception": deception,
            "sentry": sentry,
            "sentry_findings": sentry_findings,
            "orchestration": orchestration,
        }

    @app.get("/sentry/summary")
    def sentry_summary(refresh: bool = Query(default=False)) -> dict[str, Any]:
        return pingting.load_status_summary(refresh_if_stale=True, force_cli_refresh=refresh)

    @app.get("/sentry/findings")
    def sentry_findings(
        limit: int = Query(default=30, ge=1, le=200),
        severity: str | None = Query(default=None),
        include_acknowledged: bool = Query(default=True),
        include_learning: bool = Query(default=True),
    ) -> dict[str, Any]:
        payload = pingting.load_recent_findings(
            limit=limit,
            severity=severity,
            include_acknowledged=include_acknowledged,
            include_learning=include_learning,
        )
        if not bool(payload.get("ok")):
            errors = payload.get("errors", ["sentry findings unavailable"])
            joined = " ".join(str(item) for item in errors).lower()
            status_code = 400 if "invalid severity" in joined else 502
            raise HTTPException(status_code=status_code, detail=errors)
        return payload

    @app.get("/sentry/runs")
    def sentry_runs(
        limit: int = Query(default=30, ge=1, le=200),
        agent: str | None = Query(default=None),
        status: str | None = Query(default=None),
    ) -> dict[str, Any]:
        payload = pingting.load_recent_agent_runs(
            limit=limit,
            agent=agent,
            status=status,
        )
        if not bool(payload.get("ok")):
            raise HTTPException(status_code=502, detail=payload.get("errors", ["sentry runs unavailable"]))
        return payload

    @app.get("/orchestration/summary")
    def orchestration_summary() -> dict[str, Any]:
        return build_orchestration_summary(settings)

    @app.post("/orchestration/actions/smoke")
    async def orchestration_action_smoke() -> dict[str, Any]:
        return await asyncio.to_thread(
            run_action,
            action_name="smoke",
            script_path=settings.smoke_script_path,
            base_dir=settings.workspace_root,
            timeout_seconds=settings.orchestration_action_timeout_seconds,
            state_path=settings.orchestration_state_path,
        )

    @app.post("/orchestration/actions/bootstrap")
    async def orchestration_action_bootstrap() -> dict[str, Any]:
        return await asyncio.to_thread(
            run_action,
            action_name="bootstrap",
            script_path=settings.bootstrap_script_path,
            base_dir=settings.workspace_root,
            timeout_seconds=settings.orchestration_action_timeout_seconds,
            state_path=settings.orchestration_state_path,
        )

    @app.post("/orchestration/actions/update")
    async def orchestration_action_update() -> dict[str, Any]:
        return await asyncio.to_thread(
            run_action,
            action_name="update",
            script_path=settings.update_script_path,
            base_dir=settings.workspace_root,
            timeout_seconds=settings.orchestration_action_timeout_seconds,
            state_path=settings.orchestration_state_path,
        )

    @app.websocket("/deception/ws/events")
    async def deception_ws_events(websocket: WebSocket) -> None:
        await relay_deception_websocket(
            websocket=websocket,
            upstream_url=settings.clownpeanuts_ws_events_url,
        )

    @app.websocket("/deception/ws/theater/live")
    async def deception_ws_theater_live(websocket: WebSocket) -> None:
        await relay_deception_websocket(
            websocket=websocket,
            upstream_url=settings.clownpeanuts_ws_theater_url,
        )

    @app.api_route(
        "/deception/{target_path:path}",
        methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
        include_in_schema=False,
    )
    async def deception_proxy(target_path: str, request: Request) -> Response:
        normalized_path = target_path.strip()
        if normalized_path.startswith("ws/"):
            raise HTTPException(
                status_code=405,
                detail="use websocket routes at /deception/ws/events or /deception/ws/theater/live",
            )

        body = await request.body()
        content_type = request.headers.get("content-type")

        try:
            status_code, headers, content = await clownpeanuts.proxy(
                method=request.method,
                path=normalized_path,
                query_string=request.url.query,
                body=body,
                content_type=content_type,
            )
        except Exception as exc:
            raise HTTPException(status_code=502, detail=f"deception upstream error: {exc}") from exc

        response_headers = {}
        content_type_header = headers.get("content-type")
        if content_type_header:
            response_headers["content-type"] = content_type_header

        return Response(content=content, status_code=status_code, headers=response_headers)

    return app
