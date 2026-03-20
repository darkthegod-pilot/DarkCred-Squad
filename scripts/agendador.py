#!/usr/bin/env python3
"""
Agendador de Criativos — Alina Pretrov
Gera copies automaticamente às 12h, 15h e 18h30 e salva em agendados/.

USO:
  # Rodar como daemon (bloqueia, executa nos horários):
  python scripts/agendador.py

  # Gerar agora para um horário específico (ideal para cron):
  python scripts/agendador.py --agora --horario 12h
  python scripts/agendador.py --agora --horario 15h
  python scripts/agendador.py --agora --horario 18h30

CRON (adicionar com: crontab -e):
  0 12 * * * cd /home/user/DarkCred-Squad && python scripts/agendador.py --agora --horario 12h >> logs/cron.log 2>&1
  0 15 * * * cd /home/user/DarkCred-Squad && python scripts/agendador.py --agora --horario 15h >> logs/cron.log 2>&1
  30 18 * * * cd /home/user/DarkCred-Squad && python scripts/agendador.py --agora --horario 18h30 >> logs/cron.log 2>&1
"""

import argparse
import json
import os
import sys
import time
from datetime import datetime
from pathlib import Path

# Garante que imports do pacote alina funcionem
sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv

HORARIOS = {
    "12h":   {"hora": 12, "minuto": 0,  "quantidade": 5, "emoji": "☀️"},
    "15h":   {"hora": 15, "minuto": 0,  "quantidade": 5, "emoji": "🌤️"},
    "18h30": {"hora": 18, "minuto": 30, "quantidade": 5, "emoji": "🌆"},
}

DIRETORIO_AGENDADOS = Path("agendados")


def _garantir_diretorios() -> None:
    DIRETORIO_AGENDADOS.mkdir(exist_ok=True)
    Path("logs").mkdir(exist_ok=True)


def _gerar_dica_do_dia() -> str:
    """Gera uma dica de campanha baseada no aprendizado acumulado."""
    try:
        from alina.aprendizado import carregar_aprendizado, carregar_historico

        dados = carregar_aprendizado()
        historico = carregar_historico()
        dicas = []

        # Verifica frequência (se há dados de análise)
        if dados["ultimas_analises"]:
            ultima = dados["ultimas_analises"][0]
            freq = ultima["metricas"].get("frequencia")
            custo = ultima["metricas"].get("custo_mensagem")
            if freq and freq > 2.0:
                dicas.append(f"⚠️  Frequência alta ({freq:.1f}) detectada na última análise — considere trocar o criativo hoje.")
            if custo and custo < 1.50:
                dicas.append(f"🚀 Último resultado excelente (R${custo:.2f}/msg) — bom momento para escalar a verba!")
            if custo and custo > 3.50:
                dicas.append(f"🔴 Custo alto (R${custo:.2f}/msg) na última análise — use um dos copies gerados hoje.")

        # Hooks top performers
        top_hooks = sorted(dados["hooks_performance"].items(), key=lambda x: x[1], reverse=True)
        if top_hooks and top_hooks[0][1] > 0:
            dicas.append(f"⭐ Hook de melhor histórico: \"{top_hooks[0][0]}\"")

        if not dicas:
            dicas = [
                "💡 Lembre: copies genéricos têm mais escala. Não fragmenta o orçamento.",
                "📅 Horário ideal: impulsione apenas das 06h às 18h (comerciante na loja).",
                "🎯 Se CTR < 0,5%, troque o criativo antes de mexer na segmentação.",
            ]

        return dicas[datetime.now().day % len(dicas)]
    except Exception:
        return "💡 Gere, analise, aprenda. O sistema melhora a cada ciclo."


