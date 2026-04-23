"""FastAPI application entrypoint."""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.models.schemas import HealthResponse
from app.routes.analytics import router as analytics_router
from app.routes.flights import router as flights_router
from app.routes.predict import router as predict_router
from app.services.aviation_api import AviationAPIService
from app.services.weather_api import WeatherAPIService
from config import APP_NAME, APP_VERSION, LOG_LEVEL
from ml.predict import Predictor

logging.basicConfig(
    level=getattr(logging, LOG_LEVEL, logging.INFO),
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initializes application dependencies at startup and cleans up at shutdown.

    Parameters:
        app: FastAPI app instance.

    Returns:
        Async context manager lifecycle.

    Failure modes:
        Startup logs model-load errors; /health reports model_loaded accordingly.
    """

    predictor = Predictor()
    try:
        predictor.load()
    except Exception:
        logger.exception("Model bundle failed to load at startup.")
    app.state.predictor = predictor
    app.state.aviation_service = AviationAPIService()
    app.state.weather_service = WeatherAPIService()
    yield


app = FastAPI(title=APP_NAME, version=APP_VERSION, lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(predict_router)
app.include_router(flights_router)
app.include_router(analytics_router)


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    """Returns standardized payload for request validation errors.

    Parameters:
        request: Incoming request object.
        exc: Validation exception emitted by FastAPI/Pydantic.

    Returns:
        JSONResponse with status/error/message/details/meta fields.

    Failure modes:
        Always returns HTTP 422 and never re-raises.
    """

    logger.warning("validation_error path=%s details=%s", request.url.path, exc.errors())
    return JSONResponse(
        status_code=422,
        content={
            "status": "error",
            "error": "validation_error",
            "message": "Invalid request payload. Check field formats and try again.",
            "details": exc.errors(),
            "meta": {"path": request.url.path, "timestamp_utc": datetime.now(tz=timezone.utc).isoformat()},
        },
    )


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
    """Returns standardized payload for application HTTP errors.

    Parameters:
        request: Incoming request object.
        exc: HTTPException raised by route handlers.

    Returns:
        JSONResponse with status/error/message/meta fields.

    Failure modes:
        Always returns the HTTPException status code.
    """

    logger.warning("http_error path=%s status=%s detail=%s", request.url.path, exc.status_code, exc.detail)
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "status": "error",
            "error": "http_error",
            "message": str(exc.detail),
            "meta": {"path": request.url.path, "timestamp_utc": datetime.now(tz=timezone.utc).isoformat()},
        },
    )


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Returns standardized payload for unexpected server errors.

    Parameters:
        request: Incoming request object.
        exc: Unhandled exception instance.

    Returns:
        JSONResponse with generic message and metadata.

    Failure modes:
        Logs full stack trace and returns HTTP 500 safely.
    """

    logger.exception("unhandled_error path=%s", request.url.path)
    return JSONResponse(
        status_code=500,
        content={
            "status": "error",
            "error": "internal_server_error",
            "message": "Unexpected server error. Please retry.",
            "meta": {"path": request.url.path, "timestamp_utc": datetime.now(tz=timezone.utc).isoformat()},
        },
    )


@app.get("/health", response_model=HealthResponse)
async def health(request: Request) -> HealthResponse:
    """Health check endpoint with model-loaded status.

    Parameters:
        request: FastAPI request for state access.

    Returns:
        HealthResponse containing app status and model load state.

    Failure modes:
        Returns model_loaded=False when startup initialization has not completed.
    """

    predictor = getattr(request.app.state, "predictor", None)
    model_loaded = bool(predictor and predictor.is_loaded)
    return HealthResponse(status="ok", model_loaded=model_loaded, version=APP_VERSION)

