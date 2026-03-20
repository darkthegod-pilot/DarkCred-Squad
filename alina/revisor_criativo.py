"""
Revisor de Criativos Visuais — Alina Pretrov
Usa Claude Vision para analisar a imagem gerada antes do upload.

6 Dimensões de avaliação:
  1. Hierarquia Visual   — headline domina, ordem de leitura clara
  2. Compliance Visual   — sem R$, sem promessas, texto < 20% da área
  3. Originalidade       — design único, não parece template genérico
  4. Impacto Emocional   — comerciante se identifica em 2 segundos
  5. Qualidade Técnica   — nitidez, contraste, legibilidade mobile
  6. Potencial de CTR    — CTA claro, benefício visível

Aprovação: score médio ≥ 7.5 AND Compliance Visual ≥ 8.0
"""

import base64
import json
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

try:
    import anthropic as _sdk
    SDK_OK = True
except ImportError:
    SDK_OK = False


DIMENSOES = [
    "hierarquia_visual",
    "compliance_visual",
    "originalidade",
    "impacto_emocional",
    "qualidade_tecnica",
    "potencial_ctr",
]

LABELS = {
    "hierarquia_visual":  "Hierarquia Visual",
    "compliance_visual":  "Compliance Visual ",
    "originalidade":      "Originalidade     ",
    "impacto_emocional":  "Impacto Emocional ",
    "qualidade_tecnica":  "Qualidade Técnica ",
    "potencial_ctr":      "Potencial de CTR  ",
}

SCORE_MINIMO       = 7.5
COMPLIANCE_MINIMO  = 8.0


@dataclass
class ReviewResult:
    aprovado: bool
    score_total: float
    scores: dict
    melhorias: list
    justificativa: str
    tentativa: int = 1

    @property
    def passou_compliance(self) -> bool:
        return self.scores.get("compliance_visual", 0) >= COMPLIANCE_MINIMO


_PROMPT_REVISOR = """
Você é um DIRETOR DE ARTE SÊNIOR de uma agência brasileira de performance digital.
Sua tarefa é revisar o criativo Instagram abaixo como se fosse aprovação interna antes
do cliente ver.

CONTEXTO DO CRIATIVO:
- Produto: microcrédito para capital de giro (empréstimo rápido para comerciante)
- Público: pequenos comerciantes brasileiros (padeiros, sacoleiros, manicures, mercadinhos)
- Objetivo: gerar clique → mensagem no WhatsApp/Direct
- Plataforma: Instagram feed (1:1, 1080×1080px)
- Compliance: não pode ter R$ + valor, "aprovado", "garantido", "sem consulta SPC"

HOOK do copy: {hook}
CORPO do copy: {corpo}
SEGMENTO: {segmento}

Avalie a imagem em 6 dimensões com nota de 1.0 a 10.0:

1. hierarquia_visual: Headline domina a leitura? Olho sabe onde ir primeiro?
   Há contraste claro entre título, corpo e CTA?

2. compliance_visual: O criativo respeita as políticas Meta Ads?
   (Penalize fortemente se houver: R$ + número, "aprovado/garantido", texto > 20% da área,
   pessoas em sofrimento/desespero, promessa de retorno financeiro explícita)

3. originalidade: O design tem personalidade única? Não parece template de Canva?
   Cores, tipografia e composição têm identidade?

4. impacto_emocional: O comerciante se identifica em 2 segundos?
   O problema/necessidade está visível? Desperta desejo ou reconhecimento?

5. qualidade_tecnica: A imagem está nítida? Contraste adequado?
   Texto legível numa tela mobile de 5 polegadas?

6. potencial_ctr: O CTA está claro e urgente? Há benefício visível?
   O criativo motiva o comerciante a agir AGORA?

IMPORTANTE — Melhorias devem ser CIRÚRGICAS e ACIONÁVEIS.
Exemplo ruim: "melhorar o design"
Exemplo bom: "aumentar o tamanho do hook para pelo menos 80px — está ilegível em mobile"
Exemplo bom: "remover o texto 'Dinheiro na conta hoje' — pode ser interpretado como promessa financeira"

Responda SOMENTE com JSON válido, sem markdown, no formato:
{{
  "scores": {{
    "hierarquia_visual": 8.5,
    "compliance_visual": 9.0,
    "originalidade": 7.0,
    "impacto_emocional": 8.0,
    "qualidade_tecnica": 8.5,
    "potencial_ctr": 7.5
  }},
  "melhorias": [
    "instrução concreta 1",
    "instrução concreta 2"
  ],
  "justificativa": "Parágrafo de 2-3 frases explicando o diagnóstico geral."
}}
"""


