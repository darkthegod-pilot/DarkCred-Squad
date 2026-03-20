"""
Analisador de Imagens de Resultado de Campanha — Alina Pretrov
Usa Claude Vision para extrair métricas de screenshots do Instagram/Meta Ads.
"""

import base64
import os
from pathlib import Path

import anthropic

from alina.persona import construir_system_prompt_analise
from alina.config import BENCHMARKS


def _classificar_custo_mensagem(valor: float) -> str:
    b = BENCHMARKS["custo_mensagem"]
    if valor < b["excelente"]:
        return "🟢 Excelente — escale a verba!"
    elif valor < b["bom"]:
        return "🟡 Bom — mantenha e monitore"
    elif valor < b["aceitavel"]:
        return "🟠 Aceitável — otimize o copy"
    elif valor < b["ruim"]:
        return "🔴 Ruim — troque o criativo"
    else:
        return "⛔ Pause a campanha agora"


def _classificar_ctr(valor: float) -> str:
    b = BENCHMARKS["ctr"]
    if valor >= b["excelente"]:
        return "🟢 Excelente"
    elif valor >= b["bom"]:
        return "🟡 Bom"
    elif valor >= b["aceitavel"]:
        return "🟠 Aceitável"
    else:
        return "🔴 Troque o criativo"


def _classificar_frequencia(valor: float) -> str:
    b = BENCHMARKS["frequencia"]
    if valor < b["fresco"]:
        return "🟢 Público fresco"
    elif valor < b["atencao"]:
        return "🟡 Atenção — acompanhe"
    elif valor < b["saturando"]:
        return "🟠 Saturando — prepare novo criativo"
    else:
        return "⛔ Saturado — troque o criativo agora"


def _imagem_para_base64(caminho: str) -> tuple[str, str]:
    """Converte imagem para base64. Retorna (base64_string, media_type)."""
    extensao = Path(caminho).suffix.lower()
    tipos = {
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".png": "image/png",
        ".webp": "image/webp",
        ".gif": "image/gif",
    }
    media_type = tipos.get(extensao, "image/jpeg")
    with open(caminho, "rb") as f:
        dados = base64.standard_b64encode(f.read()).decode("utf-8")
    return dados, media_type


PROMPT_ANALISE_IMAGEM = """Analise essa imagem de resultado de campanha de anúncio Instagram/Meta Ads.

EXTRAIA todas as métricas visíveis na imagem:
- Impressões
- Alcance
- Frequência (se não estiver explícita, calcule: Impressões ÷ Alcance)
- CTR (taxa de clique)
- CPM (custo por mil impressões)
- Custo total investido
- Número de mensagens/resultados recebidos
- Custo por mensagem/resultado
- Período da campanha (se visível)
- Qualquer outra métrica visível

DEPOIS faça o diagnóstico completo usando os benchmarks DarkCred:

Custo/mensagem:
- < R$1,50 → Excelente (escalar)
- R$1,50-2,50 → Bom (manter)
- R$2,50-3,50 → Aceitável (monitorar)
- R$3,50-5,00 → Ruim (otimizar copy)
- >R$5,00 → Pausar

CTR:
- >1,5% → Excelente
- 1,0-1,5% → Bom
- 0,5-1,0% → Aceitável
- <0,5% → Trocar criativo

Frequência:
- <1,5 → Público fresco
- 1,5-2,0 → Atenção
- 2,0-2,5 → Saturando
- >2,5 → Saturado (trocar criativo urgente)

Retorne sua análise EXATAMENTE neste formato JSON (sem texto antes ou depois):
{
  "metricas": {
    "impressoes": número ou null,
    "alcance": número ou null,
    "frequencia": número ou null,
    "ctr": número ou null,
    "cpm": número ou null,
    "custo_total": número ou null,
    "mensagens": número ou null,
    "custo_mensagem": número ou null,
    "periodo": "string ou null"
  },
  "classificacoes": {
    "custo_mensagem": "classificação",
    "ctr": "classificação",
    "frequencia": "classificação"
  },
  "diagnostico_geral": "🟢 BOA / 🟡 REGULAR / 🔴 PRECISA DE AÇÃO",
  "analise_texto": "3-4 frases de diagnóstico direto e honesto",
  "acoes_imediatas": ["ação 1", "ação 2", "ação 3"],
  "sugestao_proximo_copy": "se o copy precisar mudar, sugira um novo hook aqui, senão deixe vazio"
}

Se alguma métrica não estiver visível na imagem, use null.
"""


