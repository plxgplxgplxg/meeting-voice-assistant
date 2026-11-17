from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.core.errors import DomainError

HTTP_STATUS_CODES: dict[int, str] = {
    400: "BAD_REQUEST",
    401: "AUTHENTICATION_REQUIRED",
    403: "PERMISSION_DENIED",
    404: "NOT_FOUND",
    405: "METHOD_NOT_ALLOWED",
    409: "CONFLICT",
    413: "PAYLOAD_TOO_LARGE",
    422: "VALIDATION_FAILED",
    429: "RATE_LIMITED",
}


def error_response(
    request: Request,
    status_code: int,
    code: str,
    message: str,
    headers: dict[str, str] | None = None,
) -> JSONResponse:
    """Build the standard error envelope.

    Args:
        request: Current request, used for the path and request id.
        status_code: HTTP status of the response.
        code: Stable machine-readable error code.
        message: Human-readable explanation.
        headers: Optional extra response headers.

    Returns:
        JSON response shaped ``{"error": {code, message, path, request_id}}``.
    """
    return JSONResponse(
        status_code=status_code,
        headers=headers,
        content={
            "error": {
                "code": code,
                "message": message,
                "path": request.url.path,
                "request_id": getattr(request.state, "request_id", None),
            }
        },
    )


def register_exception_handlers(app: FastAPI) -> None:
    """Attach handlers that map every error source to the standard envelope.

    Args:
        app: FastAPI application to configure.
    """

    @app.exception_handler(DomainError)
    async def handle_domain_error(request: Request, exc: DomainError) -> JSONResponse:
        headers = {"WWW-Authenticate": "Bearer"} if exc.status_code == 401 else None
        return error_response(request, exc.status_code, exc.code, exc.message, headers)

    @app.exception_handler(StarletteHTTPException)
    async def handle_http_exception(
        request: Request, exc: StarletteHTTPException
    ) -> JSONResponse:
        code = HTTP_STATUS_CODES.get(exc.status_code, "HTTP_ERROR")
        message = exc.detail if isinstance(exc.detail, str) else "Request failed."
        headers = dict(exc.headers) if exc.headers else None
        return error_response(request, exc.status_code, code, message, headers)

    @app.exception_handler(RequestValidationError)
    async def handle_validation_error(
        request: Request, exc: RequestValidationError
    ) -> JSONResponse:
        parts = []
        for item in exc.errors():
            location = ".".join(str(part) for part in item.get("loc", ()) if part != "body")
            message = item.get("msg", "invalid")
            parts.append(f"{location}: {message}" if location else message)
        return error_response(request, 422, "VALIDATION_FAILED", "; ".join(parts) or "Invalid request.")
