"""
Gerador de Copies — Alina Pretrov
Usa Claude (Anthropic) como primário. Fallback automático para GPT-4.1 (OpenAI)
quando Claude estiver indisponível (sem créditos, chave inválida, erro de conexão).
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

# Melhor modelo OpenAI disponível como fallback
MODELO_OPENAI_FALLBACK = "gpt-4.1"


class ErroGeracao(Exception):
    pass


# ─────────────────────────────────────────────────────────────
# CLAUDE (primário)
# ─────────────────────────────────────────────────────────────

def _chamar_api_com_retry(client: anthropic.Anthropic, **kwargs) -> anthropic.types.Message:
    """Chama a API Claude com retry exponencial em caso de rate limit ou falha de rede."""
    for tentativa in range(1, MAX_TENTATIVAS + 1):
        try:
            return client.messages.create(**kwargs)
        except anthropic.RateLimitError as e:
            if tentativa == MAX_TENTATIVAS:
                raise
            espera = ESPERA_BASE ** tentativa
            print(f"\n  ⏳ Rate limit — tentativa {tentativa}/{MAX_TENTATIVAS}, aguardando {espera}s...")
            log.warning(f"Rate limit na tentativa {tentativa}/{MAX_TENTATIVAS}, aguardando {espera}s")
            time.sleep(espera)
        except anthropic.APIConnectionError as e:
            if tentativa == MAX_TENTATIVAS:
                raise
            espera = ESPERA_BASE ** tentativa
            print(f"\n  ⏳ Falha de conexão — tentativa {tentativa}/{MAX_TENTATIVAS}, aguardando {espera}s...")
            log.warning(f"Falha de conexão na tentativa {tentativa}, aguardando {espera}s")
            time.sleep(espera)

    raise ErroGeracao("Número máximo de tentativas atingido")


def _claude_indisponivel(e: Exception) -> bool:
    """Retorna True quando o erro indica que Claude está fora (sem créditos, chave inválida)."""
    if isinstance(e, (anthropic.AuthenticationError,)):
        return True
    if isinstance(e, anthropic.BadRequestError):
        msg = str(e).lower()
        return "credit balance" in msg or "credits" in msg
    return False


# ─────────────────────────────────────────────────────────────
# OPENAI (fallback)
# ─────────────────────────────────────────────────────────────

def _chamar_openai(system: str, mensagens: list[dict], modelo: str = MODELO_OPENAI_FALLBACK) -> str:
    """
    Chama a API OpenAI (chat completions) e retorna o texto da resposta.
    Converte o formato Anthropic (system separado) para o formato OpenAI (system no messages).
    """
    try:
        import openai as _openai
    except ImportError:
        raise ErroGeracao("openai não instalado. Execute: pip install openai>=1.0.0")

    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        raise ErroGeracao("OPENAI_API_KEY não encontrada. Configure no .env")

    client = _openai.OpenAI(api_key=api_key)

    # Converte para formato OpenAI: system como primeira mensagem
    messages_openai = [{"role": "system", "content": system}] + mensagens

    resposta = client.chat.completions.create(
        model=modelo,
        messages=messages_openai,
        max_tokens=4096,
    )
    return resposta.choices[0].message.content.strip()


# ─────────────────────────────────────────────────────────────
# PARSER DE RESPOSTA (compartilhado)
# ─────────────────────────────────────────────────────────────

def _parsear_variacoes(texto_bruto: str) -> list[dict]:
    """Extrai e valida o array JSON de variações da resposta da IA."""
    texto = texto_bruto.strip()
    if texto.startswith("```"):
        linhas = texto.splitlines()
        texto = "\n".join(l for l in linhas if not l.startswith("```")).strip()

    try:
        variacoes = json.loads(texto)
    except json.JSONDecodeError as e:
        log.error(f"JSON inválido recebido da API: {e}\nResposta: {texto[:200]}")
        raise ErroGeracao(f"Resposta da API não é JSON válido: {e}\n\nResposta:\n{texto}")

    if not isinstance(variacoes, list):
        raise ErroGeracao(f"Esperado array JSON, recebido: {type(variacoes).__name__}")

    for v in variacoes:
        if "body" in v and "corpo" not in v:
            v["corpo"] = v.pop("body")

    return variacoes


# ─────────────────────────────────────────────────────────────
# API PÚBLICA
# ─────────────────────────────────────────────────────────────

def gerar_variacoes(
    segmento_key: str,
    n: int,
    modelo: str = "claude-sonnet-4-6",
) -> list[dict]:
    """
    Gera N variações de copy para o segmento informado.
    Tenta Claude primeiro; se indisponível, usa GPT-4.1 automaticamente.
    """
    log.info(f"Iniciando geração: segmento={segmento_key}, n={n}, modelo={modelo}")
    system, mensagens = construir_mensagens_geracao(segmento_key, n)

    # — Tenta Claude —
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if api_key:
        try:
            client = anthropic.Anthropic(api_key=api_key)
            resposta = _chamar_api_com_retry(
                client,
                model=modelo,
                max_tokens=4096,
                system=system,
                messages=mensagens,
            )
            texto_bruto = resposta.content[0].text
            variacoes = _parsear_variacoes(texto_bruto)
            log.info(f"Claude: {len(variacoes)} variações geradas para '{segmento_key}'")
            return variacoes
        except Exception as e:
            if _claude_indisponivel(e):
                print(f"\n  ⚡ Claude indisponível ({type(e).__name__}) — usando GPT-4.1 como fallback...")
                log.warning(f"Claude indisponível: {e} — ativando fallback OpenAI")
            else:
                raise ErroGeracao(f"Erro da API Claude: {e}") from e

    # — Fallback: GPT-4.1 —
    print(f"\n  ⚡ Usando GPT-4.1 (OpenAI) para geração de copies...")
    texto_bruto = _chamar_openai(system, mensagens)
    variacoes = _parsear_variacoes(texto_bruto)
    log.info(f"GPT-4.1 (fallback): {len(variacoes)} variações geradas para '{segmento_key}'")
    return variacoes


def chat_com_alina(
    historico_conversa: list[dict],
    modelo: str = "claude-sonnet-4-6",
) -> str:
    """
    Envia histórico de conversa para Alina e retorna a resposta.
    Tenta Claude primeiro; fallback para GPT-4.1 se indisponível.
    historico_conversa: [{"role": "user"/"assistant", "content": "..."}]
    """
    system, mensagens = construir_mensagens_chat(historico_conversa)

    # — Tenta Claude —
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if api_key:
        try:
            client = anthropic.Anthropic(api_key=api_key)
            resposta = _chamar_api_com_retry(
                client,
                model=modelo,
                max_tokens=4096,
                system=system,
                messages=mensagens,
            )
            return resposta.content[0].text
        except Exception as e:
            if _claude_indisponivel(e):
                print(f"\n  ⚡ Claude indisponível — usando GPT-4.1 como fallback...")
                log.warning(f"Claude indisponível no chat: {e} — ativando fallback OpenAI")
            else:
                raise ErroGeracao(f"Erro da API Claude: {e}") from e

    # — Fallback: GPT-4.1 —
    return _chamar_openai(system, mensagens)
