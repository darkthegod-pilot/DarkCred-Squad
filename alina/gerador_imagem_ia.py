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

# ─── Formatos de criativo suportados ────────────────────────
FORMATOS = {
    "quadrado":      (1080, 1080),   # Feed 1:1  — padrão Meta Ads
    "feed_vertical": (1080, 1350),   # Feed 4:5  — mais área no feed
    "stories":       (1080, 1920),   # Stories/Reels 9:16
}
# Tamanhos GPT-image-1 por formato (escolhe o mais próximo)
_GPT_TAMANHO = {
    "quadrado":      "1024x1024",
    "feed_vertical": "1024x1536",
    "stories":       "1024x1536",
}

# ─── Paleta elegante ────────────────────────────────────────
# Warm charcoal — mais quente que navy frio; combina com luz dourada brasileira
OVERLAY_WARM = ( 10,   7,   5)
AMBER        = (255, 175,  30)   # headline gold-amber — mais premium que laranja
ACCENT_LINE  = (255, 155,  20)   # separadores e detalhes
BRANCO       = (255, 255, 255)
BRANCO_QUENTE= (255, 248, 235)   # branco levemente amarelo para corpo
DOURADO      = (255, 205,  50)   # CTA highlight
PRETO_SUAVE  = ( 10,   8,   6)

# Manter nomes antigos como aliases para compat.
LARANJA     = AMBER
NAVY        = OVERLAY_WARM
CINZA_CLARO = BRANCO_QUENTE

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


def _tw_tracked(texto: str, fonte, tracking: int) -> int:
    """Largura total com letter-spacing."""
    total = 0
    for i, ch in enumerate(texto):
        bb = fonte.getbbox(ch)
        total += bb[2] - bb[0]
        if i < len(texto) - 1:
            total += tracking
    return total


def _draw_tracked(draw, x, y, texto, fonte, cor, tracking: int,
                  sombra_opac: int = 200, offset: int = 3):
    """
    Renderiza texto com letter-spacing manual (Pillow não suporta nativo).
    Passa por duas fases: shadow pass → text pass.
    """
    sc = (0, 0, 0, sombra_opac)
    # Shadow pass
    cx = x
    for ch in texto:
        for dx, dy in [(-offset,-offset),(offset,-offset),
                       (-offset, offset),(offset, offset),(0,offset)]:
            draw.text((cx+dx, y+dy), ch, font=fonte, fill=sc)
        bb = fonte.getbbox(ch)
        cx += (bb[2] - bb[0]) + tracking
    # Text pass
    cx = x
    for ch in texto:
        draw.text((cx, y), ch, font=fonte, fill=cor)
        bb = fonte.getbbox(ch)
        cx += (bb[2] - bb[0]) + tracking


def _draw_separador_elegante(draw, x_start: int, y: int,
                             larg: int, accent: tuple, align: str,
                             W: int) -> int:
    """
    Separador em dois elementos:
      — linha fina branca (full width)
      — linha espessa accent (50% width) deslocada
      — losango dourado central
    Retorna y após o separador.
    """
    if align == "center":
        x1 = (W - larg) // 2
    else:
        x1 = x_start

    half = larg // 2

    # Linha fina branca
    draw.line([(x1, y), (x1 + larg, y)], fill=(255, 255, 255, 70), width=1)

    # Linha espessa accent (metade)
    y2 = y + 5
    if align == "center":
        ax = (W - half) // 2
    else:
        ax = x1
    draw.line([(ax, y2), (ax + half, y2)], fill=(*accent, 220), width=3)

    # Losango no centro da linha accent
    cx = ax + half // 2
    sz = 4
    draw.polygon([(cx, y2 - sz), (cx + sz, y2),
                  (cx, y2 + sz), (cx - sz, y2)],
                 fill=DOURADO)

    return y2 + 16


