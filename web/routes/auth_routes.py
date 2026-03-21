"""Rotas de autenticação: /login e /logout."""
from pathlib import Path

from fastapi import APIRouter, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse, Response
from fastapi.templating import Jinja2Templates

from web.auth import check_pin, set_session, clear_session, is_authenticated

router = APIRouter()
ROOT = Path(__file__).parent.parent.parent
templates = Jinja2Templates(directory=str(ROOT / "web" / "templates"))


@router.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    if is_authenticated(request):
        return RedirectResponse("/dashboard")
    return templates.TemplateResponse("login.html", {"request": request, "erro": ""})


@router.post("/login")
async def login_post(request: Request, pin: str = Form(...)):
    if check_pin(pin):
        # HTMX intercepta 303 e faz swap do conteúdo no target — usar HX-Redirect
        if request.headers.get("HX-Request"):
            resp = Response(status_code=204)
            resp.headers["HX-Redirect"] = "/dashboard"
            set_session(resp)
            return resp
        response = RedirectResponse("/dashboard", status_code=303)
        set_session(response)
        return response
    # HTMX: retorna apenas o fragmento de erro
    if request.headers.get("HX-Request"):
        return HTMLResponse('<p id="erro" class="text-red-400 text-sm mt-2">PIN incorreto. Tente novamente.</p>')
    return templates.TemplateResponse("login.html", {"request": request, "erro": "PIN incorreto."})


@router.get("/logout")
async def logout():
    response = RedirectResponse("/login", status_code=303)
    clear_session(response)
    return response
