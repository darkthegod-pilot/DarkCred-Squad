"""
Gestor de Referências — Alina Pretrov
Downloads e mantém a biblioteca de assets externos: fontes profissionais,
guias de design, specs de plataforma.

Fontes baixadas do Google Fonts (licença OFL — uso comercial permitido):
  Montserrat Black 900   — headlines de máximo impacto
  Montserrat ExtraBold   — subheadlines e CTA
  Bebas Neue             — display alternativo dramático
  Inter Bold             — corpo de texto e CTA menor
  Inter Regular          — corpo secundário

Uso:
    from alina.gestor_referencias import garantir_referencias
    refs = garantir_referencias()   # retorna dict com caminhos locais
    # refs["Montserrat-Black"] → "assets/fonts/Montserrat-Black.ttf"
"""

import json
import urllib.request
import urllib.error
from pathlib import Path

ASSETS_FONTS = Path(__file__).parent.parent / "assets" / "fonts"
ASSETS_REFS  = Path(__file__).parent.parent / "assets" / "referencias"

# ─────────────────────────────────────────────────────────────
# Mapa de fontes: nome local → lista de URLs candidatas
# (tenta em ordem até uma funcionar)
# ─────────────────────────────────────────────────────────────
_GH_BASE   = "https://raw.githubusercontent.com/google/fonts/main/ofl"
_NOTO_BASE = "/usr/share/fonts/truetype/noto"

# Fontes: nome local → (urls externas, fallback local do sistema)
# Tenta URLs externas primeiro; se falhar, copia o fallback local.
# NotoSansDisplay-CondensedBlack é equivalente funcional do Montserrat Black
# para headline de alta conversão em ads — peso e condensado ideal.
FONTES: dict = {
    "Montserrat-Black": (
        [
            f"{_GH_BASE}/montserrat/static/Montserrat-Black.ttf",
            "https://fonts.gstatic.com/s/montserrat/v26/JTUFjIg1_i6t8kCHKm459Wx7xEDqNFhs.ttf",
        ],
        f"{_NOTO_BASE}/NotoSansDisplay-CondensedBlack.ttf",
    ),
    "Montserrat-ExtraBold": (
        [
            f"{_GH_BASE}/montserrat/static/Montserrat-ExtraBold.ttf",
        ],
        f"{_NOTO_BASE}/NotoSansDisplay-ExtraBold.ttf",
    ),
    "BebasNeue-Regular": (
        [
            f"{_GH_BASE}/bebasneuepro/BebasNeuePro-Regular.ttf",
        ],
        f"{_NOTO_BASE}/NotoSansDisplay-CondensedExtraBold.ttf",
    ),
    "Inter-Bold": (
        [
            f"{_GH_BASE}/inter/static/Inter_28pt-Bold.ttf",
            f"{_GH_BASE}/inter/static/Inter-Bold.ttf",
        ],
        f"{_NOTO_BASE}/NotoSans-Bold.ttf",
    ),
    "Inter-Regular": (
        [
            f"{_GH_BASE}/inter/static/Inter_28pt-Regular.ttf",
            f"{_GH_BASE}/inter/static/Inter-Regular.ttf",
        ],
        f"{_NOTO_BASE}/NotoSans-ExtraBold.ttf",
    ),
}

# ─────────────────────────────────────────────────────────────
# JSONs de princípios de design (gerados localmente)
# ─────────────────────────────────────────────────────────────
_DESIGN_PRINCIPLES = {
    "fonte": "Pesquisa: Google Fonts, Figma Community, Smashing Magazine Fintech 2025",
    "tipografia": {
        "headline_px":   {"min": 72, "ideal": 88, "max": 108},
        "subhead_px":    {"min": 40, "ideal": 52, "max": 64},
        "corpo_px":      {"min": 28, "ideal": 36, "max": 44},
        "cta_px":        {"min": 34, "ideal": 42, "max": 52},
        "contraste_min_ratio": 4.5,
        "max_linhas_hook": 3,
        "max_chars_primeira_linha": 80,
    },
    "composicao": {
        "margem_min_px":      56,
        "safe_zone_top_pct":  0.12,
        "safe_zone_bot_pct":  0.08,
        "max_texto_area_pct": 0.20,
        "thumb_stop_zone":    "top 33% must have strong visual anchor",
    },
    "fontes_por_tier": {
        "display":  ["Montserrat-Black",     "BebasNeue-Regular", "Poppins-Bold"],
        "bold":     ["Montserrat-ExtraBold", "Inter-Bold",        "Poppins-Bold"],
        "semibold": ["Inter-Bold",           "Montserrat-ExtraBold", "Poppins-SemiBold"],
        "regular":  ["Inter-Regular",        "Poppins-Regular"],
    },
    "pares_tipograficos": [
        {
            "headline": "Montserrat-Black",
            "corpo":    "Inter-Bold",
            "estilo":   "forte e moderno — fintech padrão",
        },
        {
            "headline": "BebasNeue-Regular",
            "corpo":    "Inter-Regular",
            "estilo":   "editorial e impactante — para segmentos dinâmicos",
        },
        {
            "headline": "Montserrat-ExtraBold",
            "corpo":    "Inter-Regular",
            "estilo":   "equilibrado e profissional — genérico seguro",
        },
    ],
}

