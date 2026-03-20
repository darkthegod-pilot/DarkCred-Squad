"""
Gerador de Copies — Alina Pretrov
Wrapper da API Anthropic com retry automático e logging.
"""

import json
import os
import time

import anthropic

from alina.construtor_prompt import construir_mensagens_geracao, construir_mensagens_chat
from alina.aprendizado import salvar_geracao, registrar_geracao_no_aprendizado
from alina.logger import log

MAX_TENTATIVAS = 3
ESPERA_BASE = 2  # segundos (dobra a cada tentativa: 2s, 4s, 8s)


class ErroGeracao(Exception):
    pass


def _chamar_api_com_retry(client: anthropic.Anthropic, **kwargs) -> anthropic.types.Message:
    """Chama a API Claude com retry exponencial em caso de rate limit ou falha de rede."""
    for tentativa in range(1, MAX_TENTATIVAS + 1):
        try:
            return client.messages.create(**kwargs)
        except anthropic.RateLimitError as e:
            if tentativa == MAX_TENTATIVAS:
                raise ErroGeracao(f"Rate limit atingido após {MAX_TENTATIVAS} tentativas: {e}")
            espera = ESPERA_BASE ** tentativa
            print(f"\n  ⏳ Rate limit — tentativa {tentativa}/{MAX_TENTATIVAS}, aguardando {espera}s...")
            log.warning(f"Rate limit na tentativa {tentativa}/{MAX_TENTATIVAS}, aguardando {espera}s")
            time.sleep(espera)
        except anthropic.APIConnectionError as e:
            if tentativa == MAX_TENTATIVAS:
                raise ErroGeracao(f"Falha de conexão após {MAX_TENTATIVAS} tentativas: {e}")
            espera = ESPERA_BASE ** tentativa
            print(f"\n  ⏳ Falha de conexão — tentativa {tentativa}/{MAX_TENTATIVAS}, aguardando {espera}s...")
            log.warning(f"Falha de conexão na tentativa {tentativa}, aguardando {espera}s")
            time.sleep(espera)
        except anthropic.APIStatusError as e:
            raise ErroGeracao(f"Erro da API Claude (status {e.status_code}): {e.message}")

    raise ErroGeracao("Número máximo de tentativas atingido")


def gerar_variacoes(
    segmento_key: str,
    n: int,
    modelo: str = "claude-sonnet-4-6",
) -> list[dict]:
    """
    Gera N variações de copy para o segmento informado.
    Inclui retry automático com backoff exponencial.
    Registra automaticamente no histórico de aprendizado.
    """
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        raise ErroGeracao(
            "ANTHROPIC_API_KEY não encontrada. Configure no arquivo .env"
        )

    log.info(f"Iniciando geração: segmento={segmento_key}, n={n}, modelo={modelo}")

    client = anthropic.Anthropic(api_key=api_key)
    system, mensagens = construir_mensagens_geracao(segmento_key, n)

    resposta = _chamar_api_com_retry(
        client,
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
        log.error(f"JSON inválido recebido da API: {e}\nResposta: {texto_bruto[:200]}")
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

    log.info(f"Geração concluída: {len(variacoes)} variações recebidas para '{segmento_key}'")
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

    resposta = _chamar_api_com_retry(
        client,
        model=modelo,
        max_tokens=4096,
        system=system,
        messages=mensagens,
    )

    return resposta.content[0].text
