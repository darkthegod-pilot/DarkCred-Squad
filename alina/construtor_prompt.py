"""
Construtor de Prompts — Alina Pretrov
Monta mensagens para a API Claude com contexto de aprendizado integrado.
"""

from alina.config import HOOKS, CTAS, TERMOS_SEGUROS, SEGMENTOS
from alina.persona import construir_system_prompt_geracao, construir_system_prompt_chat
from alina.aprendizado import construir_contexto_aprendizado


def construir_mensagens_geracao(segmento_key: str, n_variacoes: int) -> tuple[str, list[dict]]:
    """
    Constrói system prompt + mensagens para geração de copies.
    Retorna (system_prompt, messages_list).
    """
    segmento = SEGMENTOS[segmento_key]
    contexto_aprendizado = construir_contexto_aprendizado()

    system = construir_system_prompt_geracao(segmento["label"], contexto_aprendizado)

    termos_str = "\n".join(f'- "{t}"' for t in TERMOS_SEGUROS)
    hooks_str = "\n".join(f'- "{h}"' for h in HOOKS)
    ctas_str = "\n".join(f'- "{c}"' for c in CTAS)
    exemplos_str = ", ".join(segmento["exemplos"])

    # Injeta aprendizado na mensagem do usuário se disponível
    extra_aprendizado = ""
    if contexto_aprendizado:
        extra_aprendizado = f"\n\nCONTEXTO DO HISTÓRICO DE CAMPANHA (use para melhorar os copies):\n{contexto_aprendizado}\n"

    mensagem_usuario = f"""Gere {n_variacoes} variações de copy para anúncio Instagram (feed estático 1:1) para: {segmento['label']}.

Público: {segmento['contexto']}.{extra_aprendizado}

Termos seguros — use ao menos um por copy:
{termos_str}

Hooks sugeridos (pode adaptar levemente para o contexto):
{hooks_str}

CTAs aprovados (use EXATAMENTE como escrito, sem alterações):
{ctas_str}

Contexto do segmento — incorpore naturalmente, sem forçar todos:
{exemplos_str}

IMPORTANTE: Copies genéricos funcionam melhor. Foque no problema universal do comerciante (falta de capital, estoque, fornecedor).

Retorne EXATAMENTE {n_variacoes} variações como um array JSON válido. Nenhum texto antes ou depois.
Cada elemento deve ter:
{{
  "hook": "linha de abertura",
  "corpo": "1-2 linhas de benefício",
  "cta": "chamada para ação",
  "full_copy": "hook\\ncorpo\\ncta"
}}"""

    return system, [{"role": "user", "content": mensagem_usuario}]


def construir_mensagens_chat(historico_conversa: list[dict]) -> tuple[str, list[dict]]:
    """
    Constrói system prompt + histórico para modo chat interativo.
    historico_conversa: lista de {"role": "user"/"assistant", "content": "..."}
    """
    contexto_aprendizado = construir_contexto_aprendizado()
    system = construir_system_prompt_chat()

    if contexto_aprendizado:
        system += f"\n\nSEU HISTÓRICO DE DADOS ACUMULADOS:\n{contexto_aprendizado}"

    return system, historico_conversa