def _draw_cta_pill(draw, img_rgba, y: int, cta: str, fonte,
                   accent: tuple, W: int, margem: int, align: str) -> int:
    """
    CTA como pill button semi-transparente.
    Usa RGBA para o fundo do pill; o texto fica em branco bold dentro.
    Retorna y final.
    """
    cw = _tw(cta, fonte)
    ch = _th(cta, fonte)
    pad_h, pad_v = 28, 14

    pill_w = cw + pad_h * 2
    pill_h = ch + pad_v * 2
    radius = pill_h // 2

    if align == "center":
        pill_x = (W - pill_w) // 2
    else:
        pill_x = margem - pad_h

    pill_y = y

    # Desenha fundo do pill no layer RGBA
    ov = Image.new("RGBA", img_rgba.size, (0, 0, 0, 0))
    ov_draw = ImageDraw.Draw(ov)
    r, g, b = accent
    ov_draw.rounded_rectangle(
        [pill_x, pill_y, pill_x + pill_w, pill_y + pill_h],
        radius=radius,
        fill=(r, g, b, 200),
        outline=(255, 255, 255, 100),
        width=1,
    )
    # Compõe pill sobre a imagem
    img_rgba.alpha_composite(ov)

    # Texto do CTA dentro do pill (sem sombra para ficar limpo)
    tx = pill_x + pad_h
    ty = pill_y + pad_v
    draw = ImageDraw.Draw(img_rgba)
    draw.text((tx, ty), cta, font=fonte, fill=BRANCO)

    return pill_y + pill_h + 20




# ─────────────────────────────────────────────────────────────
# Overlays base
# ─────────────────────────────────────────────────────────────

def _overlay_gradiente(img: "Image.Image", dd: DesignDecision) -> "Image.Image":
    """
    Overlay cinematográfico premium — warm charcoal com vignette sutil.

    Três camadas:
      1. Vignette lateral + superior (20px cada) — profundidade cinematic
      2. Gradiente principal bottom-up com easing cúbico suave
      3. Camada solid no rodapé (últimos 8%) — garante contraste máximo para CTA
    """
    W, H    = img.size
    base    = img.convert("RGBA")
    ov      = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    draw    = ImageDraw.Draw(ov)
    r, g, b = OVERLAY_WARM

    # ── 1. Vignette lateral suave ──────────────────────────
    vig = 90
    for i in range(vig):
        a = int(75 * (1 - i / vig) ** 2)
        draw.line([(i, 0), (i, H)],   fill=(r, g, b, a))
        draw.line([(W-i, 0), (W-i, H)], fill=(r, g, b, a))

    # ── 2. Vignette superior ────────────────────────────────
    for i in range(50):
        a = int(55 * (1 - i / 50) ** 1.5)
        draw.line([(0, i), (W, i)], fill=(r, g, b, a))

    # ── 3. Gradiente principal (easing cúbico) ──────────────
    ini      = int(H * dd.overlay_start_pct)
    grad_len = H - ini
    for y in range(ini, H):
        t     = (y - ini) / max(grad_len, 1)
        # Easing cúbico: devagar no início, rápido no final
        t_eas = t * t * (3 - 2 * t)
        a     = int(dd.overlay_opacity * t_eas)
        draw.line([(0, y), (W, y)], fill=(r, g, b, a))

    # ── 4. Floor sólido (últimos 8%) ───────────────────────
    floor_y = int(H * 0.92)
    draw.rectangle([0, floor_y, W, H], fill=(r, g, b, dd.overlay_opacity))

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
                 y_start: int, img_rgba=None) -> int:
    """
    Renderiza bloco tipográfico premium:
      ‣ Headline com letter-tracking (+2px) — look editorial
      ‣ Separador elegante (linha dupla + losango)
      ‣ Corpo em branco quente com entrelinha generosa
      ‣ CTA como pill button semi-transparente

    img_rgba: se fornecido, é usado para renderização RGBA (pill, badge).
    Retorna y final.
    """
    hook  = _limpar(variacao.get("hook",  ""))
    corpo = _limpar(variacao.get("corpo", variacao.get("body", "")))
    cta   = _limpar(variacao.get("cta",   "Me chama que a gente conversa"))

    f_hook  = _fonte(dd.hook_size_px,  "display")
    f_corpo = _fonte(dd.corpo_size_px, "semibold")
    f_cta   = _fonte(dd.cta_size_px,   "bold")

    TRACKING_HOOK  = 2   # letter-spacing para headlines — feel premium
    TRACKING_CORPO = 0

    linhas_hook  = _quebrar(hook,  f_hook,
                            max_w - TRACKING_HOOK * max(len(hook), 1))
    linhas_corpo = _quebrar(corpo, f_corpo, max_w)

    y = y_start

    # ── Hook (com letter-tracking) ─────────────────────────
    for linha in linhas_hook:
        tw_t = _tw_tracked(linha, f_hook, TRACKING_HOOK)
        if dd.hook_align == "center":
            x = (W - tw_t) // 2
        else:
            x = margem
        _draw_tracked(draw, x, y, linha, f_hook,
                      dd.accent_color, TRACKING_HOOK,
                      sombra_opac=210, offset=4)
        y += _th(linha, f_hook) + 12

    # ── Separador elegante ─────────────────────────────────
    y += 10
    if dd.hook_align == "center":
        larg_sep = min(_tw_tracked(linhas_hook[0], f_hook, TRACKING_HOOK) + 30,
                       W - margem * 2)
    else:
        larg_sep = 180
    y = _draw_separador_elegante(
        draw, margem, y, larg_sep, ACCENT_LINE, dd.hook_align, W
    )

    # ── Corpo ──────────────────────────────────────────────
    for linha in linhas_corpo:
        x = _text_x(linha, f_corpo, W, margem, dd.hook_align)
        _draw_sombra(draw, x, y, linha, f_corpo,
                     BRANCO_QUENTE, offset=2, sombra_opac=190)
        y += _th(linha, f_corpo) + 10   # entrelinha mais generosa

    # ── CTA — pill button ──────────────────────────────────
    y += 24

    if img_rgba is not None:
        # Renderização RGBA: pill com fundo semi-transparente
        y = _draw_cta_pill(
            draw, img_rgba, y, cta, f_cta,
            dd.accent_color, W, margem, dd.hook_align
        )
    else:
        # Fallback: texto com sublinhado elegante único
        x = _text_x(cta, f_cta, W, margem, dd.hook_align)
        _draw_sombra(draw, x, y, cta, f_cta, BRANCO, offset=2)
        cw = _tw(cta, f_cta)
        ch = _th(cta, f_cta)
        draw.line([(x, y + ch + 6), (x + cw, y + ch + 6)],
                  fill=(*DOURADO, 220), width=2)
        y += ch + 20

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

    h_hook  = sum(_th(l, f_hook)  + 12 for l in linhas_hook)  + 46  # sep elegante
    h_corpo = sum(_th(l, f_corpo) + 10 for l in linhas_corpo) + 24  # gap
    h_cta   = _th(cta, f_cta) + 28 + 24   # pill: pad_v*2 + margin

    h_total = h_hook + h_corpo + h_cta + 20
    y_hint  = int(H * dd.hook_y_pct)
    y_max   = H - h_total - 40

    return min(y_hint, y_max)


