"""
Gerador de Imagens com IA — Alina Pretrov
GPT-image-1 quality="high" + composição tipográfica profissional.

Stack de fontes (3 tiers):
  Display : Montserrat Black 900  → headlines de máximo impacto
  Bold    : Montserrat ExtraBold  → subheadlines e CTAs fortes
  Body    : Inter Bold            → corpo legível, moderno

4 Layouts (selecionados pelo pipeline):
  TIPOGRAFIA_FORTE      — headline gigante 96px, minimalista, 1 cor de acento
  SPLIT_DIAGONAL        — faixa diagonal no terço inferior, texto à esquerda
  HEADLINE_CENTRALIZADA — bloco central com linhas decorativas duplas
  LATERAL_ESQUERDA      — coluna de texto na lateral, foto domina a direita

Suporte a DesignDecision — o revisor pode injetar parâmetros de posicionamento
via melhorias iterativas (ex: "hook_size:96", "overlay_start:0.40", "align:left").

Saída: PNG 1024×1024 sem marca d'água, pronto para Meta Ads.
"""

import base64
import os
import re
from dataclasses import dataclass, field
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

from .gestor_referencias import garantir_referencias, ASSETS_FONTS as _ASSETS_FONTS


DIRETORIO_SAIDA = Path("saidas/imagens")

# ─── Paleta base ────────────────────────────────────────────
LARANJA     = (255, 107,  53)
BRANCO      = (255, 255, 255)
CINZA_CLARO = (215, 215, 215)
NAVY        = ( 13,  27,  75)
DOURADO     = (255, 200,   0)
PRETO_SUAVE = ( 10,  10,  20)

LAYOUTS = ["TIPOGRAFIA_FORTE", "SPLIT_DIAGONAL",
           "HEADLINE_CENTRALIZADA", "LATERAL_ESQUERDA"]


# ─────────────────────────────────────────────────────────────
# DesignDecision — parâmetros autônomos de layout
# ─────────────────────────────────────────────────────────────

@dataclass
class DesignDecision:
    hook_size_px:       int   = 88
    hook_align:         str   = "center"    # "left" | "center"
    hook_y_pct:         float = 0.50        # onde começa o bloco de texto
    corpo_size_px:      int   = 38
    cta_size_px:        int   = 40
    overlay_start_pct:  float = 0.32        # início do gradiente escuro
    overlay_opacity:    int   = 210
    accent_color:       tuple = field(default_factory=lambda: LARANJA)
    cta_color:          tuple = field(default_factory=lambda: DOURADO)

    @classmethod
    def from_melhorias(cls, melhorias: list) -> "DesignDecision":
        """
        Parseia instruções de posicionamento das melhorias do revisor.
        Comandos reconhecidos: hook_size:N  hook_y:0.NN  align:left|center
          overlay_start:0.NN  overlay_opacity:N  corpo_size:N  cta_size:N
        """
        d = cls()
        for m in melhorias:
            for cmd, val in re.findall(r"(\w+):([0-9.a-z]+)", m.lower()):
                try:
                    if cmd == "hook_size":     d.hook_size_px      = int(val)
                    elif cmd == "corpo_size":  d.corpo_size_px     = int(val)
                    elif cmd == "cta_size":    d.cta_size_px       = int(val)
                    elif cmd == "hook_y":      d.hook_y_pct        = float(val)
                    elif cmd == "align":       d.hook_align        = str(val)
                    elif cmd == "overlay_start": d.overlay_start_pct = float(val)
                    elif cmd == "overlay_opacity": d.overlay_opacity = int(val)
                except (ValueError, TypeError):
                    pass
        return d


# ─────────────────────────────────────────────────────────────
# FONT SYSTEM
# ─────────────────────────────────────────────────────────────

_FONT_CACHE: dict = {}

