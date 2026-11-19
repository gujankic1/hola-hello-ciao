from typing import Any, Literal

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from sqlalchemy.exc import SQLAlchemyError

ErrorCode = Literal["validation_error", "not_found", "conflict", "storage_error", "internal_error"]


class ErrorDetail(BaseModel):
    loc: list[str | int]
    msg: str


class ErrorBody(BaseModel):
    code: ErrorCode
    message: str
    details: list[ErrorDetail] | None = None  # only for validation_error; omitted otherwise


class ErrorResponse(BaseModel):
    """The body of every error response."""

    error: ErrorBody


def error_responses(*status_codes: int) -> dict[int | str, dict[str, Any]]:
    """OpenAPI `responses` for these statuses. Exception handlers are invisible to OpenAPI, and
    declaring 422 replaces FastAPI's default `HTTPValidationError`, which this API never returns."""
    return {status_code: {"model": ErrorResponse} for status_code in status_codes}


class AppError(Exception):
    """Base class for domain errors; rendered as `ErrorResponse`."""

    status_code = 500
    code: ErrorCode = "internal_error"

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


def _error_body(
    code: ErrorCode, message: str, details: list[ErrorDetail] | None = None
) -> dict[str, Any]:
    body = ErrorResponse(error=ErrorBody(code=code, message=message, details=details))
    return body.model_dump(mode="json", exclude_none=True)


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
        details = [ErrorDetail(loc=list(e["loc"]), msg=e["msg"]) for e in exc.errors()]
        return JSONResponse(
            status_code=422,
            content=_error_body("validation_error", "Request validation failed", details),
        )