def _layout_tipografia_forte(img, variacao, dd):
    img      = _overlay_gradiente(img, dd)
    img_rgba = img.convert("RGBA")
    W, H     = img_rgba.size
    draw     = ImageDraw.Draw(img_rgba)
    margem   = 64
    max_w    = W - margem * 2
    y        = _calcular_y_inicio(variacao, dd, W, H, margem, max_w)
    _bloco_texto(draw, variacao, dd, W, H, margem, max_w, y, img_rgba=img_rgba)
    return img_rgba.convert("RGB")


def _layout_split_diagonal(img, variacao, dd):
    img      = _overlay_diagonal(img, dd)
    img_rgba = img.convert("RGBA")
    W, H     = img_rgba.size
    draw     = ImageDraw.Draw(img_rgba)
    margem   = 56
    max_w    = int(W * 0.85) - margem
    dd.hook_align = "left"
    y        = _calcular_y_inicio(variacao, dd, W, H, margem, max_w)
    # Barra vertical de acento
    bar_h = min(int(H - y - 40), int(H * 0.45))
    draw.rectangle([margem - 12, y + 6, margem - 6, y + bar_h],
                   fill=(*ACCENT_LINE, 220))
    _bloco_texto(draw, variacao, dd, W, H, margem + 4, max_w, y, img_rgba=img_rgba)
    return img_rgba.convert("RGB")


def _layout_headline_centralizada(img, variacao, dd):
    img      = _overlay_gradiente(img, dd)
    img_rgba = img.convert("RGBA")
    W, H     = img_rgba.size
    draw     = ImageDraw.Draw(img_rgba)
    margem   = 70
    max_w    = W - margem * 2
    dd.hook_align = "center"
    y        = _calcular_y_inicio(variacao, dd, W, H, margem, max_w)
    # Decoração dupla acima do hook
    draw.line([(margem, y - 18), (W - margem, y - 18)],
              fill=(255, 255, 255, 80), width=1)
    draw.line([(margem + 30, y - 10), (W - margem - 30, y - 10)],
              fill=(*ACCENT_LINE, 200), width=3)
    _bloco_texto(draw, variacao, dd, W, H, margem, max_w, y, img_rgba=img_rgba)
    draw.line([(margem + 30, H - 46), (W - margem - 30, H - 46)],
              fill=(*ACCENT_LINE, 180), width=2)
    draw.line([(margem, H - 38), (W - margem, H - 38)],
              fill=(255, 255, 255, 70), width=1)
    return img_rgba.convert("RGB")


