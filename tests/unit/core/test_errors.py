from fastapi import FastAPI
from fastapi.testclient import TestClient

from hola_hello_ciao.core.errors import register_error_handlers


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
