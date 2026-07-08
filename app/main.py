from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse, JSONResponse
from app.config import get_settings
from app.routers import auth as auth_router
from app.routers import skills as skills_router
from app.routers import users as users_router
from app.routers import search as search_router
import traceback

settings = get_settings()

app = FastAPI(
    title="SymbiCircle",
    description="Campus collaboration and skill discovery platform for SIT Pune",
    version="0.1.0",
)

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    traceback.print_exc()
    return JSONResponse(
        status_code=500,
        content={"detail": f"Internal server error: {str(exc)}"},
    )

app.mount("/static", StaticFiles(directory="app/static"), name="static")
templates = Jinja2Templates(directory="app/templates")

app.include_router(auth_router.router)
app.include_router(skills_router.router)
app.include_router(users_router.router)
app.include_router(search_router.router)


@app.get("/health")
async def health_check():
    return {"status": "ok", "env": settings.APP_ENV, "domain": settings.ALLOWED_EMAIL_DOMAIN}

@app.get("/", response_class=HTMLResponse)
async def landing(request: Request):
    return templates.TemplateResponse("landing.html", {"request": request})

@app.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    return templates.TemplateResponse("login.html", {"request": request})

@app.get("/register", response_class=HTMLResponse)
async def register_page(request: Request):
    return templates.TemplateResponse("register.html", {"request": request})

@app.get("/dashboard", response_class=HTMLResponse)
async def dashboard_page(request: Request):
    return templates.TemplateResponse("dashboard.html", {"request": request})

@app.get("/profile/me", response_class=HTMLResponse)
async def own_profile(request: Request):
    return templates.TemplateResponse("profile.html", {"request": request, "user_id": "me"})

@app.get("/profile/{user_id}", response_class=HTMLResponse)
async def profile_page(request: Request, user_id: str):
    return templates.TemplateResponse("profile.html", {"request": request, "user_id": user_id})