def _layout_lateral_esquerda(img, variacao, dd):
    img      = _overlay_lateral(img, dd)
    img_rgba = img.convert("RGBA")
    W, H     = img_rgba.size
    draw     = ImageDraw.Draw(img_rgba)
    coluna_w = int(W * 0.50)
    margem   = 48
    max_w    = coluna_w - margem - 20
    dd.hook_align   = "left"
    dd.hook_size_px = max(dd.hook_size_px - 12, 62)
    y = _calcular_y_inicio(variacao, dd, W, H, margem, max_w)
    # Acento no topo da coluna
    draw.rectangle([margem, y - 18, margem + 72, y - 12],
                   fill=(*ACCENT_LINE, 220))
    draw.line([(coluna_w, int(H * 0.15)), (coluna_w, int(H * 0.85))],
              fill=(*ACCENT_LINE, 60), width=2)
    _bloco_texto(draw, variacao, dd, W, H, margem, max_w, y, img_rgba=img_rgba)
    return img_rgba.convert("RGB")


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

# Descrição feminina base — eslava, elegante, enérgica
# Usada em todos os segmentos que têm mulher como modelo.
_MULHER_ESLAVA = [
    "a strikingly elegant Slavic woman in her late 20s, porcelain skin, sharp cheekbones, vivid blue eyes, glossy hair, radiant confident smile, upright poised posture",
    "a gorgeous Slavic woman in her early 30s, high cheekbones, light eyes, perfectly groomed, luminous complexion, warm magnetic smile, effortlessly chic",
    "a beautiful Slavic woman in her 30s, striking facial features, bright eyes, smooth fair skin, elegant relaxed expression, stylish and vibrant energy",
    "a stunning Slavic woman, refined bone structure, expressive light eyes, glowing skin, natural elegance, genuinely joyful and lively expression",
]

