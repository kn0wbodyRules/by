import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.auth import router as auth_router
from app.api.boq import router as boq_router
from app.api.calculate import router as calculate_router
from app.api.chat import router as chat_router
from app.api.constraints import router as constraints_router
from app.api.plans import router as plans_router
from app.api.rooms import router as rooms_router
from app.api.upload import router as upload_router
from app.config import get_settings
from app.core.exceptions import DomainError
from app.database import check_db_connection

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("boq.main")

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    try:
        check_db_connection()
        logger.info("Database connection OK")
    except Exception as exc:
        raise RuntimeError(
            "Cannot reach the database. Is Postgres running? "
            "Run `docker compose up -d` and check `docker compose ps`."
        ) from exc
    yield


app = FastAPI(title="BOQ Automation Tool API", version="0.1.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(DomainError)
async def domain_error_handler(request: Request, exc: DomainError):
    return JSONResponse(status_code=exc.status_code, content={"detail": exc.message})


@app.get("/health")
def health():
    return {"status": "ok"}


app.include_router(auth_router)
app.include_router(plans_router)
app.include_router(upload_router)
app.include_router(rooms_router)
app.include_router(constraints_router)
app.include_router(calculate_router)
app.include_router(boq_router)
app.include_router(chat_router)
