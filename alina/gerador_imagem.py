"""
Gerador de Imagens — Alina Pretrov
Cria criativos 1080x1080px para Instagram usando Pillow.

Três templates DarkCred:
  1 — Escuro Moderno   (gradiente roxo/azul escuro, padrão)
  2 — Claro Impacto    (branco + bloco laranja no topo)
  3 — Comerciante      (gradiente verde, tom terra brasileiro)
"""

import random
import textwrap
from datetime import datetime
from pathlib import Path

# Pillow é importado com fallback claro
try:
    from PIL import Image, ImageDraw, ImageFont, ImageFilter
    PILLOW_DISPONIVEL = True
except ImportError:
    PILLOW_DISPONIVEL = False

# ─────────────────────────────────────────────────────────────
# PALETA DARKCRED
# ─────────────────────────────────────────────────────────────

CORES = {
    # Escuros
    "roxo_escuro":  (26, 5, 51),       # #1a0533
    "azul_escuro":  (13, 27, 75),      # #0d1b4b
    "verde_escuro": (13, 51, 33),      # #0d3321
    "verde_medio":  (26, 92, 58),      # #1a5c3a
    # Acentos
    "laranja":      (255, 107, 53),    # #FF6B35
    "dourado":      (255, 215, 0),     # #FFD700
    "branco":       (255, 255, 255),
    "branco_suave": (240, 240, 240),
    "cinza_claro":  (200, 200, 200),
    "preto":        (0, 0, 0),
    "preto_suave":  (26, 26, 26),      # #1a1a1a
}

TAMANHO_CANVAS = (1080, 1080)
DIRETORIO_SAIDA = Path("saidas/imagens")

# ─────────────────────────────────────────────────────────────
# FONTES
# ─────────────────────────────────────────────────────────────

_CANDIDATOS_FONTES = [
    "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
    "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
]

def _carregar_fonte(tamanho: int, negrito: bool = False) -> "ImageFont.FreeTypeFont":
    """Carrega a melhor fonte disponível no sistema."""
    if not PILLOW_DISPONIVEL:
        raise RuntimeError("Pillow não está instalado.")
    preferencia = [f for f in _CANDIDATOS_FONTES if ("Bold" in f) == negrito]
    if not preferencia:
        preferencia = _CANDIDATOS_FONTES
    for caminho in preferencia:
        if Path(caminho).exists():
            try:
                return ImageFont.truetype(caminho, tamanho)
            except Exception:
                continue
    return ImageFont.load_default()


# ─────────────────────────────────────────────────────────────
# HELPERS DE DESENHO
# ─────────────────────────────────────────────────────────────

def _gradiente_vertical(
    draw: "ImageDraw.ImageDraw",
    cor_topo: tuple,
    cor_base: tuple,
    largura: int,
    altura: int,
) -> None:
    """Preenche o canvas com gradiente vertical."""
    for y in range(altura):
        t = y / altura
        r = int(cor_topo[0] + (cor_base[0] - cor_topo[0]) * t)
        g = int(cor_topo[1] + (cor_base[1] - cor_topo[1]) * t)
        b = int(cor_topo[2] + (cor_base[2] - cor_topo[2]) * t)
        draw.line([(0, y), (largura, y)], fill=(r, g, b))


def _gradiente_diagonal(
    draw: "ImageDraw.ImageDraw",
    cor_topo: tuple,
    cor_base: tuple,
    largura: int,
    altura: int,
) -> None:
    """Gradiente diagonal (canto superior esquerdo → inferior direito)."""
    for y in range(altura):
        for x_band in range(0, largura, 4):
            t = (x_band / largura + y / altura) / 2
            r = int(cor_topo[0] + (cor_base[0] - cor_topo[0]) * t)
            g = int(cor_topo[1] + (cor_base[1] - cor_topo[1]) * t)
            b = int(cor_topo[2] + (cor_base[2] - cor_topo[2]) * t)
            draw.line([(x_band, y), (min(x_band + 4, largura), y)], fill=(r, g, b))


def _quebrar_texto(texto: str, fonte: "ImageFont.FreeTypeFont", max_px: int) -> list[str]:
    """Quebra texto para caber em max_px de largura."""
    palavras = texto.split()
    linhas = []
    linha_atual = ""

    for palavra in palavras:
        candidato = (linha_atual + " " + palavra).strip()
        bbox = fonte.getbbox(candidato)
        largura = bbox[2] - bbox[0]
        if largura <= max_px:
            linha_atual = candidato
        else:
            if linha_atual:
                linhas.append(linha_atual)
            linha_atual = palavra
    if linha_atual:
        linhas.append(linha_atual)

    return linhas


