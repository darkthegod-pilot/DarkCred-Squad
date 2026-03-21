"""Geração de copies e imagens via formulário HTMX."""
import asyncio
import traceback
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

_LABELS = {
    "generico":    "Genérico",
    "padaria":     "Padaria",
    "pizzaria":    "Pizzaria",
    "barbearia":   "Barbearia",
    "salao":       "Salão de Beleza",
    "lanchonete":  "Lanchonete",
    "acai":        "Açaí",
    "restaurante": "Restaurante",
    "food_truck":  "Food Truck",
    "vestuario":   "Vestuário",
    "farmacia":    "Farmácia",
    "mercadinho":  "Mercadinho",
    "academia":    "Academia",
    "manicure":    "Manicure / Nail",
    "estetica":    "Estética",
    "mecanico":    "Mecânico",
    "variedades":  "Loja de Variedades",
}


def _get_segmentos_labels() -> list[tuple[str, str]]:
    """Retorna [(key, label_formatado)] ordenado, generico primeiro."""
    try:
        from alina.config import SEGMENTOS
        keys = sorted(SEGMENTOS.keys())
    except Exception:
        keys = ["generico", "padaria", "barbearia", "pizzaria"]

    # garante generico primeiro
    if "generico" in keys:
        keys.remove("generico")
        keys.insert(0, "generico")

    return [(k, _LABELS.get(k, k.replace("_", " ").title())) for k in keys]


def _html_erro(msg: str, detalhe: str = "") -> str:
    detalhe_html = (
        f'<div style="margin-top:8px;font-family:monospace;font-size:11px;opacity:.65;'
        f'word-break:break-all">{detalhe}</div>'
    ) if detalhe else ""
    return (
        f'<div class="alert alert-error">'
        f'<strong>⚠️ {msg}</strong>'
        f'{detalhe_html}'
        f'</div>'
    )


@router.get("/generate", response_class=HTMLResponse)
async def generate_page(request: Request):
    require_auth(request)
    return templates.TemplateResponse("generate.html", {
        "request":          request,
        "segmentos_labels": _get_segmentos_labels(),
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

        variacoes = await asyncio.to_thread(gerar_variacoes, segmento, quantidade)

        seg_label = _LABELS.get(segmento, segmento.replace("_", " ").title())
        return templates.TemplateResponse("partials/copy_result.html", {
            "request":   request,
            "variacoes": variacoes,
            "segmento":  segmento,
            "seg_label": seg_label,
        })

    except Exception as e:
        detalhe = traceback.format_exc().splitlines()[-2] if traceback.format_exc() else ""
        return HTMLResponse(_html_erro(f"Erro ao gerar copies: {e}", detalhe))


@router.post("/generate/image", response_class=HTMLResponse)
async def generate_image(
    request: Request,
    segmento: str = Form("generico"),
    hook: str = Form(""),
    corpo: str = Form(""),
    cta: str = Form(""),
):
    require_auth(request)

    try:
        from alina.pipeline_criativo import executar_pipeline

        variacao = {"hook": hook, "corpo": corpo, "cta": cta}
        resultado = await asyncio.to_thread(executar_pipeline, variacao, segmento, False)

        filename = Path(resultado.img_path).name if resultado.img_path else ""

        if filename:
            return templates.TemplateResponse("partials/image_card.html", {
                "request":  request,
                "filename": filename,
                "segmento": segmento,
                "url":      resultado.url or "",
            })
        return HTMLResponse(
            '<div class="alert alert-info">Imagem gerada mas caminho não encontrado.</div>'
        )

    except Exception as e:
        detalhe = traceback.format_exc().splitlines()[-2] if traceback.format_exc() else ""
        return HTMLResponse(_html_erro(f"Erro ao gerar imagem: {e}", detalhe))
