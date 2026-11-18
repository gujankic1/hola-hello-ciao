from typing import Any

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from sqlalchemy.exc import SQLAlchemyError


class AppError(Exception):
    """Base class for domain errors; rendered as {"error": {"code", "message"}}."""

    status_code = 500
    code = "internal_error"

    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message


class NotFoundError(AppError):
    status_code = 404
    code = "not_found"


class ConflictError(AppError):
    status_code = 409
    code = "conflict"


class StorageError(AppError):
    status_code = 500
    code = "storage_error"


def _error_body(code: str, message: str, details: Any = None) -> dict[str, Any]:
    error: dict[str, Any] = {"code": code, "message": message}
    if details is not None:
        error["details"] = details
    return {"error": error}


def register_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(AppError)
    async def _app_error(_request: Request, exc: AppError) -> JSONResponse:
        return JSONResponse(status_code=exc.status_code, content=_error_body(exc.code, exc.message))

    @app.exception_handler(SQLAlchemyError)
    async def _db_error(_request: Request, _exc: SQLAlchemyError) -> JSONResponse:
        # Fallback for database failures a repository did not translate; no internals leaked.
        return JSONResponse(
            status_code=StorageError.status_code,
            content=_error_body(StorageError.code, "A storage error occurred"),
        )

    @app.exception_handler(Exception)
    async def _unexpected_error(_request: Request, _exc: Exception) -> JSONResponse:
        # Last resort, no internals leaked; Starlette still re-raises so the server logs it.
        return JSONResponse(
            status_code=AppError.status_code,
            content=_error_body(AppError.code, "An unexpected error occurred"),
        )

    @app.exception_handler(RequestValidationError)
    async def _validation_error(_request: Request, exc: RequestValidationError) -> JSONResponse:
        details = [{"loc": list(e["loc"]), "msg": e["msg"]} for e in exc.errors()]
        return JSONResponse(
            status_code=422,
            content=_error_body("validation_error", "Request validation failed", details),
        )
