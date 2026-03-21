"""
DarkCred Agency — Painel Web
FastAPI app principal.

Iniciar:
    cd /home/user/DarkCred-Squad
    uvicorn web.app:app --host 0.0.0.0 --port 8000 --reload
"""
import sys
from pathlib import Path

# Garante que o root do projeto está no path
ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

from fastapi import FastAPI, Request
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from web.auth import _LoginRequired
from web.routes import dashboard, agents, gallery, generate, analyze
from web.routes.auth_routes import router as auth_router

app = FastAPI(title="DarkCred Agency", docs_url=None, redoc_url=None)

# ── Arquivos estáticos ──────────────────────────────────────────────────────
app.mount("/static",  StaticFiles(directory=str(ROOT / "web" / "static")),         name="static")
app.mount("/images",  StaticFiles(directory=str(ROOT / "saidas" / "imagens")),      name="images")

# ── Templates ───────────────────────────────────────────────────────────────
templates = Jinja2Templates(directory=str(ROOT / "web" / "templates"))

# ── Routers ─────────────────────────────────────────────────────────────────
app.include_router(auth_router)
app.include_router(dashboard.router)
app.include_router(agents.router)
app.include_router(gallery.router)
app.include_router(generate.router)
app.include_router(analyze.router)

# ── Raiz ────────────────────────────────────────────────────────────────────
@app.get("/")
async def root():
    return RedirectResponse("/dashboard")

# ── Exception handler para auth ─────────────────────────────────────────────
@app.exception_handler(_LoginRequired)
async def login_required_handler(request: Request, exc: _LoginRequired):
    return RedirectResponse("/login")
