from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from backend.api.routes import router as api_router
from backend.core.config import load_app_config, load_providers_config
from backend.core.storage import init_storage
from backend.services.subscriptions import SubscriptionScheduler

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

BASE_DIR = Path(__file__).resolve().parents[1]
FRONTEND_DIR = BASE_DIR / "frontend" / "dist"


@asynccontextmanager
async def lifespan(app: FastAPI):
    app_cfg = load_app_config()
    providers_cfg = load_providers_config()
    init_storage(app_cfg)
    app.state.app_cfg = app_cfg
    app.state.providers_cfg = providers_cfg
    
    # Initialize and start scheduler
    scheduler = SubscriptionScheduler(app_cfg, providers_cfg)
    scheduler.start()
    app.state.scheduler = scheduler
    logger.info("Application started with subscription scheduler")
    
    yield
    
    # Shutdown scheduler
    scheduler.shutdown()
    logger.info("Application shutdown complete")


app = FastAPI(title="x-feed-digest", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

if FRONTEND_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(FRONTEND_DIR)), name="static")

app.include_router(api_router, prefix="/api")