"""
Gerador de Imagens com IA — Alina Pretrov
GPT-image-1 quality="high" (teto da OpenAI) + composição profissional com Poppins.

Design:
- Fundo 1024×1024 nativo (sem upscale)
- Painel escuro no terço inferior + gradiente de transição acima
- Hook em LARANJA (#FF6B35), Poppins Bold 78px
- Corpo em BRANCO, Poppins SemiBold 40px
- Sombra de texto em 4 offsets
- Botão CTA laranja grande

Saída: PNG 1024×1024 sem marca d'água, sem logo, pronto para Meta Ads.
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

LARANJA   = (255, 107, 53)
LARANJA_E = (190, 65, 15)
BRANCO    = (255, 255, 255)
SOMBRA    = (0, 0, 0)

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
                or cat in ("Po","Pd","Ps","Pe","Pc","Zs"):
            out.append(ch)
        else:
            out.append(" ")
    return " ".join("".join(out).split())


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


def _draw_sombra(draw, x, y, texto, fonte, cor, sombra=SOMBRA, offset=2):
    """Sombra em 4 offsets diagonais para simular profundidade sem blur."""
    for dx, dy in [(-offset,-offset),(offset,-offset),(-offset,offset),(offset,offset)]:
        draw.text((x+dx, y+dy), texto, font=fonte, fill=sombra)
    draw.text((x, y), texto, font=fonte, fill=cor)


# ─────────────────────────────────────────────────────────────
# OVERLAY — painel escuro no terço inferior com gradiente de transição
# ─────────────────────────────────────────────────────────────

def _overlay_painel(img: "Image.Image") -> "Image.Image":
    """
    Preserva foto no topo. Escurece progressivamente a partir de 40% da altura
    até opacidade ~195/255 no rodapé — área limpa para o texto.
    """
    W, H = img.size
    base = img.convert("RGBA")
    overlay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)

    inicio_transicao = int(H * 0.38)
    fim_transicao    = int(H * 0.58)
    opacidade_painel = 195

    # Gradiente de transição
    for y in range(inicio_transicao, fim_transicao):
        progresso = (y - inicio_transicao) / max(fim_transicao - inicio_transicao, 1)
        a = int(opacidade_painel * progresso)
        draw.line([(0, y), (W, y)], fill=(0, 0, 0, a))

    # Painel sólido abaixo da transição
    draw.rectangle([0, fim_transicao, W, H], fill=(0, 0, 0, opacidade_painel))

    return Image.alpha_composite(base, overlay).convert("RGB")


# ─────────────────────────────────────────────────────────────
# COMPOSIÇÃO DE TEXTO
# ─────────────────────────────────────────────────────────────

def _botao_cta(draw: "ImageDraw.ImageDraw", texto: str, y_centro: int, W: int):
    f   = _fonte(38, "bold")
    bb  = f.getbbox(texto)
    tw  = bb[2] - bb[0]
    th  = bb[3] - bb[1]
    ph, pv = 70, 24
    bw  = tw + ph * 2
    bh  = th + pv * 2
    x0  = (W - bw) // 2
    y0  = y_centro - bh // 2
    x1, y1 = x0 + bw, y0 + bh
    r   = 48

    # Sombra sólida
    draw.rounded_rectangle([x0+4, y0+5, x1+4, y1+5], radius=r, fill=LARANJA_E)
    # Botão
    draw.rounded_rectangle([x0, y0, x1, y1], radius=r, fill=LARANJA)
    # Texto
    xt = x0 + (bw - tw) // 2
    yt = y0 + pv - bb[1]
    draw.text((xt, yt), texto, font=f, fill=BRANCO)


def _compor_texto(img: "Image.Image", variacao: dict) -> "Image.Image":
    W, H  = img.size
    draw  = ImageDraw.Draw(img)

    hook  = _limpar(variacao.get("hook", ""))
    corpo = _limpar(variacao.get("corpo", variacao.get("body", "")))
    cta   = variacao.get("cta", "Manda uma mensagem agora")

    f_hook  = _fonte(78, "bold")
    f_corpo = _fonte(40, "semibold")

    margem   = 72
    max_larg = W - margem * 2

    linhas_hook  = _quebrar(hook,  f_hook,  max_larg)
    linhas_corpo = _quebrar(corpo, f_corpo, max_larg)

    # Calcula altura total do bloco de texto
    def alt_bloco(linhas, fonte, esp):
        return sum((fonte.getbbox(l)[3] - fonte.getbbox(l)[1]) + esp for l in linhas)

    h_hook  = alt_bloco(linhas_hook,  f_hook,  18)
    h_sep   = 5 + 28 + 28          # separador + margens
    h_corpo = alt_bloco(linhas_corpo, f_corpo, 14)
    h_btn   = 90
    h_total = h_hook + h_sep + h_corpo + 56 + h_btn

    # Posiciona o bloco no rodapé da imagem (com padding de 48px abaixo)
    y = H - h_total - 54

    # — Hook em LARANJA —
    for linha in linhas_hook:
        bb = f_hook.getbbox(linha)
        lw = bb[2] - bb[0]
        lh = bb[3] - bb[1]
        x  = (W - lw) // 2
        _draw_sombra(draw, x, y, linha, f_hook, LARANJA, offset=3)
        y += lh + 18

    # — Separador —
    y += 14
    sw = 72
    draw.rounded_rectangle([(W-sw)//2, y, (W+sw)//2, y+5], radius=3, fill=LARANJA)
    y += 5 + 22

    # — Corpo em BRANCO SemiBold —
    for linha in linhas_corpo:
        bb = f_corpo.getbbox(linha)
        lw = bb[2] - bb[0]
        lh = bb[3] - bb[1]
        x  = (W - lw) // 2
        _draw_sombra(draw, x, y, linha, f_corpo, BRANCO, offset=2)
        y += lh + 14

    # — Botão CTA —
    y += 44
    _botao_cta(draw, cta, y + 36, W)

    return img


# ─────────────────────────────────────────────────────────────
# PROMPT DE IMAGEM (Claude → GPT-image-1)
# ─────────────────────────────────────────────────────────────

_CENAS: dict[str, str] = {
    "generico":   "a confident and determined Brazilian small business owner, standing at their shop, looking directly at camera",
    "padaria":    "a Brazilian bakery owner behind the counter, fresh golden bread on warm shelves",
    "pizzaria":   "a Brazilian pizzeria chef near a glowing pizza oven, professional kitchen",
    "lanchonete": "a small Brazilian snack bar owner behind a colorful counter display",
    "restaurante":"a Brazilian restaurant owner in a warmly lit dining room",
    "acai":       "a vibrant Brazilian açaí shop attendant with colorful cups on the counter",
    "salao":      "a Brazilian hairdresser in a modern salon with mirrors and styling chairs",
    "barbearia":  "a Brazilian barber in a stylish barbershop with professional tools",
    "manicure":   "a Brazilian nail technician at a bright nail salon, polish bottles on display",
    "estetica":   "inside a clean modern Brazilian aesthetics studio with professional lighting",
    "academia":   "a Brazilian gym owner in a well-equipped fitness studio",
    "vestuario":  "a Brazilian clothing store owner among racks of colorful garments",
    "mercadinho": "a Brazilian neighborhood market owner with shelves full of products",
    "mecanico":   "a Brazilian mechanic in an auto repair shop with professional tools",
}

_BASE_PROMPT = (
    "Cinematic dark commercial photography for a Brazilian Instagram ad. {cena}. "
    "Subject positioned in the UPPER or CENTER portion of the frame — "
    "the LOWER HALF of the image must be VERY DARK (almost black) to allow text overlay. "
    "Dramatic warm orange and amber side lighting. Deep shadows. Bokeh background. "
    "Ultra sharp focus on subject. Professional editorial magazine quality. "
    "Color palette: very dark charcoal/black background, rich warm orange accent highlights. "
    "NO text, NO logos, NO watermarks, NO readable signs. Perfect square 1:1 composition."
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
            max_tokens=300,
            system=(
                "You are a world-class art director specializing in Instagram ads. "
                "Write a single English image generation prompt for GPT-image-1. "
                "CRITICAL: The lower half of the image MUST be very dark for text overlay. "
                "Subject must be in upper/center portion. NO text, logos, or watermarks. "
                "Output ONLY the prompt."
            ),
            messages=[{"role": "user", "content":
                f"Hook: {variacao.get('hook','')}\n"
                f"Segment: {segmento_key}\n"
                f"Base scene: {cena}\n\n"
                "Generate a premium cinematic ad photography prompt. "
                "Dark lower half mandatory. Orange accent lighting. Ultra quality."}],
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
        quality="high",     # plano mais caro / maior qualidade disponível
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
    Gera criativo 1024×1024 com GPT-image-1 quality="high" + composição Poppins.

    Fluxo:
      1. Claude escreve prompt cinematográfico (ou usa base prompt)
      2. GPT-image-1 gera fundo fotorrealista 1024×1024 (sem upscale)
      3. Painel escuro no terço inferior preserva foto no topo
      4. Hook laranja + corpo branco SemiBold + botão CTA

    Retorna caminho absoluto do PNG.
    """
    if not PILLOW_DISPONIVEL:
        raise RuntimeError("Pillow não instalado: pip install Pillow")

    DIRETORIO_SAIDA.mkdir(parents=True, exist_ok=True)

    # 1. Prompt
    prompt = _construir_prompt(variacao, segmento_key)

    # 2. Fundo via GPT-image-1 (1024×1024 nativo, sem resize)
    raw = _gerar_fundo(prompt)
    img = Image.open(_io.BytesIO(raw)).convert("RGB")
    # Não redimensiona — mantém qualidade nativa 1024×1024

    # 3. Painel escuro para legibilidade
    img = _overlay_painel(img)

    # 4. Composição de texto
    img = _compor_texto(img, variacao)

    # 5. Salva em máxima qualidade (compress_level=1 = mínima compressão)
    ts   = datetime.now().strftime("%Y%m%d_%H%M%S")
    nome = f"criativo_{segmento_key}_{ts}.png"
    dest = DIRETORIO_SAIDA / nome
    img.save(str(dest), format="PNG", optimize=False, compress_level=1)
    return str(dest)
