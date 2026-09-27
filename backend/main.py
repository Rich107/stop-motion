"""FastAPI app for the stop-motion Pi."""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.responses import JSONResponse

from backend.camera import Camera, get_camera
from backend.config import Settings


def create_app(settings: Settings, camera: Camera | None = None) -> FastAPI:
    """The app; `camera` defaults to the one `settings` names, and runs while the app does."""
    if camera is None:
        camera = get_camera(settings)

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        camera.start()
        try:
            yield
        finally:
            camera.stop()

    app = FastAPI(title="Stop motion", lifespan=lifespan)
    app.state.camera = camera

    @app.get("/health")
    def health() -> JSONResponse:
        # deploy.sh rolls back unless this is 200, so a release that can't see the camera fails
        if not camera.is_open:
            return JSONResponse(
                {"status": "error", "reason": "camera not open", "revision": settings.revision},
                status_code=503,
            )
        return JSONResponse({"status": "ok", "revision": settings.revision})

    return app


app = create_app(Settings.from_env())
