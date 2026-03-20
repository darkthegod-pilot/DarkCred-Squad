"""
Gerador de Imagens — Alina Pretrov
Cria criativos 1080x1080px para Instagram usando Pillow.

Três templates DarkCred:
  1 — Escuro Moderno   (gradiente roxo/azul escuro, padrão)
  2 — Claro Impacto    (branco + bloco laranja no topo)
  3 — Comerciante      (gradiente verde, tom terra brasileiro)
"""

import random
from datetime import datetime
from pathlib import Path
from typing import Optional

try:
    from PIL import Image, ImageDraw, ImageFont
    PILLOW_DISPONIVEL = True
except ImportError:
    PILLOW_DISPONIVEL = False

try:
    import numpy as np
    NUMPY_DISPONIVEL = True
except ImportError:
    NUMPY_DISPONIVEL = False

# ─────────────────────────────────────────────────────────────
# PALETA DARKCRED
# ─────────────────────────────────────────────────────────────

CORES = {
    "roxo_escuro":  (26, 5, 51),
    "azul_escuro":  (13, 27, 75),
    "verde_escuro": (13, 51, 33),
    "verde_medio":  (26, 92, 58),
    "laranja":      (255, 107, 53),
    "laranja_sombra": (180, 70, 30),
    "dourado":      (255, 215, 0),
    "dourado_sombra": (180, 150, 0),
    "branco":       (255, 255, 255),
    "branco_suave": (240, 240, 240),
    "cinza_claro":  (200, 200, 200),
    "preto":        (0, 0, 0),
    "preto_suave":  (26, 26, 26),
    "sombra_escura": (0, 0, 0),
}

TAMANHO_CANVAS = (1080, 1080)
DIRETORIO_SAIDA = Path("saidas/imagens")

# ─────────────────────────────────────────────────────────────
# FONTES com cache
# ─────────────────────────────────────────────────────────────

_CANDIDATOS_FONTES_BOLD = [
    "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
]
_CANDIDATOS_FONTES_REGULAR = [
    "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
]
_FONTE_CACHE: dict = {}


def _carregar_fonte(tamanho: int, negrito: bool = False) -> "ImageFont.FreeTypeFont":
    key = (tamanho, negrito)
    if key in _FONTE_CACHE:
        return _FONTE_CACHE[key]
    candidatos = _CANDIDATOS_FONTES_BOLD if negrito else _CANDIDATOS_FONTES_REGULAR
    for caminho in candidatos:
        if Path(caminho).exists():
            try:
                fonte = ImageFont.truetype(caminho, tamanho)
                _FONTE_CACHE[key] = fonte
                return fonte
            except Exception:
                continue
    fonte = ImageFont.load_default()
    _FONTE_CACHE[key] = fonte
    return fonte


# ─────────────────────────────────────────────────────────────
# GRADIENTES (otimizados com numpy quando disponível)
# ─────────────────────────────────────────────────────────────

def _gradiente_vertical_img(
    cor_topo: tuple, cor_base: tuple, largura: int, altura: int
) -> "Image.Image":
    """Gera imagem com gradiente vertical usando numpy (rápido) ou fallback."""
    if NUMPY_DISPONIVEL:
        t = np.linspace(0, 1, altura, dtype=np.float32)
        r = (cor_topo[0] + (cor_base[0] - cor_topo[0]) * t).astype(np.uint8)
        g = (cor_topo[1] + (cor_base[1] - cor_topo[1]) * t).astype(np.uint8)
        b = (cor_topo[2] + (cor_base[2] - cor_topo[2]) * t).astype(np.uint8)
        array = np.stack([r, g, b], axis=1)          # (altura, 3)
        array = np.repeat(array[:, np.newaxis, :], largura, axis=1)  # (altura, largura, 3)
        return Image.fromarray(array, "RGB")
    else:
        img = Image.new("RGB", (largura, altura))
        draw = ImageDraw.Draw(img)
        for y in range(altura):
            t = y / max(altura - 1, 1)
            r = int(cor_topo[0] + (cor_base[0] - cor_topo[0]) * t)
            g = int(cor_topo[1] + (cor_base[1] - cor_topo[1]) * t)
            b = int(cor_topo[2] + (cor_base[2] - cor_topo[2]) * t)
            draw.line([(0, y), (largura, y)], fill=(r, g, b))
        return img


