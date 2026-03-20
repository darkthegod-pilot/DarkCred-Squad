"""
Gerador de Imagens com IA — Alina Pretrov
Usa GPT-image-1 (OpenAI) para gerar fundos profissionais + Pillow para sobrepor texto.

Fluxo:
  1. Claude escreve prompt de imagem em inglês baseado no copy e segmento
  2. GPT-image-1 gera fundo fotorrealista/editorial 1024x1024
  3. Pillow redimensiona para 1080x1080, aplica overlay e sobrepõe texto exato
  4. Salva PNG em saidas/imagens/ sem marca d'água, sem logo
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

# ─────────────────────────────────────────────────────────────
# MAPEAMENTO DE SEGMENTO → CENA
# ─────────────────────────────────────────────────────────────

_CENAS_SEGMENTO = {
    "padaria":       "inside a warm, busy Brazilian bakery, fresh bread on shelves, golden lighting",
    "pizzaria":      "inside a lively Brazilian pizzeria kitchen, pizza oven glowing, chef at work",
    "lanchonete":    "behind the counter of a small Brazilian snack bar, bustling atmosphere",
    "restaurante":   "inside a cozy Brazilian restaurant, tables with warm lighting",
    "acai":          "at a colorful açaí smoothie shop counter in Brazil",
    "salao":         "inside a modern Brazilian hair salon, styling chairs and mirrors",
    "barbearia":     "inside a stylish Brazilian barbershop, barber tools on counter",
    "manicure":      "at a beauty nail salon in Brazil, nail tools and polish bottles",
    "estetica":      "inside a clean Brazilian aesthetics studio, professional setting",
    "academia":      "inside a well-equipped Brazilian gym, weights and equipment",
    "vestuario":     "inside a small clothing boutique in Brazil, racks of clothes",
    "calcados":      "inside a small shoe store in Brazil, shelves with shoes",
    "eletronicos":   "inside a small electronics shop in Brazil, devices on display",
    "mercadinho":    "inside a small Brazilian neighborhood market, shelves with products",
    "farmacia":      "inside a small Brazilian pharmacy, medicine shelves",
    "mecanico":      "inside a small auto repair shop in Brazil, tools and cars",
    "generico":      "a hardworking Brazilian small business owner at their shop counter, confident expression, warm lighting",
}

_CENA_PADRAO = "a confident Brazilian small business owner standing proudly at their shop, warm ambient lighting"

# ─────────────────────────────────────────────────────────────
# PROMPT BUILDER
# ─────────────────────────────────────────────────────────────

def _construir_prompt_imagem(variacao: dict, segmento_key: str) -> str:
    """
    Usa Claude para escrever um prompt de imagem detalhado em inglês.
    Se Claude não estiver disponível, usa prompt padrão baseado no segmento.
    """
    cena = _CENAS_SEGMENTO.get(segmento_key, _CENA_PADRAO)
    hook = variacao.get("hook", "")

    prompt_base = (
        f"Professional Instagram marketing photo for a Brazilian small business financial "
        f"services company. Scene: {cena}. "
        "Deep dark background with subtle warm orange and amber accent lighting. "
        "High-end commercial photography style, cinematic mood, shallow depth of field. "
        "No text, no logos, no watermarks, no signs with readable text. "
        "Square 1:1 composition. Award-winning editorial photography quality."
    )

    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not ANTHROPIC_SDK_DISPONIVEL or not api_key:
        return prompt_base

    try:
        client = _anthropic_sdk.Anthropic(api_key=api_key)
        resposta = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=300,
            system=(
                "You are an expert art director writing image generation prompts for Instagram ads. "
                "Write a single, detailed English prompt for GPT-image-1. "
                "The prompt must produce a professional marketing background photo. "
                "NEVER include text, logos, or watermarks in the scene description. "
                "Output ONLY the prompt, no explanation."
            ),
            messages=[{
                "role": "user",
                "content": (
                    f"Write an image prompt for this Brazilian small business ad:\n"
                    f"Hook: {hook}\n"
                    f"Segment: {segmento_key}\n"
                    f"Base scene: {cena}\n\n"
                    "Requirements: dark cinematic mood, deep navy/dark background, "
                    "warm orange/amber accent lighting, professional commercial photography, "
                    "no text, no logos, no watermarks, 1:1 square, ultra high quality."
                ),
            }],
        )
        return resposta.content[0].text.strip()
    except Exception:
        return prompt_base


# ─────────────────────────────────────────────────────────────
# GERAÇÃO DE FUNDO VIA GPT-IMAGE-1
# ─────────────────────────────────────────────────────────────

def _gerar_fundo_openai(prompt: str) -> bytes:
    """Chama GPT-image-1 e retorna bytes PNG da imagem gerada."""
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError(
            "OPENAI_API_KEY não encontrado. Adicione ao .env:\n  OPENAI_API_KEY=sk-proj-..."
        )
    if not OPENAI_SDK_DISPONIVEL:
        raise RuntimeError("openai não instalado. Execute: pip install openai>=1.0.0")

    client = _openai_sdk.OpenAI(api_key=api_key)
    resposta = client.images.generate(
        model="gpt-image-1",
        prompt=prompt,
        size="1024x1024",
        quality="high",
        n=1,
        output_format="png",
    )
    # gpt-image-1 retorna b64_json
    b64 = resposta.data[0].b64_json
    return base64.b64decode(b64)


# ─────────────────────────────────────────────────────────────
# COMPOSIÇÃO: FUNDO + OVERLAY + TEXTO
# ─────────────────────────────────────────────────────────────

def _aplicar_overlay(img: "Image.Image", opacidade: int = 145) -> "Image.Image":
    """Aplica overlay escuro semi-transparente para legibilidade do texto."""
    overlay = Image.new("RGBA", img.size, (0, 0, 0, opacidade))
    base = img.convert("RGBA")
    composto = Image.alpha_composite(base, overlay)
    return composto.convert("RGB")


def _sobrepor_texto(img: "Image.Image", variacao: dict) -> "Image.Image":
    """
    Sobrepõe hook, corpo e CTA sobre a imagem com tipografia profissional.
    Sem watermark, sem logo.
    """
    from alina.gerador_imagem import (
        _carregar_fonte,
        _quebrar_texto,
        _renderizar_texto_multilinha,
        _desenhar_botao_cta,
        _limpar_emojis,
        CORES,
    )

    W, H = img.size
    draw = ImageDraw.Draw(img)

    hook  = _limpar_emojis(variacao.get("hook", ""))
    corpo = _limpar_emojis(variacao.get("corpo", variacao.get("body", "")))
    cta   = variacao.get("cta", "Chama no direct")

    # Acento laranja no topo e lateral esquerda
    draw.rectangle([0, 0, W, 6], fill=CORES["laranja"])
    draw.rectangle([0, 0, 6, H], fill=CORES["laranja"])

    fonte_hook  = _carregar_fonte(68, negrito=True)
    fonte_corpo = _carregar_fonte(36, negrito=False)
    margem = 72
    max_larg = W - margem * 2

    linhas_hook  = _quebrar_texto(hook,  fonte_hook,  max_larg)
    linhas_corpo = _quebrar_texto(corpo, fonte_corpo, max_larg)

    alt_hook_bloco = sum(
        fonte_hook.getbbox(l)[3] - fonte_hook.getbbox(l)[1] + 14
        for l in linhas_hook
    )
    alt_corpo_bloco = sum(
        fonte_corpo.getbbox(l)[3] - fonte_corpo.getbbox(l)[1] + 10
        for l in linhas_corpo
    )
    alt_total = alt_hook_bloco + 52 + alt_corpo_bloco + 90 + 70
    y = max(80, (H - alt_total) // 2)

    y = _renderizar_texto_multilinha(
        draw, linhas_hook, fonte_hook, margem, y,
        CORES["branco"], centralizar=True, largura_canvas=W, espacamento=14,
    )

    # Separador laranja
    y += 22
    sep = 90
    draw.rectangle([(W - sep) // 2, y, (W + sep) // 2, y + 5], fill=CORES["laranja"])
    y += 28

    y = _renderizar_texto_multilinha(
        draw, linhas_corpo, fonte_corpo, margem, y,
        (230, 230, 230), centralizar=True, largura_canvas=W, espacamento=10,
    )
    y += 52
    _desenhar_botao_cta(draw, cta, y + 36, CORES["laranja"], CORES["branco"], CORES["laranja_sombra"])

    return img


# ─────────────────────────────────────────────────────────────
# PONTO DE ENTRADA PÚBLICO
# ─────────────────────────────────────────────────────────────

def gerar_criativo_ia(
    variacao: dict,
    segmento_key: str = "generico",
    template: Optional[int] = None,
) -> str:
    """
    Gera criativo Instagram com GPT-image-1 + texto sobreposto.

    Args:
        variacao:     Dict com hook, corpo/body, cta
        segmento_key: Chave do segmento (influi no prompt de imagem)
        template:     Ignorado — mantido por compatibilidade com gerar_criativo()

    Returns:
        Caminho absoluto do PNG salvo (1080x1080).
    """
    if not PILLOW_DISPONIVEL:
        raise RuntimeError("Pillow não instalado. Execute: pip install Pillow")

    DIRETORIO_SAIDA.mkdir(parents=True, exist_ok=True)

    # 1. Prompt de imagem via Claude
    prompt = _construir_prompt_imagem(variacao, segmento_key)

    # 2. Fundo via GPT-image-1
    bytes_img = _gerar_fundo_openai(prompt)

    # 3. Carrega e redimensiona para 1080x1080
    img = Image.open(_io.BytesIO(bytes_img)).convert("RGB")
    img = img.resize((1080, 1080), Image.LANCZOS)

    # 4. Overlay escuro para legibilidade
    img = _aplicar_overlay(img, opacidade=145)

    # 5. Sobrepõe texto (sem watermark, sem logo)
    img = _sobrepor_texto(img, variacao)

    # 6. Salva
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    nome = f"alina_{segmento_key}_{ts}_ia.png"
    caminho = DIRETORIO_SAIDA / nome
    img.save(str(caminho), format="PNG", optimize=True)
    return str(caminho)