def revisar_criativo(
    img_path: str,
    variacao: dict,
    segmento: str = "generico",
    tentativa: int = 1,
) -> ReviewResult:
    """
    Analisa visualmente o criativo usando Claude Vision.

    Parâmetros:
        img_path   — caminho local do PNG gerado
        variacao   — dict com hook, corpo, cta
        segmento   — chave do segmento (ex: "padaria", "generico")
        tentativa  — número da tentativa atual (1-3)

    Retorna ReviewResult com scores, melhorias e flag aprovado.
    """
    if not SDK_OK:
        raise RuntimeError("anthropic não instalado: pip install anthropic")

    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        raise RuntimeError("ANTHROPIC_API_KEY não encontrada no .env")

    # Lê e codifica a imagem
    img_bytes = Path(img_path).read_bytes()
    img_b64   = base64.standard_b64encode(img_bytes).decode()

    prompt = _PROMPT_REVISOR.format(
        hook=variacao.get("hook", ""),
        corpo=variacao.get("corpo", variacao.get("body", "")),
        segmento=segmento,
    )

    client = _sdk.Anthropic(api_key=api_key)
    resp = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=1024,
        messages=[{
            "role": "user",
            "content": [
                {
                    "type":       "image",
                    "source": {
                        "type":       "base64",
                        "media_type": "image/png",
                        "data":       img_b64,
                    },
                },
                {
                    "type": "text",
                    "text": prompt,
                },
            ],
        }],
    )

    raw = resp.content[0].text.strip()

    # Remove markdown code fences se Claude colocar
    if raw.startswith("```"):
        raw = raw.split("```")[1]
        if raw.startswith("json"):
            raw = raw[4:]
        raw = raw.strip()

    data = json.loads(raw)

    scores    = data.get("scores", {})
    melhorias = data.get("melhorias", [])
    justif    = data.get("justificativa", "")

    # Garante todas as dimensões (default 5.0 se ausente)
    for dim in DIMENSOES:
        if dim not in scores:
            scores[dim] = 5.0

    score_total = sum(scores[d] for d in DIMENSOES) / len(DIMENSOES)
    aprovado    = (score_total >= SCORE_MINIMO and
                   scores.get("compliance_visual", 0) >= COMPLIANCE_MINIMO)

    return ReviewResult(
        aprovado=aprovado,
        score_total=round(score_total, 2),
        scores=scores,
        melhorias=melhorias,
        justificativa=justif,
        tentativa=tentativa,
    )


def formatar_review(review: ReviewResult) -> str:
    """Retorna string formatada para exibição no terminal."""
    linhas = []
    for dim in DIMENSOES:
        nota  = review.scores.get(dim, 0)
        label = LABELS[dim]
        icon  = "✅" if nota >= 7.5 else ("⚠️ " if nota >= 6.0 else "❌")
        linhas.append(f"    {label}  {nota:.1f}  {icon}")

    status = "✅ APROVADO" if review.aprovado else "❌ REPROVADO"
    bloco  = "\n".join(linhas)

    saida = (
        f"\n{bloco}\n\n"
        f"    Score Total: {review.score_total:.2f}/10  {status}\n"
    )

    if not review.aprovado and review.melhorias:
        saida += "\n    Melhorias para próxima tentativa:\n"
        for i, m in enumerate(review.melhorias, 1):
            saida += f"      {i}. {m}\n"

    if review.justificativa:
        saida += f"\n    Diagnóstico: {review.justificativa}\n"

    return saida