def _resolve_font_path(nome: str) -> str | None:
    """Retorna caminho para uma fonte por nome, procurando em assets/fonts/."""
    local = _ASSETS_FONTS / f"{nome}.ttf"
    if local.exists():
        return str(local)
    # fallback sistema
    sistemas = {
        "Montserrat-Black":     "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
        "Montserrat-ExtraBold": "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
        "BebasNeue-Regular":    "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
        "Inter-Bold":           "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
        "Inter-Regular":        "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
        "Poppins-Bold":         str(_ASSETS_FONTS / "Poppins-Bold.ttf"),
        "Poppins-SemiBold":     str(_ASSETS_FONTS / "Poppins-SemiBold.ttf"),
        "Poppins-Regular":      str(_ASSETS_FONTS / "Poppins-Regular.ttf"),
    }
    return sistemas.get(nome)


def _fonte(tamanho: int, tier: str = "display") -> "ImageFont.FreeTypeFont":
    """
    tier:
      display  → Montserrat Black (máximo impacto para headlines)
      bold     → Montserrat ExtraBold (CTAs e subheads fortes)
      semibold → Inter Bold (corpo legível)
      regular  → Inter Regular (corpo secundário)
    """
    key = (tamanho, tier)
    if key in _FONT_CACHE:
        return _FONT_CACHE[key]

    candidatos = {
        "display":  ["Montserrat-Black", "Montserrat-ExtraBold",
                     "Poppins-Bold", "BebasNeue-Regular"],
        "bold":     ["Montserrat-ExtraBold", "Montserrat-Black",
                     "Inter-Bold", "Poppins-Bold"],
        "semibold": ["Inter-Bold", "Montserrat-ExtraBold", "Poppins-SemiBold"],
        "regular":  ["Inter-Regular", "Poppins-Regular"],
    }

    for nome in candidatos.get(tier, candidatos["display"]):
        path = _resolve_font_path(nome)
        if path and Path(path).exists():
            try:
                f = ImageFont.truetype(path, tamanho)
                _FONT_CACHE[key] = f
                return f
            except Exception:
                continue

    f = ImageFont.load_default()
    _FONT_CACHE[key] = f
    return f


# ─────────────────────────────────────────────────────────────
# Helpers tipográficos
# ─────────────────────────────────────────────────────────────

def _limpar(texto: str) -> str:
    import unicodedata
    out = []
    for ch in texto:
        cat = unicodedata.category(ch)
        cp  = ord(ch)
        if (cp < 0x2000 or cat.startswith("L") or cat.startswith("N")
                or cat in ("Po", "Pd", "Ps", "Pe", "Pc", "Zs")):
            out.append(ch)
        else:
            out.append(" ")
    return " ".join("".join(out).split())


def _quebrar(texto: str, fonte, max_px: int) -> list:
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


def _tw(t: str, f) -> int:
    bb = f.getbbox(t); return bb[2] - bb[0]

def _th(t: str, f) -> int:
    bb = f.getbbox(t); return bb[3] - bb[1]


def _text_x(txt: str, fonte, W: int, margem: int, align: str) -> int:
    if align == "center":
        return (W - _tw(txt, fonte)) // 2
    return margem


def _draw_sombra(draw, x, y, texto, fonte, cor, offset=3, sombra_opac=180):
    s = (0, 0, 0, sombra_opac)
    for dx, dy in [(-offset, -offset), (offset, -offset),
                   (-offset,  offset), (offset,  offset),
                   (0, offset), (0, -offset)]:
        draw.text((x + dx, y + dy), texto, font=fonte, fill=s)
    draw.text((x, y), texto, font=fonte, fill=cor)


# ─────────────────────────────────────────────────────────────
# Overlays base
# ─────────────────────────────────────────────────────────────

def _overlay_gradiente(img: "Image.Image", dd: DesignDecision) -> "Image.Image":
    """Gradiente vertical escuro de inicio_pct até o fundo."""
    W, H    = img.size
    base    = img.convert("RGBA")
    ov      = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    draw    = ImageDraw.Draw(ov)
    r, g, b = NAVY
    ini     = int(H * dd.overlay_start_pct)
    trans   = int(H * (dd.overlay_start_pct + 0.18))
    for y in range(ini, trans):
        t = (y - ini) / max(trans - ini, 1)
        draw.line([(0, y), (W, y)], fill=(r, g, b, int(dd.overlay_opacity * t * t)))
    draw.rectangle([0, trans, W, H], fill=(r, g, b, dd.overlay_opacity))
    return Image.alpha_composite(base, ov).convert("RGB")


