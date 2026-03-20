"""
Gerador de Imagens com IA — Alina Pretrov
GPT-image-1 quality="high" + composição tipográfica sem badges genéricos.

4 Layouts Únicos (selecionados pelo pipeline):
  TIPOGRAFIA_FORTE      — headline gigante (96px), sem enfeites, 1 cor de destaque
  SPLIT_DIAGONAL        — faixa diagonal no canto separa foto do texto
  HEADLINE_CENTRALIZADA — bloco de texto centralizado com linhas decorativas finas
  LATERAL_ESQUERDA      — coluna de texto à esquerda, foto domina a direita

Suporte a melhorias iterativas via parâmetro `melhorias: list[str]`
quando chamado pela segunda ou terceira vez pelo pipeline.

Saída: PNG 1024×1024 sem marca d'água, pronto para Meta Ads.
"""

import base64
import os
from datetime import datetime
from pathlib import Path
from typing import Optional

try:
    import anthropic as _anthropic_sdk
    ANTHROPIC_SDK_DISPONIVEL = True
except ImportError:
    ANTHROPIC_SDK_DISPONIVEL = False

try:
    import openai as _openai_sdk
    OPENAI_SDK_DISPONIVEL = True
except ImportError:
    OPENAI_SDK_DISPONIVEL = False

try:
    from PIL import Image, ImageDraw, ImageFont
    import io as _io
    PILLOW_DISPONIVEL = True
except ImportError:
    PILLOW_DISPONIVEL = False

try:
    import numpy as np
    NUMPY_DISPONIVEL = True
except ImportError:
    NUMPY_DISPONIVEL = False


DIRETORIO_SAIDA = Path("saidas/imagens")
ASSETS_FONTS    = Path(__file__).parent.parent / "assets" / "fonts"

# Paleta base
LARANJA     = (255, 107,  53)
LARANJA_E   = (190,  65,  15)
BRANCO      = (255, 255, 255)
CINZA_CLARO = (220, 220, 220)
NAVY        = ( 13,  27,  75)
DOURADO     = (255, 200,   0)
SOMBRA      = (  0,   0,   0)

LAYOUTS = ["TIPOGRAFIA_FORTE", "SPLIT_DIAGONAL", "HEADLINE_CENTRALIZADA", "LATERAL_ESQUERDA"]


# ─────────────────────────────────────────────────────────────
# FONTS
# ─────────────────────────────────────────────────────────────

_FONT_CACHE: dict = {}

def _fonte(tamanho: int, peso: str = "bold") -> "ImageFont.FreeTypeFont":
    key = (tamanho, peso)
    if key in _FONT_CACHE:
        return _FONT_CACHE[key]
    candidatos = {
        "bold":     [str(ASSETS_FONTS / "Poppins-Bold.ttf"),
                     "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf"],
        "semibold": [str(ASSETS_FONTS / "Poppins-SemiBold.ttf"),
                     str(ASSETS_FONTS / "Poppins-Bold.ttf"),
                     "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf"],
        "regular":  [str(ASSETS_FONTS / "Poppins-Regular.ttf"),
                     "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf"],
    }
    for caminho in candidatos.get(peso, candidatos["regular"]):
        if Path(caminho).exists():
            try:
                f = ImageFont.truetype(caminho, tamanho)
                _FONT_CACHE[key] = f
                return f
            except Exception:
                continue
    f = ImageFont.load_default()
    _FONT_CACHE[key] = f
    return f


# ─────────────────────────────────────────────────────────────
# HELPERS TIPOGRÁFICOS
# ─────────────────────────────────────────────────────────────

def _limpar(texto: str) -> str:
    import unicodedata
    out = []
    for ch in texto:
        cp  = ord(ch)
        cat = unicodedata.category(ch)
        if (cp < 0x2000 or cat.startswith("L") or cat.startswith("N")
                or cat in ("Po", "Pd", "Ps", "Pe", "Pc", "Zs")):
            out.append(ch)
        else:
            out.append(" ")
    return " ".join("".join(out).split())