def _renderizar_texto_multilinha(
    draw: "ImageDraw.ImageDraw",
    linhas: list[str],
    fonte: "ImageFont.FreeTypeFont",
    x: int,
    y_inicio: int,
    cor: tuple,
    centralizar: bool = True,
    largura_canvas: int = 1080,
    espacamento: int = 8,
) -> int:
    """Renderiza linhas de texto. Retorna Y final."""
    y = y_inicio
    for linha in linhas:
        bbox = fonte.getbbox(linha)
        larg_texto = bbox[2] - bbox[0]
        alt_texto = bbox[3] - bbox[1]
        x_pos = (largura_canvas - larg_texto) // 2 if centralizar else x
        draw.text((x_pos, y), linha, font=fonte, fill=cor)
        y += alt_texto + espacamento
    return y


def _desenhar_botao_cta(
    img: "Image.Image",
    draw: "ImageDraw.ImageDraw",
    texto: str,
    y_centro: int,
    cor_fundo: tuple,
    cor_texto: tuple,
    largura_canvas: int = 1080,
) -> None:
    """Desenha botão CTA arredondado centralizado."""
    fonte = _carregar_fonte(34, negrito=True)
    bbox = fonte.getbbox(texto)
    larg_texto = bbox[2] - bbox[0]
    alt_texto = bbox[3] - bbox[1]

    padding_h = 60
    padding_v = 24
    larg_botao = larg_texto + padding_h * 2
    alt_botao = alt_texto + padding_v * 2

    x0 = (largura_canvas - larg_botao) // 2
    y0 = y_centro - alt_botao // 2
    x1 = x0 + larg_botao
    y1 = y0 + alt_botao

    # Sombra sutil
    sombra_offset = 4
    draw.rounded_rectangle(
        [x0 + sombra_offset, y0 + sombra_offset, x1 + sombra_offset, y1 + sombra_offset],
        radius=40,
        fill=(0, 0, 0, 80) if img.mode == "RGBA" else (0, 0, 0),
    )

    draw.rounded_rectangle([x0, y0, x1, y1], radius=40, fill=cor_fundo)

    x_texto = x0 + padding_h
    y_texto = y0 + padding_v
    draw.text((x_texto, y_texto), texto, font=fonte, fill=cor_texto)


def _watermark(draw: "ImageDraw.ImageDraw", largura: int, altura: int) -> None:
    """Watermark DarkCred discreto no rodapé."""
    fonte = _carregar_fonte(22, negrito=False)
    texto = "DarkCred"
    bbox = fonte.getbbox(texto)
    larg = bbox[2] - bbox[0]
    x = largura - larg - 28
    y = altura - (bbox[3] - bbox[1]) - 20
    draw.text((x, y), texto, font=fonte, fill=(255, 255, 255, 60) if draw._image.mode == "RGBA" else (120, 120, 120))


# ─────────────────────────────────────────────────────────────
# TEMPLATES
# ─────────────────────────────────────────────────────────────

