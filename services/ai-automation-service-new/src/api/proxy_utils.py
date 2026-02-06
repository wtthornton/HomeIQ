"""
Shared Proxy Utility for Service Proxying

Extracted from pattern_router, synergy_router, analysis_router (M1: DRY fix).
Uses the best error handling from synergy_router as the base.
"""

import logging

import httpx
from fastapi import HTTPException, Request
from fastapi.responses import Response

from ..config import settings

logger = logging.getLogger(__name__)


async def proxy_to_service(
    request: Request,
    service_base_url: str,
    path_prefix: str,
    path: str = "",
    method: str = "GET",
    body: dict | None = None,
    timeout: float = 30.0,
) -> Response:
    """
    Proxy a request to an upstream service.

    Args:
        request: The incoming FastAPI request
        service_base_url: Base URL of the upstream service
        path_prefix: API path prefix (e.g. "/api/v1/patterns")
        path: Sub-path after the prefix
        method: HTTP method
        body: Request body for POST/PUT requests
        timeout: Request timeout in seconds

    Returns:
        Proxied response
    """
    try:
        base = service_base_url.rstrip("/")
        if path:
            url = f"{base}/{path_prefix.strip('/')}/{path}".rstrip("/")
        else:
            url = f"{base}/{path_prefix.strip('/')}"

        logger.debug(f"Proxying {method} request to: {url}")

        # Forward auth headers from original request
        headers = {}
        if "authorization" in request.headers:
            headers["Authorization"] = request.headers["authorization"]
        if "x-homeiq-api-key" in request.headers:
            headers["X-HomeIQ-API-Key"] = request.headers["x-homeiq-api-key"]

        async with httpx.AsyncClient(timeout=timeout) as client:
            if method == "GET":
                response = await client.get(
                    url, headers=headers, params=dict(request.query_params)
                )
            elif method == "POST":
                response = await client.post(url, headers=headers, json=body)
            else:
                raise HTTPException(
                    status_code=405, detail=f"Method {method} not supported"
                )

            # Handle non-2xx responses
            if response.status_code >= 400:
                error_detail = "Upstream service error"
                try:
                    error_body = response.json()
                    if isinstance(error_body, dict):
                        error_detail = error_body.get(
                            "detail", error_body.get("message", str(error_body))
                        )
                    else:
                        error_detail = str(error_body)
                except Exception:
                    error_detail = response.text[:200] if response.text else "Unknown error"

                logger.error(
                    f"Upstream service returned {response.status_code}: {error_detail}"
                )
                raise HTTPException(
                    status_code=response.status_code, detail=error_detail
                )

            return Response(
                content=response.content,
                status_code=response.status_code,
                headers={
                    k: v
                    for k, v in response.headers.items()
                    if k.lower() not in ["content-length", "transfer-encoding"]
                },
                media_type="application/json",
            )
    except httpx.ConnectError as e:
        logger.error(f"Failed to connect to upstream service at {service_base_url}: {e}")
        raise HTTPException(
            status_code=502, detail="Upstream service unavailable"
        )
    except httpx.TimeoutException as e:
        logger.error(f"Timeout connecting to upstream service: {e}")
        raise HTTPException(
            status_code=504, detail="Upstream service timeout"
        )
    except httpx.RequestError as e:
        logger.error(f"Failed to proxy to upstream service: {e}")
        raise HTTPException(status_code=502, detail="Upstream service unavailable")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error proxying to upstream service: {e}", exc_info=True)
        raise HTTPException(
            status_code=500, detail="Internal server error"
        )
