#!/usr/bin/env python3
"""
Alina Pretrov — Sistema DarkCred
CLI principal com modos: geração, análise de imagem e chat interativo.
"""

import argparse
import sys
import time
from pathlib import Path

from dotenv import load_dotenv
from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.rule import Rule
from rich import box

from alina.config import SEGMENTOS
from alina.gerador import ErroGeracao, gerar_variacoes, chat_com_alina
from alina.validador import validar_todas
from alina.saida import (
    salvar_saida,
    exibir_variacoes_terminal,
    exibir_resumo_geracao,
    exibir_violacoes,
    console,
)
from alina.aprendizado import (
    salvar_geracao,
    registrar_geracao_no_aprendizado,
    resumo_aprendizado,
    construir_contexto_aprendizado,
)
from alina.analisador import analisar_imagem_campanha, formatar_analise_para_exibicao
from alina.aprendizado import salvar_analise_resultado
from alina.persona import SAUDACAO_INICIAL, NOME
from alina.logger import log


# ─────────────────────────────────────────────────────────────
# ARGUMENTOS CLI
# ─────────────────────────────────────────────────────────────

def configurar_argumentos() -> argparse.Namespace:
    opcoes_segmento = list(SEGMENTOS.keys()) + ["todos"]

    parser = argparse.ArgumentParser(
        prog="alina",
        description="Alina Pretrov — Especialista em Criativos DarkCred para Instagram",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Exemplos:
  python main.py                              # 5 copies genéricos
  python main.py --segmento padaria           # copies para padaria
  python main.py --segmento todos -q 3       # todos os segmentos
  python main.py --imagem                     # copies + imagem PNG
  python main.py --imagem --template 1        # força template escuro
  python main.py --imagem --ia                # fundo gerado por IA (requer infsh)
  python main.py --preview-templates          # visualiza os 3 layouts (sem API)
  python main.py --regenerar-imagens out.json # regera imagens de JSON salvo
  python main.py --analisar foto.jpg          # analisa resultado
  python main.py --chat                       # conversa com Alina
  python main.py --aprendizado                # ver aprendizado
        """,
    )
    parser.add_argument(
        "--segmento", choices=opcoes_segmento, default="generico", metavar="SEGMENTO",
        help="Segmento alvo. Use 'todos' para todos. Padrão: generico",
    )
    parser.add_argument(
        "--quantidade", "-q", type=int, default=5,
        help="Número de variações por segmento. Padrão: 5",
    )
    parser.add_argument(
        "--diretorio-saida", default="saidas",
        help="Diretório para salvar arquivos. Padrão: ./saidas",
    )
    parser.add_argument(
        "--formato", choices=["json", "texto", "ambos"], default="ambos",
        help="Formato de saída. Padrão: ambos",
    )
    parser.add_argument(
        "--modelo", default="claude-sonnet-4-6",
        help="Modelo Claude. Padrão: claude-sonnet-4-6",
    )
    parser.add_argument(
        "--analisar", metavar="IMAGEM",
        help="Caminho para screenshot de resultado de campanha",
    )
    parser.add_argument("--chat", action="store_true", help="Chat interativo com Alina")
    parser.add_argument("--aprendizado", action="store_true", help="Resumo do aprendizado acumulado")
    parser.add_argument("--listar-segmentos", action="store_true", help="Lista segmentos e sai")
    parser.add_argument(
        "--imagem", action="store_true",
        help="Gera imagem PNG 1080x1080 do criativo para cada copy aprovado",
    )
    parser.add_argument(
        "--template", type=int, choices=[1, 2, 3], default=None,
        help="Template da imagem: 1=Escuro, 2=Claro, 3=Verde. Padrão: aleatório",
    )
    parser.add_argument(
        "--ia", action="store_true",
        help="Usa nano-banana-2 (Gemini) para gerar fundo da imagem (requer infsh)",
    )
    parser.add_argument(
        "--preview-templates", action="store_true",
        help="Gera preview dos 3 templates com copy fictício (sem API key)",
    )
    parser.add_argument(
        "--regenerar-imagens", metavar="JSON",
        help="Caminho para JSON de saída salvo — regera as imagens dos copies",
    )

    return parser.parse_args()


# ─────────────────────────────────────────────────────────────
# LISTAGEM DE SEGMENTOS
# ─────────────────────────────────────────────────────────────

def listar_segmentos() -> None:
    from rich.table import Table

    console.print()
    console.rule("[bold cyan]📋 Segmentos Disponíveis — Alina Pretrov[/bold cyan]")

    categorias: dict[str, list] = {}
    for chave, seg in SEGMENTOS.items():
        cat = seg.get("categoria", "outros")
        categorias.setdefault(cat, []).append((chave, seg["label"]))

    icones = {
        "geral": "🌐", "alimentacao": "🍽️", "beleza": "💅",
        "varejo": "🛍️", "servicos": "🔧", "ambulante": "🏪",
        "mobilidade": "🚗", "educacao": "📚", "artesanato": "🎨", "mei": "📋",
    }

    for cat, itens in categorias.items():
        icone = icones.get(cat, "•")
        table = Table(box=box.SIMPLE, show_header=False, padding=(0, 1))
        table.add_column("Chave", style="cyan", width=24)
        table.add_column("Label")
        for chave, label in itens:
            table.add_row(chave, label)
        console.print(f"\n{icone} [bold]{cat.upper()}[/bold]")
        console.print(table)

    console.print(f"\n[dim]Total: {len(SEGMENTOS)} segmentos | Use --segmento todos para gerar para todos[/dim]\n")


# ─────────────────────────────────────────────────────────────
# CONTEXTO DE APRENDIZADO (exibido ao iniciar se houver dados)
# ─────────────────────────────────────────────────────────────

def _exibir_contexto_aprendizado_se_houver() -> None:
    ctx = construir_contexto_aprendizado()
    if ctx:
        console.print(
            Panel(
                f"[dim]{ctx}[/dim]",
                title="[bold yellow]📚 Contexto do Aprendizado[/bold yellow]",
                border_style="yellow",
                box=box.ROUNDED,
                padding=(0, 1),
            )
        )
        console.print()


# ─────────────────────────────────────────────────────────────
# GERAÇÃO DE COPIES
# ─────────────────────────────────────────────────────────────

def executar_segmento(
    segmento_key: str,
    quantidade: int,
    modelo: str,
    diretorio_saida: str,
    formato: str,
    gerar_imagem: bool = False,
    template_imagem: int | None = None,
    usar_ia: bool = False,
) -> tuple[int, int]:
    """Gera copies (e opcionalmente imagens) para um segmento. Retorna (aprovadas, reprovadas)."""
    label = SEGMENTOS[segmento_key]["label"]
    log.info(f"Executando segmento: {segmento_key}")

    console.print(f"\n[bold]✍️  {label}[/bold]")

    # Spinner enquanto chama a API
    variacoes = None
    with Progress(
        SpinnerColumn(spinner_name="dots"),
        TextColumn("[cyan]Alina está gerando...[/cyan]"),
        console=console,
        transient=True,
    ) as progress:
        progress.add_task("", total=None)
        inicio = time.time()
        try:
            variacoes = gerar_variacoes(segmento_key, quantidade, modelo)
        except ErroGeracao as e:
            console.print(f"  [red]❌ ERRO:[/red] {e}")
            log.error(f"Erro ao gerar para {segmento_key}: {e}")
            return 0, 0
        tempo_total = time.time() - inicio

    aprovadas, violacoes = validar_todas(variacoes)
    exibir_violacoes(violacoes)

    n_aprovadas = len(aprovadas)
    n_reprovadas = len(violacoes)

    if aprovadas:
        exibir_variacoes_terminal(aprovadas, segmento_key)
        arquivos = salvar_saida(aprovadas, segmento_key, diretorio_saida, formato)
        exibir_resumo_geracao(label, len(variacoes), n_aprovadas, n_reprovadas, tempo_total, arquivos)
        salvar_geracao(segmento_key, aprovadas, n_aprovadas, n_reprovadas)
        registrar_geracao_no_aprendizado(segmento_key, n_aprovadas)

        # ── Geração de imagens ──────────────────────────────────
        if gerar_imagem:
            _executar_geracao_imagens(aprovadas, segmento_key, template_imagem, usar_ia)
    else:
        console.print("  [red]Nenhuma variação aprovada no compliance.[/red]")

    return n_aprovadas, n_reprovadas


def _executar_geracao_imagens(
    aprovadas: list[dict],
    segmento_key: str,
    template: int | None,
    usar_ia: bool,
) -> None:
    """Gera PNGs para as variações aprovadas e exibe os caminhos."""
    try:
        from alina.gerador_imagem import gerar_criativos_para_variacoes, PILLOW_DISPONIVEL
    except ImportError:
        console.print("  [yellow]⚠️  Pillow não instalado. Execute: pip install Pillow[/yellow]")
        return

    if not PILLOW_DISPONIVEL:
        console.print("  [yellow]⚠️  Pillow não disponível. Execute: pip install Pillow[/yellow]")
        return

    # Verifica infsh se --ia solicitado
    if usar_ia:
        try:
            from alina.nano_banana import verificar_infsh_disponivel
            if not verificar_infsh_disponivel():
                console.print("  [yellow]⚠️  infsh não encontrado. Instale em inference.sh para usar --ia.[/yellow]")
                usar_ia = False
        except ImportError:
            usar_ia = False

    spinner_txt = "[magenta]Gerando imagens...[/magenta]"
    if usar_ia:
        spinner_txt = "[magenta]Gerando imagens com IA (Gemini)...[/magenta]"

    caminhos = []
    with Progress(
        SpinnerColumn(spinner_name="dots"),
        TextColumn(spinner_txt),
        console=console,
        transient=True,
    ) as progress:
        progress.add_task("", total=None)
        try:
            caminhos = gerar_criativos_para_variacoes(
                aprovadas,
                segmento_key=segmento_key,
                template=template,
                usar_ia=usar_ia,
            )
        except Exception as e:
            console.print(f"  [red]❌ Erro ao gerar imagens:[/red] {e}")
            log.error(f"Erro ao gerar imagens para {segmento_key}: {e}")
            return

    if caminhos:
        from rich import box as rbox
        from rich.table import Table
        tbl = Table(
            title="📸 Criativos Gerados",
            box=rbox.SIMPLE,
            show_header=False,
            padding=(0, 1),
        )
        tbl.add_column("N", style="dim", width=4)
        tbl.add_column("Arquivo", style="cyan")
        for i, c in enumerate(caminhos, 1):
            tbl.add_row(str(i), c)
        console.print(tbl)
        console.print(
            f"  [dim]Abra as imagens ou use o Read tool para visualizá-las aqui no chat.[/dim]\n"
        )
        log.info(f"Imagens geradas: {caminhos}")


# ─────────────────────────────────────────────────────────────
# ANÁLISE DE IMAGEM
# ─────────────────────────────────────────────────────────────

def executar_analise_imagem(caminho_imagem: str, modelo: str) -> None:
    if not Path(caminho_imagem).exists():
        console.print(f"\n[red]❌ Arquivo não encontrado:[/red] {caminho_imagem}")
        sys.exit(1)

    console.print()
    console.rule("[bold magenta]📸 Análise de Resultado — Alina Pretrov[/bold magenta]")

    resultado = None
    with Progress(
        SpinnerColumn(spinner_name="dots"),
        TextColumn("[magenta]Alina está analisando a imagem...[/magenta]"),
        console=console,
        transient=True,
    ) as progress:
        progress.add_task("", total=None)
        try:
            resultado = analisar_imagem_campanha(caminho_imagem, modelo)
        except Exception as e:
            console.print(f"\n[red]❌ Erro ao analisar imagem:[/red] {e}")
            log.error(f"Erro ao analisar imagem {caminho_imagem}: {e}")
            sys.exit(1)

    print(formatar_analise_para_exibicao(resultado))

    metricas = resultado.get("metricas", {})
    diagnostico = resultado.get("analise_texto", "")
    acoes = resultado.get("acoes_imediatas", [])
    caminho_salvo = salvar_analise_resultado(metricas, diagnostico, acoes)
    console.print(f"  [dim]💾 Análise salva em: {caminho_salvo}[/dim]")
    log.info(f"Análise de imagem salva em: {caminho_salvo}")


# ─────────────────────────────────────────────────────────────
# MODO CHAT
# ─────────────────────────────────────────────────────────────

def executar_chat(modelo: str) -> None:
    console.print()
    console.print(
        Panel(
            SAUDACAO_INICIAL,
            border_style="cyan",
            box=box.ROUNDED,
            padding=(0, 2),
        )
    )
    console.print()

    historico: list[dict] = []

    while True:
        try:
            entrada = console.input("[bold cyan]Você:[/bold cyan] ").strip()
        except (KeyboardInterrupt, EOFError):
            console.print("\n\n[cyan]Alina: Até logo! Boas campanhas! 🚀[/cyan]")
            break

        if not entrada:
            continue

        if entrada.lower() in ("sair", "exit", "quit", "tchau", "bye"):
            console.print("\n[cyan]Alina: Até logo! Boas campanhas! 🚀[/cyan]")
            break

        # Analisa imagem se o usuário pedir no chat
        if entrada.lower().startswith(("analisa ", "analisar ", "/analisar ")):
            partes = entrada.split(maxsplit=1)
            if len(partes) == 2:
                executar_analise_imagem(partes[1].strip(), modelo)
                historico.append({"role": "user", "content": f"[Imagem {partes[1].strip()} analisada — veja resultado acima]"})
                historico.append({"role": "assistant", "content": "[Análise processada e exibida acima]"})
                continue

        historico.append({"role": "user", "content": entrada})

        resposta = None
        with Progress(
            SpinnerColumn(spinner_name="dots"),
            TextColumn("[dim]Alina está pensando...[/dim]"),
            console=console,
            transient=True,
        ) as progress:
            progress.add_task("", total=None)
            try:
                resposta = chat_com_alina(historico, modelo)
            except ErroGeracao as e:
                console.print(f"\n[red]❌ Erro:[/red] {e}")
                break

        console.print(
            Panel(
                resposta,
                title="[bold cyan]Alina Pretrov[/bold cyan]",
                border_style="cyan",
                box=box.ROUNDED,
                padding=(0, 1),
            )
        )
        console.print()
        historico.append({"role": "assistant", "content": resposta})

        # Mantém histórico razoável (últimas 40 mensagens)
        if len(historico) > 40:
            historico = historico[-40:]


# ─────────────────────────────────────────────────────────────
# PREVIEW DE TEMPLATES
# ─────────────────────────────────────────────────────────────

def _executar_preview_templates(template_forçado: int | None = None) -> None:
    """Gera PNGs de preview dos templates sem precisar de API key."""
    try:
        from alina.gerador_imagem import gerar_previews_templates, PILLOW_DISPONIVEL
    except ImportError:
        console.print("[yellow]⚠️  Pillow não instalado. Execute: pip install Pillow[/yellow]")
        return

    if not PILLOW_DISPONIVEL:
        console.print("[yellow]⚠️  Pillow não disponível. Execute: pip install Pillow[/yellow]")
        return

    console.print()
    console.rule("[bold magenta]🎨 Preview dos Templates — Alina Pretrov[/bold magenta]")
    console.print()

    with Progress(
        SpinnerColumn(spinner_name="dots"),
        TextColumn("[magenta]Gerando previews...[/magenta]"),
        console=console,
        transient=True,
    ) as progress:
        progress.add_task("", total=None)
        caminhos = gerar_previews_templates()

    nomes = ["Template 1 — Escuro Moderno", "Template 2 — Claro Impacto", "Template 3 — Comerciante"]
    for i, (nome, caminho) in enumerate(zip(nomes, caminhos), 1):
        console.print(
            Panel(
                f"[cyan]{caminho}[/cyan]",
                title=f"[bold]{nome}[/bold]",
                border_style="magenta",
                box=box.ROUNDED,
                padding=(0, 1),
            )
        )

    console.print(
        f"\n  [dim]Use o Read tool nos caminhos acima para visualizar aqui no chat.[/dim]\n"
    )
    log.info(f"Previews gerados: {caminhos}")


# ─────────────────────────────────────────────────────────────
# REGENERAR IMAGENS
# ─────────────────────────────────────────────────────────────

def _executar_regenerar_imagens(caminho_json: str, template: int | None = None) -> None:
    """Lê JSON de saída salvo e regera imagens para os copies nele contidos."""
    try:
        from alina.gerador_imagem import regenerar_imagens_de_json, PILLOW_DISPONIVEL
    except ImportError:
        console.print("[yellow]⚠️  Pillow não instalado. Execute: pip install Pillow[/yellow]")
        return

    if not PILLOW_DISPONIVEL:
        console.print("[yellow]⚠️  Pillow não disponível. Execute: pip install Pillow[/yellow]")
        return

    if not Path(caminho_json).exists():
        console.print(f"[red]❌ Arquivo não encontrado:[/red] {caminho_json}")
        return

    console.print()
    console.rule(f"[bold cyan]🔄 Regenerando Imagens — {Path(caminho_json).name}[/bold cyan]")
    console.print()

    caminhos = []
    with Progress(
        SpinnerColumn(spinner_name="dots"),
        TextColumn("[cyan]Gerando imagens...[/cyan]"),
        console=console,
        transient=True,
    ) as progress:
        progress.add_task("", total=None)
        try:
            caminhos = regenerar_imagens_de_json(caminho_json, template=template)
        except Exception as e:
            console.print(f"[red]❌ Erro:[/red] {e}")
            log.error(f"Erro ao regenerar imagens de {caminho_json}: {e}")
            return

    if caminhos:
        from rich.table import Table
        tbl = Table(box=box.SIMPLE, show_header=False, padding=(0, 1))
        tbl.add_column("N", style="dim", width=4)
        tbl.add_column("Arquivo", style="cyan")
        for i, c in enumerate(caminhos, 1):
            tbl.add_row(str(i), c)
        console.print(tbl)
        console.print(f"  [dim]{len(caminhos)} imagem(ns) gerada(s) com sucesso.[/dim]\n")
        log.info(f"Imagens regeneradas de {caminho_json}: {caminhos}")


# ─────────────────────────────────────────────────────────────
# PONTO DE ENTRADA
# ─────────────────────────────────────────────────────────────

def main() -> None:
    load_dotenv()
    args = configurar_argumentos()

    if args.listar_segmentos:
        listar_segmentos()
        return

    if args.aprendizado:
        console.print(resumo_aprendizado())
        return

    if args.analisar:
        executar_analise_imagem(args.analisar, args.modelo)
        return

    if args.chat:
        executar_chat(args.modelo)
        return

    if args.preview_templates:
        _executar_preview_templates(args.template)
        return

    if args.regenerar_imagens:
        _executar_regenerar_imagens(args.regenerar_imagens, args.template)
        return

    # ── Modo geração ───────────────────────────────────────────
    segmentos = (
        list(SEGMENTOS.keys()) if args.segmento == "todos" else [args.segmento]
    )

    console.print()
    console.rule(f"[bold cyan]✍️  {NOME} — Gerador de Criativos DarkCred[/bold cyan]")

    # Exibe contexto de aprendizado se houver
    _exibir_contexto_aprendizado_se_houver()

    total_aprovadas = 0
    total_reprovadas = 0
    inicio_total = time.time()

    for seg_key in segmentos:
        aprovadas, reprovadas = executar_segmento(
            seg_key, args.quantidade, args.modelo, args.diretorio_saida, args.formato,
            gerar_imagem=args.imagem,
            template_imagem=args.template,
            usar_ia=args.ia,
        )
        total_aprovadas += aprovadas
        total_reprovadas += reprovadas

    tempo_total = time.time() - inicio_total

    # Sumário final
    if len(segmentos) > 1:
        console.print()
        console.rule("[bold]📊 Sumário Final[/bold]")
        console.print(f"  [green]✅ {total_aprovadas} copies aprovados[/green]")
        if total_reprovadas:
            console.print(f"  [red]❌ {total_reprovadas} reprovados no compliance[/red]")
        console.print(f"  ⏱️  Tempo total: [dim]{tempo_total:.1f}s[/dim]")
        console.print(f"  💾 Arquivos em: [dim]./{args.diretorio_saida}/[/dim]")
        console.print()

    log.info(f"Sessão encerrada: {total_aprovadas} aprovados, {total_reprovadas} reprovados")


if __name__ == "__main__":
    main()
