"""
Gerador de Imagens com IA — Alina Pretrov
GPT-image-1 quality="high" + composição multi-camada inspirada nas referências reais.

Design (7 camadas):
  1. Fundo fotorrealista 1024×1024 (comerciante + moedas/notas + loja)
  2. Overlay gradiente azul naval (não preto puro) — começa em 35% da altura
  3. Headline LARANJA em Poppins Bold 72px
  4. Badge pílula azul "SEM BUROCRACIA" em amarelo
  5. Card branco arredondado com corpo em cinza escuro
  6. Botão CTA dourado/amarelo — "DINHEIRO NA CONTA HOJE!"
  7. Botão WhatsApp verde — CTA secundário

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
    from PIL import Image, ImageDraw, ImageFont, ImageFilter
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

# Paleta de cores — inspirada nas referências reais
LARANJA      = (255, 107,  53)   # hook headline
LARANJA_E    = (190,  65,  15)   # sombra do hook
DOURADO      = (255, 210,   0)   # badge + CTA primário
DOURADO_E    = (180, 140,   0)   # sombra do CTA dourado
NAVY         = ( 13,  27,  75)   # overlay azul naval
AZUL_BADGE   = ( 20,  60, 160)   # fundo do badge pílula
VERDE_WP     = ( 37, 211, 102)   # botão WhatsApp
VERDE_WP_E   = ( 18, 130,  60)   # sombra WhatsApp
BRANCO       = (255, 255, 255)
CINZA_TEXTO  = ( 30,  30,  30)   # texto no card branco
SOMBRA       = (  0,   0,   0)


# ─────────────────────────────────────────────────────────────
# FONTS — Poppins com fallback
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
# HELPERS
# ─────────────────────────────────────────────────────────────

def _limpar(texto: str) -> str:
    import unicodedata
    out = []
    for ch in texto:
        cp = ord(ch)
        cat = unicodedata.category(ch)
        if cp < 0x2000 or cat.startswith("L") or cat.startswith("N") \
                or cat in ("Po", "Pd", "Ps", "Pe", "Pc", "Zs"):
            out.append(ch)
        else:
            out.append(" ")
    return " ".join("".join(out).split())


def _quebrar(texto: str, fonte: "ImageFont.FreeTypeFont", max_px: int) -> list:
    palavras = texto.split()
    linhas, atual = [], ""
    for p in palavras:
        cand = (atual + " " + p).strip()
        w = fonte.getbbox(cand)[2] - fonte.getbbox(cand)[0]
        if w <= max_px:
            atual = cand
        else:
            if atual:
                linhas.append(atual)
            atual = p
    if atual:
        linhas.append(atual)
    return linhas


def _texto_w(texto: str, fonte: "ImageFont.FreeTypeFont") -> int:
    bb = fonte.getbbox(texto)
    return bb[2] - bb[0]


def _texto_h(texto: str, fonte: "ImageFont.FreeTypeFont") -> int:
    bb = fonte.getbbox(texto)
    return bb[3] - bb[1]


def _draw_sombra(draw, x, y, texto, fonte, cor, sombra=SOMBRA, offset=2):
    """Sombra em 4 offsets diagonais para profundidade."""
    for dx, dy in [(-offset, -offset), (offset, -offset),
                   (-offset,  offset), (offset,  offset)]:
        draw.text((x + dx, y + dy), texto, font=fonte, fill=sombra)
    draw.text((x, y), texto, font=fonte, fill=cor)


def _draw_sombra_suave(draw, x, y, texto, fonte, cor, sombra=SOMBRA, blur=6):
    """Sombra via múltiplos offsets para simular blur — mais suave."""
    for dx, dy, op in [(-3, -3, 80), (3, -3, 80), (-3, 3, 80), (3, 3, 80),
                       (-5, -5, 40), (5, -5, 40), (-5, 5, 40), (5, 5, 40)]:
        s = (*sombra, op)
        draw.text((x + dx, y + dy), texto, font=fonte, fill=s)
    draw.text((x, y), texto, font=fonte, fill=cor)


# ─────────────────────────────────────────────────────────────
# CAMADA 2 — Overlay azul naval com gradiente de transição
# ─────────────────────────────────────────────────────────────

def _overlay_naval(img: "Image.Image") -> "Image.Image":
    """
    Overlay com gradiente azul naval (#0D1B4B).
    Preserva foto no topo; escurece com cor navy do meio para baixo.
    """
    W, H = img.size
    base    = img.convert("RGBA")
    overlay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    draw    = ImageDraw.Draw(overlay)

    inicio = int(H * 0.32)   # começa a transição em 32% da altura
    fim    = int(H * 0.56)   # navy sólido a partir de 56%
    opac   = 215              # opacidade do navy sólido

    r, g, b = NAVY

    # Gradiente de transição
    faixa = fim - inicio
    for y in range(inicio, fim):
        t = (y - inicio) / max(faixa, 1)
        a = int(opac * t)
        draw.line([(0, y), (W, y)], fill=(r, g, b, a))

    # Bloco sólido navy abaixo da transição
    draw.rectangle([0, fim, W, H], fill=(r, g, b, opac))

    return Image.alpha_composite(base, overlay).convert("RGB")


# ─────────────────────────────────────────────────────────────
# CAMADAS 3-7 — Composição de texto multi-camada
# ─────────────────────────────────────────────────────────────

def _desenhar_badge_pilula(draw: "ImageDraw.ImageDraw", texto: str,
                            y_centro: int, W: int):
    """Camada 4 — Badge pílula azul escuro com texto amarelo."""
    f   = _fonte(32, "bold")
    tw  = _texto_w(texto, f)
    th  = _texto_h(texto, f) + 6
    ph, pv = 50, 14
    bw  = tw + ph * 2
    bh  = th + pv * 2
    x0  = (W - bw) // 2
    y0  = y_centro - bh // 2
    x1  = x0 + bw
    y1  = y0 + bh
    r   = bh // 2  # pílula perfeita

    # Sombra da pílula
    draw.rounded_rectangle([x0 + 3, y0 + 4, x1 + 3, y1 + 4],
                            radius=r, fill=(0, 0, 0, 100))
    # Fundo azul
    draw.rounded_rectangle([x0, y0, x1, y1], radius=r, fill=AZUL_BADGE)
    # Borda brilhante
    draw.rounded_rectangle([x0, y0, x1, y1], radius=r, outline=DOURADO, width=2)

    bb = f.getbbox(texto)
    xt = x0 + ph - bb[0]
    yt = y0 + pv - bb[1]
    draw.text((xt, yt), texto, font=f, fill=DOURADO)

    return bh


def _desenhar_card_info(draw: "ImageDraw.ImageDraw", linhas: list,
                         fonte: "ImageFont.FreeTypeFont",
                         y_topo: int, W: int,
                         margem_lateral: int = 72) -> int:
    """Camada 5 — Card branco arredondado com texto cinza escuro."""
    if not linhas:
        return y_topo

    espacamento = 12
    alturas = [_texto_h(l, fonte) for l in linhas]
    h_texto = sum(alturas) + espacamento * (len(linhas) - 1)
    ph, pv  = 48, 22
    bw      = W - margem_lateral * 2
    bh      = h_texto + pv * 2
    x0      = margem_lateral
    y0      = y_topo
    x1      = x0 + bw
    y1      = y0 + bh

    # Sombra do card
    draw.rounded_rectangle([x0 + 3, y0 + 5, x1 + 3, y1 + 5],
                            radius=18, fill=(0, 0, 0, 90))
    # Fundo branco
    draw.rounded_rectangle([x0, y0, x1, y1], radius=18, fill=(255, 255, 255, 240))

    # Texto centralizado linha a linha
    y_txt = y0 + pv
    for i, linha in enumerate(linhas):
        bb = fonte.getbbox(linha)
        tw = bb[2] - bb[0]
        lh = alturas[i]
        xt = x0 + (bw - tw) // 2 - bb[0]
        draw.text((xt, y_txt - bb[1]), linha, font=fonte, fill=CINZA_TEXTO)
        y_txt += lh + espacamento

    return bh


def _desenhar_botao(draw: "ImageDraw.ImageDraw", texto: str,
                     y_centro: int, W: int,
                     cor_fundo: tuple, cor_sombra: tuple,
                     cor_texto: tuple,
                     icone: str = "",
                     margem_lateral: int = 72) -> int:
    """Camada genérica de botão CTA."""
    f       = _fonte(38, "bold")
    label   = (icone + " " + texto).strip() if icone else texto
    tw      = _texto_w(label, f)
    th      = _texto_h(label, f) + 4
    ph, pv  = 50, 20
    bw      = W - margem_lateral * 2
    bh      = th + pv * 2
    x0      = margem_lateral
    y0      = y_centro - bh // 2
    x1      = x0 + bw
    y1      = y0 + bh
    r       = bh // 2

    # Sombra
    draw.rounded_rectangle([x0 + 4, y0 + 5, x1 + 4, y1 + 5],
                            radius=r, fill=cor_sombra)
    # Botão
    draw.rounded_rectangle([x0, y0, x1, y1], radius=r, fill=cor_fundo)

    bb  = f.getbbox(label)
    xt  = x0 + (bw - tw) // 2 - bb[0]
    yt  = y0 + pv - bb[1]
    draw.text((xt, yt), label, font=f, fill=cor_texto)

    return bh


def _compor_texto(img: "Image.Image", variacao: dict) -> "Image.Image":
    """
    Composição de texto multi-camada.

    De baixo para cima:
      CTA WhatsApp (verde) ← primário de resposta
      CTA Dourado "DINHEIRO NA CONTA HOJE!" ← urgência
      Card branco com corpo ← informação
      Badge pílula azul "SEM BUROCRACIA" ← objeção removida
      Hook em LARANJA ← gancho emocional
    """
    W, H   = img.size
    draw   = ImageDraw.Draw(img)

    hook  = _limpar(variacao.get("hook",  ""))
    corpo = _limpar(variacao.get("corpo", variacao.get("body", "")))
    cta   = variacao.get("cta", "Manda uma mensagem agora")

    f_hook  = _fonte(72, "bold")
    f_corpo = _fonte(34, "semibold")

    margem    = 68
    max_larg  = W - margem * 2
    pad_baixo = 44          # margem do rodapé

    linhas_hook  = _quebrar(hook,  f_hook,  max_larg)
    linhas_corpo = _quebrar(corpo, f_corpo, max_larg - 32)  # card tem padding

    # — Calcula alturas dos blocos —
    def h_bloco(linhas, fonte, esp):
        return sum(_texto_h(l, fonte) + esp for l in linhas) - esp if linhas else 0

    h_hook     = h_bloco(linhas_hook, f_hook, 16)
    h_badge    = 60    # pílula
    h_card     = max(h_bloco(linhas_corpo, f_corpo, 12) + 44, 0)  # card c/ padding
    h_cta_ouro = 72
    h_cta_wp   = 64
    gaps       = 18 + 18 + 22 + 16   # entre cada bloco

    h_total = h_hook + gaps + h_badge + h_card + h_cta_ouro + h_cta_wp
    y = H - h_total - pad_baixo

    # ── Camada 3: Hook em LARANJA ──────────────────────────────
    for linha in linhas_hook:
        tw = _texto_w(linha, f_hook)
        th = _texto_h(linha, f_hook)
        x  = (W - tw) // 2
        _draw_sombra_suave(draw, x, y, linha, f_hook, LARANJA)
        y += th + 16

    y += 18

    # ── Camada 4: Badge pílula "SEM BUROCRACIA" ───────────────
    _desenhar_badge_pilula(draw, "SEM BUROCRACIA.", y + h_badge // 2, W)
    y += h_badge + 18

    # ── Camada 5: Card branco com corpo ───────────────────────
    if linhas_corpo:
        _desenhar_card_info(draw, linhas_corpo, f_corpo, y, W, margem)
        y += h_card + 22
    else:
        y += 22

    # ── Camada 6: Botão CTA dourado ───────────────────────────
    _desenhar_botao(draw, "DINHEIRO NA CONTA HOJE!",
                    y + h_cta_ouro // 2, W,
                    cor_fundo=DOURADO, cor_sombra=DOURADO_E,
                    cor_texto=CINZA_TEXTO, margem_lateral=margem)
    y += h_cta_ouro + 16

    # ── Camada 7: Botão WhatsApp verde ────────────────────────
    _desenhar_botao(draw, cta,
                    y + h_cta_wp // 2, W,
                    cor_fundo=VERDE_WP, cor_sombra=VERDE_WP_E,
                    cor_texto=BRANCO, icone="",
                    margem_lateral=margem + 20)

    return img


# ─────────────────────────────────────────────────────────────
# PROMPT GPT-image-1 — comerciante real + moedas + navy
# ─────────────────────────────────────────────────────────────

_CENAS: dict = {
    "generico":   "a smiling confident Brazilian small business owner wearing an apron, arms crossed, standing in their shop, upper right of frame",
    "padaria":    "a smiling Brazilian bakery owner behind the counter, fresh golden bread on warm shelves, flour on apron",
    "pizzaria":   "a smiling Brazilian pizzeria chef near a glowing pizza oven, tossing dough",
    "lanchonete": "a cheerful Brazilian snack bar owner behind a colorful counter with food on display",
    "restaurante":"a proud Brazilian restaurant owner in a warmly lit dining room, welcoming gesture",
    "acai":       "a vibrant Brazilian açaí shop attendant smiling, colorful cups and fruits visible",
    "salao":      "a Brazilian hairdresser in a modern salon with mirrors and styling chairs, scissors in hand",
    "barbearia":  "a confident Brazilian barber in a stylish barbershop with professional tools and razor",
    "manicure":   "a smiling Brazilian nail technician at a bright nail salon, nail polish bottles on display",
    "estetica":   "a professional Brazilian aesthetics technician in a clean modern studio",
    "academia":   "a confident Brazilian gym owner in a well-equipped fitness studio, flexing arms",
    "vestuario":  "a smiling Brazilian clothing store owner among racks of colorful garments",
    "mercadinho": "a proud Brazilian neighborhood market owner with shelves full of products behind them",
    "mecanico":   "a skilled Brazilian mechanic in an auto repair shop, wiping hands on a rag, confident smile",
}

_BASE_PROMPT = (
    "Ultra-vibrant cinematic commercial photography for a Brazilian Instagram ad. "
    "{cena}. "
    "Multiple large shiny gold dollar coins floating and scattered throughout the frame. "
    "A few fanned-out Brazilian R$100 banknotes visible. "
    "Extremely dark NAVY BLUE (#0D1B4B) lower 50% of the frame for text overlay. "
    "Subject in upper-right or center-right portion of frame, looking at camera with confidence. "
    "Dramatic golden/amber rim lighting on subject. Deep rich shadows. Beautiful bokeh on store background. "
    "Ultra sharp focus. Professional commercial ad photography. High energy, vibrant, alive. "
    "Color palette: deep navy blue background, bright golden coins, warm amber lighting on person. "
    "NO text, NO logos, NO watermarks, NO readable signs anywhere. Perfect square 1:1 composition. "
    "Style: high-end Brazilian fintech advertisement, similar to Nubank and Mercado Pago ads."
)


def _construir_prompt(variacao: dict, segmento_key: str) -> str:
    cena = _CENAS.get(segmento_key, _CENAS["generico"])
    base = _BASE_PROMPT.format(cena=cena)

    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not ANTHROPIC_SDK_DISPONIVEL or not api_key:
        return base
    try:
        client = _anthropic_sdk.Anthropic(api_key=api_key)
        r = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=350,
            system=(
                "You are a world-class art director specializing in Brazilian fintech Instagram ads. "
                "Write a single English image generation prompt for GPT-image-1. "
                "CRITICAL requirements: "
                "(1) The lower 50% of the image MUST be deep navy blue (#0D1B4B) for text overlay — non-negotiable. "
                "(2) Person (merchant) must be in upper-center or upper-right portion. "
                "(3) Include floating golden coins and R$100 bills. "
                "(4) High energy, vibrant, alive — NOT flat or dull. "
                "(5) NO text, logos, or watermarks. "
                "Output ONLY the prompt, nothing else."
            ),
            messages=[{"role": "user", "content":
                f"Hook: {variacao.get('hook', '')}\n"
                f"Segment: {segmento_key}\n"
                f"Base scene: {cena}\n\n"
                "Generate a premium vibrant commercial ad photography prompt following all 5 requirements above."}],
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
    template: Optional[int] = None,
) -> str:
    """
    Gera criativo 1024×1024 com GPT-image-1 quality="high" + composição 7 camadas.

    Fluxo:
      1. Claude refina prompt cinematográfico (navy + pessoa + moedas)
      2. GPT-image-1 gera fundo fotorrealista 1024×1024
      3. Overlay azul naval substitui preto puro — preserva foto no topo
      4. Hook LARANJA + badge azul "SEM BUROCRACIA" + card branco
      5. Botão CTA dourado + botão WhatsApp verde

    Retorna caminho absoluto do PNG.
    """
    if not PILLOW_DISPONIVEL:
        raise RuntimeError("Pillow não instalado: pip install Pillow")

    DIRETORIO_SAIDA.mkdir(parents=True, exist_ok=True)

    # 1. Prompt refinado pelo Claude
    prompt = _construir_prompt(variacao, segmento_key)

    # 2. Fundo via GPT-image-1 (1024×1024 nativo, sem resize)
    raw = _gerar_fundo(prompt)
    img = Image.open(_io.BytesIO(raw)).convert("RGB")

    # 3. Overlay azul naval (navy, não preto)
    img = _overlay_naval(img)

    # 4. Composição multi-camada
    img = _compor_texto(img, variacao)

    # 5. Salva em máxima qualidade
    ts   = datetime.now().strftime("%Y%m%d_%H%M%S")
    nome = f"criativo_{segmento_key}_{ts}.png"
    dest = DIRETORIO_SAIDA / nome
    img.save(str(dest), format="PNG", optimize=False, compress_level=1)
    return str(dest)