def _gradiente_diagonal_img(
    cor_topo: tuple, cor_base: tuple, largura: int, altura: int
) -> "Image.Image":
    """Gera imagem com gradiente diagonal (canto sup-esq → inf-dir)."""
    if NUMPY_DISPONIVEL:
        y_idx = np.linspace(0, 1, altura, dtype=np.float32)
        x_idx = np.linspace(0, 1, largura, dtype=np.float32)
        # t[y, x] = (y + x) / 2
        t = (y_idx[:, np.newaxis] + x_idx[np.newaxis, :]) / 2
        t = np.clip(t, 0, 1).astype(np.float32)
        r = (cor_topo[0] + (cor_base[0] - cor_topo[0]) * t).astype(np.uint8)
        g = (cor_topo[1] + (cor_base[1] - cor_topo[1]) * t).astype(np.uint8)
        b = (cor_topo[2] + (cor_base[2] - cor_topo[2]) * t).astype(np.uint8)
        array = np.stack([r, g, b], axis=2)
        return Image.fromarray(array, "RGB")
    else:
        return _gradiente_vertical_img(cor_topo, cor_base, largura, altura)


# ─────────────────────────────────────────────────────────────
# HELPERS DE TEXTO
# ─────────────────────────────────────────────────────────────

def _quebrar_texto(texto: str, fonte: "ImageFont.FreeTypeFont", max_px: int) -> list:
    """Quebra texto em linhas para caber em max_px de largura."""
    palavras = texto.split()
    linhas = []
    linha_atual = ""
    for palavra in palavras:
        candidato = (linha_atual + " " + palavra).strip()
        bbox = fonte.getbbox(candidato)
        if (bbox[2] - bbox[0]) <= max_px:
            linha_atual = candidato
        else:
            if linha_atual:
                linhas.append(linha_atual)
            # Trunca palavra que sozinha excede o limite
            while True:
                bbox_p = fonte.getbbox(palavra)
                if (bbox_p[2] - bbox_p[0]) <= max_px or len(palavra) <= 3:
                    break
                palavra = palavra[:-1]
            linha_atual = palavra
    if linha_atual:
        linhas.append(linha_atual)
    return linhas


def _limpar_emojis(texto: str) -> str:
    """Remove emojis que não renderizam corretamente em DejaVu/Liberation."""
    import unicodedata
    resultado = []
    for ch in texto:
        cat = unicodedata.category(ch)
        cp = ord(ch)
        # Mantém ASCII, latim estendido, pontuação comum, letras acentuadas
        if cp < 0x2000 or cat.startswith("L") or cat.startswith("N") or cat in ("Po", "Pd", "Ps", "Pe", "Pc"):
            resultado.append(ch)
        else:
            resultado.append(" ")
    # Une os chars sem separador, depois colapsa espaços duplos
    return " ".join("".join(resultado).split())


def _renderizar_texto_multilinha(
    draw: "ImageDraw.ImageDraw",
    linhas: list,
    fonte: "ImageFont.FreeTypeFont",
    x: int,
    y_inicio: int,
    cor: tuple,
    centralizar: bool = True,
    largura_canvas: int = 1080,
    espacamento: int = 8,
) -> int:
    """Renderiza linhas de texto. Retorna Y após última linha."""
    y = y_inicio
    for linha in linhas:
        bbox = fonte.getbbox(linha)
        larg = bbox[2] - bbox[0]
        alt = bbox[3] - bbox[1]
        x_pos = (largura_canvas - larg) // 2 if centralizar else x
        draw.text((x_pos, y), linha, font=fonte, fill=cor)
        y += alt + espacamento
    return y


def _desenhar_botao_cta(
    draw: "ImageDraw.ImageDraw",
    texto: str,
    y_centro: int,
    cor_fundo: tuple,
    cor_texto: tuple,
    cor_sombra: tuple,
    largura_canvas: int = 1080,
) -> None:
    """Desenha botão CTA arredondado centralizado com sombra sólida."""
    texto = _limpar_emojis(texto)
    fonte = _carregar_fonte(36, negrito=True)
    bbox = fonte.getbbox(texto)
    larg_texto = bbox[2] - bbox[0]
    alt_linha = bbox[3] - bbox[1]
    offset_baseline = bbox[1]  # distância do topo até a baseline visual

    padding_h = 64
    padding_v = 22
    larg_botao = larg_texto + padding_h * 2
    alt_botao = alt_linha + padding_v * 2

    x0 = (largura_canvas - larg_botao) // 2
    y0 = y_centro - alt_botao // 2
    x1 = x0 + larg_botao
    y1 = y0 + alt_botao

    # Sombra sólida (offset de 5px) — funciona em RGB sem alpha
    s = 5
    draw.rounded_rectangle([x0 + s, y0 + s, x1 + s, y1 + s], radius=42, fill=cor_sombra)
    # Botão principal
    draw.rounded_rectangle([x0, y0, x1, y1], radius=42, fill=cor_fundo)
    # Texto centralizado vertical e horizontalmente
    x_texto = x0 + (larg_botao - larg_texto) // 2
    y_texto = y0 + padding_v - offset_baseline
    draw.text((x_texto, y_texto), texto, font=fonte, fill=cor_texto)



