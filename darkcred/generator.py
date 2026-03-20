import json
import os

import anthropic

from darkcred.prompt_builder import build_messages


class GenerationError(Exception):
    pass


def generate_variations(
    segment_key: str, n: int, model: str = "claude-sonnet-4-6"
) -> list[dict]:
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        raise GenerationError(
            "ANTHROPIC_API_KEY não encontrada. Configure no arquivo .env"
        )

    client = anthropic.Anthropic(api_key=api_key)
    messages = build_messages(segment_key, n)

    response = client.messages.create(
        model=model,
        max_tokens=4096,
        messages=messages,
    )

    raw = response.content[0].text.strip()

    # Strip markdown code fences if Claude wraps the JSON
    if raw.startswith("```"):
        lines = raw.splitlines()
        raw = "\n".join(
            line for line in lines if not line.startswith("```")
        ).strip()

    try:
        variations = json.loads(raw)
    except json.JSONDecodeError as e:
        raise GenerationError(
            f"Resposta da API não é JSON válido: {e}\n\nResposta recebida:\n{raw}"
        )

    if not isinstance(variations, list):
        raise GenerationError(
            f"Esperado array JSON, recebido: {type(variations).__name__}"
        )

    return variations
