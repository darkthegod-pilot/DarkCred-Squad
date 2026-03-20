"""
Validador de Compliance — Alina Pretrov
Garante que nenhum copy viola as regras DarkCred antes de ser entregue.
"""

import re

from alina.config import TERMOS_PROIBIDOS_EXATOS, PADROES_PROIBIDOS, LIMITE_CARACTERES_COPY


class ViolacaoCompliance:
    def __init__(self, indice: int, motivos: list[str]):
        self.indice = indice
        self.motivos = motivos

    def __str__(self) -> str:
        motivos_str = " | ".join(self.motivos)
        return f"Variação {self.indice + 1}: {motivos_str}"


def validar_variacao(variacao: dict) -> list[str]:
    """Valida uma variação. Retorna lista de motivos de violação (vazia = aprovada)."""
    texto_completo = variacao.get("full_copy", "").lower()
    violacoes = []

    for termo in TERMOS_PROIBIDOS_EXATOS:
        if termo.lower() in texto_completo:
            violacoes.append(f"Termo proibido: '{termo}'")

    for padrao in PADROES_PROIBIDOS:
        if re.search(padrao, texto_completo, re.IGNORECASE):
            violacoes.append(f"Padrão proibido detectado: {padrao}")

    comprimento = len(variacao.get("full_copy", ""))
    if comprimento > LIMITE_CARACTERES_COPY:
        violacoes.append(
            f"Copy muito longa: {comprimento} caracteres (máx {LIMITE_CARACTERES_COPY})"
        )

    return violacoes


def validar_todas(variacoes: list[dict]) -> tuple[list[dict], list[ViolacaoCompliance]]:
    """
    Valida todas as variações.
    Retorna (aprovadas, lista_de_violações).
    """
    aprovadas = []
    violacoes = []

    for i, var in enumerate(variacoes):
        motivos = validar_variacao(var)
        if motivos:
            violacoes.append(ViolacaoCompliance(i, motivos))
        else:
            aprovadas.append(var)

    return aprovadas, violacoes