# ─────────────────────────────────────────────────────────────
# TEMPLATE 1 — ESCURO MODERNO
# ─────────────────────────────────────────────────────────────

def _template_escuro(variacao: dict) -> "Image.Image":
    W, H = TAMANHO_CANVAS
    img = _gradiente_diagonal_img(CORES["roxo_escuro"], CORES["azul_escuro"], W, H)
    draw = ImageDraw.Draw(img)

    # Acento lateral laranja
    draw.rectangle([0, 0, 7, H], fill=CORES["laranja"])
    # Linha topo
    draw.rectangle([0, 0, W, 7], fill=CORES["laranja"])

    hook  = _limpar_emojis(variacao.get("hook", ""))
    corpo = _limpar_emojis(variacao.get("corpo", variacao.get("body", "")))
    cta   = variacao.get("cta", "Chama no direct")

    fonte_hook  = _carregar_fonte(66, negrito=True)
    fonte_corpo = _carregar_fonte(36, negrito=False)
    margem = 72
    max_larg = W - margem * 2

    linhas_hook  = _quebrar_texto(hook,  fonte_hook,  max_larg)
    linhas_corpo = _quebrar_texto(corpo, fonte_corpo, max_larg)

    alt_hook_bloco  = sum(
        fonte_hook.getbbox(l)[3] - fonte_hook.getbbox(l)[1] + 14
        for l in linhas_hook
    )
    alt_corpo_bloco = sum(
        fonte_corpo.getbbox(l)[3] - fonte_corpo.getbbox(l)[1] + 10
        for l in linhas_corpo
    )
    alt_total = alt_hook_bloco + 52 + alt_corpo_bloco + 90 + 70
    y = max(60, (H - alt_total) // 2)

    y = _renderizar_texto_multilinha(
        draw, linhas_hook, fonte_hook, margem, y,
        CORES["branco"], centralizar=True, largura_canvas=W, espacamento=14,
    )
    # Separador
    y += 22
    sep = 90
    draw.rectangle([(W - sep) // 2, y, (W + sep) // 2, y + 5], fill=CORES["laranja"])
    y += 26

    y = _renderizar_texto_multilinha(
        draw, linhas_corpo, fonte_corpo, margem, y,
        CORES["cinza_claro"], centralizar=True, largura_canvas=W, espacamento=10,
    )
    y += 52
    _desenhar_botao_cta(draw, cta, y + 36, CORES["laranja"], CORES["branco"], CORES["laranja_sombra"])
    return img


# ─────────────────────────────────────────────────────────────
# TEMPLATE 2 — CLARO IMPACTO
# ─────────────────────────────────────────────────────────────

def _template_claro(variacao: dict) -> "Image.Image":
    W, H = TAMANHO_CANVAS
    img = Image.new("RGB", (W, H), CORES["branco"])
    draw = ImageDraw.Draw(img)

    ALTURA_BLOCO = 390

    # Bloco laranja com gradiente sutil
    bloco = _gradiente_vertical_img(CORES["laranja"], (220, 85, 35), W, ALTURA_BLOCO)
    img.paste(bloco, (0, 0))
    draw = ImageDraw.Draw(img)

    # Linha branca no rodapé do bloco
    draw.rectangle([0, ALTURA_BLOCO - 7, W, ALTURA_BLOCO], fill=CORES["branco"])

    hook  = _limpar_emojis(variacao.get("hook", ""))
    corpo = _limpar_emojis(variacao.get("corpo", variacao.get("body", "")))
    cta   = variacao.get("cta", "Chama no direct")

    fonte_hook  = _carregar_fonte(60, negrito=True)
    fonte_corpo = _carregar_fonte(36, negrito=False)
    margem = 64
    max_larg = W - margem * 2

    linhas_hook  = _quebrar_texto(hook,  fonte_hook,  max_larg)
    linhas_corpo = _quebrar_texto(corpo, fonte_corpo, max_larg)

    # Centraliza hook na área laranja
    alt_hook_bloco = sum(
        fonte_hook.getbbox(l)[3] - fonte_hook.getbbox(l)[1] + 14
        for l in linhas_hook
    )
    y_hook = max(24, (ALTURA_BLOCO - alt_hook_bloco) // 2)
    _renderizar_texto_multilinha(
        draw, linhas_hook, fonte_hook, margem, y_hook,
        CORES["branco"], centralizar=True, largura_canvas=W, espacamento=14,
    )

    # Corpo na área branca
    y = ALTURA_BLOCO + 56
    y = _renderizar_texto_multilinha(
        draw, linhas_corpo, fonte_corpo, margem, y,
        CORES["preto_suave"], centralizar=True, largura_canvas=W, espacamento=12,
    )
    y += 52
    _desenhar_botao_cta(draw, cta, y + 36, CORES["preto_suave"], CORES["branco"], (80, 80, 80))
    return img


# ─────────────────────────────────────────────────────────────
# TEMPLATE 3 — COMERCIANTE DIRETO
# ─────────────────────────────────────────────────────────────

def _template_verde(variacao: dict) -> "Image.Image":
    W, H = TAMANHO_CANVAS
    img = _gradiente_vertical_img(CORES["verde_escuro"], CORES["verde_medio"], W, H)
    draw = ImageDraw.Draw(img)

    # Decoração: arcos dourados no canto superior direito
    draw.arc([W - 210, -90, W + 70, 210],  start=140, end=260, fill=(180, 140, 0), width=3)
    draw.arc([W - 150, -30, W + 10, 150],  start=145, end=255, fill=(150, 115, 0), width=2)

    # Linha decorativa inferior
    draw.rectangle([40, H - 12, W - 40, H - 8], fill=(180, 140, 0))

    hook  = _limpar_emojis(variacao.get("hook", ""))
    corpo = _limpar_emojis(variacao.get("corpo", variacao.get("body", "")))
    cta   = variacao.get("cta", "Chama no direct")

    fonte_hook  = _carregar_fonte(64, negrito=True)
    fonte_corpo = _carregar_fonte(36, negrito=False)
    margem = 72
    max_larg = W - margem * 2

    linhas_hook  = _quebrar_texto(hook,  fonte_hook,  max_larg)
    linhas_corpo = _quebrar_texto(corpo, fonte_corpo, max_larg)

    alt_hook_bloco  = sum(
        fonte_hook.getbbox(l)[3] - fonte_hook.getbbox(l)[1] + 14
        for l in linhas_hook
    )
    alt_corpo_bloco = sum(
        fonte_corpo.getbbox(l)[3] - fonte_corpo.getbbox(l)[1] + 10
        for l in linhas_corpo
    )
    alt_total = alt_hook_bloco + 52 + alt_corpo_bloco + 90 + 70
    y = max(60, (H - alt_total) // 2)

    y = _renderizar_texto_multilinha(
        draw, linhas_hook, fonte_hook, margem, y,
        CORES["dourado"], centralizar=True, largura_canvas=W, espacamento=14,
    )
    y += 24
    draw.rectangle([margem, y, W - margem, y + 3], fill=(180, 140, 0))
    y += 28

    y = _renderizar_texto_multilinha(
        draw, linhas_corpo, fonte_corpo, margem, y,
        CORES["branco_suave"], centralizar=True, largura_canvas=W, espacamento=10,
    )
    y += 52
    _desenhar_botao_cta(draw, cta, y + 36, CORES["dourado"], CORES["preto_suave"], CORES["dourado_sombra"])
    return img


# ─────────────────────────────────────────────────────────────
# PONTO DE ENTRADA
# ─────────────────────────────────────────────────────────────

_TEMPLATES = {1: _template_escuro, 2: _template_claro, 3: _template_verde}

_VARIACAO_PREVIEW = {
    "hook":  "Precisa de giro pro seu negocio?",
    "corpo": "Comerciante que e comerciante sabe o que e aperto. A gente esta aqui pra dar forca no caixa quando voce mais precisa. Sem burocracia.",
    "cta":   "Chama no direct",
}


def gerar_criativo(
    variacao: dict,
    segmento_key: str = "generico",
    template: Optional[int] = None,
    fundo_ia: Optional[str] = None,
) -> str:
    """
    Gera imagem PNG 1080x1080 para o criativo.

    Quando OPENAI_API_KEY estiver configurada, usa GPT-image-1 (IA de última geração).
    Caso contrário, usa templates Pillow como fallback.

    Args:
        variacao:     Dict com hook, corpo/body, cta
        segmento_key: Chave do segmento (para nome do arquivo)
        template:     1, 2 ou 3 — None = aleatório (ignorado no modo IA)
        fundo_ia:     Caminho para fundo externo (ignorado no modo IA)

    Returns:
        Caminho absoluto do PNG salvo.
    """
    import os
    if os.getenv("OPENAI_API_KEY"):
        from alina.gerador_imagem_ia import gerar_criativo_ia
        return gerar_criativo_ia(variacao, segmento_key, template)

    if not PILLOW_DISPONIVEL:
        raise RuntimeError("Pillow não está instalado. Execute: pip install Pillow")

    DIRETORIO_SAIDA.mkdir(parents=True, exist_ok=True)
    num = template if template in _TEMPLATES else random.randint(1, 3)
    img = _TEMPLATES[num](variacao)

    if fundo_ia and Path(fundo_ia).exists():
        try:
            fundo = Image.open(fundo_ia).convert("RGB").resize(TAMANHO_CANVAS)
            fundo_rgba = fundo.convert("RGBA")
            overlay = Image.new("RGBA", TAMANHO_CANVAS, (0, 0, 0, 150))
            fundo_escurecido = Image.alpha_composite(fundo_rgba, overlay)
            img_rgba = _TEMPLATES[num](variacao).convert("RGBA")
            img = Image.alpha_composite(fundo_escurecido, img_rgba).convert("RGB")
        except Exception:
            try:
                from alina.logger import log
                log.warning("Falha ao aplicar fundo IA — usando template Pillow puro")
            except Exception:
                pass

    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    nome = f"alina_{segmento_key}_{ts}_t{num}.png"
    caminho = DIRETORIO_SAIDA / nome
    img.save(str(caminho), format="PNG", optimize=True)
    return str(caminho)


def gerar_criativos_para_variacoes(
    variacoes: list,
    segmento_key: str = "generico",
    template: Optional[int] = None,
    usar_ia: bool = False,
) -> list:
    """
    Gera imagens para uma lista de variações aprovadas.

    Returns:
        Lista de caminhos dos PNGs gerados.
    """
    if not PILLOW_DISPONIVEL:
        raise RuntimeError("Pillow não está instalado. Execute: pip install Pillow")

    fundo_ia = None
    if usar_ia:
        try:
            from alina.nano_banana import gerar_fundo_ia, verificar_infsh_disponivel
            if verificar_infsh_disponivel():
                fundo_ia = gerar_fundo_ia(segmento_key)
        except Exception:
            pass

    caminhos = []
    for i, var in enumerate(variacoes):
        num = template if template else ((i % 3) + 1)
        caminho = gerar_criativo(var, segmento_key, template=num, fundo_ia=fundo_ia)
        caminhos.append(caminho)
    return caminhos


def gerar_previews_templates() -> list:
    """
    Gera 3 PNGs de preview (um por template) com copy fictício.
    Útil para o usuário visualizar os layouts sem precisar gerar copies reais.

    Returns:
        Lista com 3 caminhos de PNGs.
    """
    if not PILLOW_DISPONIVEL:
        raise RuntimeError("Pillow não está instalado. Execute: pip install Pillow")

    DIRETORIO_SAIDA.mkdir(parents=True, exist_ok=True)
    caminhos = []
    for num in [1, 2, 3]:
        img = _TEMPLATES[num](_VARIACAO_PREVIEW)
        nome = f"preview_template_{num}.png"
        caminho = DIRETORIO_SAIDA / nome
        img.save(str(caminho), format="PNG", optimize=True)
        caminhos.append(str(caminho))
    return caminhos


def regenerar_imagens_de_json(caminho_json: str, template: Optional[int] = None) -> list:
    """
    Lê um JSON de saída salvo e gera novas imagens para os copies nele contidos.

    Args:
        caminho_json: Caminho para arquivo JSON gerado por salvar_saida()
        template:     Template a usar (None = aleatório)

    Returns:
        Lista de caminhos dos PNGs gerados.
    """
    import json

    if not PILLOW_DISPONIVEL:
        raise RuntimeError("Pillow não está instalado. Execute: pip install Pillow")

    p = Path(caminho_json)
    if not p.exists():
        raise FileNotFoundError(f"Arquivo não encontrado: {caminho_json}")

    with open(p, encoding="utf-8") as f:
        dados = json.load(f)

    variacoes = dados.get("variacoes", [])
    if not variacoes:
        raise ValueError(f"Nenhuma variação encontrada em {caminho_json}")

    segmento = dados.get("segmento", "generico")
    return gerar_criativos_para_variacoes(variacoes, segmento_key=segmento, template=template)