def _overlay_lateral(img: "Image.Image", dd: DesignDecision) -> "Image.Image":
    W, H    = img.size
    base    = img.convert("RGBA")
    ov      = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    draw    = ImageDraw.Draw(ov)
    r, g, b = NAVY
    solido  = int(W * 0.50)
    trans   = int(W * 0.62)
    draw.rectangle([0, 0, solido, H], fill=(r, g, b, dd.overlay_opacity))
    for x in range(solido, trans):
        t = (x - solido) / max(trans - solido, 1)
        draw.line([(x, 0), (x, H)], fill=(r, g, b, int(dd.overlay_opacity * (1 - t))))
    return Image.alpha_composite(base, ov).convert("RGB")


def _overlay_diagonal(img: "Image.Image", dd: DesignDecision) -> "Image.Image":
    W, H    = img.size
    base    = img.convert("RGBA")
    ov      = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    draw    = ImageDraw.Draw(ov)
    r, g, b = NAVY
    ini     = int(H * (dd.overlay_start_pct - 0.05))
    trans   = int(H * (dd.overlay_start_pct + 0.12))
    pontos  = [(0, int(H * dd.overlay_start_pct)),
               (W, int(H * (dd.overlay_start_pct + 0.10))),
               (W, H), (0, H)]
    draw.polygon(pontos, fill=(r, g, b, dd.overlay_opacity))
    for y in range(ini, trans):
        t = (y - ini) / max(trans - ini, 1)
        draw.line([(0, y), (W, y)], fill=(r, g, b, int(160 * t * t)))
    return Image.alpha_composite(base, ov).convert("RGB")


# ─────────────────────────────────────────────────────────────
# Bloco de texto compartilhado
# ─────────────────────────────────────────────────────────────

def _bloco_texto(draw, variacao: dict, dd: DesignDecision,
                 W: int, H: int, margem: int, max_w: int,
                 y_start: int) -> int:
    """
    Renderiza hook + separador + corpo + CTA a partir de y_start.
    Retorna y final.
    """
    hook  = _limpar(variacao.get("hook",  ""))
    corpo = _limpar(variacao.get("corpo", variacao.get("body", "")))
    cta   = _limpar(variacao.get("cta",   "Me chama que a gente conversa"))

    f_hook  = _fonte(dd.hook_size_px,  "display")
    f_corpo = _fonte(dd.corpo_size_px, "semibold")
    f_cta   = _fonte(dd.cta_size_px,   "bold")

    linhas_hook  = _quebrar(hook,  f_hook,  max_w)
    linhas_corpo = _quebrar(corpo, f_corpo, max_w)

    y = y_start

    # ── Hook ──────────────────────────────────────────────
    for linha in linhas_hook:
        x = _text_x(linha, f_hook, W, margem, dd.hook_align)
        _draw_sombra(draw, x, y, linha, f_hook, dd.accent_color, offset=4)
        y += _th(linha, f_hook) + 10

    # ── Separador de acento ────────────────────────────────
    y += 8
    if dd.hook_align == "center":
        larg = min(_tw(linhas_hook[0], f_hook) + 40, W - margem * 2)
        x1   = (W - larg) // 2
    else:
        larg = 160
        x1   = margem
    draw.line([(x1, y), (x1 + larg, y)], fill=dd.accent_color, width=4)
    # Ponto de acento no final da linha
    draw.ellipse([(x1 + larg + 8, y - 3), (x1 + larg + 14, y + 3)],
                 fill=dd.cta_color)
    y += 22

    # ── Corpo ──────────────────────────────────────────────
    for linha in linhas_corpo:
        x = _text_x(linha, f_corpo, W, margem, dd.hook_align)
        _draw_sombra(draw, x, y, linha, f_corpo, CINZA_CLARO, offset=2)
        y += _th(linha, f_corpo) + 8

    # ── CTA ────────────────────────────────────────────────
    y += 22
    x = _text_x(cta, f_cta, W, margem, dd.hook_align)
    _draw_sombra(draw, x, y, cta, f_cta, BRANCO, offset=2)
    # Sublinhado duplo colorido
    ch = _th(cta, f_cta)
    cw = _tw(cta, f_cta)
    draw.line([(x, y + ch + 5), (x + cw, y + ch + 5)],
              fill=dd.cta_color,   width=3)
    draw.line([(x, y + ch + 10), (x + int(cw * 0.6), y + ch + 10)],
              fill=dd.accent_color, width=2)
    y += ch + 16

    return y