_INSTAGRAM_SPECS = {
    "fonte":   "Instagram Advertiser Specs 2025 + Meta Ads Guide",
    "formato": {
        "feed_quadrado": {"w": 1080, "h": 1080, "ratio": "1:1"},
        "feed_retrato":  {"w": 1080, "h": 1350, "ratio": "4:5"},
        "stories":       {"w": 1080, "h": 1920, "ratio": "9:16"},
    },
    "limites_texto": {
        "max_pct_area":    20,
        "primeira_linha":  125,
        "headline_chars":  40,
        "descricao_chars": 30,
    },
    "safe_zones_px": {
        "top":    130,
        "bottom": 220,
        "sides":  50,
    },
    "compliance_visual": {
        "proibido": [
            "R$ + valor numérico",
            "percentual de juros (%)",
            "aprovado / garantido / imediato",
            "sem consulta SPC/Serasa",
            "pessoas em sofrimento financeiro",
        ],
        "permitido": [
            "comerciante feliz/confiante em ambiente de trabalho",
            "capital de giro / sem burocracia",
            "moedas douradas genéricas",
            "texto com termos aprovados DarkCred",
        ],
    },
}

_FINTECH_PALETTES = {
    "fonte":    "Referência: Nubank, Inter, Stone, PicPay — identidades visuais 2024-2025",
    "paletas": [
        {
            "nome":    "DarkCred Padrão",
            "hook":    [255, 107,  53],
            "overlay": [ 13,  27,  75],
            "cta":     [255, 200,   0],
            "acento":  [255, 107,  53],
        },
        {
            "nome":    "Confiança Profunda",
            "hook":    [255, 255, 255],
            "overlay": [ 10,  20,  60],
            "cta":     [255, 180,   0],
            "acento":  [ 60, 120, 220],
        },
        {
            "nome":    "Energia Comerciante",
            "hook":    [255, 230,   0],
            "overlay": [ 20,  20,  30],
            "cta":     [255, 107,  53],
            "acento":  [255, 230,   0],
        },
    ],
}


# ─────────────────────────────────────────────────────────────
# Download
# ─────────────────────────────────────────────────────────────

def _baixar_fonte(nome: str, urls: list, fallback_local: str | None = None) -> str | None:
    """
    Tenta baixar de cada URL em ordem.
    Se todas falharem e um caminho local de fallback for fornecido, copia-o.
    Retorna caminho local ou None.
    """
    import shutil
    ASSETS_FONTS.mkdir(parents=True, exist_ok=True)
    dest = ASSETS_FONTS / f"{nome}.ttf"

    if dest.exists() and dest.stat().st_size > 10_000:
        return str(dest)

    for url in urls:
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=15) as resp:
                data = resp.read()
            if len(data) < 5_000:
                continue
            dest.write_bytes(data)
            print(f"    ✅ {nome}.ttf baixado ({len(data)//1024}KB)")
            return str(dest)
        except Exception:
            continue

    # Fallback: usa fonte do sistema
    if fallback_local and Path(fallback_local).exists():
        shutil.copy2(fallback_local, dest)
        print(f"    ✅ {nome}.ttf copiado do sistema ({dest.stat().st_size//1024}KB)")
        return str(dest)

    print(f"    ⚠️  {nome}.ttf indisponível — fallback Poppins")
    return None


def _salvar_jsons():
    """Salva os JSONs de referência de design."""
    ASSETS_REFS.mkdir(parents=True, exist_ok=True)
    arquivos = {
        "design_principles.json":    _DESIGN_PRINCIPLES,
        "instagram_ad_specs.json":   _INSTAGRAM_SPECS,
        "fintech_color_palette.json": _FINTECH_PALETTES,
    }
    for nome, dados in arquivos.items():
        path = ASSETS_REFS / nome
        if not path.exists():
            path.write_text(json.dumps(dados, ensure_ascii=False, indent=2))
            print(f"    ✅ {nome} salvo")


# ─────────────────────────────────────────────────────────────
# API pública
# ─────────────────────────────────────────────────────────────

_cache: dict | None = None


def garantir_referencias(verbose: bool = False) -> dict:
    """
    Garante que fontes e JSONs de referência estão disponíveis localmente.
    Faz download na primeira execução; subsequentes usam cache.

    Retorna dict: nome_fonte → caminho_local (ou None se falhou).
    """
    global _cache
    if _cache is not None:
        return _cache

    if verbose:
        print("  Verificando biblioteca de referências...")

    _salvar_jsons()

    resultado = {}
    for nome, (urls, fallback) in FONTES.items():
        resultado[nome] = _baixar_fonte(nome, urls, fallback)

    _cache = resultado
    return resultado


def carregar_principios() -> dict:
    """Lê design_principles.json. Cria se não existir."""
    garantir_referencias()
    path = ASSETS_REFS / "design_principles.json"
    return json.loads(path.read_text())


def caminho_fonte(nome: str) -> str | None:
    """Retorna caminho local de uma fonte pelo nome. Ex: 'Montserrat-Black'."""
    refs = garantir_referencias()
    return refs.get(nome)
