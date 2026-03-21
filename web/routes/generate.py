"""Geração de copies e imagens via formulário HTMX."""
import asyncio
import sys
from pathlib import Path

from fastapi import APIRouter, Form, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from web.auth import require_auth

ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(ROOT))

router    = APIRouter()
templates = Jinja2Templates(directory=str(ROOT / "web" / "templates"))


def _get_segmentos() -> list[str]:
    try:
        from alina.config import SEGMENTOS
        return sorted(SEGMENTOS.keys())
    except Exception:
        return ["generico", "padaria", "barbearia", "salão", "pizzaria"]


@router.get("/generate", response_class=HTMLResponse)
async def generate_page(request: Request):
    require_auth(request)
    return templates.TemplateResponse("generate.html", {
        "request":   request,
        "segmentos": _get_segmentos(),
    })


@router.post("/generate/copy", response_class=HTMLResponse)
async def generate_copy(
    request: Request,
    segmento: str = Form("generico"),
    quantidade: int = Form(3),
):
    require_auth(request)
    quantidade = max(1, min(quantidade, 8))

    try:
        from alina.gerador import gerar_variacoes
        from alina.aprendizado import construir_contexto_aprendizado
        from alina.config import SEGMENTOS

        seg_info = SEGMENTOS.get(segmento, SEGMENTOS.get("generico", {}))
        ctx      = construir_contexto_aprendizado(segmento)

        variacoes = await asyncio.to_thread(
            gerar_variacoes, segmento, seg_info, ctx, quantidade
        )

        return templates.TemplateResponse("partials/copy_result.html", {
            "request":   request,
            "variacoes": variacoes,
            "segmento":  segmento,
        })

    except Exception as e:
        return HTMLResponse(
            f'<div class="alert-error p-4 rounded-lg text-red-400 border border-red-800">'
            f'<strong>Erro ao gerar:</strong> {e}</div>'
        )


@router.post("/generate/image", response_class=HTMLResponse)
async def generate_image(
    request: Request,
    segmento: str = Form("generico"),
):
    require_auth(request)

    try:
        from alina.pipeline_criativo import executar_pipeline

        resultado = await asyncio.to_thread(executar_pipeline, segmento)

        caminho = resultado.get("caminho_imagem", "")
        filename = Path(caminho).name if caminho else ""

        if filename:
            return templates.TemplateResponse("partials/image_card.html", {
                "request":  request,
                "filename": filename,
                "segmento": segmento,
            })
        return HTMLResponse(
            '<div class="text-yellow-400 p-4">Imagem gerada mas caminho não encontrado.</div>'
        )

    except Exception as e:
        return HTMLResponse(
            f'<div class="text-red-400 p-4 border border-red-800 rounded-lg">'
            f'<strong>Erro:</strong> {e}</div>'
        )
