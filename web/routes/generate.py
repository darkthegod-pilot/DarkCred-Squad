"""Geração de copies e imagens via formulário HTMX."""
import asyncio
import shutil
import tempfile
import traceback
import sys
from pathlib import Path

from fastapi import APIRouter, File, Form, Request, UploadFile
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from web.auth import require_auth

ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(ROOT))

router    = APIRouter()
templates = Jinja2Templates(directory=str(ROOT / "web" / "templates"))

_LABELS = {
    "generico":      "Genérico",
    "padaria":       "Padaria",
    "pizzaria":      "Pizzaria",
    "barbearia":     "Barbearia",
    "salao":         "Salão de Beleza",
    "lanchonete":    "Lanchonete",
    "acai":          "Açaí",
    "restaurante":   "Restaurante",
    "food_truck":    "Food Truck",
    "vestuario":     "Vestuário",
    "farmacia":      "Farmácia",
    "mercadinho":    "Mercadinho",
    "academia":      "Academia",
    "manicure":      "Manicure / Nail",
    "estetica":      "Estética",
    "mecanico":      "Mecânico",
    "variedades":    "Loja de Variedades",
    "pastelaria":    "Pastelaria",
    "bar":           "Bar / Boteco",
    "pet_shop":      "Pet Shop",
    "hortifruti":    "Hortifruti",
    "sorveteria":    "Sorveteria",
    "lavanderia":    "Lavanderia",
    "eletronicos":   "Eletrônicos",
    "relojoaria":    "Relojoaria",
    "sapataria":     "Sapataria",
    "taxi_uber":     "Motorista de App",
    "mototaxi":      "Mototaxi / Motoboy",
    "aula_particular": "Prof. Autônomo",
    "artesanato":    "Artesão / Costureira",
    "mei_generico":  "MEI / Autônomo",
}


def _get_segmentos_labels() -> list[tuple[str, str]]:
    """Retorna [(key, label_formatado)] — generico primeiro."""
    try:
        from alina.config import SEGMENTOS
        keys = sorted(SEGMENTOS.keys())
    except Exception:
        keys = ["generico", "padaria", "barbearia", "pizzaria"]

    if "generico" in keys:
        keys.remove("generico")
        keys.insert(0, "generico")

    return [(k, _LABELS.get(k, k.replace("_", " ").title())) for k in keys]


def _html_erro(msg: str, detalhe: str = "") -> str:
    det = (
        f'<div style="margin-top:8px;font-family:monospace;font-size:11px;'
        f'opacity:.6;word-break:break-all">{detalhe}</div>'
    ) if detalhe else ""
    return (
        f'<div class="alert alert-error">'
        f'<strong>⚠️ {msg}</strong>{det}'
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
    request:    Request,
    segmento:   str = Form("generico"),
    quantidade: int = Form(3),
    dicas:      str = Form(""),
):
    require_auth(request)
    quantidade = max(1, min(quantidade, 8))

    try:
        from alina.gerador import gerar_variacoes

        variacoes = await asyncio.to_thread(
            gerar_variacoes, segmento, quantidade, "claude-sonnet-4-6", dicas
        )

        seg_label = _LABELS.get(segmento, segmento.replace("_", " ").title())
        return templates.TemplateResponse("partials/copy_result.html", {
            "request":   request,
            "variacoes": variacoes,
            "segmento":  segmento,
            "seg_label": seg_label,
        })

    except Exception as e:
        tb = traceback.format_exc()
        detalhe = tb.splitlines()[-2] if tb else ""
        return HTMLResponse(_html_erro(f"Erro ao gerar copies: {e}", detalhe))


@router.post("/generate/image", response_class=HTMLResponse)
async def generate_image(
    request:         Request,
    segmento:        str         = Form("generico"),
    hook:            str         = Form(""),
    corpo:           str         = Form(""),
    cta:             str         = Form(""),
    foto_referencia: UploadFile  = File(None),
):
    require_auth(request)

    foto_path = ""
    if foto_referencia and foto_referencia.filename:
        suffix = Path(foto_referencia.filename).suffix or ".jpg"
        tmp = tempfile.NamedTemporaryFile(delete=False, suffix=suffix)
        shutil.copyfileobj(foto_referencia.file, tmp)
        tmp.close()
        foto_path = tmp.name

    try:
        from alina.pipeline_criativo import executar_pipeline

        variacao  = {"hook": hook, "corpo": corpo, "cta": cta}
        resultado = await asyncio.to_thread(
            executar_pipeline, variacao, segmento, False, foto_path
        )

        filename = Path(resultado.img_path).name if resultado.img_path else ""

        if filename:
            return templates.TemplateResponse("partials/image_card.html", {
                "request":  request,
                "filename": filename,
                "segmento": segmento,
                "url":      resultado.url or "",
                "aprovado": resultado.aprovado,
                "score":    resultado.review.score_total,
            })
        return HTMLResponse(
            '<div class="alert alert-info">Imagem gerada mas caminho não encontrado.</div>'
        )

    except Exception as e:
        tb = traceback.format_exc()
        detalhe = tb.splitlines()[-2] if tb else ""
        return HTMLResponse(_html_erro(f"Erro ao gerar imagem: {e}", detalhe))
    finally:
        if foto_path:
            try:
                Path(foto_path).unlink()
            except Exception:
                pass