def analisar_imagem_campanha(caminho_imagem: str, modelo: str = "claude-sonnet-4-6") -> dict:
    """
    Analisa screenshot de campanha usando Claude Vision.
    Retorna dict com métricas extraídas, diagnóstico e recomendações.
    """
    import json

    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        raise ValueError("ANTHROPIC_API_KEY não encontrada. Configure no arquivo .env")

    if not Path(caminho_imagem).exists():
        raise FileNotFoundError(f"Imagem não encontrada: {caminho_imagem}")

    dados_imagem, media_type = _imagem_para_base64(caminho_imagem)

    client = anthropic.Anthropic(api_key=api_key)

    resposta = client.messages.create(
        model=modelo,
        max_tokens=2048,
        system=construir_system_prompt_analise(),
        messages=[
            {
                "role": "user",
                "content": [
                    {
                        "type": "image",
                        "source": {
                            "type": "base64",
                            "media_type": media_type,
                            "data": dados_imagem,
                        },
                    },
                    {
                        "type": "text",
                        "text": PROMPT_ANALISE_IMAGEM,
                    },
                ],
            }
        ],
    )

    texto_bruto = resposta.content[0].text.strip()

    # Remove markdown se presente
    if texto_bruto.startswith("```"):
        linhas = texto_bruto.splitlines()
        texto_bruto = "\n".join(
            linha for linha in linhas if not linha.startswith("```")
        ).strip()

    resultado = json.loads(texto_bruto)
    return resultado


def formatar_analise_para_exibicao(resultado: dict) -> str:
    """Formata o resultado da análise para exibição no terminal."""
    m = resultado.get("metricas", {})
    c = resultado.get("classificacoes", {})
    linhas = [
        "",
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━",
        "📸 ANÁLISE DE RESULTADO — ALINA PRETROV",
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━",
        "",
        "📊 MÉTRICAS EXTRAÍDAS DA IMAGEM",
        "───────────────────────────────",
    ]

    def fmt_num(v, prefixo="", sufixo="", casas=0):
        if v is None:
            return "Não visível na imagem"
        if casas > 0:
            return f"{prefixo}{v:.{casas}f}{sufixo}"
        return f"{prefixo}{int(v):,}{sufixo}".replace(",", ".")

    def fmt_linha(label, valor, classi=None):
        parte = f"{label:<18} {valor}"
        if classi:
            parte += f"  →  {classi}"
        return parte

    linhas += [
        fmt_linha("Período:", m.get("periodo") or "Não visível"),
        fmt_linha("Custo total:", fmt_num(m.get("custo_total"), "R$ ", "", 2)),
        fmt_linha("Impressões:", fmt_num(m.get("impressoes"))),
        fmt_linha("Alcance:", fmt_num(m.get("alcance"))),
        fmt_linha("Frequência:", fmt_num(m.get("frequencia"), casas=2), c.get("frequencia", "")),
        fmt_linha("CTR:", fmt_num(m.get("ctr"), sufixo="%", casas=2), c.get("ctr", "")),
        fmt_linha("CPM:", fmt_num(m.get("cpm"), "R$ ", "", 2)),
        fmt_linha("Mensagens:", fmt_num(m.get("mensagens"))),
        fmt_linha("Custo/Mensagem:", fmt_num(m.get("custo_mensagem"), "R$ ", "", 2), c.get("custo_mensagem", "")),
        "",
    ]

    # Projeção de funil
    if m.get("mensagens"):
        msgs = m["mensagens"]
        whats = int(msgs * 0.75)
        quali = int(msgs * 0.45)
        docs = int(msgs * 0.35)
        fechamentos = int(msgs * 0.30)
        linhas += [
            "📈 PROJEÇÃO DE FUNIL",
            "────────────────────",
            f"{msgs} mensagens",
            f"  → ~{whats} no WhatsApp",
            f"  → ~{quali} qualificados",
            f"  → ~{docs} docs enviados",
            f"  → ~{fechamentos} fechamentos esperados",
            "",
        ]

    diagnostico_geral = resultado.get("diagnostico_geral", "")
    linhas += [
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━",
        f"🎯 DIAGNÓSTICO GERAL: {diagnostico_geral}",
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━",
        "",
        resultado.get("analise_texto", ""),
        "",
    ]

    acoes = resultado.get("acoes_imediatas", [])
    if acoes:
        linhas += [
            "⚡ O QUE FAZER AGORA",
            "─────────────────────",
        ]
        for i, acao in enumerate(acoes, 1):
            linhas.append(f"{i}. {acao}")
        linhas.append("")

    prox_copy = resultado.get("sugestao_proximo_copy", "")
    if prox_copy:
        linhas += [
            "✍️ SUGESTÃO PARA O PRÓXIMO COPY",
            "────────────────────────────────",
            prox_copy,
            "",
        ]

    linhas.append("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    return "\n".join(linhas)
