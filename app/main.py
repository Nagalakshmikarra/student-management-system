from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.exception_handlers import http_exception_handler
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.config import settings
from app.database import create_db_and_tables
from app.deps import NotLoggedIn
from app.routers import auth, register
from app.templating import BASE_DIR, render


@asynccontextmanager
async def lifespan(app: FastAPI):
    create_db_and_tables()
    yield


app = FastAPI(title=settings.APP_NAME, lifespan=lifespan)
app.mount("/static", StaticFiles(directory=str(BASE_DIR / "static")), name="static")

app.include_router(auth.router)
app.include_router(register.router)


@app.exception_handler(NotLoggedIn)
async def not_logged_in_handler(request: Request, exc: NotLoggedIn):
    return RedirectResponse("/login", status_code=303)


@app.exception_handler(StarletteHTTPException)
async def custom_http_handler(request: Request, exc: StarletteHTTPException):
    if exc.status_code == 403:
        return render(request, "403.html", status_code=403)
    return await http_exception_handler(request, exc)


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/")
def root():
    return RedirectResponse("/login")