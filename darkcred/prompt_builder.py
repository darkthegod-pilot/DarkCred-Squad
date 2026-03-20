from darkcred.config import HOOKS, CTAS, SAFE_TERMS, SEGMENTS


def build_messages(segment_key: str, n_variations: int) -> list[dict]:
    segment = SEGMENTS[segment_key]

    safe_terms_str = "\n".join(f'- "{t}"' for t in SAFE_TERMS)
    forbidden_str = (
        "- NUNCA mencione valores específicos em reais (R$ 200, R$ 350, qualquer número)\n"
        "- NUNCA use: 'Sem consulta SPC/Serasa', 'Aprovação garantida', "
        "'Liberação imediata', 'Crédito fácil'\n"
        "- NÃO descreva imagens de dinheiro, notas ou itens de luxo\n"
        "- NÃO mencione taxas de juros ou percentuais"
    )
    hooks_str = "\n".join(f'- "{h}"' for h in HOOKS)
    ctas_str = "\n".join(f'- "{c}"' for c in CTAS)
    examples_str = ", ".join(segment["examples"])

    system_prompt = f"""Você é um copywriter brasileiro para a DarkCred, empresa de capital de giro para pequenos comerciantes.
Seu trabalho é escrever copy para anúncios estáticos no feed do Instagram (formato 1:1) direcionados a: {segment['context']}.

REGRAS OBRIGATÓRIAS — NÃO quebre nenhuma delas:
{forbidden_str}

Termos seguros — use pelo menos um deles naturalmente em cada copy:
{safe_terms_str}

Tom: direto, amigável, de igual para igual. Como um amigo de confiança que ajuda no negócio.
Linguagem: português brasileiro informal (você, tutear). Máximo 500 caracteres por copy.

Formato de saída: retorne APENAS um array JSON válido. Nenhum texto antes ou depois.
Cada elemento do array deve ter exatamente este schema:
{{
  "hook": "linha de abertura que chama atenção",
  "body": "1-2 linhas de corpo explicando o benefício",
  "cta": "chamada para ação exata conforme aprovado",
  "full_copy": "hook\\nbody\\ncta (tudo junto com quebras de linha)"
}}"""

    user_message = f"""Gere {n_variations} variações de copy para anúncio no Instagram para: {segment['label']}.

Hooks sugeridos (você pode adaptar levemente para o segmento):
{hooks_str}

CTAs aprovados (use EXATAMENTE como escrito, sem alterações):
{ctas_str}

Contexto do segmento para incorporar naturalmente (não force todos):
{examples_str}

Retorne exatamente {n_variations} variações como um array JSON."""

    return [
        {"role": "user", "content": system_prompt + "\n\n" + user_message}
    ]