def _quebrar(texto: str, fonte: "ImageFont.FreeTypeFont", max_px: int) -> list:
    palavras = texto.split()
    linhas, atual = [], ""
    for p in palavras:
        cand = (atual + " " + p).strip()
        w    = fonte.getbbox(cand)[2] - fonte.getbbox(cand)[0]
        if w <= max_px:
            atual = cand
        else:
            if atual:
                linhas.append(atual)
            atual = p
    if atual:
        linhas.append(atual)
    return linhas


def _tw(texto: str, fonte) -> int:
    bb = fonte.getbbox(texto)
    return bb[2] - bb[0]


def _th(texto: str, fonte) -> int:
    bb = fonte.getbbox(texto)
    return bb[3] - bb[1]


def _draw_sombra(draw, x, y, texto, fonte, cor, offset=3):
    for dx, dy in [(-offset, -offset), (offset, -offset),
                   (-offset,  offset), (offset,  offset)]:
        draw.text((x + dx, y + dy), texto, font=fonte, fill=(*SOMBRA, 160))
    draw.text((x, y), texto, font=fonte, fill=cor)


# ─────────────────────────────────────────────────────────────
# OVERLAY BASE — Gradiente escuro no terço inferior
# ─────────────────────────────────────────────────────────────

def _overlay_base(img: "Image.Image", inicio_pct: float = 0.35,
                  cor: tuple = NAVY, opac_max: int = 220) -> "Image.Image":
    W, H    = img.size
    base    = img.convert("RGBA")
    overlay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    draw    = ImageDraw.Draw(overlay)
    inicio  = int(H * inicio_pct)
    fim     = int(H * (inicio_pct + 0.20))
    r, g, b = cor
    for y in range(inicio, fim):
        t = (y - inicio) / max(fim - inicio, 1)
        draw.line([(0, y), (W, y)], fill=(r, g, b, int(opac_max * t)))
    draw.rectangle([0, fim, W, H], fill=(r, g, b, opac_max))
    return Image.alpha_composite(base, overlay).convert("RGB")


def _overlay_lateral(img: "Image.Image") -> "Image.Image":
    """Overlay para LATERAL_ESQUERDA: gradiente da esquerda para direita."""
    W, H    = img.size
    base    = img.convert("RGBA")
    overlay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    draw    = ImageDraw.Draw(overlay)
    r, g, b = NAVY
    fim_solido = int(W * 0.52)
    ini_trans  = int(W * 0.40)
    draw.rectangle([0, 0, ini_trans, H], fill=(r, g, b, 230))
    for x in range(ini_trans, fim_solido):
        t = (x - ini_trans) / max(fim_solido - ini_trans, 1)
        draw.line([(x, 0), (x, H)], fill=(r, g, b, int(230 * (1 - t))))
    return Image.alpha_composite(base, overlay).convert("RGB")


def _overlay_diagonal(img: "Image.Image") -> "Image.Image":
    """Overlay para SPLIT_DIAGONAL: gradiente diagonal no canto inferior esquerdo."""
    W, H    = img.size
    base    = img.convert("RGBA")
    overlay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    draw    = ImageDraw.Draw(overlay)
    r, g, b = NAVY
    # Bloco diagonal — cobrindo a metade inferior com inclinação
    pontos = [(0, int(H * 0.45)), (W, int(H * 0.60)), (W, H), (0, H)]
    draw.polygon(pontos, fill=(r, g, b, 210))
    # Gradiente de transição acima do polígono
    for y in range(int(H * 0.30), int(H * 0.60)):
        t = (y - int(H * 0.30)) / max(int(H * 0.30), 1)
        a = int(180 * t * t)
        draw.line([(0, y), (W, y)], fill=(r, g, b, a))
    return Image.alpha_composite(base, overlay).convert("RGB")


# ─────────────────────────────────────────────────────────────
# LAYOUTS DE COMPOSIÇÃO
# ─────────────────────────────────────────────────────────────

