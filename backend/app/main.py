from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from pathlib import Path

from app.api import admin, alerts, collectors, matching, news, strike_zone, users
from app.api import sealing, research, templates, auth, collab, companies, demo, health, intake, judgments, scoring, strategy
from app.config import get_settings
from app.core import errors
from app.core.http_security import SecurityMiddleware
from starlette.middleware.trustedhost import TrustedHostMiddleware

settings = get_settings()

_docs = settings.docs_enabled or settings.auth_mode == "dev"
app = FastAPI(title="Value Investment Platform API", version="0.0.1",
              docs_url="/docs" if _docs else None, redoc_url="/redoc" if _docs else None,
              openapi_url="/openapi.json" if _docs else None)
errors.install(app)
app.add_middleware(SecurityMiddleware)
_hosts = [h.strip() for h in settings.allowed_hosts.split(",") if h.strip()]
if _hosts and _hosts != ["*"]:
    app.add_middleware(TrustedHostMiddleware, allowed_hosts=_hosts)
app.include_router(health.router)
app.include_router(sealing.router)
app.include_router(research.router)
app.include_router(auth.router)
app.include_router(demo.router)
app.include_router(intake.router)
app.include_router(companies.router)
app.include_router(judgments.router)
app.include_router(scoring.router)
app.include_router(strategy.router)
app.include_router(templates.router)
app.include_router(collab.router)
app.include_router(collab.worker_router)
app.include_router(strike_zone.router)
app.include_router(admin.router)
app.include_router(users.router)
app.include_router(news.router)
app.include_router(alerts.router)
app.include_router(collectors.router)
app.include_router(matching.watchlist_router)
app.include_router(matching.companies_router)
app.include_router(matching.news_router)


@app.get("/api")
def api_root():
    return {"name": "value-investment-platform", "version": "0.0.1"}


# Static research UI (mount last so /api/* wins)
_STATIC = Path(__file__).resolve().parents[1] / "static"
app.mount("/", StaticFiles(directory=str(_STATIC), html=True), name="static")
