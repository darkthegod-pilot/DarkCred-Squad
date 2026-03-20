"""
Nano Banana 2 — Wrapper inference.sh
Gera fundos com Google Gemini 3.1 Flash Image Preview via CLI `infsh`.

Skill original: inference-sh/skills@nano-banana-2
Docs: https://inference.sh/docs/apps/running

Uso:
    from alina.nano_banana import verificar_infsh_disponivel, gerar_fundo_ia

    if verificar_infsh_disponivel():
        caminho = gerar_fundo_ia("padaria")
        # → "saidas/imagens/fundo_ia_padaria_20260320_1430.png" ou None
"""

import json
import shutil
import subprocess
import tempfile
import urllib.request
from pathlib import Path

DIRETORIO_SAIDA = Path("saidas/imagens")

# Prompts de fundo por contexto DarkCred
# Focados em cenários de pequeno comerciante brasileiro
_PROMPTS_FUNDO: dict[str, str] = {
    "generico": (
        "Small Brazilian merchant shop interior, warm natural lighting, "
        "colorful products on shelves, bokeh background, professional photography, "
        "no text, no logos, square format, cinematic"
    ),
    "padaria": (
        "Brazilian bakery interior with fresh bread and pastries, warm golden light, "
        "wooden counters, bokeh background, no text, square format"
    ),
    "lanchonete": (
        "Brazilian snack bar kitchen, busy lunch service, warm lighting, "
        "vibrant food colors, no text, square format, professional photography"
    ),
    "restaurante": (
        "Brazilian small restaurant interior, lunch rush, colorful food on counter, "
        "warm inviting light, no text, square format"
    ),
    "bar": (
        "Brazilian boteco bar counter at evening, warm amber lights, bottles, "
        "cozy atmosphere, no text, square format"
    ),
    "salao": (
        "Brazilian beauty salon interior, modern chairs, warm lighting, "
        "professional hair products, no text, square format"
    ),
    "barbearia": (
        "Brazilian barbershop interior, classic barber chair, warm tones, "
        "professional tools, no text, square format"
    ),
    "mercadinho": (
        "Brazilian neighborhood mini-market interior, colorful product shelves, "
        "warm overhead lighting, no text, square format"
    ),
    "feirante": (
        "Brazilian open air market stall with colorful products, natural sunlight, "
        "vibrant colors, no text, square format"
    ),
    "mecanico": (
        "Brazilian auto repair shop, tools on workbench, warm industrial lighting, "
        "no text, square format, professional photography"
    ),
}

_PROMPT_PADRAO = _PROMPTS_FUNDO["generico"]


def verificar_infsh_disponivel() -> bool:
    """Retorna True se o CLI `infsh` estiver instalado e no PATH."""
    return shutil.which("infsh") is not None


def _baixar_imagem(url: str, destino: Path) -> bool:
    """Faz download de uma imagem de URL para o destino local."""
    try:
        urllib.request.urlretrieve(url, str(destino))
        return destino.exists() and destino.stat().st_size > 0
    except Exception:
        return False


def _extrair_caminho_ou_url(saida_cli: str) -> str | None:
    """
    Tenta extrair caminho de arquivo ou URL da saída do `infsh`.
    O CLI pode retornar JSON com { "images": [...] } ou um path direto.
    """
    saida = saida_cli.strip()

    # Tenta JSON primeiro
    try:
        dados = json.loads(saida)
        imagens = dados.get("images") or dados.get("output", {}).get("images", [])
        if imagens and len(imagens) > 0:
            return imagens[0] if isinstance(imagens[0], str) else None
    except (json.JSONDecodeError, AttributeError):
        pass

    # Procura por URL ou path na saída linha por linha
    for linha in saida.splitlines():
        linha = linha.strip()
        if linha.startswith(("http://", "https://", "/", "./")):
            return linha
        # Pode ser que o CLI escreva "Image saved to: /path/to/file.png"
        if "saved to" in linha.lower() or "output:" in linha.lower():
            partes = linha.split(":", 1)
            if len(partes) == 2:
                candidato = partes[1].strip()
                if Path(candidato).exists():
                    return candidato

    return None


def gerar_fundo_ia(
    segmento_key: str = "generico",
    timeout_segundos: int = 90,
) -> str | None:
    """
    Gera imagem de fundo 1:1 via nano-banana-2 (Gemini 3.1 Flash Image).

    Args:
        segmento_key:      Chave do segmento DarkCred (para prompt contextualizado)
        timeout_segundos:  Timeout máximo para o CLI (padrão 90s)

    Returns:
        Caminho do PNG salvo localmente, ou None se falhar.
    """
    if not verificar_infsh_disponivel():
        return None

    DIRETORIO_SAIDA.mkdir(parents=True, exist_ok=True)

    prompt = _PROMPTS_FUNDO.get(segmento_key, _PROMPT_PADRAO)

    payload = json.dumps({
        "prompt": prompt,
        "aspect_ratio": "1:1",
        "resolution": "1K",
        "num_images": 1,
    })

    cmd = [
        "infsh", "app", "run",
        "google/gemini-3-1-flash-image-preview",
        "--input", payload,
    ]

    try:
        resultado = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout_segundos,
        )

        if resultado.returncode != 0:
            # Log silencioso — o chamador decide se exibe erro
            return None

        saida = resultado.stdout + resultado.stderr
        referencia = _extrair_caminho_ou_url(saida)

        if not referencia:
            return None

        from datetime import datetime
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        destino = DIRETORIO_SAIDA / f"fundo_ia_{segmento_key}_{ts}.png"

        # URL remota → faz download
        if referencia.startswith(("http://", "https://")):
            sucesso = _baixar_imagem(referencia, destino)
            return str(destino) if sucesso else None

        # Arquivo local → copia para o diretório de saída
        origem = Path(referencia)
        if origem.exists():
            import shutil as _shutil
            _shutil.copy2(str(origem), str(destino))
            return str(destino)

    except subprocess.TimeoutExpired:
        pass
    except Exception:
        pass

    return None
