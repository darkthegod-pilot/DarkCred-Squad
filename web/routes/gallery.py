"""Banco de Imagens — listar, filtrar e deletar criativos gerados."""
import re
from pathlib import Path
from datetime import datetime

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates

from web.auth import require_auth

router = APIRouter()
ROOT       = Path(__file__).parent.parent.parent
IMAGENS    = ROOT / "saidas" / "imagens"
templates  = Jinja2Templates(directory=str(ROOT / "web" / "templates"))


def _parse_filename(name: str) -> dict:
    """Extrai segmento e timestamp do nome do arquivo."""
    # Padrão: alina_padaria_20260320_040418_t1.png  ou  criativo_generico_...
    seg = "generico"
    ts  = ""
    parts = name.replace(".png", "").split("_")
    for i, p in enumerate(parts):
        if re.match(r"^\d{8}$", p):   # data YYYYMMDD
            ts = p
        elif i > 0 and not re.match(r"^\d", p) and p not in ("t1","t2","t3","ia","stories","v1","v2"):
            seg = p
            break
    return {"segment": seg, "ts": ts}


def _list_images(seg_filter: str = "") -> list[dict]:
    if not IMAGENS.exists():
        return []
    files = sorted(IMAGENS.glob("*.png"), key=lambda f: f.stat().st_mtime, reverse=True)
    result = []
    for f in files:
        info   = _parse_filename(f.name)
        seg    = info["segment"]
        if seg_filter and seg_filter.lower() not in seg.lower():
            continue
        mtime  = datetime.fromtimestamp(f.stat().st_mtime)
        result.append({
            "filename": f.name,
            "segment":  seg,
            "size_kb":  round(f.stat().st_size / 1024),
            "date":     mtime.strftime("%d/%m/%Y %H:%M"),
        })
    return result


def _all_segments() -> list[str]:
    segs = set()
    for img in _list_images():
        segs.add(img["segment"])
    return sorted(segs)


@router.get("/gallery", response_class=HTMLResponse)
async def gallery_page(request: Request, seg: str = ""):
    require_auth(request)
    images   = _list_images(seg)
    segments = _all_segments()
    return templates.TemplateResponse("gallery.html", {
        "request":  request,
        "images":   images,
        "segments": segments,
        "seg_filter": seg,
        "total":    len(images),
    })


@router.get("/gallery/filter", response_class=HTMLResponse)
async def gallery_filter(request: Request, seg: str = ""):
    """Partial HTMX — retorna só o grid de imagens."""
    require_auth(request)
    images = _list_images(seg)
    return templates.TemplateResponse("partials/image_grid.html", {
        "request": request,
        "images":  images,
        "total":   len(images),
    })


@router.delete("/gallery/{filename}")
async def gallery_delete(request: Request, filename: str):
    require_auth(request)
    # Sanitiza: evita path traversal
    filename = Path(filename).name
    target   = IMAGENS / filename
    if target.exists() and target.suffix == ".png":
        target.unlink()
        return HTMLResponse("", status_code=200, headers={"HX-Trigger": "galleryUpdated"})
    return JSONResponse({"erro": "Arquivo não encontrado"}, status_code=404)
