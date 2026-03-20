"""
Módulo de Saída — Alina Pretrov
Salva copies gerados com feedback intuitivo.
"""

import json
from datetime import datetime
from pathlib import Path


def salvar_saida(
    variacoes: list[dict],
    segmento_key: str,
    diretorio: str = "saidas",
    formato: str = "ambos",
) -> dict[str, str]:
    """
    Salva as variações aprovadas em arquivo(s).
    Retorna dict mapeando formato → caminho do arquivo.
    """
    Path(diretorio).mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    base = f"{diretorio}/alina_{segmento_key}_{timestamp}"
    salvos = {}

    if formato in ("json", "ambos"):
        caminho_json = base + ".json"
        payload = {
            "agente": "Alina Pretrov",
            "segmento": segmento_key,
            "gerado_em": timestamp,
            "total": len(variacoes),
            "variacoes": variacoes,
        }
        with open(caminho_json, "w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False, indent=2)
        salvos["json"] = caminho_json

    if formato in ("texto", "ambos"):
        caminho_txt = base + ".txt"
        with open(caminho_txt, "w", encoding="utf-8") as f:
            f.write(f"✍️ ALINA PRETROV — Segmento: {segmento_key} — {timestamp}\n")
            f.write("=" * 55 + "\n\n")
            for i, var in enumerate(variacoes, 1):
                f.write(f"━━ VARIAÇÃO {i} ━━\n")
                f.write(var.get("full_copy", "") + "\n")
                comprimento = len(var.get("full_copy", ""))
                f.write(f"[{comprimento} caracteres]\n\n")
        salvos["texto"] = caminho_txt

    return salvos


def exibir_variacoes_terminal(variacoes: list[dict]) -> None:
    """Exibe as variações aprovadas no terminal com formatação intuitiva."""
    print()
    for i, var in enumerate(variacoes, 1):
        full = var.get("full_copy", "")
        comprimento = len(full)

        # Indicador de comprimento
        if comprimento <= 200:
            icone_comp = "✅"
        elif comprimento <= 350:
            icone_comp = "🟡"
        else:
            icone_comp = "⚠️"

        print(f"  【 VARIAÇÃO {i} 】{icone_comp} {comprimento} caracteres")
        for linha in full.splitlines():
            print(f"      {linha}")
        print()