_CENAS: dict[str, list[str]] = {
    "generico": [
        "{mulher}, small business owner, stylish minimalist outfit, blurred modern shop interior, golden hour bokeh",
        "a handsome Brazilian man in his late 20s, confident entrepreneur, clean modern outfit, bright genuine smile, blurred store background",
        "{mulher}, successful merchant, elegant simple blouse, professional workspace background in warm bokeh",
        "a charming Brazilian man in his 30s, merchant apron over stylish shirt, charismatic smile, blurred shop shelves background",
    ],
    "padaria": [
        "{mulher}, pristine white baker's apron, holding a perfect golden artisan bread loaf, warm amber bakery glow behind her",
        "a handsome Brazilian man baker, strong forearms, flour-dusted apron, artisan bread in background, golden amber bakery lighting",
        "{mulher}, elegant baker, showcase of golden pastries softly blurred behind her, warm glowing bakery light",
    ],
    "pizzaria": [
        "a strikingly handsome Brazilian pizza chef, strong jawline, rolling dough confidently, wood-fired oven glow behind him, dynamic energy",
        "{mulher}, crisp chef whites, vibrant smile, colorful artisan pizzas in blurred background, warm cinematic orange light",
        "a charismatic Brazilian man in his late 30s, pizzeria owner, casual chef attire, tossing pizza dough playfully, cinematic warm light",
    ],
    "lanchonete": [
        "{mulher}, snack bar owner, bright neat casual outfit, energetic confident pose, colorful counter blurred behind",
        "a handsome lively Brazilian man at lanchonete counter, bright casual uniform, charming smile, colorful menu boards in soft bokeh",
    ],
    "restaurante": [
        "{mulher}, restaurant owner, elegant simple dress, warmly lit dining room in cinematic soft focus, graceful welcoming expression",
        "a distinguished handsome Brazilian man restaurateur, well-groomed, smart casual attire, warmly lit dining room bokeh, confident calm expression",
    ],
    "acai": [
        "{mulher}, açaí shop owner, fresh vibrant style, colorful bowls and toppings blurred behind her, healthy energetic glow",
        "a handsome Brazilian man açaí shop attendant, bright smile, athletic casual style, vivid purple and green bokeh background",
    ],
    "salao": [
        "{mulher}, hair salon owner, impeccably styled hair, chic personal fashion, modern salon mirrors in warm bokeh, poised professional confidence",
        "{mulher}, hairstylist, elegant updo, stylish minimalist outfit, blurred salon chairs and mirrors, radiant professional smile",
        "a handsome Brazilian male hairstylist, modern groomed look, stylish casual clothes, blurred salon interior, charming relaxed expression",
    ],
    "barbearia": [
        "a handsome sharp-looking Brazilian barber in his 30s, well-groomed beard, stylish barber attire, classic barbershop bokeh, strong confident pose",
        "a charismatic young Brazilian barber, tattooed forearms, holding scissors elegantly, vintage barbershop interior in warm bokeh",
    ],
    "manicure": [
        "{mulher}, nail technician, impeccably manicured hands, elegant minimal outfit, bright modern nail studio bokeh, warm genuine smile",
        "{mulher}, nail studio owner, colorful polish display softly blurred behind her, professional polished look, bright energy",
    ],
    "estetica": [
        "{mulher}, aesthetics specialist, flawless glowing skin, clean white clinic uniform, modern spa studio in soft focus, serene confident smile",
        "{mulher}, esthetician, elegant clinic attire, warm spa-like bokeh environment, calm self-assured expression",
    ],
    "academia": [
        "a fit handsome Brazilian gym owner, athletic build, casual sporty outfit, well-equipped gym equipment blurred behind, energetic confident smile",
        "{mulher}, gym owner, athletic graceful posture, stylish sportswear, modern fitness center in soft bokeh, motivational radiant energy",
    ],
    "vestuario": [
        "{mulher}, clothing boutique owner, naturally fashionable outfit, colorful garment racks in warm bokeh, poised confident smile",
        "a handsome stylish Brazilian man clothing store owner, well-dressed, racks of clothes softly blurred, sophisticated relaxed expression",
    ],
    "mercadinho": [
        "{mulher}, neighborhood market owner, neat casual attire, stocked colorful shelves softly blurred, genuine warm welcoming smile",
        "a handsome reliable Brazilian market owner in his 40s, strong honest expression, market interior warmly lit in background",
    ],
    "mecanico": [
        "a handsome confident Brazilian auto mechanic, clean work uniform, organized professional workshop blurred behind, strong capable expression",
        "{mulher}, auto mechanic, confident capable stance, clean work outfit, professional workshop tools in warm bokeh",
    ],
}


def _escolher_cena(segmento_key: str) -> str:
    """Sorteia um perfil de modelo; substitui {mulher} por uma descrição eslava aleatória."""
    import random
    opcoes = _CENAS.get(segmento_key, _CENAS["generico"])
    cena   = random.choice(opcoes)
    if "{mulher}" in cena:
        cena = cena.replace("{mulher}", random.choice(_MULHER_ESLAVA))
    return cena



_LAYOUT_COMPOSITION = {
    "TIPOGRAFIA_FORTE":      "subject in upper-right third, lower 55% must be very dark navy (#0D1B4B) for text overlay",
    "SPLIT_DIAGONAL":        "subject center-right, dramatic diagonal dark area on lower-left for text, dynamic composition",
    "HEADLINE_CENTRALIZADA": "subject behind or above center, bottom 60% dark navy gradient, clear central vertical space",
    "LATERAL_ESQUERDA":      "subject firmly on RIGHT half (60% of frame), left 50% gradients dark navy for text column",
}

_BASE_PROMPT = (
    "Premium cinematic commercial photography for high-conversion Instagram ad. "
    "Brazilian small business owner. "
    "{cena}. "
    "Composition: {comp}. "
    # Lighting — chave da elegância
    "Lighting: dramatic warm golden-hour backlight creating a luminous rim around subject, "
    "soft fill from front, rich amber-orange tones, deep bokeh background with warm blur. "
    # Subject — expressão genuína
    "Subject: genuine warm confident smile, professional natural pose, "
    "eyes slightly bright with optimism, skin tones warm and vibrant. "
    # Fotografia
    "Camera: f/1.8 50mm portrait lens, shallow depth of field, "
    "sharp subject against beautifully blurred background. "
    # Gradiente/zona de texto
    "Text zone (lower 45% of frame): very dark warm charcoal — almost black with slight warmth — "
    "smooth seamless gradient from mid-frame, no hard edges (NON-NEGOTIABLE for legibility). "
    # Proibições
    "NO text, NO logos, NO watermarks, NO signs, NO numbers visible anywhere. "
    "Hyper-realistic editorial magazine cover quality. Perfect 1:1 square ratio."
)


