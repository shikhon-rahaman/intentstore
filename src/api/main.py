from dotenv import load_dotenv
load_dotenv()

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../"))

try:
    from fastapi import FastAPI, HTTPException
    from fastapi.middleware.cors import CORSMiddleware
    from pydantic import BaseModel
    FASTAPI_AVAILABLE = True
except ImportError:
    FASTAPI_AVAILABLE = False
    FastAPI = None
    HTTPException = Exception
    CORSMiddleware = None

    class BaseModel:
        pass

from src import __version__
from src.database import init_db, get_stats, get_all_files, get_high_urgency_files
from src.collector.file_watcher import scan_directory
from src.engine.semantic_engine import batch_analyze
from src.logger import get_logger

logger = get_logger("api")

if FASTAPI_AVAILABLE:
    app = FastAPI(
        title="IntentStore API",
        description="LLM-powered semantic storage intelligence for CDAC SSM Next-Gen Kernel",
        version=__version__,
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_methods=["*"],
        allow_headers=["*"],
    )

    class ScanRequest(BaseModel):
        path: str

    class ScanResponse(BaseModel):
        path: str
        files_found: int
        files_analyzed: int

    @app.on_event("startup")
    def startup():
        try:
            init_db()
        except Exception as exc:
            logger.error("API startup failed: %s", exc)

    @app.get("/status")
    def status():
        try:
            return get_stats()
        except Exception as exc:
            logger.error("GET /status failed: %s", exc)
            raise HTTPException(status_code=500, detail=str(exc))

    @app.get("/files")
    def files():
        try:
            return get_all_files()
        except Exception as exc:
            logger.error("GET /files failed: %s", exc)
            raise HTTPException(status_code=500, detail=str(exc))

    @app.get("/report")
    def report(threshold: float = 0.6):
        try:
            return {
                "threshold": threshold,
                "stats": get_stats(),
                "high_urgency_files": get_high_urgency_files(threshold=threshold),
            }
        except Exception as exc:
            logger.error("GET /report failed: %s", exc)
            raise HTTPException(status_code=500, detail=str(exc))

    # Only allow scanning inside the user's home directory (or an explicit
    #