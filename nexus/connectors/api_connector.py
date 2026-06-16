"""
NexusCore — موصل REST/GraphQL
بديل شامل لـ satellite_connector.py — يتصل بأي API خارجي.
"""
import asyncio
import json
import logging
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

logger = logging.getLogger("nexus.connectors.api")


@dataclass
class APIConfig:
    name: str
    base_url: str
    headers: Dict[str, str] = field(default_factory=dict)
    timeout: int = 30
    retry_count: int = 3
    rate_limit_rps: float = 10.0


@dataclass
class APIResponse:
    url: str
    status_code: int
    data: Any
    elapsed_ms: float
    success: bool
    error: Optional[str] = None


class APIConnector:
    """موصل API متعدد البروتوكولات مع Rate Limiting وإعادة المحاولة"""

    def __init__(self):
        self.configs: Dict[str, APIConfig] = {}
        self._call_times: Dict[str, List[float]] = {}
        self.stats = {"calls": 0, "errors": 0, "avg_ms": 0.0}
        logger.info("🌐 APIConnector initialized")

    def register(self, config: APIConfig) -> None:
        self.configs[config.name] = config
        self._call_times[config.name] = []

    async def get(self, api_name: str, endpoint: str,
                  params: Optional[Dict] = None) -> APIResponse:
        return await self._request(api_name, "GET", endpoint, params=params)

    async def post(self, api_name: str, endpoint: str,
                   body: Optional[Dict] = None) -> APIResponse:
        return await self._request(api_name, "POST", endpoint, json_body=body)

    async def _request(self, api_name: str, method: str, endpoint: str,
                       params: Optional[Dict] = None,
                       json_body: Optional[Dict] = None) -> APIResponse:
        cfg = self.configs.get(api_name)
        if not cfg:
            return APIResponse(url=endpoint, status_code=0, data=None,
                               elapsed_ms=0, success=False,
                               error=f"API '{api_name}' not registered")
        await self._rate_limit(api_name, cfg.rate_limit_rps)
        url = cfg.base_url.rstrip("/") + "/" + endpoint.lstrip("/")
        start = time.time()
        last_exc: Optional[str] = None
        for attempt in range(cfg.retry_count):
            try:
                import httpx
                async with httpx.AsyncClient(timeout=cfg.timeout) as client:
                    if method == "GET":
                        resp = await client.get(url, headers=cfg.headers, params=params)
                    else:
                        resp = await client.post(url, headers=cfg.headers, json=json_body)
                    resp.raise_for_status()
                    elapsed = (time.time() - start) * 1000
                    self._update_stats(elapsed, success=True)
                    try:
                        data = resp.json()
                    except Exception:
                        data = resp.text
                    return APIResponse(url=url, status_code=resp.status_code,
                                       data=data, elapsed_ms=round(elapsed, 2), success=True)
            except Exception as exc:
                last_exc = str(exc)
                if attempt < cfg.retry_count - 1:
                    await asyncio.sleep(2 ** attempt)
        elapsed = (time.time() - start) * 1000
        self._update_stats(elapsed, success=False)
        return APIResponse(url=url, status_code=0, data=None,
                           elapsed_ms=round(elapsed, 2), success=False, error=last_exc)

    async def _rate_limit(self, name: str, rps: float) -> None:
        now = time.time()
        window = 1.0 / rps
        times = self._call_times[name]
        times.append(now)
        times[:] = [t for t in times if now - t < 1.0]
        if len(times) > rps:
            await asyncio.sleep(window)

    def _update_stats(self, elapsed_ms: float, success: bool) -> None:
        self.stats["calls"] += 1
        if not success:
            self.stats["errors"] += 1
        n = self.stats["calls"]
        self.stats["avg_ms"] = (self.stats["avg_ms"] * (n - 1) + elapsed_ms) / n

    def get_stats(self) -> Dict:
        return {**self.stats,
                "registered_apis": list(self.configs.keys()),
                "error_rate": round(self.stats["errors"] / max(self.stats["calls"], 1), 3)}
