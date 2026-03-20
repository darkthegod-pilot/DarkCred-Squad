"""
Gerador de Copies — Alina Pretrov
Wrapper da API Anthropic para geração de copies.
"""

import json
import os

import anthropic

from alina.construtor_prompt import construir_mensagens_geracao, construir_mensagens_chat
from alina.aprendizado import salvar_geracao, registrar_geracao_no_aprendizado


class ErroGeracao(Exception):
    pass


def gerar_variacoes(
    segmento_key: str,
    n: int,
    modelo: str = "claude-sonnet-4-6",
) -> list[dict]:
    """
    Gera N variações de copy para o segmento informado.
    Registra automaticamente no histórico de aprendizado.
    """
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        raise ErroGeracao(
            "ANTHROPIC_API_KEY não encontrada. Configure no arquivo .env"
        )

    client = anthropic.Anthropic(api_key=api_key)
    system, mensagens = construir_mensagens_geracao(segmento_key, n)

    resposta = client.messages.create(
        model=modelo,
        max_tokens=4096,
        system=system,
        messages=mensagens,
    )

    texto_bruto = resposta.content[0].text.strip()

    # Remove markdown code fences se presente
    if texto_bruto.startswith("```"):
        linhas = texto_bruto.splitlines()
        texto_bruto = "\n".join(
            linha for linha in linhas if not linha.startswith("```")
        ).strip()

    try:
        variacoes = json.loads(texto_bruto)
    except json.JSONDecodeError as e:
        raise ErroGeracao(
            f"Resposta da API não é JSON válido: {e}\n\nResposta recebida:\n{texto_bruto}"
        )

    if not isinstance(variacoes, list):
        raise ErroGeracao(
            f"Esperado array JSON, recebido: {type(variacoes).__name__}"
        )

    # Normaliza campo: suporta "corpo" ou "body" no JSON
    for v in variacoes:
        if "body" in v and "corpo" not in v:
            v["corpo"] = v.pop("body")

    return variacoes


def chat_com_alina(
    historico_conversa: list[dict],
    modelo: str = "claude-sonnet-4-6",
) -> str:
    """
    Envia histórico de conversa para Alina e retorna a resposta.
    historico_conversa: [{"role": "user"/"assistant", "content": "..."}]
    """
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        raise ErroGeracao(
            "ANTHROPIC_API_KEY não encontrada. Configure no arquivo .env"
        )

    client = anthropic.Anthropic(api_key=api_key)
    system, mensagens = construir_mensagens_chat(historico_conversa)

    resposta = client.messages.create(
        model=modelo,
        max_tokens=4096,
        system=system,
        messages=mensagens,
    )

    return resposta.content[0].text
