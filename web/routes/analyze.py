"""Análise de campanha — upload de screenshot para Mila processar."""
import asyncio
import shutil
import tempfile
from pathlib import Path

from fastapi import APIRouter, File, Request, UploadFile
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from web.auth import require_auth

router    = APIRouter()
ROOT      = Path(__file__).parent.parent.parent
templates = Jinja2Templates(directory=str(ROOT / "web" / "templates"))

_ALLOWED = {".jpg", ".jpeg", ".png", ".webp", ".gif"}


@router.get("/analyze", response_class=HTMLResponse)
async def analyze_page(request: Request):
    require_auth(request)
    return templates.TemplateResponse("analyze.html", {"request": request})


@router.post("/analyze", response_class=HTMLResponse)
async def analyze_post(request: Request, arquivo: UploadFile = File(...)):
    require_auth(request)

    ext = Path(arquivo.filename or "").suffix.lower()
    if ext not in _ALLOWED:
        return HTMLResponse(
            '<div class="text-red-400 p-4 border border-red-800 rounded-lg">'
            'Formato inválido. Use JPG, PNG, WEBP ou GIF.</div>'
        )

    # Salva temporariamente
    with tempfile.NamedTemporaryFile(suffix=ext, delete=False) as tmp:
        shutil.copyfileobj(arquivo.file, tmp)
        tmp_path = tmp.name

    try:
        from alina.analisador import analisar_resultado

        resultado = await asyncio.to_thread(analisar_resultado, tmp_path)

        return templates.TemplateResponse("partials/analyze_result.html", {
            "request":   request,
            "resultado": resultado,
        })

    except Exception as e:
        return HTMLResponse(
            f'<div class="text-red-400 p-4 border border-red-800 rounded-lg">'
            f'<strong>Erro na análise:</strong> {e}</div>'
        )
    finally:
        Path(tmp_path).unlink(missing_ok=True)
