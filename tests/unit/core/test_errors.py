import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from pydantic import BaseModel
from sqlalchemy.exc import OperationalError

from hola_hello_ciao.core.errors import (
    ConflictError,
    ErrorResponse,
    NotFoundError,
    StorageError,
    register_error_handlers,
)


def test_unexpected_exception_returns_generic_500_without_internals() -> None:
    app = FastAPI()
    register_error_handlers(app)

    @app.get("/boom")
    def boom() -> None:
        raise RuntimeError("secret internals")

    response = TestClient(app, raise_server_exceptions=False).get("/boom")

    assert response.status_code == 500
    assert response.json() == {
        "error": {"code": "internal_error", "message": "An unexpected error occurred"}
    }


@pytest.mark.parametrize(
    ("exception", "status_code", "code"),
    [
        (NotFoundError("Sensor 42 not found"), 404, "not_found"),
        (ConflictError("Different value"), 409, "conflict"),
        (StorageError("Could not load the sensor"), 500, "storage_error"),
        (OperationalError("SELECT 1", {}, Exception("disk I/O error")), 500, "storage_error"),
        (RuntimeError("boom"), 500, "internal_error"),
    ],
)
def test_raised_errors_match_the_documented_shape(
    exception: Exception, status_code: int, code: str
) -> None:
    app = FastAPI()
    register_error_handlers(app)

    @app.get("/fail")
    def fail() -> None:
        raise exception

    response = TestClient(app, raise_server_exceptions=False).get("/fail")

    assert response.status_code == status_code
    assert ErrorResponse.model_validate(response.json()).error.code == code
    assert "details" not in response.json()["error"]


def test_validation_errors_match_the_documented_shape_with_details() -> None:
    app = FastAPI()
    register_error_handlers(app)

    class Body(BaseModel):
        count: int

    @app.post("/items")
    def create(body: Body) -> None:
        return None

    response = TestClient(app).post("/items", json={"count": "many"})

    assert response.status_code == 422
    error = ErrorResponse.model_validate(response.json()).error
    assert error.code == "validation_error"
    assert [detail.loc for detail in error.details or []] == [["body", "count"]]
