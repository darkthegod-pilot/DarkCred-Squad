#!/usr/bin/env python3
"""
Alina Pretrov — Sistema DarkCred
CLI principal com modos: geração, análise de imagem e chat interativo.
"""

import argparse
import sys
from pathlib import Path

from dotenv import load_dotenv

from alina.config import SEGMENTOS
from alina.gerador import ErroGeracao, gerar_variacoes, chat_com_alina
from alina.validador import validar_todas
from alina.saida import salvar_saida, exibir_variacoes_terminal
from alina.aprendizado import salvar_geracao, registrar_geracao_no_aprendizado, resumo_aprendizado
from alina.analisador import analisar_imagem_campanha, formatar_analise_para_exibicao
from alina.aprendizado import salvar_analise_resultado
from alina.persona import SAUDACAO_INICIAL, NOME


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
  python main.py                              # Gera 5 copies genéricos
  python main.py --segmento padaria           # Copies para padaria
  python main.py --segmento todos --quantidade 3  # Todos os segmentos
  python main.py --analisar foto.jpg          # Analisa resultado de campanha
  python main.py --chat                       # Conversa com a Alina
  python main.py --aprendizado                # Ver histórico de aprendizado
        """,
    )

    parser.add_argument(
        "--segmento",
        choices=opcoes_segmento,
        default="generico",
        metavar="SEGMENTO",
        help=f"Segmento alvo. Use 'todos' para todos. Padrão: generico",
    )
    parser.add_argument(
        "--quantidade",
        type=int,
        default=5,
        help="Número de variações por segmento. Padrão: 5",
    )
    parser.add_argument(
        "--diretorio-saida",
        default="saidas",
        help="Diretório para salvar os arquivos. Padrão: ./saidas",
    )
    parser.add_argument(
        "--formato",
        choices=["json", "texto", "ambos"],
        default="ambos",
        help="Formato de saída. Padrão: ambos",
    )
    parser.add_argument(
        "--modelo",
        default="claude-sonnet-4-6",
        help="Modelo Claude a usar. Padrão: claude-sonnet-4-6",
    )
    parser.add_argument(
        "--analisar",
        metavar="IMAGEM",
        help="Caminho para imagem/screenshot de resultado de campanha",
    )
    parser.add_argument(
        "--chat",
        action="store_true",
        help="Inicia modo chat interativo com a Alina",
    )
    parser.add_argument(
        "--aprendizado",
        action="store_true",
        help="Exibe resumo do aprendizado acumulado",
    )
    parser.add_argument(
        "--listar-segmentos",
        action="store_true",
        help="Lista todos os segmentos disponíveis e sai",
    )

    return parser.parse_args()


# ─────────────────────────────────────────────────────────────
# LISTAGEM DE SEGMENTOS
# ─────────────────────────────────────────────────────────────

def listar_segmentos() -> None:
    print()
    print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    print("📋 SEGMENTOS DISPONÍVEIS — Alina Pretrov")
    print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")

    categorias: dict[str, list] = {}
    for chave, seg in SEGMENTOS.items():
        cat = seg.get("categoria", "outros")
        categorias.setdefault(cat, []).append((chave, seg["label"]))

    nomes_categorias = {
        "geral": "🌐 GERAL",
        "alimentacao": "🍽️  ALIMENTAÇÃO & BEBIDAS",
        "beleza": "💅 BELEZA & CUIDADO PESSOAL",
        "varejo": "🛍️  VAREJO & COMÉRCIO",
        "servicos": "🔧 SERVIÇOS",
        "ambulante": "🏪 AMBULANTES & FEIRA",
        "mobilidade": "🚗 MOBILIDADE",
        "educacao": "📚 EDUCAÇÃO",
        "artesanato": "🎨 ARTESANATO",
        "mei": "📋 MEI & AUTÔNOMO",
    }

    for cat, itens in categorias.items():
        titulo = nomes_categorias.get(cat, cat.upper())
        print(f"\n{titulo}")
        for chave, label in itens:
            print(f"  {chave:<22} {label}")

    print()
    print(f"Total: {len(SEGMENTOS)} segmentos")
    print("Use --segmento todos para gerar para todos ao mesmo tempo.")
    print()


# ─────────────────────────────────────────────────────────────
# GERAÇÃO DE COPIES
# ─────────────────────────────────────────────────────────────

def executar_segmento(
    segmento_key: str,
    quantidade: int,
    modelo: str,
    diretorio_saida: str,
    formato: str,
) -> tuple[int, int]:
    """Gera copies para um segmento. Retorna (aprovadas, reprovadas)."""
    label = SEGMENTOS[segmento_key]["label"]
    print()
    print(f"  ✍️  Gerando {quantidade} variações para: {label}...")

    try:
        variacoes = gerar_variacoes(segmento_key, quantidade, modelo)
    except ErroGeracao as e:
        print(f"  ❌ ERRO: {e}", file=sys.stderr)
        return 0, 0

    aprovadas, violacoes = validar_todas(variacoes)

    if violacoes:
        print(f"  ⚠️  {len(violacoes)} variação(ões) reprovada(s) no compliance:")
        for v in violacoes:
            print(f"     ❌ {v}")

    n_aprovadas = len(aprovadas)
    n_reprovadas = len(violacoes)
    print(f"  ✅ {n_aprovadas} variação(ões) aprovada(s)")

    if aprovadas:
        # Exibe no terminal
        exibir_variacoes_terminal(aprovadas)

        # Salva em arquivo
        salvos = salvar_saida(aprovadas, segmento_key, diretorio_saida, formato)
        for tipo_fmt, caminho in salvos.items():
            print(f"  💾 Salvo ({tipo_fmt}): {caminho}")

        # Registra no aprendizado
        salvar_geracao(segmento_key, aprovadas, n_aprovadas, n_reprovadas)
        registrar_geracao_no_aprendizado(segmento_key, n_aprovadas)

    return n_aprovadas, n_reprovadas


# ─────────────────────────────────────────────────────────────
# ANÁLISE DE IMAGEM
# ─────────────────────────────────────────────────────────────

def executar_analise_imagem(caminho_imagem: str, modelo: str) -> None:
    """Analisa screenshot de resultado de campanha."""
    if not Path(caminho_imagem).exists():
        print(f"\n❌ Arquivo não encontrado: {caminho_imagem}", file=sys.stderr)
        sys.exit(1)

    print()
    print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    print(f"📸 Analisando imagem: {caminho_imagem}")
    print("   Aguarde, Alina está processando...")
    print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")

    try:
        resultado = analisar_imagem_campanha(caminho_imagem, modelo)
    except Exception as e:
        print(f"\n❌ Erro ao analisar imagem: {e}", file=sys.stderr)
        sys.exit(1)

    # Exibe resultado formatado
    print(formatar_analise_para_exibicao(resultado))

    # Salva resultado
    metricas = resultado.get("metricas", {})
    diagnostico = resultado.get("analise_texto", "")
    acoes = resultado.get("acoes_imediatas", [])
    caminho_salvo = salvar_analise_resultado(metricas, diagnostico, acoes)
    print(f"  💾 Análise salva em: {caminho_salvo}")


# ─────────────────────────────────────────────────────────────
# MODO CHAT
# ─────────────────────────────────────────────────────────────

def executar_chat(modelo: str) -> None:
    """Inicia sessão de chat interativo com a Alina."""
    print()
    print(SAUDACAO_INICIAL)
    print()

    historico: list[dict] = []

    while True:
        try:
            entrada = input("Você: ").strip()
        except (KeyboardInterrupt, EOFError):
            print("\n\nAlina: Até logo! Boas campanhas! 🚀")
            break

        if not entrada:
            continue

        if entrada.lower() in ("sair", "exit", "quit", "tchau", "bye"):
            print("\nAlina: Até logo! Boas campanhas! 🚀")
            break

        # Verifica se o usuário quer analisar uma imagem no chat
        if entrada.lower().startswith(("analisa ", "analisar ", "/analisar ")):
            partes = entrada.split(maxsplit=1)
            if len(partes) == 2:
                caminho = partes[1].strip()
                executar_analise_imagem(caminho, modelo)
                historico.append({
                    "role": "user",
                    "content": f"[Enviei a imagem {caminho} para análise — veja os resultados acima]"
                })
                historico.append({
                    "role": "assistant",
                    "content": "[Análise de imagem processada e exibida acima]"
                })
                continue

        historico.append({"role": "user", "content": entrada})

        try:
            resposta = chat_com_alina(historico, modelo)
        except ErroGeracao as e:
            print(f"\n❌ Erro: {e}", file=sys.stderr)
            break

        print(f"\nAlina: {resposta}\n")
        historico.append({"role": "assistant", "content": resposta})

        # Limita histórico para evitar contexto muito longo (mantém últimas 20 trocas)
        if len(historico) > 40:
            historico = historico[-40:]


# ─────────────────────────────────────────────────────────────
# PONTO DE ENTRADA
# ─────────────────────────────────────────────────────────────

def main() -> None:
    load_dotenv()
    args = configurar_argumentos()

    # ── Modo: listar segmentos ────────────────────────────────
    if args.listar_segmentos:
        listar_segmentos()
        return

    # ── Modo: resumo de aprendizado ───────────────────────────
    if args.aprendizado:
        print(resumo_aprendizado())
        return

    # ── Modo: análise de imagem ───────────────────────────────
    if args.analisar:
        executar_analise_imagem(args.analisar, args.modelo)
        return

    # ── Modo: chat interativo ─────────────────────────────────
    if args.chat:
        executar_chat(args.modelo)
        return

    # ── Modo: geração de copies ───────────────────────────────
    segmentos = (
        list(SEGMENTOS.keys()) if args.segmento == "todos" else [args.segmento]
    )

    print()
    print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    print(f"✍️  {NOME} — Gerador de Criativos DarkCred")
    if len(segmentos) > 1:
        print(f"   {len(segmentos)} segmentos | {args.quantidade} variações cada")
    print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")

    total_aprovadas = 0
    total_reprovadas = 0

    for seg_key in segmentos:
        aprovadas, reprovadas = executar_segmento(
            seg_key,
            args.quantidade,
            args.modelo,
            args.diretorio_saida,
            args.formato,
        )
        total_aprovadas += aprovadas
        total_reprovadas += reprovadas

    # Sumário final (para múltiplos segmentos)
    if len(segmentos) > 1:
        print()
        print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
        print(f"📊 SUMÁRIO FINAL")
        print(f"   ✅ {total_aprovadas} copies aprovados")
        if total_reprovadas:
            print(f"   ❌ {total_reprovadas} reprovados no compliance")
        print(f"   💾 Arquivos em: ./{args.diretorio_saida}/")
        print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
        print()


if __name__ == "__main__":
    main()
