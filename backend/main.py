"""FastAPI app for the stop-motion Pi."""

from fastapi import FastAPI

from backend.config import Settings


def create_app(settings: Settings) -> FastAPI:
    app = FastAPI(title="Stop motion")

    @app.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok", "revision": settings.revision}

    return app


app = create_app(Settings.from_env())
