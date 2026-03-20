"""
Sistema de Auto-Alimentação — Alina Pretrov
Aprende com cada geração e análise para melhorar progressivamente.
"""

import json
from datetime import datetime
from pathlib import Path

CAMINHO_HISTORICO = Path("dados/historico.json")
CAMINHO_APRENDIZADO = Path("dados/aprendizado.json")
CAMINHO_RESULTADOS = Path("dados/resultados")


def _garantir_diretorios() -> None:
    CAMINHO_HISTORICO.parent.mkdir(parents=True, exist_ok=True)
    CAMINHO_RESULTADOS.mkdir(parents=True, exist_ok=True)


def _carregar_json(caminho: Path, padrao) -> dict | list:
    if caminho.exists():
        try:
            with open(caminho, encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, OSError):
            pass
    return padrao


def _salvar_json(caminho: Path, dados) -> None:
    _garantir_diretorios()
    with open(caminho, "w", encoding="utf-8") as f:
        json.dump(dados, f, ensure_ascii=False, indent=2)


# ─────────────────────────────────────────────────────────────
# HISTÓRICO DE GERAÇÕES
# ─────────────────────────────────────────────────────────────

def carregar_historico() -> list:
    return _carregar_json(CAMINHO_HISTORICO, [])


def salvar_geracao(segmento: str, copies: list[dict], aprovados: int, reprovados: int) -> None:
    historico = carregar_historico()
    entrada = {
        "data": datetime.now().isoformat(),
        "segmento": segmento,
        "aprovados": aprovados,
        "reprovados": reprovados,
        "copies": copies,
    }
    historico.append(entrada)
    _salvar_json(CAMINHO_HISTORICO, historico)


# ─────────────────────────────────────────────────────────────
# DADOS DE APRENDIZADO
# ─────────────────────────────────────────────────────────────

def _estrutura_aprendizado_vazia() -> dict:
    return {
        "hooks_performance": {},
        "ctas_performance": {},
        "segmentos_ativos": [],
        "ultimas_analises": [],
        "metricas_historicas": {
            "custo_medio_mensagem": [],
            "ctr_medio": [],
            "frequencia_media": [],
        },
        "padroes_vencedores": [],
        "padroes_a_evitar": [],
        "total_gerações": 0,
        "total_analises": 0,
        "ultima_atualizacao": None,
    }


def carregar_aprendizado() -> dict:
    dados = _carregar_json(CAMINHO_APRENDIZADO, _estrutura_aprendizado_vazia())
    # Garante campos novos em dados antigos
    padrao = _estrutura_aprendizado_vazia()
    for chave, valor in padrao.items():
        if chave not in dados:
            dados[chave] = valor
    return dados


def registrar_geracao_no_aprendizado(segmento: str, aprovados: int) -> None:
    dados = carregar_aprendizado()
    dados["total_gerações"] += 1
    if segmento not in dados["segmentos_ativos"]:
        dados["segmentos_ativos"].append(segmento)
    dados["ultima_atualizacao"] = datetime.now().isoformat()
    _salvar_json(CAMINHO_APRENDIZADO, dados)


def registrar_analise_resultado(metricas: dict) -> None:
    """Chamado após análise de imagem de campanha."""
    dados = carregar_aprendizado()
    dados["total_analises"] += 1

    # Registra métricas históricas
    if "custo_mensagem" in metricas and metricas["custo_mensagem"]:
        dados["metricas_historicas"]["custo_medio_mensagem"].append(metricas["custo_mensagem"])
    if "ctr" in metricas and metricas["ctr"]:
        dados["metricas_historicas"]["ctr_medio"].append(metricas["ctr"])
    if "frequencia" in metricas and metricas["frequencia"]:
        dados["metricas_historicas"]["frequencia_media"].append(metricas["frequencia"])

    # Armazena análise completa
    analise = {
        "data": datetime.now().isoformat(),
        "metricas": metricas,
    }
    dados["ultimas_analises"] = ([analise] + dados["ultimas_analises"])[:20]  # mantém últimas 20

    # Extrai padrões de aprendizado
    if metricas.get("custo_mensagem") and metricas["custo_mensagem"] < 1.50:
        if metricas.get("copy_hook"):
            hook = metricas["copy_hook"]
            dados["hooks_performance"][hook] = dados["hooks_performance"].get(hook, 0) + 2
            if hook not in dados["padroes_vencedores"]:
                dados["padroes_vencedores"].append(f"Hook de alto desempenho: '{hook}'")

    if metricas.get("custo_mensagem") and metricas["custo_mensagem"] > 5.00:
        if metricas.get("copy_hook"):
            hook = metricas["copy_hook"]
            dados["hooks_performance"][hook] = dados["hooks_performance"].get(hook, 0) - 1
            if hook not in dados["padroes_a_evitar"]:
                dados["padroes_a_evitar"].append(f"Hook com baixo desempenho: '{hook}'")

    dados["ultima_atualizacao"] = datetime.now().isoformat()
    _salvar_json(CAMINHO_APRENDIZADO, dados)