# ─────────────────────────────────────────────────────────────
# Layouts
# ─────────────────────────────────────────────────────────────

def _calcular_y_inicio(variacao: dict, dd: DesignDecision,
                       W: int, H: int, margem: int, max_w: int) -> int:
    """Calcula y_start para o bloco de texto caber na imagem."""
    hook  = _limpar(variacao.get("hook",  ""))
    corpo = _limpar(variacao.get("corpo", variacao.get("body", "")))
    cta   = _limpar(variacao.get("cta",   ""))

    f_hook  = _fonte(dd.hook_size_px,  "display")
    f_corpo = _fonte(dd.corpo_size_px, "semibold")
    f_cta   = _fonte(dd.cta_size_px,   "bold")

    linhas_hook  = _quebrar(hook,  f_hook,  max_w)
    linhas_corpo = _quebrar(corpo, f_corpo, max_w)

    h_hook  = sum(_th(l, f_hook)  + 10 for l in linhas_hook)  + 34  # sep
    h_corpo = sum(_th(l, f_corpo) + 8  for l in linhas_corpo) + 22  # gap
    h_cta   = _th(cta, f_cta) + 38

    h_total = h_hook + h_corpo + h_cta + 20
    y_hint  = int(H * dd.hook_y_pct)
    y_max   = H - h_total - 40

    return min(y_hint, y_max)


def _layout_tipografia_forte(img, variacao, dd):
    img  = _overlay_gradiente(img, dd)
    W, H = img.size
    draw = ImageDraw.Draw(img)
    margem = 64
    max_w  = W - margem * 2
    y      = _calcular_y_inicio(variacao, dd, W, H, margem, max_w)
    _bloco_texto(draw, variacao, dd, W, H, margem, max_w, y)
    return img


def _layout_split_diagonal(img, variacao, dd):
    img  = _overlay_diagonal(img, dd)
    W, H = img.size
    draw = ImageDraw.Draw(img)
    margem = 56
    max_w  = int(W * 0.85) - margem
    # Barra vertical de acento (lateral esquerda)
    dd.hook_align = "left"
    y = _calcular_y_inicio(variacao, dd, W, H, margem, max_w)
    # Barra lateral
    bar_h = min(int(H - y - 40), int(H * 0.45))
    draw.rectangle([margem - 12, y + 6, margem - 6, y + bar_h],
                   fill=dd.accent_color)
    _bloco_texto(draw, variacao, dd, W, H, margem + 4, max_w, y)
    return img


def _layout_headline_centralizada(img, variacao, dd):
    img  = _overlay_gradiente(img, dd)
    W, H = img.size
    draw = ImageDraw.Draw(img)
    margem = 70
    max_w  = W - margem * 2
    dd.hook_align = "center"
    y = _calcular_y_inicio(variacao, dd, W, H, margem, max_w)
    # Decoração dupla acima do hook
    draw.line([(margem, y - 18), (W - margem, y - 18)],
              fill=(*BRANCO, 120), width=1)
    draw.line([(margem + 30, y - 10), (W - margem - 30, y - 10)],
              fill=dd.accent_color, width=3)
    _bloco_texto(draw, variacao, dd, W, H, margem, max_w, y)
    # Decoração abaixo do bloco
    y_fim = _calcular_y_inicio(variacao, dd, W, H, margem, max_w)
    draw.line([(margem + 30, H - 46), (W - margem - 30, H - 46)],
              fill=dd.accent_color, width=2)
    draw.line([(margem, H - 38), (W - margem, H - 38)],
              fill=(*BRANCO, 100), width=1)
    return img


