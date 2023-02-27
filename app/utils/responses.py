from typing import Any, Optional

from aiohttp.web import json_response as aiohttp_json_response
from aiohttp.web_response import Response


def json_response(data: Any = None, status: str = "ok") -> Response:
    return aiohttp_json_response(
        data={
            "status": status,
            "data": data or {},
        }
    )


def error_json_response(
        http_status: int,
        message: str,
        data: Optional[Any],
        status: str = "error",
):
    return aiohttp_json_response(
        status=http_status,
        data={
            "status": status,
            "message": str(message),
            "data": data or {},
        },
    )
