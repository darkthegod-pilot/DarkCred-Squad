"""
Gerador de Imagens com IA — Alina Pretrov
GPT-image-1 gera fundo fotográfico profissional. Pillow sobrepõe texto com
tipografia Poppins, hierarquia visual clara e overlay gradiente cinematográfico.

Saída: PNG 1080x1080 sem marca d'água, sem logo, pronto para Meta Ads.
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
ASSETS_FONTS = Path(__file__).parent.parent / "assets" / "fonts"

LARANJA   = (255, 107, 53)
LARANJA_E = (200, 75, 20)
BRANCO    = (255, 255, 255)
PRETO     = (0, 0, 0)

# ─────────────────────────────────────────────────────────────
# FONTS — Poppins com fallback para Liberation/DejaVu
# ─────────────────────────────────────────────────────────────

_FONT_CACHE: dict = {}

def _fonte(tamanho: int, peso: str = "bold") -> "ImageFont.FreeTypeFont":
    key = (tamanho, peso)
    if key in _FONT_CACHE:
        return _FONT_CACHE[key]

    candidatos = {
        "bold":     [str(ASSETS_FONTS / "Poppins-Bold.ttf"),
                     "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
                     "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"],
        "semibold": [str(ASSETS_FONTS / "Poppins-SemiBold.ttf"),
                     "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf"],
        "regular":  [str(ASSETS_FONTS / "Poppins-Regular.ttf"),
                     "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
                     "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"],
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

def _limpar_texto(texto: str) -> str:
    import unicodedata
    resultado = []
    for ch in texto:
        cp = ord(ch)
        cat = unicodedata.category(ch)
        if cp < 0x2000 or cat.startswith("L") or cat.startswith("N") or cat in ("Po","Pd","Ps","Pe","Pc","Zs"):
            resultado.append(ch)
        else:
            resultado.append(" ")
    return " ".join("".join(resultado).split())


def _quebrar(texto: str, fonte: "ImageFont.FreeTypeFont", max_px: int) -> list[str]:
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


def _altura_bloco(linhas: list[str], fonte: "ImageFont.FreeTypeFont", esp: int) -> int:
    total = 0
    for l in linhas:
        bb = fonte.getbbox(l)
        total += (bb[3] - bb[1]) + esp
    return total


def _draw_texto(draw, linhas, fonte, y, cor, W, esp=8):
    for l in linhas:
        bb = fonte.getbbox(l)
        lw = bb[2] - bb[0]
        lh = bb[3] - bb[1]
        x = (W - lw) // 2
        draw.text((x, y), l, font=fonte, fill=cor)
        y += lh + esp
    return y


def _draw_botao(img: "Image.Image", draw, texto: str, y_centro: int, W: int):
    texto = _limpar_texto(texto)
    f = _fonte(38, "bold")
    bb = f.getbbox(texto)
    tw = bb[2] - bb[0]
    th = bb[3] - bb[1]
    pad_h, pad_v = 72, 26
    bw = tw + pad_h * 2
    bh = th + pad_v * 2
    x0 = (W - bw) // 2
    y0 = y_centro - bh // 2
    x1, y1 = x0 + bw, y0 + bh
    r = 50

    # Sombra
    draw.rounded_rectangle([x0+4, y0+4, x1+4, y1+4], radius=r, fill=LARANJA_E)
    # Botão
    draw.rounded_rectangle([x0, y0, x1, y1], radius=r, fill=LARANJA)
    # Texto
    xt = x0 + (bw - tw) // 2
    yt = y0 + pad_v - bb[1]
    draw.text((xt, yt), texto, font=f, fill=BRANCO)


# ─────────────────────────────────────────────────────────────
# OVERLAY GRADIENTE (mais escuro embaixo onde está o texto)
# ─────────────────────────────────────────────────────────────

def _overlay_gradiente(img: "Image.Image") -> "Image.Image":
    """Overlay escuro em gradiente: quase transparente no topo, opaco embaixo."""
    W, H = img.size
    base = img.convert("RGBA")

    if NUMPY_DISPONIVEL:
        alpha = np.linspace(30, 210, H, dtype=np.uint8)          # topo claro → base escura
        overlay_arr = np.zeros((H, W, 4), dtype=np.uint8)
        overlay_arr[:, :, 3] = alpha[:, np.newaxis]               # só canal alpha
        overlay = Image.fromarray(overlay_arr, "RGBA")
    else:
        overlay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        od = ImageDraw.Draw(overlay)
        for y in range(H):
            a = int(30 + (210 - 30) * (y / H))
            od.line([(0, y), (W, y)], fill=(0, 0, 0, a))

    return Image.alpha_composite(base, overlay).convert("RGB")


# ─────────────────────────────────────────────────────────────
# COMPOSIÇÃO DO TEXTO
# ─────────────────────────────────────────────────────────────

def _compor_texto(img: "Image.Image", variacao: dict) -> "Image.Image":
    W, H = img.size
    draw = ImageDraw.Draw(img)

    hook  = _limpar_texto(variacao.get("hook", ""))
    corpo = _limpar_texto(variacao.get("corpo", variacao.get("body", "")))
    cta   = variacao.get("cta", "Manda uma mensagem agora")

    # Fontes
    f_hook  = _fonte(72, "bold")
    f_corpo = _fonte(38, "regular")

    margem  = 80
    max_larg = W - margem * 2

    linhas_hook  = _quebrar(hook,  f_hook,  max_larg)
    linhas_corpo = _quebrar(corpo, f_corpo, max_larg)

    h_hook  = _altura_bloco(linhas_hook,  f_hook,  16)
    h_corpo = _altura_bloco(linhas_corpo, f_corpo, 12)
    h_sep   = 16   # separador laranja
    h_btn   = 90   # botão
    h_total = h_hook + 36 + h_sep + 28 + h_corpo + 56 + h_btn

    y = max(60, (H - h_total) // 2)

    # Hook — branco, bold, com sombra suave
    for l in linhas_hook:
        bb = f_hook.getbbox(l)
        lw = bb[2] - bb[0]
        lh = bb[3] - bb[1]
        x  = (W - lw) // 2
        # sombra
        draw.text((x+2, y+2), l, font=f_hook, fill=(0, 0, 0, 160) if img.mode == "RGBA" else (10, 10, 10))
        draw.text((x, y),     l, font=f_hook, fill=BRANCO)
        y += lh + 16

    # Separador laranja
    y += 20
    sw = 80
    draw.rounded_rectangle([(W-sw)//2, y, (W+sw)//2, y+5], radius=3, fill=LARANJA)
    y += 5 + 24

    # Corpo — branco suave
    for l in linhas_corpo:
        bb = f_corpo.getbbox(l)
        lw = bb[2] - bb[0]
        lh = bb[3] - bb[1]
        x  = (W - lw) // 2
        draw.text((x, y), l, font=f_corpo, fill=(230, 230, 230))
        y += lh + 12

    # Botão CTA
    y += 48
    _draw_botao(img, draw, cta, y + 38, W)

    return img


# ─────────────────────────────────────────────────────────────
# PROMPT DE IMAGEM
# ─────────────────────────────────────────────────────────────

_CENAS = {
    "generico":   "a confident Brazilian small business owner, male or female, standing proudly at their shop counter or workspace, looking directly at camera with a determined expression",
    "padaria":    "inside a warm Brazilian bakery, golden bread on shelves, soft morning light",
    "pizzaria":   "inside a lively Brazilian pizzeria, glowing pizza oven, chef at work",
    "lanchonete": "behind a small Brazilian snack bar counter, colorful food display",
    "restaurante":"inside a cozy Brazilian restaurant, warm candlelight ambiance",
    "acai":       "at a vibrant Brazilian açaí smoothie shop, colorful cups on counter",
    "salao":      "inside a modern Brazilian hair salon, styling chairs, mirrors and warm lighting",
    "barbearia":  "inside a stylish Brazilian barbershop, barber tools artistically arranged",
    "manicure":   "at a bright Brazilian nail salon, polish bottles and tools on display",
    "estetica":   "inside a clean modern Brazilian aesthetics studio, professional lighting",
    "academia":   "inside a well-equipped Brazilian gym, weights and equipment in background",
    "vestuario":  "inside a small trendy clothing boutique in Brazil, racks of colorful clothes",
    "mercadinho": "inside a small Brazilian neighborhood market, shelves full of products",
    "mecanico":   "inside a small auto repair shop in Brazil, mechanic with professional tools",
}

def _construir_prompt(variacao: dict, segmento_key: str) -> str:
    cena = _CENAS.get(segmento_key, _CENAS["generico"])
    base = (
        f"Cinematic commercial photography for Instagram ad. {cena}. "
        "Dramatic dark background, deep shadows, warm orange and amber accent lighting from the side. "
        "Bokeh background, shallow depth of field, professional studio quality. "
        "Color palette: very dark navy/charcoal background with rich warm orange highlights. "
        "Ultra sharp focus on subject, editorial magazine quality. "
        "NO text, NO logos, NO watermarks, NO signs with words. Square 1:1 format."
    )

    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not ANTHROPIC_SDK_DISPONIVEL or not api_key:
        return base
    try:
        client = _anthropic_sdk.Anthropic(api_key=api_key)
        r = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=250,
            system="You are an expert art director. Write a single English prompt for GPT-image-1 to generate a professional Instagram ad background photo. Output ONLY the prompt, no explanation.",
            messages=[{"role": "user", "content":
                f"Segment: {segmento_key}\nScene base: {cena}\n"
                "Requirements: cinematic dark mood, warm orange accent lighting, "
                "NO text, NO logos, square 1:1, ultra high quality commercial photography."}],
        )
        return r.content[0].text.strip()
    except Exception:
        return base


# ─────────────────────────────────────────────────────────────
# GERAÇÃO DE FUNDO
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
    Gera criativo 1080x1080 com GPT-image-1 + tipografia Poppins.
    Sem marca d'água. Sem logo. Pronto para Meta Ads.
    Retorna caminho absoluto do PNG.
    """
    if not PILLOW_DISPONIVEL:
        raise RuntimeError("Pillow não instalado: pip install Pillow")

    DIRETORIO_SAIDA.mkdir(parents=True, exist_ok=True)

    prompt   = _construir_prompt(variacao, segmento_key)
    raw      = _gerar_fundo(prompt)

    img = Image.open(_io.BytesIO(raw)).convert("RGB")
    img = img.resize((1080, 1080), Image.LANCZOS)
    img = _overlay_gradiente(img)
    img = _compor_texto(img, variacao)

    ts    = datetime.now().strftime("%Y%m%d_%H%M%S")
    nome  = f"criativo_{segmento_key}_{ts}.png"
    dest  = DIRETORIO_SAIDA / nome
    img.save(str(dest), format="PNG", optimize=False, compress_level=1)   # máxima qualidade
    return str(dest)