def salvar_analise_resultado(metricas: dict, diagnostico: str, recomendacoes: list[str]) -> str:
    """Salva análise completa em arquivo separado. Retorna caminho."""
    _garantir_diretorios()
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    caminho = CAMINHO_RESULTADOS / f"resultado_{timestamp}.json"
    dados = {
        "data": timestamp,
        "metricas_extraidas": metricas,
        "diagnostico": diagnostico,
        "recomendacoes": recomendacoes,
    }
    with open(caminho, "w", encoding="utf-8") as f:
        json.dump(dados, f, ensure_ascii=False, indent=2)
    registrar_analise_resultado(metricas)
    return str(caminho)


# ─────────────────────────────────────────────────────────────
# CONTEXTO DE APRENDIZADO PARA INJETAR NO PROMPT
# ─────────────────────────────────────────────────────────────

def construir_contexto_aprendizado() -> str:
    """Retorna string de contexto para injetar no prompt de geração."""
    dados = carregar_aprendizado()
    linhas = []

    if dados["total_analises"] > 0:
        linhas.append(f"Você já analisou {dados['total_analises']} resultado(s) de campanha.")

    # Métricas médias
    historico = dados["metricas_historicas"]
    if historico["custo_medio_mensagem"]:
        media = sum(historico["custo_medio_mensagem"]) / len(historico["custo_medio_mensagem"])
        linhas.append(f"Custo médio por mensagem das campanhas: R$ {media:.2f}")

    if historico["ctr_medio"]:
        media = sum(historico["ctr_medio"]) / len(historico["ctr_medio"])
        linhas.append(f"CTR médio das campanhas: {media:.2f}%")

    # Padrões vencedores
    if dados["padroes_vencedores"]:
        linhas.append("\nPadrões que funcionaram bem:")
        for p in dados["padroes_vencedores"][:5]:
            linhas.append(f"  ✅ {p}")

    # Padrões a evitar
    if dados["padroes_a_evitar"]:
        linhas.append("\nPadrões com baixo desempenho:")
        for p in dados["padroes_a_evitar"][:3]:
            linhas.append(f"  ❌ {p}")

    # Hooks top performers
    top_hooks = sorted(dados["hooks_performance"].items(), key=lambda x: x[1], reverse=True)[:3]
    if top_hooks and top_hooks[0][1] > 0:
        linhas.append("\nHooks com melhor histórico:")
        for hook, score in top_hooks:
            if score > 0:
                linhas.append(f"  ⭐ '{hook}' (score: {score})")

    # Última análise
    if dados["ultimas_analises"]:
        ultima = dados["ultimas_analises"][0]
        custo = ultima["metricas"].get("custo_mensagem")
        if custo:
            linhas.append(f"\nÚltima análise de campanha: custo/msg = R$ {custo:.2f}")

    return "\n".join(linhas) if linhas else ""


def resumo_aprendizado() -> str:
    """Retorna resumo legível do aprendizado acumulado."""
    dados = carregar_aprendizado()

    if dados["total_gerações"] == 0 and dados["total_analises"] == 0:
        return "📚 Nenhum dado de aprendizado ainda. Gere copies e analise resultados para começar!"

    linhas = [
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━",
        "📚 RESUMO DO APRENDIZADO — ALINA",
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━",
        f"Gerações realizadas:  {dados['total_gerações']}",
        f"Campanhas analisadas: {dados['total_analises']}",
        f"Segmentos usados:     {', '.join(dados['segmentos_ativos'][:5]) or 'nenhum ainda'}",
    ]

    historico = dados["metricas_historicas"]
    if historico["custo_medio_mensagem"]:
        media = sum(historico["custo_medio_mensagem"]) / len(historico["custo_medio_mensagem"])
        linhas.append(f"Custo médio/msg:      R$ {media:.2f}")

    if dados["padroes_vencedores"]:
        linhas.append("\n✅ Padrões vencedores:")
        for p in dados["padroes_vencedores"][:3]:
            linhas.append(f"   {p}")

    return "\n".join(linhas)