def gerar_envio(identificador_horario: str) -> dict | None:
    """
    Gera copies para o horário informado e salva em agendados/.
    Retorna dict com os dados gerados ou None em caso de erro.
    """
    _garantir_diretorios()

    config = HORARIOS.get(identificador_horario)
    if not config:
        print(f"❌ Horário inválido: {identificador_horario}. Use: {list(HORARIOS.keys())}")
        return None

    agora = datetime.now()
    timestamp = agora.strftime("%Y%m%d_%H-%M")
    emoji = config["emoji"]
    qtd = config["quantidade"]

    print(f"\n{emoji} Gerando envio das {identificador_horario} — {agora.strftime('%d/%m/%Y %H:%M')}")

    try:
        from alina.gerador import gerar_variacoes
        from alina.validador import validar_todas

        variacoes_brutas = gerar_variacoes("generico", qtd)
        aprovadas, violacoes = validar_todas(variacoes_brutas)

        if not aprovadas:
            print(f"⚠️  Nenhuma variação aprovada no compliance. Tentando novamente...")
            variacoes_brutas = gerar_variacoes("generico", qtd + 2)
            aprovadas, violacoes = validar_todas(variacoes_brutas)

        dica = _gerar_dica_do_dia()

        # ── Gera imagens para os copies aprovados ──────────────
        imagens_geradas = []
        try:
            from alina.gerador_imagem import gerar_criativos_para_variacoes, PILLOW_DISPONIVEL
            if PILLOW_DISPONIVEL and aprovadas:
                print(f"   Gerando imagens PNG...")
                imagens_geradas = gerar_criativos_para_variacoes(
                    aprovadas,
                    segmento_key="generico",
                    template=None,   # aleatório
                    usar_ia=False,   # sem IA no agendador (evita dependência de infsh no cron)
                )
                print(f"   📸 {len(imagens_geradas)} imagem(ns) gerada(s)")
        except Exception as e:
            print(f"   ⚠️  Imagens não geradas: {e}")

        # Associa cada copy ao seu PNG (se gerado)
        copies_com_imagem = []
        for i, copy in enumerate(aprovadas):
            entry = dict(copy)
            if i < len(imagens_geradas):
                entry["imagem_png"] = imagens_geradas[i]
            copies_com_imagem.append(entry)

        envio = {
            "horario": identificador_horario,
            "gerado_em": agora.isoformat(),
            "emoji": emoji,
            "total_aprovadas": len(aprovadas),
            "dica_do_dia": dica,
            "copies": copies_com_imagem,
            "imagens": imagens_geradas,
            "exibido": False,
        }

        caminho = DIRETORIO_AGENDADOS / f"envio_{timestamp}_{identificador_horario}.json"
        with open(caminho, "w", encoding="utf-8") as f:
            json.dump(envio, f, ensure_ascii=False, indent=2)

        print(f"✅ {len(aprovadas)} copies gerados e salvos em: {caminho}")
        return envio

    except Exception as e:
        print(f"❌ Erro ao gerar envio das {identificador_horario}: {e}")
        return None


def rodar_daemon() -> None:
    """Roda como daemon, executando nos horários definidos."""
    try:
        import schedule
    except ImportError:
        print("❌ Instale o schedule: pip install schedule")
        sys.exit(1)

    print(f"\n🤖 Alina Pretrov — Agendador iniciado")
    print(f"   Horários: 12h00 | 15h00 | 18h30")
    print(f"   Ctrl+C para parar\n")

    schedule.every().day.at("12:00").do(gerar_envio, "12h")
    schedule.every().day.at("15:00").do(gerar_envio, "15h")
    schedule.every().day.at("18:30").do(gerar_envio, "18h30")

    while True:
        schedule.run_pending()
        time.sleep(30)  # verifica a cada 30 segundos


def main() -> None:
    load_dotenv()

    parser = argparse.ArgumentParser(description="Agendador de Criativos — Alina Pretrov")
    parser.add_argument("--agora", action="store_true", help="Gera imediatamente (para cron)")
    parser.add_argument(
        "--horario",
        choices=list(HORARIOS.keys()),
        help="Horário a simular (requer --agora)",
    )
    args = parser.parse_args()

    if args.agora:
        horario = args.horario or "12h"
        resultado = gerar_envio(horario)
        sys.exit(0 if resultado else 1)
    else:
        rodar_daemon()


if __name__ == "__main__":
    main()
