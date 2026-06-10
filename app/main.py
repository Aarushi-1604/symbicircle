from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from app.config import get_settings
from app.routers import auth as auth_router
from app.routers import skills as skills_router

settings = get_settings()

app = FastAPI(
    title="SymbiCircle",
    description="Campus collaboration and skill discovery platform for SIT Pune",
    version="0.1.0",
)

app.mount("/static", StaticFiles(directory="app/static"), name="static")
templates = Jinja2Templates(directory="app/templates")

app.include_router(auth_router.router)
app.include_router(skills_router.router)


@app.get("/health")
async def health_check():
    return {
        "status": "ok",
        "env": settings.APP_ENV,
        "domain": settings.ALLOWED_EMAIL_DOMAIN,
    }