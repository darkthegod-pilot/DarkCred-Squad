"""Dashboard principal — KPIs do sistema de aprendizado."""
import json
from datetime import datetime, timedelta
from pathlib import Path

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from web.auth import require_auth

router = APIRouter()
ROOT = Path(__file__).parent.parent.parent
templates = Jinja2Templates(directory=str(ROOT / "web" / "templates"))

HISTORICO   = ROOT / "dados" / "historico.json"
APRENDIZADO = ROOT / "dados" / "aprendizado.json"
RESULTADOS  = ROOT / "dados" / "resultados"


def _load(path: Path, default):
    if path.exists():
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            pass
    return default


def _semana_atras() -> str:
    return (datetime.now() - timedelta(weeks=1)).isoformat()


def _build_data() -> dict:
    historico   = _load(HISTORICO, [])
    aprendizado = _load(APRENDIZADO, {})

    resultados = []
    if RESULTADOS.exists():
        for f in sorted(RESULTADOS.glob("resultado_*.json"), reverse=True)[:5]:
            try:
                resultados.append(json.loads(f.read_text(encoding="utf-8")))
            except Exception:
                pass

    corte = _semana_atras()
    semana = [e for e in historico if e.get("data", "") >= corte]

    hooks_perf = aprendizado.get("hooks_performance", {})
    top_hooks  = sorted(hooks_perf.items(), key=lambda x: x[1], reverse=True)[:6]
    max_score  = max((s for _, s in top_hooks), default=1) or 1

    metricas = aprendizado.get("metricas_historicas", {})
    custos   = metricas.get("custo_medio_mensagem", [])
    freqs    = metricas.get("frequencia_media", [])

    return {
        "total_geracoes":   aprendizado.get("total_gerações", 0),
        "total_analises":   aprendizado.get("total_analises", 0),
        "segmentos_ativos": aprendizado.get("segmentos_ativos", []),
        "padroes_venc":     aprendizado.get("padroes_vencedores", [])[:5],
        "padroes_evitar":   aprendizado.get("padroes_a_evitar", [])[:3],
        "aprovados_semana": sum(e.get("aprovados", 0) for e in semana),
        "n_semana":         len(semana),
        "custo_medio":      f"R$ {sum(custos)/len(custos):.2f}" if custos else "—",
        "freq_media":       f"{sum(freqs)/len(freqs):.1f}" if freqs else "—",
        "top_hooks":        [(h, s, int(s / max_score * 100)) for h, s in top_hooks if s > 0],
        "geracoes_recentes": list(reversed(historico[-8:])),
        "resultados":        resultados,
    }


@router.get("/dashboard", response_class=HTMLResponse)
async def dashboard_page(request: Request):
    require_auth(request)
    data = _build_data()
    return templates.TemplateResponse("dashboard.html", {"request": request, **data})


@router.get("/dashboard/data", response_class=HTMLResponse)
async def dashboard_data(request: Request):
    """Partial HTMX — retorna só os KPI cards."""
    require_auth(request)
    data = _build_data()
    return templates.TemplateResponse("partials/kpi_cards.html", {"request": request, **data})
