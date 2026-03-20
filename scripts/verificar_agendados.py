#!/usr/bin/env python3
"""
Verificador de Agendados — Alina Pretrov
Exibe copies agendados pendentes no chat do Claude Code.

Este script é executado automaticamente pelo hook do Claude Code.
Quando há copies pendentes em agendados/, eles são exibidos aqui no chat.
"""

import json
import sys
from datetime import datetime
from pathlib import Path

# Garante imports do pacote alina
sys.path.insert(0, str(Path(__file__).parent.parent))

DIRETORIO_AGENDADOS = Path("agendados")

BANNER = """
╔══════════════════════════════════════════════════════════╗
║        📬 ALINA PRETROV — CRIATIVOS DO DIA              ║
╚══════════════════════════════════════════════════════════╝"""


def _formatar_envio(envio: dict) -> str:
    """Formata um envio para exibição no terminal."""
    horario = envio.get("horario", "?")
    emoji = envio.get("emoji", "📢")
    gerado_em_str = envio.get("gerado_em", "")
    dica = envio.get("dica_do_dia", "")
    copies = envio.get("copies", [])

    # Formata data/hora legível
    try:
        dt = datetime.fromisoformat(gerado_em_str)
        data_legivel = dt.strftime("%d/%m/%Y às %H:%M")
    except Exception:
        data_legivel = gerado_em_str

    linhas = [
        "",
        f"  {emoji}  Envio das {horario} — {data_legivel}",
        "  " + "─" * 52,
    ]

    for i, copy in enumerate(copies, 1):
        full = copy.get("full_copy", "")
        linhas.append(f"\n  【 VARIAÇÃO {i} 】")
        for linha in full.splitlines():
            linhas.append(f"      {linha}")

    if dica:
        linhas += [
            "",
            "  💡 DICA DO DIA:",
            f"     {dica}",
        ]

    linhas.append("")
    return "\n".join(linhas)


def verificar_e_exibir() -> int:
    """
    Verifica arquivos pendentes em agendados/ e exibe no terminal.
    Retorna o número de envios exibidos.
    """
    if not DIRETORIO_AGENDADOS.exists():
        return 0

    # Busca arquivos não marcados como exibidos
    pendentes = sorted(
        [
            f for f in DIRETORIO_AGENDADOS.glob("envio_*.json")
            if "_exibido" not in f.name
        ]
    )

    if not pendentes:
        return 0

    print(BANNER)
    print(f"  Você tem {len(pendentes)} envio(s) pendente(s):\n")

    exibidos = 0
    for caminho in pendentes:
        try:
            with open(caminho, encoding="utf-8") as f:
                envio = json.load(f)

            # Marca como exibido ANTES de exibir (evita loop)
            novo_nome = caminho.with_name(caminho.stem + "_exibido.json")
            caminho.rename(novo_nome)

            print(_formatar_envio(envio))
            exibidos += 1

        except Exception as e:
            # Silencia erros para não quebrar o hook
            pass

    if exibidos > 0:
        print("━" * 60)
        print("  Use `python main.py --chat` para conversar com a Alina sobre esses copies.")
        print("  Use `python main.py --analisar foto.jpg` para analisar o resultado de campanha.")
        print("━" * 60)
        print()

    return exibidos


if __name__ == "__main__":
    n = verificar_e_exibir()
    sys.exit(0)