def _construir_prompt_ia(variacao: dict, segmento_key: str,
                         layout: str, melhorias: list | None) -> str:
    cena = _escolher_cena(segmento_key)
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


def _gerar_fundo(prompt: str, tamanho_gpt: str = "1024x1024") -> bytes:
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY não encontrada no .env")
    if not OPENAI_SDK_DISPONIVEL:
        raise RuntimeError("openai não instalado: pip install openai>=1.0.0")

    client = _openai_sdk.OpenAI(api_key=api_key)
    r = client.images.generate(
        model="gpt-image-1",
        prompt=prompt,
        size=tamanho_gpt,
        quality="high",
        n=1,
        output_format="png",
    )
    return base64.b64decode(r.data[0].b64_json)


def _redimensionar_para_formato(img: "Image.Image", formato: str) -> "Image.Image":
    """
    Redimensiona e/ou recorta a imagem para as dimensões do formato alvo.
    Mantém proporção preenchendo com crop central.
    """
    w_alvo, h_alvo = FORMATOS.get(formato, (1080, 1080))
    w_orig, h_orig = img.size

    # Calcula escala para cobrir o alvo (cover)
    escala = max(w_alvo / w_orig, h_alvo / h_orig)
    w_nova = int(w_orig * escala)
    h_nova = int(h_orig * escala)
    img = img.resize((w_nova, h_nova), Image.LANCZOS)

    # Crop central para atingir exatamente as dimensões alvo
    left = (w_nova - w_alvo) // 2
    top  = (h_nova - h_alvo) // 2
    img  = img.crop((left, top, left + w_alvo, top + h_alvo))
    return img


# ─────────────────────────────────────────────────────────────
# Ponto de entrada
# ─────────────────────────────────────────────────────────────

def gerar_criativo_ia(
    variacao:     dict,
    segmento_key: str  = "generico",
    layout:       str  = "TIPOGRAFIA_FORTE",
    melhorias:    list = None,
    template:     Optional[int] = None,  # ignorado — compat. retroativa
    formato:      str  = "quadrado",     # quadrado | feed_vertical | stories
) -> str:
    """
    Gera criativo com GPT-image-1 + overlay tipográfico profissional.

    Parâmetros:
        variacao     — dict com: hook, corpo, cta
        segmento_key — chave do segmento (ex: "padaria", "generico")
        layout       — TIPOGRAFIA_FORTE | SPLIT_DIAGONAL |
                       HEADLINE_CENTRALIZADA | LATERAL_ESQUERDA
        melhorias    — lista de correções do revisor (iterações 2 e 3)
        formato      — quadrado (1080×1080) | feed_vertical (1080×1350) | stories (1080×1920)

    Retorna caminho absoluto do PNG gerado.
    """
    if not PILLOW_DISPONIVEL:
        raise RuntimeError("Pillow não instalado: pip install Pillow")

    if layout not in _LAYOUT_FN:
        layout = "TIPOGRAFIA_FORTE"

    if formato not in FORMATOS:
        formato = "quadrado"

    # Garante fontes disponíveis (download silencioso se necessário)
    garantir_referencias(verbose=False)

    DIRETORIO_SAIDA.mkdir(parents=True, exist_ok=True)

    # Parseia DesignDecision a partir das melhorias do revisor
    dd = DesignDecision.from_melhorias(melhorias or [])

    # Constrói prompt + gera fundo via GPT-image-1
    prompt         = _construir_prompt_ia(variacao, segmento_key, layout, melhorias)
    tamanho_gpt    = _GPT_TAMANHO.get(formato, "1024x1024")
    raw            = _gerar_fundo(prompt, tamanho_gpt)
    img            = Image.open(_io.BytesIO(raw)).convert("RGB")

    # Redimensiona para as dimensões exatas do formato alvo
    img = _redimensionar_para_formato(img, formato)

    # Aplica overlay + tipografia profissional
    img = _compor_texto(img, variacao, layout, dd)

    # Salva
    ts     = datetime.now().strftime("%Y%m%d_%H%M%S")
    sufixo = "" if formato == "quadrado" else f"_{formato}"
    nome   = f"criativo_{segmento_key}_{layout.lower()}{sufixo}_{ts}.png"
    dest   = DIRETORIO_SAIDA / nome
    img.save(str(dest), format="PNG", optimize=False, compress_level=1)
    return str(dest)
