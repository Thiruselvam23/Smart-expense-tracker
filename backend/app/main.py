from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
import os, logging

from app.config import settings
from app.database import connect_db, disconnect_db
from app.routers import auth, expenses, budgets, receipts, dashboard, insights, reports, chatbot

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
limiter = Limiter(key_func=get_remote_address)


@asynccontextmanager
async def lifespan(app: FastAPI):
    await connect_db()
    yield
    await disconnect_db()


app = FastAPI(
    title=settings.APP_NAME,
    version="1.0.0",
    docs_url="/docs" if settings.DEBUG else None,
    redoc_url="/redoc" if settings.DEBUG else None,
    lifespan=lifespan,
)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.FRONTEND_URL, "http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Serve uploaded files (profile images, receipts)
app.mount("/uploads", StaticFiles(directory=settings.UPLOAD_DIR), name="uploads")


class AppException(Exception):
    def __init__(self, status_code: int, message: str, error_code: str = None):
        self.status_code = status_code
        self.message = message
        self.error_code = error_code


@app.exception_handler(AppException)
async def app_exception_handler(request: Request, exc: AppException):
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.message, "error_code": exc.error_code},
    )


@app.exception_handler(Exception)
async def generic_exception_handler(request: Request, exc: Exception):
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    return JSONResponse(status_code=500, content={"detail": "Internal server error"})


app.include_router(auth.router,      prefix="/api/auth",      tags=["Auth"])
app.include_router(expenses.router,  prefix="/api/expenses",  tags=["Expenses"])
app.include_router(budgets.router,   prefix="/api/budgets",   tags=["Budgets"])
app.include_router(receipts.router,  prefix="/api/receipts",  tags=["Receipts"])
app.include_router(dashboard.router, prefix="/api/dashboard", tags=["Dashboard"])
app.include_router(insights.router,  prefix="/api/insights",  tags=["Insights"])
app.include_router(reports.router,   prefix="/api/reports",   tags=["Reports"])
app.include_router(chatbot.router,   prefix="/api/chatbot",   tags=["Chatbot"])


@app.get("/health")
async def health():
    return {"status": "healthy", "app": settings.APP_NAME}
