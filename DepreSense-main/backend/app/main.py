"""
DepreSense API — main application entry point.
"""

from __future__ import annotations

import logging

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.middleware.error_handler import register_error_handlers
from app.middleware.logging_middleware import LoggingMiddleware
from app.routes.auth import router as auth_router
from app.routes.eeg import router as eeg_router
from app.routes.health import router as health_router
from app.routes.predictions import router as predictions_router
from app.routes.admin import router as admin_router
from app.utils.logger import setup_logging

# ── Initialise structured logging ──────────────────────────
setup_logging(settings.LOG_LEVEL)

logger = logging.getLogger(__name__)

# ── Create the FastAPI application ─────────────────────────
app = FastAPI(
    title="DepreSense API",
    version="1.0.0",
    description="EEG-based depression detection system",
)

# ── Middleware (order matters: outermost first) ────────────
app.add_middleware(LoggingMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Global error handlers ─────────────────────────────────
register_error_handlers(app)

# ── Register routers ──────────────────────────────────────
app.include_router(health_router)
app.include_router(auth_router)
app.include_router(eeg_router)
app.include_router(predictions_router)
app.include_router(admin_router)


# ── Startup event ─────────────────────────────────────────
@app.on_event("startup")
async def startup_event():
    """Initialise resources when the server starts."""
    logger.info("═" * 50)
    logger.info("DepreSense API starting …")
    logger.info("  DEBUG       = %s", settings.DEBUG)
    logger.info("  LOG_LEVEL   = %s", settings.LOG_LEVEL)
    logger.info("  CORS        = %s", settings.ALLOWED_ORIGINS)
    logger.info("  MODEL_PATH  = %s", settings.MODEL_PATH)
    logger.info("  UPLOAD_DIR  = %s", settings.UPLOAD_DIR)

    # Load ML model
    try:
        from app.models.model_loader import get_model, get_shap_background

        model = get_model()
        logger.info(
            "ML model loaded successfully: %s", type(model).__name__
        )
        bg = get_shap_background()
        if bg is not None:
            logger.info("SHAP background loaded: shape=%s", bg.shape)
        else:
            logger.warning("SHAP background data not available.")
    except Exception as exc:
        logger.error("Failed to load ML model at startup: %s", exc)
        logger.warning(
            "Prediction endpoints will return 503 until the model is available."
        )

    logger.info("DepreSense API started ✔")
    logger.info("═" * 50)


# ── Shutdown event ────────────────────────────────────────
@app.on_event("shutdown")
async def shutdown_event():
    """Clean up resources when the server stops."""
    logger.info("DepreSense API shutting down …")

    try:
        from app.models.model_loader import unload_model

        unload_model()
        logger.info("ML model unloaded.")
    except Exception as exc:
        logger.warning("Model unload error: %s", exc)

    logger.info("DepreSense API stopped ✔")


# ── Root endpoint ──────────────────────────────────────────
@app.get("/", tags=["Root"])
async def root():
    """Root endpoint — quick sanity check."""
    return {"status": "ok"}


# ── Local development entry point ──────────────────────────
if __name__ == "__main__":
    uvicorn.run(
        "app.main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG,
    )
