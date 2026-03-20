"""
Módulo de Saída — Alina Pretrov
Salva copies gerados com feedback visual rico usando rich.
"""

import json
from datetime import datetime
from pathlib import Path

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich import box
from rich.text import Text

console = Console()


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


def exibir_variacoes_terminal(variacoes: list[dict], segmento_key: str = "") -> None:
    """Exibe as variações aprovadas no terminal com painéis ricos."""
    console.print()

    for i, var in enumerate(variacoes, 1):
        full = var.get("full_copy", "")
        hook = var.get("hook", "")
        corpo = var.get("corpo", var.get("body", ""))
        cta = var.get("cta", "")
        comprimento = len(full)

        # Cor do painel por comprimento
        if comprimento <= 200:
            cor_borda = "green"
            icone = "✅"
        elif comprimento <= 350:
            cor_borda = "yellow"
            icone = "🟡"
        else:
            cor_borda = "red"
            icone = "⚠️"

        # Constrói texto colorido
        texto = Text()
        texto.append(f"{hook}\n", style="bold white")
        if corpo:
            texto.append(f"{corpo}\n", style="white")
        if cta:
            texto.append(cta, style="bold cyan")

        # Painel com número e comprimento
        titulo = f"[bold]Variação {i}[/bold]  {icone} [dim]{comprimento} caracteres[/dim]"
        panel = Panel(
            texto,
            title=titulo,
            border_style=cor_borda,
            box=box.ROUNDED,
            padding=(0, 1),
        )
        console.print(panel)

    console.print()


def exibir_resumo_geracao(
    segmento_label: str,
    total_gerado: int,
    aprovadas: int,
    reprovadas: int,
    tempo_segundos: float,
    arquivos_salvos: dict[str, str],
) -> None:
    """Exibe tabela de resumo após geração."""
    table = Table(
        title=f"Resumo — {segmento_label}",
        box=box.SIMPLE_HEAVY,
        show_header=False,
        padding=(0, 1),
    )
    table.add_column("Campo", style="dim")
    table.add_column("Valor")

    table.add_row("Total gerado", str(total_gerado))
    table.add_row(
        "Aprovadas",
        f"[green]{aprovadas}[/green]" if aprovadas > 0 else "[dim]0[/dim]",
    )
    if reprovadas > 0:
        table.add_row("Reprovadas", f"[red]{reprovadas}[/red]")
    table.add_row("Tempo", f"{tempo_segundos:.1f}s")

    for tipo_fmt, caminho in arquivos_salvos.items():
        table.add_row(f"Salvo ({tipo_fmt})", f"[dim]{caminho}[/dim]")

    console.print(table)


def exibir_violacoes(violacoes: list) -> None:
    """Exibe violações de compliance com destaque visual."""
    if not violacoes:
        return
    console.print(
        f"\n  [yellow]⚠️  {len(violacoes)} variação(ões) reprovada(s) no compliance:[/yellow]"
    )
    for v in violacoes:
        console.print(f"     [red]❌ {v}[/red]")
