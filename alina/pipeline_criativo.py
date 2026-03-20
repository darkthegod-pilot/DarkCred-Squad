"""
Pipeline de Criativo — Alina Pretrov
Workflow completo de agência: Briefing → Arte → Geração → Revisão → Entrega

5 Etapas:
  1. Compliance de copy (validador.py)
  2. Direção de arte — sorteia layout dinâmico
  3. Geração do fundo + overlay (gerador_imagem_ia.py)
  4. Revisão visual por IA (revisor_criativo.py) — até 3 tentativas
  5. Upload público + entrega do link

Uso:
    from alina.pipeline_criativo import executar_pipeline
    resultado = executar_pipeline(
        variacao={"hook": "...", "corpo": "...", "cta": "..."},
        segmento="generico",
    )
    print(resultado.url)
"""

import os
import random
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from .validador import validar_variacao
from .gerador_imagem_ia import gerar_criativo_ia
from .revisor_criativo import revisar_criativo, formatar_review, ReviewResult


MAX_TENTATIVAS = 3

# Mapeamento segmento → layout preferido (pode ser sobrescrito)
_LAYOUT_POR_SEGMENTO: dict = {
    "padaria":    "SPLIT_DIAGONAL",
    "lanchonete": "SPLIT_DIAGONAL",
    "restaurante":"SPLIT_DIAGONAL",
    "pizzaria":   "SPLIT_DIAGONAL",
    "acai":       "SPLIT_DIAGONAL",
    "food_truck": "SPLIT_DIAGONAL",
    "salao":      "HEADLINE_CENTRALIZADA",
    "barbearia":  "HEADLINE_CENTRALIZADA",
    "manicure":   "HEADLINE_CENTRALIZADA",
    "estetica":   "HEADLINE_CENTRALIZADA",
    "academia":   "HEADLINE_CENTRALIZADA",
    "vestuario":  "LATERAL_ESQUERDA",
    "mercadinho": "LATERAL_ESQUERDA",
    "farmacia":   "LATERAL_ESQUERDA",
    "mecanico":   "TIPOGRAFIA_FORTE",
    "generico":   "TIPOGRAFIA_FORTE",
}

_TODOS_LAYOUTS = ["TIPOGRAFIA_FORTE", "SPLIT_DIAGONAL",
                  "HEADLINE_CENTRALIZADA", "LATERAL_ESQUERDA"]


@dataclass
class PipelineResult:
    img_path: str
    url: str
    review: ReviewResult
    tentativas: int
    aprovado: bool


class ComplianceError(Exception):
    def __init__(self, violacoes: list):
        self.violacoes = violacoes
        msgs = "; ".join(v.razoes[0] if v.razoes else "violação" for v in violacoes)
        super().__init__(f"Copy com violações de compliance: {msgs}")


def _sortear_layout(segmento: str, tentativa: int) -> str:
    """
    Retorna o layout ideal para o segmento.
    Em retentativas, força um layout diferente para gerar variedade.
    """
    preferido = _LAYOUT_POR_SEGMENTO.get(segmento, "TIPOGRAFIA_FORTE")
    if tentativa == 1:
        return preferido
    # Em retentativas, escolhe diferente do preferido
    alternativas = [l for l in _TODOS_LAYOUTS if l != preferido]
    return alternativas[(tentativa - 2) % len(alternativas)]


def _upload_catbox(img_path: str) -> Optional[str]:
    """Faz upload da imagem para catbox.moe e retorna a URL pública."""
    try:
        result = subprocess.run(
            [
                "curl", "-s", "--max-time", "30",
                "-F", "reqtype=fileupload",
                "-F", f"fileToUpload=@{img_path}",
                "https://catbox.moe/user/api.php",
            ],
            capture_output=True,
            text=True,
            timeout=40,
        )
        url = result.stdout.strip()
        if url.startswith("https://"):
            return url
        return None
    except Exception:
        return None


def _separador(largura: int = 40) -> str:
    return "━" * largura


def executar_pipeline(
    variacao: dict,
    segmento: str = "generico",
    verbose: bool = True,
) -> PipelineResult:
    """
    Executa o pipeline completo de criativo com revisão automática.

    Parâmetros:
        variacao — dict com keys: hook, corpo, cta
        segmento — chave do segmento (ex: "padaria", "generico")
        verbose  — exibe progresso no terminal

    Retorna PipelineResult com img_path, url, review e tentativas.
    Levanta ComplianceError se o copy tiver violações.
    """

    sep = _separador()

    if verbose:
        print(f"\n{sep}")
        print("PIPELINE DE CRIATIVO — ALINA PRETROV")
        print(sep)

    # ── Etapa 1: Compliance de copy ──────────────────────────
    if verbose:
        print("[1/5] Validando compliance do copy...")

    violacoes = validar_variacao(variacao)
    if violacoes:
        if verbose:
            print(f"      BLOQUEADO — {len(violacoes)} violação(ões) encontrada(s)")
            for v in violacoes:
                for r in v.razoes:
                    print(f"      ❌ {r}")
        raise ComplianceError(violacoes)

    if verbose:
        print("      ✅ Copy aprovado — sem violações de compliance")

    # ── Loop de até 3 tentativas ─────────────────────────────
    melhorias_acumuladas: list = []
    ultimo_result = None

    for tentativa in range(1, MAX_TENTATIVAS + 1):

        # ── Etapa 2: Direção de arte ─────────────────────────
        layout = _sortear_layout(segmento, tentativa)

        if verbose:
            retentativa = f" (retentativa {tentativa})" if tentativa > 1 else ""
            print(f"\n[2/5] Layout selecionado: {layout}{retentativa}")

        # ── Etapa 3: Geração ─────────────────────────────────
        if verbose:
            print("[3/5] Gerando com GPT-image-1 quality=high...")
            if melhorias_acumuladas:
                print(f"      Incorporando {len(melhorias_acumuladas)} melhoria(s) da revisão anterior")

        img_path = gerar_criativo_ia(
            variacao,
            segmento_key=segmento,
            layout=layout,
            melhorias=melhorias_acumuladas,
        )

        if verbose:
            print(f"      Salvo em: {img_path}")

        # ── Etapa 4: Revisão visual ───────────────────────────
        if verbose:
            print("[4/5] Revisando com Claude Vision...")

        review = revisar_criativo(img_path, variacao, segmento, tentativa=tentativa)
        ultimo_result = review

        if verbose:
            print(formatar_review(review))

        if review.aprovado:
            break
        else:
            melhorias_acumuladas = review.melhorias
            if tentativa < MAX_TENTATIVAS:
                if verbose:
                    print(f"      Criativo reprovado na tentativa {tentativa}. Gerando nova versão...")
            else:
                if verbose:
                    print(f"      {MAX_TENTATIVAS} tentativas esgotadas. Subindo melhor versão obtida.")

    # ── Etapa 5: Upload e entrega ────────────────────────────
    if verbose:
        print("[5/5] Fazendo upload...")

    url = _upload_catbox(img_path)

    if verbose:
        print(f"\n{sep}")
        status = "CRIATIVO APROVADO" if (ultimo_result and ultimo_result.aprovado) else "CRIATIVO ENVIADO (nota máxima obtida)"
        print(f"{status}")
        if url:
            print(f"Link: {url}")
        else:
            print(f"Upload falhou. Arquivo local: {img_path}")
        print(sep)

    return PipelineResult(
        img_path=img_path,
        url=url or "",
        review=ultimo_result,
        tentativas=tentativa,
        aprovado=ultimo_result.aprovado if ultimo_result else False,
    )