def _layout_lateral_esquerda(img, variacao, dd):
    img  = _overlay_lateral(img, dd)
    W, H = img.size
    draw = ImageDraw.Draw(img)
    coluna_w = int(W * 0.50)
    margem   = 48
    max_w    = coluna_w - margem - 20
    dd.hook_align  = "left"
    dd.hook_size_px = max(dd.hook_size_px - 12, 62)  # menor para caber na coluna
    y = _calcular_y_inicio(variacao, dd, W, H, margem, max_w)
    # Acento no topo da coluna
    draw.rectangle([margem, y - 18, margem + 72, y - 12],
                   fill=dd.accent_color)
    # Linha vertical de separação entre coluna e foto
    draw.line([(coluna_w, int(H * 0.15)), (coluna_w, int(H * 0.85))],
              fill=(*dd.accent_color, 60), width=2)
    _bloco_texto(draw, variacao, dd, W, H, margem, max_w, y)
    return img


_LAYOUT_FN = {
    "TIPOGRAFIA_FORTE":      _layout_tipografia_forte,
    "SPLIT_DIAGONAL":        _layout_split_diagonal,
    "HEADLINE_CENTRALIZADA": _layout_headline_centralizada,
    "LATERAL_ESQUERDA":      _layout_lateral_esquerda,
}


def _compor_texto(img, variacao, layout, dd) -> "Image.Image":
    fn = _LAYOUT_FN.get(layout, _layout_tipografia_forte)
    return fn(img, variacao, dd)


# ─────────────────────────────────────────────────────────────
# Prompts GPT-image-1
# ─────────────────────────────────────────────────────────────

_CENAS = {
    "generico":   "a confident cheerful Brazilian small business owner, apron, arms crossed, shop background, upper-right composition",
    "padaria":    "a proud Brazilian bakery owner behind counter with golden fresh bread loaves, warm amber lighting",
    "pizzaria":   "a Brazilian pizzeria chef smiling near glowing wood-fired oven, tossing dough, dynamic composition",
    "lanchonete": "a vibrant Brazilian snack bar owner at colorful counter, high energy atmosphere",
    "restaurante":"a welcoming Brazilian restaurant owner in warmly lit dining room, elegant gesture",
    "acai":       "a Brazilian açaí shop attendant smiling, colorful bowls and toppings visible, fresh colors",
    "salao":      "a confident Brazilian hair stylist in modern salon, mirrors and professional chairs",
    "barbearia":  "a skilled Brazilian barber in stylish barbershop, professional tools and clean aesthetic",
    "manicure":   "a happy Brazilian nail technician at bright nail studio, colorful nail polish display",
    "estetica":   "a professional Brazilian aesthetics specialist in clean modern studio",
    "academia":   "a energetic Brazilian gym owner in well-equipped fitness center, motivational pose",
    "vestuario":  "a stylish Brazilian clothing store owner among racks of colorful garments",
    "mercadinho": "a trustworthy Brazilian neighborhood market owner at full-stocked shelves",
    "mecanico":   "a confident Brazilian auto mechanic in clean organized repair shop, tools visible",
}

_LAYOUT_COMPOSITION = {
    "TIPOGRAFIA_FORTE":      "subject in upper-right third, lower 55% must be very dark navy (#0D1B4B) for text overlay",
    "SPLIT_DIAGONAL":        "subject center-right, dramatic diagonal dark area on lower-left for text, dynamic composition",
    "HEADLINE_CENTRALIZADA": "subject behind or above center, bottom 60% dark navy gradient, clear central vertical space",
    "LATERAL_ESQUERDA":      "subject firmly on RIGHT half (60% of frame), left 50% gradients dark navy for text column",
}

_BASE_PROMPT = (
    "Ultra-vibrant cinematic commercial photography. Brazilian Instagram ad. "
    "{cena}. "
    "Composition: {comp}. "
    "Dramatic cinematic golden-hour rim lighting. Rich bokeh background. "
    "Ultra-sharp subject, editorial quality, high energy. "
    "Deep navy blue in text zone (NON-NEGOTIABLE — must be very dark for text legibility). "
    "NO text, NO logos, NO watermarks, NO readable signs whatsoever. "
    "Hyper-realistic, magazine cover quality. Perfect 1:1 square ratio."
)