def _template_escuro(variacao: dict) -> "Image.Image":
    """
    Template 1 — Escuro Moderno
    Fundo: gradiente roxo-escuro → azul-escuro
    Acento: linha lateral laranja
    Texto: branco/cinza claro
    """
    W, H = TAMANHO_CANVAS
    img = Image.new("RGB", (W, H))
    draw = ImageDraw.Draw(img)

    # Gradiente diagonal
    _gradiente_diagonal(draw, CORES["roxo_escuro"], CORES["azul_escuro"], W, H)

    # Linha lateral esquerda (acento laranja)
    draw.rectangle([0, 0, 6, H], fill=CORES["laranja"])

    # Bloco superior sutil
    draw.rectangle([0, 0, W, 8], fill=(*CORES["laranja"], 180))

    hook = variacao.get("hook", "")
    corpo = variacao.get("corpo", variacao.get("body", ""))
    cta = variacao.get("cta", "Chama no direct 📩")

    # Fonte hook grande
    fonte_hook = _carregar_fonte(66, negrito=True)
    fonte_corpo = _carregar_fonte(36, negrito=False)

    margem = 70
    max_larg = W - margem * 2

    linhas_hook = _quebrar_texto(hook, fonte_hook, max_larg)
    linhas_corpo = _quebrar_texto(corpo, fonte_corpo, max_larg)

    # Calcula altura total do bloco de texto
    alt_linha_hook = 66 + 12
    alt_linha_corpo = 36 + 10
    alt_total = len(linhas_hook) * alt_linha_hook + 40 + len(linhas_corpo) * alt_linha_corpo + 80 + 70
    y_inicio = (H - alt_total) // 2

    # Renderiza hook
    y_atual = _renderizar_texto_multilinha(
        draw, linhas_hook, fonte_hook,
        x=margem, y_inicio=y_inicio,
        cor=CORES["branco"],
        centralizar=True, largura_canvas=W, espacamento=12,
    )

    # Separador
    y_atual += 30
    sep_larg = 80
    draw.rectangle(
        [(W - sep_larg) // 2, y_atual, (W + sep_larg) // 2, y_atual + 3],
        fill=CORES["laranja"],
    )
    y_atual += 22

    # Renderiza corpo
    y_atual = _renderizar_texto_multilinha(
        draw, linhas_corpo, fonte_corpo,
        x=margem, y_inicio=y_atual,
        cor=CORES["cinza_claro"],
        centralizar=True, largura_canvas=W, espacamento=10,
    )

    # Botão CTA
    y_atual += 48
    _desenhar_botao_cta(img, draw, cta, y_atual + 35, CORES["laranja"], CORES["branco"])

    _watermark(draw, W, H)
    return img


def _template_claro(variacao: dict) -> "Image.Image":
    """
    Template 2 — Claro Impacto
    Fundo: branco
    Bloco topo: laranja com hook branco
    Corpo: texto escuro
    """
    W, H = TAMANHO_CANVAS
    img = Image.new("RGB", (W, H), CORES["branco"])
    draw = ImageDraw.Draw(img)

    hook = variacao.get("hook", "")
    corpo = variacao.get("corpo", variacao.get("body", ""))
    cta = variacao.get("cta", "Chama no direct 📩")

    ALTURA_BLOCO = 400
    # Bloco laranja (topo)
    draw.rectangle([0, 0, W, ALTURA_BLOCO], fill=CORES["laranja"])

    # Linha decorativa branca no rodapé do bloco laranja
    draw.rectangle([0, ALTURA_BLOCO - 6, W, ALTURA_BLOCO], fill=CORES["branco"])

    fonte_hook = _carregar_fonte(60, negrito=True)
    fonte_corpo = _carregar_fonte(36, negrito=False)

    margem = 64
    max_larg = W - margem * 2

    linhas_hook = _quebrar_texto(hook, fonte_hook, max_larg)
    linhas_corpo = _quebrar_texto(corpo, fonte_corpo, max_larg)

    # Centraliza hook no bloco laranja
    alt_hook_total = len(linhas_hook) * (60 + 14)
    y_hook = (ALTURA_BLOCO - alt_hook_total) // 2

    _renderizar_texto_multilinha(
        draw, linhas_hook, fonte_hook,
        x=margem, y_inicio=y_hook,
        cor=CORES["branco"],
        centralizar=True, largura_canvas=W, espacamento=14,
    )

    # Corpo na área branca
    y_corpo = ALTURA_BLOCO + 52
    y_atual = _renderizar_texto_multilinha(
        draw, linhas_corpo, fonte_corpo,
        x=margem, y_inicio=y_corpo,
        cor=CORES["preto_suave"],
        centralizar=True, largura_canvas=W, espacamento=12,
    )

    # Botão CTA escuro
    y_atual += 48
    _desenhar_botao_cta(img, draw, cta, y_atual + 35, CORES["preto_suave"], CORES["branco"])

    # Watermark escuro
    fonte_wm = _carregar_fonte(22, negrito=False)
    wm_texto = "DarkCred"
    bbox = fonte_wm.getbbox(wm_texto)
    draw.text((W - (bbox[2] - bbox[0]) - 28, H - (bbox[3] - bbox[1]) - 20), wm_texto, font=fonte_wm, fill=(180, 180, 180))

    return img


def _template_verde(variacao: dict) -> "Image.Image":
    """
    Template 3 — Comerciante Direto
    Fundo: gradiente verde-escuro brasileiro
    Hook: amarelo-dourado, corpo branco
    """
    W, H = TAMANHO_CANVAS
    img = Image.new("RGB", (W, H))
    draw = ImageDraw.Draw(img)

    _gradiente_vertical(draw, CORES["verde_escuro"], CORES["verde_medio"], W, H)

    # Elementos decorativos (círculos sutis no canto)
    draw.ellipse([W - 220, -80, W + 80, 220], outline=(*CORES["dourado"][:3], 30), width=2)
    draw.ellipse([W - 160, -20, W + 20, 160], outline=(*CORES["dourado"][:3], 20), width=1)

    hook = variacao.get("hook", "")
    corpo = variacao.get("corpo", variacao.get("body", ""))
    cta = variacao.get("cta", "Chama no direct 📩")

    fonte_hook = _carregar_fonte(64, negrito=True)
    fonte_corpo = _carregar_fonte(36, negrito=False)

    margem = 70
    max_larg = W - margem * 2

    linhas_hook = _quebrar_texto(hook, fonte_hook, max_larg)
    linhas_corpo = _quebrar_texto(corpo, fonte_corpo, max_larg)

    alt_linha_hook = 64 + 14
    alt_linha_corpo = 36 + 10
    alt_total = len(linhas_hook) * alt_linha_hook + 50 + len(linhas_corpo) * alt_linha_corpo + 80 + 70
    y_inicio = (H - alt_total) // 2

    y_atual = _renderizar_texto_multilinha(
        draw, linhas_hook, fonte_hook,
        x=margem, y_inicio=y_inicio,
        cor=CORES["dourado"],
        centralizar=True, largura_canvas=W, espacamento=14,
    )

    y_atual += 38
    draw.rectangle([margem, y_atual, W - margem, y_atual + 2], fill=(*CORES["dourado"][:3], 80))
    y_atual += 22

    y_atual = _renderizar_texto_multilinha(
        draw, linhas_corpo, fonte_corpo,
        x=margem, y_inicio=y_atual,
        cor=CORES["branco_suave"],
        centralizar=True, largura_canvas=W, espacamento=10,
    )

    y_atual += 50
    _desenhar_botao_cta(img, draw, cta, y_atual + 35, CORES["dourado"], CORES["preto_suave"])

    _watermark(draw, W, H)
    return img


# ─────────────────────────────────────────────────────────────
# PONTO DE ENTRADA PRINCIPAL
# ─────────────────────────────────────────────────────────────

_TEMPLATES = {1: _template_escuro, 2: _template_claro, 3: _template_verde}


def gerar_criativo(
    variacao: dict,
    segmento_key: str = "generico",
    template: int | None = None,
    fundo_ia: str | None = None,
) -> str:
    """
    Gera imagem PNG 1080x1080 para o criativo.

    Args:
        variacao:     Dict com hook, corpo, cta, full_copy
        segmento_key: Chave do segmento (para nome do arquivo)
        template:     1, 2 ou 3. None = aleatório
        fundo_ia:     Caminho para imagem de fundo gerada por IA (nano-banana)

    Returns:
        Caminho absoluto do PNG salvo.

    Raises:
        RuntimeError: Se Pillow não estiver instalado.
    """
    if not PILLOW_DISPONIVEL:
        raise RuntimeError(
            "Pillow não está instalado. Execute: pip install Pillow"
        )

    DIRETORIO_SAIDA.mkdir(parents=True, exist_ok=True)

    num_template = template if template in _TEMPLATES else random.randint(1, 3)
    fn_template = _TEMPLATES[num_template]

    img = fn_template(variacao)

    # Aplica fundo de IA se fornecido (sobrepõe o fundo Pillow)
    if fundo_ia and Path(fundo_ia).exists():
        try:
            fundo = Image.open(fundo_ia).convert("RGB").resize(TAMANHO_CANVAS)
            # Mistura: 60% fundo IA + texto do template (recria com alpha)
            img_texto = fn_template(variacao).convert("RGBA")
            fundo_rgba = fundo.convert("RGBA")
            # Overlay semi-transparente sobre o fundo IA para legibilidade
            overlay = Image.new("RGBA", TAMANHO_CANVAS, (0, 0, 0, 140))
            fundo_escurecido = Image.alpha_composite(fundo_rgba, overlay)
            # Desenha apenas os textos sobre o fundo IA escurecido
            img = Image.alpha_composite(fundo_escurecido, img_texto).convert("RGB")
        except Exception:
            pass  # Se falhar, usa o template Pillow original

    # Nome do arquivo
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    nome = f"alina_{segmento_key}_{ts}_t{num_template}.png"
    caminho = DIRETORIO_SAIDA / nome
    img.save(str(caminho), format="PNG", optimize=True)

    return str(caminho)


def gerar_criativos_para_variacoes(
    variacoes: list[dict],
    segmento_key: str = "generico",
    template: int | None = None,
    usar_ia: bool = False,
) -> list[str]:
    """
    Gera imagens para uma lista de variações aprovadas.

    Args:
        variacoes:    Lista de dicts aprovados pelo validador
        segmento_key: Chave do segmento
        template:     Forçar template específico (None = aleatório por imagem)
        usar_ia:      Tentar gerar fundo com nano-banana-2

    Returns:
        Lista de caminhos dos PNGs gerados.
    """
    if not PILLOW_DISPONIVEL:
        raise RuntimeError("Pillow não está instalado. Execute: pip install Pillow")

    caminhos = []
    fundo_ia = None

    if usar_ia:
        try:
            from alina.nano_banana import gerar_fundo_ia, verificar_infsh_disponivel
            if verificar_infsh_disponivel():
                fundo_ia = gerar_fundo_ia(segmento_key)
        except Exception:
            pass

    for i, var in enumerate(variacoes):
        # Alterna template se não forçado
        num = template if template else ((i % 3) + 1)
        caminho = gerar_criativo(var, segmento_key, template=num, fundo_ia=fundo_ia)
        caminhos.append(caminho)

    return caminhos