def _layout_tipografia_forte(img: "Image.Image", variacao: dict) -> "Image.Image":
    """
    TIPOGRAFIA_FORTE — headline gigante, corpo minimalista, linha diagonal de acento.
    Hierarquia: HEADLINE (96px laranja) → linha fina dourada → corpo (42px branco) → CTA
    """
    img  = _overlay_base(img, inicio_pct=0.30, opac_max=215)
    W, H = img.size
    draw = ImageDraw.Draw(img)

    hook  = _limpar(variacao.get("hook",  ""))
    corpo = _limpar(variacao.get("corpo", variacao.get("body", "")))
    cta   = variacao.get("cta", "Me chama que a gente conversa")

    f_hook  = _fonte(88, "bold")
    f_corpo = _fonte(40, "semibold")
    f_cta   = _fonte(38, "bold")
    margem  = 64
    max_w   = W - margem * 2

    linhas_hook  = _quebrar(hook,  f_hook,  max_w)
    linhas_corpo = _quebrar(corpo, f_corpo, max_w)

    # Altura total do bloco
    h_hook  = sum(_th(l, f_hook)  + 14 for l in linhas_hook)
    h_sep   = 32
    h_corpo = sum(_th(l, f_corpo) + 10 for l in linhas_corpo)
    h_cta   = 72
    h_total = h_hook + h_sep + h_corpo + 44 + h_cta
    y       = H - h_total - 50

    # Hook
    for linha in linhas_hook:
        lw = _tw(linha, f_hook)
        _draw_sombra(draw, (W - lw) // 2, y, linha, f_hook, LARANJA, offset=4)
        y += _th(linha, f_hook) + 14

    # Linha de acento dourada
    y += 8
    larg = min(int(_tw(linhas_hook[0], f_hook) * 0.6), 320)
    draw.line([(W // 2 - larg // 2, y), (W // 2 + larg // 2, y)],
              fill=DOURADO, width=4)
    y += 24

    # Corpo
    for linha in linhas_corpo:
        lw = _tw(linha, f_corpo)
        _draw_sombra(draw, (W - lw) // 2, y, linha, f_corpo, CINZA_CLARO, offset=2)
        y += _th(linha, f_corpo) + 10

    # CTA — texto simples sublinhado (sem botão preenchido)
    y += 30
    cta_limpo = _limpar(cta)
    cw = _tw(cta_limpo, f_cta)
    cx = (W - cw) // 2
    cy = y
    _draw_sombra(draw, cx, cy, cta_limpo, f_cta, BRANCO, offset=2)
    # Sublinhado dourado
    ch = _th(cta_limpo, f_cta)
    draw.line([(cx, cy + ch + 4), (cx + cw, cy + ch + 4)],
              fill=DOURADO, width=3)

    return img


def _layout_split_diagonal(img: "Image.Image", variacao: dict) -> "Image.Image":
    """
    SPLIT_DIAGONAL — faixa diagonal escura na base + texto alinhado à esquerda.
    Visual: energético, editorial, foge do template padrão.
    """
    img  = _overlay_diagonal(img)
    W, H = img.size
    draw = ImageDraw.Draw(img)

    hook  = _limpar(variacao.get("hook",  ""))
    corpo = _limpar(variacao.get("corpo", variacao.get("body", "")))
    cta   = variacao.get("cta", "Me chama que a gente conversa")

    f_hook  = _fonte(80, "bold")
    f_corpo = _fonte(36, "semibold")
    f_cta   = _fonte(34, "bold")
    margem  = 56
    max_w   = W - margem * 2

    linhas_hook  = _quebrar(hook,  f_hook,  max_w)
    linhas_corpo = _quebrar(corpo, f_corpo, max_w)

    h_hook  = sum(_th(l, f_hook)  + 12 for l in linhas_hook)
    h_sep   = 24
    h_corpo = sum(_th(l, f_corpo) + 8  for l in linhas_corpo)
    h_cta   = 60
    h_total = h_hook + h_sep + h_corpo + 36 + h_cta
    y       = H - h_total - 44

    # Hook — alinhado à esquerda com barra vertical de acento
    bar_w, bar_h = 6, h_hook - 10
    draw.rectangle([margem, y + 4, margem + bar_w, y + bar_h],
                   fill=LARANJA)
    txt_x = margem + bar_w + 16

    for linha in linhas_hook:
        _draw_sombra(draw, txt_x, y, linha, f_hook, BRANCO, offset=3)
        y += _th(linha, f_hook) + 12

    # Linha divisória fina
    y += 4
    draw.line([(margem, y), (W - margem, y)], fill=(*LARANJA, 140), width=2)
    y += 20

    # Corpo
    for linha in linhas_corpo:
        _draw_sombra(draw, margem, y, linha, f_corpo, CINZA_CLARO, offset=2)
        y += _th(linha, f_corpo) + 8

    # CTA
    y += 24
    cta_limpo = _limpar(cta)
    _draw_sombra(draw, margem, y, f">> {cta_limpo}", f_cta, DOURADO, offset=2)

    return img


def _layout_headline_centralizada(img: "Image.Image", variacao: dict) -> "Image.Image":
    """
    HEADLINE_CENTRALIZADA — bloco de texto centralizado com linhas horizontais decorativas.
    Visual: limpo, premium, confiança.
    """
    img  = _overlay_base(img, inicio_pct=0.28, opac_max=225)
    W, H = img.size
    draw = ImageDraw.Draw(img)

    hook  = _limpar(variacao.get("hook",  ""))
    corpo = _limpar(variacao.get("corpo", variacao.get("body", "")))
    cta   = variacao.get("cta", "Me chama que a gente conversa")

    f_hook  = _fonte(82, "bold")
    f_corpo = _fonte(38, "semibold")
    f_cta   = _fonte(36, "bold")
    margem  = 70
    max_w   = W - margem * 2

    linhas_hook  = _quebrar(hook,  f_hook,  max_w)
    linhas_corpo = _quebrar(corpo, f_corpo, max_w)

    h_hook  = sum(_th(l, f_hook)  + 12 for l in linhas_hook)
    h_corpo = sum(_th(l, f_corpo) + 8  for l in linhas_corpo)
    h_total = 24 + h_hook + 32 + h_corpo + 40 + 60
    y       = H - h_total - 48

    # Linha superior decorativa dupla
    draw.line([(margem, y), (W - margem, y)], fill=BRANCO, width=2)
    draw.line([(margem + 20, y + 6), (W - margem - 20, y + 6)],
              fill=LARANJA, width=1)
    y += 22

    # Hook centralizado
    for linha in linhas_hook:
        lw = _tw(linha, f_hook)
        _draw_sombra(draw, (W - lw) // 2, y, linha, f_hook, BRANCO, offset=4)
        y += _th(linha, f_hook) + 12

    y += 10
    # Corpo
    for linha in linhas_corpo:
        lw = _tw(linha, f_corpo)
        _draw_sombra(draw, (W - lw) // 2, y, linha, f_corpo, CINZA_CLARO, offset=2)
        y += _th(linha, f_corpo) + 8

    # Linha inferior decorativa
    y += 12
    draw.line([(margem + 20, y), (W - margem - 20, y)], fill=LARANJA, width=1)
    draw.line([(margem, y + 6), (W - margem, y + 6)], fill=BRANCO, width=2)
    y += 22

    # CTA centralizado em dourado
    cta_limpo = _limpar(cta)
    cw = _tw(cta_limpo, f_cta)
    _draw_sombra(draw, (W - cw) // 2, y, cta_limpo, f_cta, DOURADO, offset=2)

    return img


def _layout_lateral_esquerda(img: "Image.Image", variacao: dict) -> "Image.Image":
    """
    LATERAL_ESQUERDA — coluna de texto na lateral esquerda.
    Visual: editorial, moderno, máximo destaque para a foto.
    """
    img  = _overlay_lateral(img)
    W, H = img.size
    draw = ImageDraw.Draw(img)

    hook  = _limpar(variacao.get("hook",  ""))
    corpo = _limpar(variacao.get("corpo", variacao.get("body", "")))
    cta   = variacao.get("cta", "Me chama que a gente conversa")

    coluna_w = int(W * 0.48)
    f_hook   = _fonte(68, "bold")
    f_corpo  = _fonte(32, "semibold")
    f_cta    = _fonte(30, "bold")
    margem   = 44
    max_w    = coluna_w - margem * 2

    linhas_hook  = _quebrar(hook,  f_hook,  max_w)
    linhas_corpo = _quebrar(corpo, f_corpo, max_w)

    h_hook  = sum(_th(l, f_hook)  + 10 for l in linhas_hook)
    h_sep   = 20
    h_corpo = sum(_th(l, f_corpo) + 8  for l in linhas_corpo)
    h_total = h_hook + h_sep + h_corpo + 34 + 56
    y       = (H - h_total) // 2  # centralizado verticalmente na coluna

    # Acento laranja no topo da coluna
    draw.rectangle([margem, y - 12, margem + 80, y - 8], fill=LARANJA)

    # Hook
    for linha in linhas_hook:
        _draw_sombra(draw, margem, y, linha, f_hook, BRANCO, offset=3)
        y += _th(linha, f_hook) + 10

    # Separador
    y += 4
    draw.line([(margem, y), (coluna_w - margem, y)], fill=LARANJA, width=3)
    y += 16

    # Corpo
    for linha in linhas_corpo:
        _draw_sombra(draw, margem, y, linha, f_corpo, CINZA_CLARO, offset=2)
        y += _th(linha, f_corpo) + 8

    # CTA
    y += 18
    cta_limpo = _limpar(cta)
    _draw_sombra(draw, margem, y, cta_limpo, f_cta, DOURADO, offset=2)

    return img


# ─────────────────────────────────────────────────────────────
# DESPACHO DE LAYOUT
# ─────────────────────────────────────────────────────────────

_LAYOUT_FN = {
    "TIPOGRAFIA_FORTE":      _layout_tipografia_forte,
    "SPLIT_DIAGONAL":        _layout_split_diagonal,
    "HEADLINE_CENTRALIZADA": _layout_headline_centralizada,
    "LATERAL_ESQUERDA":      _layout_lateral_esquerda,
}


def _compor_texto(img: "Image.Image", variacao: dict,
                  layout: str = "TIPOGRAFIA_FORTE") -> "Image.Image":
    fn = _LAYOUT_FN.get(layout, _layout_tipografia_forte)
    return fn(img, variacao)


# ─────────────────────────────────────────────────────────────
# PROMPT GPT-image-1 — cenas por segmento
# ─────────────────────────────────────────────────────────────

_CENAS: dict = {
    "generico":   "a smiling confident Brazilian small business owner wearing an apron, arms crossed, standing in their shop, upper-right of frame",
    "padaria":    "a smiling Brazilian bakery owner behind the counter with fresh golden bread and warm soft lighting",
    "pizzaria":   "a smiling Brazilian pizzeria chef near a glowing pizza oven, tossing dough",
    "lanchonete": "a cheerful Brazilian snack bar owner behind a colorful counter",
    "restaurante":"a proud Brazilian restaurant owner in a warmly lit dining room, welcoming gesture",
    "acai":       "a vibrant Brazilian açaí shop attendant smiling, colorful cups visible",
    "salao":      "a Brazilian hairdresser in a modern salon with mirrors and styling chairs",
    "barbearia":  "a confident Brazilian barber in a stylish barbershop with professional tools",
    "manicure":   "a smiling Brazilian nail technician at a bright nail salon",
    "estetica":   "a professional Brazilian aesthetics technician in a clean modern studio",
    "academia":   "a confident Brazilian gym owner in a well-equipped fitness studio",
    "vestuario":  "a smiling Brazilian clothing store owner among racks of colorful garments",
    "mercadinho": "a proud Brazilian neighborhood market owner with shelves full of products",
    "mecanico":   "a skilled Brazilian mechanic in an auto repair shop, confident smile",
}

_LAYOUT_HINTS: dict = {
    "TIPOGRAFIA_FORTE":      "subject in upper third, lower 55% very dark navy blue for text",
    "SPLIT_DIAGONAL":        "subject on the right side, lower-left diagonal area dark navy for text",
    "HEADLINE_CENTRALIZADA": "subject behind or above center, lower 60% dark navy, clear vertical space for centered text",
    "LATERAL_ESQUERDA":      "subject positioned on the RIGHT half of frame, left half has dark navy gradient for text column",
}

_BASE_PROMPT = (
    "Ultra-vibrant cinematic commercial photography for a Brazilian Instagram ad. "
    "{cena}. "
    "Composition: {hint}. "
    "Dramatic warm golden/amber rim lighting on subject. Deep rich bokeh background. "
    "Ultra sharp focus on subject. Professional editorial quality. High energy, alive. "
    "Deep navy blue (#0D1B4B) in the designated text area (non-negotiable). "
    "NO text, NO logos, NO watermarks, NO readable signs. Perfect square 1:1."
)


def _construir_prompt(variacao: dict, segmento_key: str,
                      layout: str = "TIPOGRAFIA_FORTE",
                      melhorias: list = None) -> str:
    cena  = _CENAS.get(segmento_key, _CENAS["generico"])
    hint  = _LAYOUT_HINTS.get(layout, _LAYOUT_HINTS["TIPOGRAFIA_FORTE"])
    base  = _BASE_PROMPT.format(cena=cena, hint=hint)

    if melhorias:
        correcoes = " | ".join(melhorias[:4])
        base += f" VISUAL CORRECTIONS FOR THIS VERSION: {correcoes}"

    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not ANTHROPIC_SDK_DISPONIVEL or not api_key:
        return base
    try:
        client = _anthropic_sdk.Anthropic(api_key=api_key)
        r = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=380,
            system=(
                "You are a world-class art director for Brazilian fintech Instagram ads. "
                "Write a single English image generation prompt for GPT-image-1. "
                "CRITICAL: Follow the composition hint exactly. NO text/logos/watermarks. "
                "High energy and vibrant, NOT flat or stock-photo generic. "
                "Output ONLY the prompt."
            ),
            messages=[{"role": "user", "content":
                f"Hook: {variacao.get('hook', '')}\n"
                f"Segment: {segmento_key}\n"
                f"Layout: {layout}\n"
                f"Scene: {cena}\n"
                f"Composition hint: {hint}\n"
                + (f"Visual corrections needed: {correcoes}\n" if melhorias else "")
                + "Generate a premium vibrant commercial ad photography prompt."}],
        )
        return r.content[0].text.strip()
    except Exception:
        return base


# ─────────────────────────────────────────────────────────────
# GERAÇÃO DE FUNDO — GPT-image-1 quality="high"
# ─────────────────────────────────────────────────────────────

def _gerar_fundo(prompt: str) -> bytes:
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY não encontrada no .env")
    if not OPENAI_SDK_DISPONIVEL:
        raise RuntimeError("openai não instalado: pip install openai>=1.0.0")

    client = _openai_sdk.OpenAI(api_key=api_key)
    r = client.images.generate(
        model="gpt-image-1",
        prompt=prompt,
        size="1024x1024",
        quality="high",
        n=1,
        output_format="png",
    )
    return base64.b64decode(r.data[0].b64_json)


# ─────────────────────────────────────────────────────────────
# PONTO DE ENTRADA
# ─────────────────────────────────────────────────────────────

def gerar_criativo_ia(
    variacao: dict,
    segmento_key: str = "generico",
    layout: str = "TIPOGRAFIA_FORTE",
    melhorias: list = None,
    template: Optional[int] = None,   # ignorado — mantido por compatibilidade
) -> str:
    """
    Gera criativo 1024×1024 com GPT-image-1 quality="high".

    Parâmetros:
        variacao    — dict com hook, corpo, cta
        segmento_key— chave do segmento
        layout      — um dos 4 layouts: TIPOGRAFIA_FORTE, SPLIT_DIAGONAL,
                       HEADLINE_CENTRALIZADA, LATERAL_ESQUERDA
        melhorias   — lista de correções da revisão anterior (para iterações)

    Retorna caminho absoluto do PNG gerado.
    """
    if not PILLOW_DISPONIVEL:
        raise RuntimeError("Pillow não instalado: pip install Pillow")

    if layout not in _LAYOUT_FN:
        layout = "TIPOGRAFIA_FORTE"

    DIRETORIO_SAIDA.mkdir(parents=True, exist_ok=True)

    # 1. Prompt (com melhorias se houver)
    prompt = _construir_prompt(variacao, segmento_key, layout, melhorias)

    # 2. Fundo 1024×1024 nativo via GPT-image-1
    raw = _gerar_fundo(prompt)
    img = Image.open(_io.BytesIO(raw)).convert("RGB")

    # 3. Composição tipográfica (layout escolhido)
    img = _compor_texto(img, variacao, layout)

    # 4. Salva em máxima qualidade
    ts   = datetime.now().strftime("%Y%m%d_%H%M%S")
    nome = f"criativo_{segmento_key}_{layout.lower()}_{ts}.png"
    dest = DIRETORIO_SAIDA / nome
    img.save(str(dest), format="PNG", optimize=False, compress_level=1)
    return str(dest)
