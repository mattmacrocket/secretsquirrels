from __future__ import annotations

from typing import Any, Mapping

import httpx


class ClownPeanutsAdapter:
    """HTTP adapter for talking to ClownPeanuts API endpoints."""

    def __init__(
        self,
        *,
        base_url: str,
        api_token: str | None = None,
        timeout_seconds: float = 5.0,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.api_token = (api_token or "").strip()
        self.timeout_seconds = timeout_seconds

    def _headers(self, *, content_type: str | None = None) -> dict[str, str]:
        headers: dict[str, str] = {}
        if self.api_token:
            headers["Authorization"] = f"Bearer {self.api_token}"
        if content_type:
            headers["Content-Type"] = content_type
        return headers

    async def request_json(
        self,
        *,
        method: str,
        path: str,
        params: Mapping[str, str] | None = None,
        json_body: Any | None = None,
    ) -> dict[str, Any]:
        url = f"{self.base_url}/{path.lstrip('/')}"
        async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
            response = await client.request(
                method.upper(),
                url,
                params=params,
                json=json_body,
                headers=self._headers(),
            )
        response.raise_for_status()
        payload = response.json()
        if not isinstance(payload, dict):
            return {"payload": payload}
        return payload

    async def status(self) -> dict[str, Any]:
        return await self.request_json(method="GET", path="/status")

    async def proxy(
        self,
        *,
        method: str,
        path: str,
        query_string: str,
        body: bytes,
        content_type: str | None,
    ) -> tuple[int, dict[str, str], bytes]:
        url = f"{self.base_url}/{path.lstrip('/')}"
        if query_string:
            url = f"{url}?{query_string}"

        async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
            response = await client.request(
                method.upper(),
                url,
                content=body,
                headers=self._headers(content_type=content_type),
            )

        headers = {"content-type": response.headers.get("content-type", "application/json")}
        return response.status_code, headers, response.content