def _construir_prompt_ia(variacao: dict, segmento_key: str,
                         layout: str, melhorias: list | None) -> str:
    cena = _CENAS.get(segmento_key, _CENAS["generico"])
    comp = _LAYOUT_COMPOSITION.get(layout, _LAYOUT_COMPOSITION["TIPOGRAFIA_FORTE"])
    base = _BASE_PROMPT.format(cena=cena, comp=comp)

    if melhorias:
        # filtra apenas correções visuais de fundo (ignora tipografia que é aplicada em Pillow)
        visuais = [m for m in melhorias[:4]
                   if not any(kw in m.lower() for kw in
                              ["fonte", "tamanho", "px", "pt", "bold", "cta_size",
                               "hook_size", "corpo_size", "align"])]
        if visuais:
            base += " VISUAL CORRECTIONS: " + " | ".join(visuais)

    if not ANTHROPIC_SDK_DISPONIVEL:
        return base

    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        return base

    try:
        client = _anthropic_sdk.Anthropic(api_key=api_key)
        r = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=400,
            system=(
                "You are a world-class art director for Brazilian fintech performance ads. "
                "Rewrite the image prompt to maximize emotional impact and commercial conversion. "
                "Keep composition hint EXACTLY. Emphasize: authentic subject emotion, "
                "dramatic lighting, cinematic energy. NO text/logos. Output ONLY the improved prompt."
            ),
            messages=[{"role": "user", "content":
                f"Base prompt: {base}\n"
                f"Hook: {variacao.get('hook', '')}\n"
                f"Segment: {segmento_key} | Layout: {layout}\n"
                "Improve this prompt for maximum commercial impact."}],
        )
        improved = r.content[0].text.strip()
        # Garante que não perdeu a instrução de composição
        if "NO text" not in improved and "no text" not in improved.lower():
            improved += " NO text, NO logos, NO watermarks."
        return improved
    except Exception:
        return base


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
# Ponto de entrada
# ─────────────────────────────────────────────────────────────

def gerar_criativo_ia(
    variacao:     dict,
    segmento_key: str  = "generico",
    layout:       str  = "TIPOGRAFIA_FORTE",
    melhorias:    list = None,
    template:     Optional[int] = None,  # ignorado — compat. retroativa
) -> str:
    """
    Gera criativo 1024×1024 com GPT-image-1 + overlay tipográfico profissional.

    Parâmetros:
        variacao     — dict com: hook, corpo, cta
        segmento_key — chave do segmento (ex: "padaria", "generico")
        layout       — TIPOGRAFIA_FORTE | SPLIT_DIAGONAL |
                       HEADLINE_CENTRALIZADA | LATERAL_ESQUERDA
        melhorias    — lista de correções do revisor (iterações 2 e 3)

    Retorna caminho absoluto do PNG gerado.
    """
    if not PILLOW_DISPONIVEL:
        raise RuntimeError("Pillow não instalado: pip install Pillow")

    if layout not in _LAYOUT_FN:
        layout = "TIPOGRAFIA_FORTE"

    # Garante fontes disponíveis (download silencioso se necessário)
    garantir_referencias(verbose=False)

    DIRETORIO_SAIDA.mkdir(parents=True, exist_ok=True)

    # Parseia DesignDecision a partir das melhorias do revisor
    dd = DesignDecision.from_melhorias(melhorias or [])

    # Constrói prompt + gera fundo via GPT-image-1
    prompt = _construir_prompt_ia(variacao, segmento_key, layout, melhorias)
    raw    = _gerar_fundo(prompt)
    img    = Image.open(_io.BytesIO(raw)).convert("RGB")

    # Aplica overlay + tipografia profissional
    img = _compor_texto(img, variacao, layout, dd)

    # Salva
    ts   = datetime.now().strftime("%Y%m%d_%H%M%S")
    nome = f"criativo_{segmento_key}_{layout.lower()}_{ts}.png"
    dest = DIRETORIO_SAIDA / nome
    img.save(str(dest), format="PNG", optimize=False, compress_level=1)
    return str(dest)
