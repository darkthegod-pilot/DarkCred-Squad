"""
Construtor de Prompts — Alina Pretrov
Monta mensagens para a API Claude com contexto de aprendizado integrado.
"""

from alina.config import HOOKS, CTAS, TERMOS_SEGUROS, SEGMENTOS
from alina.persona import construir_system_prompt_geracao, construir_system_prompt_chat
from alina.aprendizado import (
    construir_contexto_aprendizado,
    top_hooks_por_segmento,
    hooks_recentes,
)


def construir_mensagens_geracao(segmento_key: str, n_variacoes: int) -> tuple[str, list[dict]]:
    """
    Constrói system prompt + mensagens para geração de copies.
    Inclui anti-repetição de hooks e injeção de hooks campeões do segmento.
    Retorna (system_prompt, messages_list).
    """
    segmento = SEGMENTOS[segmento_key]
    contexto_aprendizado = construir_contexto_aprendizado()

    system = construir_system_prompt_geracao(segmento["label"], contexto_aprendizado)

    termos_str = "\n".join(f'- "{t}"' for t in TERMOS_SEGUROS)
    ctas_str = "\n".join(f'- "{c}"' for c in CTAS)
    exemplos_str = ", ".join(segmento["exemplos"])

    # Anti-repetição: exclui hooks usados recentemente
    recentes = hooks_recentes(n=6)
    hooks_disponiveis = [h for h in HOOKS if h not in recentes]
    if len(hooks_disponiveis) < 4:
        hooks_disponiveis = HOOKS  # fallback se todos foram usados
    hooks_str = "\n".join(f'- "{h}"' for h in hooks_disponiveis)

    # Injeta hooks campeões do segmento se existirem
    tops_segmento = top_hooks_por_segmento(segmento_key, n=3)
    extra_tops = ""
    if tops_segmento:
        lista = "\n".join(f'  ⭐ "{h}"' for h in tops_segmento)
        extra_tops = f"\n\nHOOKS COM MELHOR HISTÓRICO NESSE SEGMENTO (priorize variações desses):\n{lista}"

    # Injeta contexto de aprendizado geral
    extra_aprendizado = ""
    if contexto_aprendizado:
        extra_aprendizado = f"\n\nCONTEXTO DO HISTÓRICO DE CAMPANHA (use para melhorar os copies):\n{contexto_aprendizado}\n"

    # Aviso de anti-repetição
    extra_evitar = ""
    if recentes:
        lista_recentes = "\n".join(f'  ✗ "{h}"' for h in recentes[:5])
        extra_evitar = f"\n\nHOOKS JÁ USADOS RECENTEMENTE (não repita esses exatos):\n{lista_recentes}"

    mensagem_usuario = f"""Gere {n_variacoes} variações de copy para anúncio Instagram (feed estático 1:1) para: {segmento['label']}.

Público: {segmento['contexto']}.{extra_aprendizado}{extra_tops}{extra_evitar}

Termos seguros — use ao menos um por copy:
{termos_str}

Hooks sugeridos (pode adaptar levemente para o contexto):
{hooks_str}

CTAs aprovados (use EXATAMENTE como escrito, sem alterações):
{ctas_str}

Contexto do segmento — incorpore naturalmente, sem forçar todos:
{exemplos_str}

IMPORTANTE: Copies genéricos funcionam melhor. Foque no problema universal do comerciante (falta de capital, estoque, fornecedor).
PROIBIDO: Nunca mencione o nome da empresa, marca ou razão social em nenhum copy. Os copies não devem identificar quem está anunciando.

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
