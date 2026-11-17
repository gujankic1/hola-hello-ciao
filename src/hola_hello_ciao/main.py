from fastapi import FastAPI

from hola_hello_ciao.core.errors import register_error_handlers
from hola_hello_ciao.readings.router import router as readings_router
from hola_hello_ciao.sensors.router import router as sensors_router
from hola_hello_ciao.statistics.router import router as statistics_router


def create_app() -> FastAPI:
    app = FastAPI(title="Weather Sensor Metrics API", version="0.1.0")
    register_error_handlers(app)
    app.include_router(sensors_router, prefix="/api/v1")
    app.include_router(readings_router, prefix="/api/v1")
    app.include_router(statistics_router, prefix="/api/v1")

    @app.get("/health", tags=["meta"])
    def health() -> dict[str, str]:
        return {"status": "ok"}

    return app


app = create_app()
