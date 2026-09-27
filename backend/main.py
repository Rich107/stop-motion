"""FastAPI app for the stop-motion Pi."""

import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.responses import JSONResponse

from backend.camera import Camera, get_camera
from backend.config import Settings

log = logging.getLogger(__name__)


def create_app(settings: Settings, camera: Camera | None = None) -> FastAPI:
    """The app; `camera` defaults to the one `settings` names, and runs while the app does."""
    if camera is None:
        camera = get_camera(settings)

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        try:
            camera.start()
        except Exception:
            # Stay up so /health can say why (and deploy.sh rolls back), rather than crash-looping
            log.exception("Camera failed to start")
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
