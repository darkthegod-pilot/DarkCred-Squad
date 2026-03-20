"""
Pipeline de Criativo — Alina Pretrov
Workflow completo de agência: Briefing → Arte → Geração → Revisão → Entrega

5 Etapas:
  1. Compliance de copy (validador.py)
  2. Direção de arte — sorteia layout dinâmico por segmento
  3. Geração do fundo + overlay tipográfico (gerador_imagem_ia.py)
  4. Revisão visual por IA (revisor_criativo.py) — até 3 tentativas
  5. Upload público + Relatório de Produção completo

O Relatório mostra cada tentativa com scores individuais, comparativo
entre tentativas, correções aplicadas e o link final em destaque.

Uso:
    from alina.pipeline_criativo import executar_pipeline
    resultado = executar_pipeline(
        variacao={"hook": "...", "corpo": "...", "cta": "..."},
        segmento="generico",
    )
    print(resultado.url)
"""

import os
import subprocess
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Optional

from .validador import validar_variacao
from .gerador_imagem_ia import gerar_criativo_ia
from .revisor_criativo import revisar_criativo, ReviewResult, DIMENSOES, LABELS
from .config import score_minimo_aprovacao
from .aprendizado import carregar_aprendizado

MAX_TENTATIVAS = 3


def _score_minimo_atual() -> float:
    """Score mínimo de aprovação adaptado ao nível de experiência acumulada."""
    try:
        dados = carregar_aprendizado()
        return score_minimo_aprovacao(dados.get("total_gerações", 0))
    except Exception:
        return 7.5

# ─── Mapa segmento → layout preferido ───────────────────────
_LAYOUT_POR_SEGMENTO: dict = {
    "padaria": "SPLIT_DIAGONAL", "lanchonete": "SPLIT_DIAGONAL",
    "restaurante": "SPLIT_DIAGONAL", "pizzaria": "SPLIT_DIAGONAL",
    "acai": "SPLIT_DIAGONAL", "food_truck": "SPLIT_DIAGONAL",
    "salao": "HEADLINE_CENTRALIZADA", "barbearia": "HEADLINE_CENTRALIZADA",
    "manicure": "HEADLINE_CENTRALIZADA", "estetica": "HEADLINE_CENTRALIZADA",
    "academia": "HEADLINE_CENTRALIZADA",
    "vestuario": "LATERAL_ESQUERDA", "mercadinho": "LATERAL_ESQUERDA",
    "farmacia": "LATERAL_ESQUERDA", "variedades": "LATERAL_ESQUERDA",
    "mecanico": "TIPOGRAFIA_FORTE", "generico": "TIPOGRAFIA_FORTE",
}
_TODOS_LAYOUTS = ["TIPOGRAFIA_FORTE", "SPLIT_DIAGONAL",
                  "HEADLINE_CENTRALIZADA", "LATERAL_ESQUERDA"]


@dataclass
class PipelineResult:
    img_path:   str
    url:        str
    review:     ReviewResult
    tentativas: int
    aprovado:   bool
    historico:  list   # lista de ReviewResult por tentativa


class ComplianceError(Exception):
    def __init__(self, violacoes: list):
        self.violacoes = violacoes
        msgs = "; ".join(v.razoes[0] if v.razoes else "violação" for v in violacoes)
        super().__init__(f"Copy com violações de compliance: {msgs}")


# ─────────────────────────────────────────────────────────────
# Helpers de formatação do relatório
# ─────────────────────────────────────────────────────────────

_W = 58  # largura do relatório

def _sep(char="━", w=_W):        return char * w
def _box_top(w=_W):              return "╔" + "═" * (w-2) + "╗"
def _box_bot(w=_W):              return "╚" + "═" * (w-2) + "╝"
def _box_mid(w=_W):              return "╠" + "═" * (w-2) + "╣"
def _box_row(txt, w=_W):
    pad = w - 4 - len(txt)
    return f"║  {txt}{' ' * max(pad, 0)}  ║"

def _score_icon(nota: float) -> str:
    if nota >= 8.0: return "✅"
    if nota >= 7.0: return "⚠️ "
    return "❌"

def _delta_icon(d: float) -> str:
    if d > 0.4:  return "⬆⬆"
    if d > 0:    return "⬆ "
    if d == 0:   return "──"
    return "⬇ "

def _barra_score(nota: float, w: int = 20) -> str:
    filled = round(nota / 10 * w)
    return "█" * filled + "░" * (w - filled)


def _render_scores(review: ReviewResult) -> list[str]:
    linhas = []
    linhas.append("  ┌" + "─" * 46 + "┐")
    for dim in DIMENSOES:
        nota  = review.scores.get(dim, 0)
        label = LABELS[dim]
        icon  = _score_icon(nota)
        barra = _barra_score(nota, 14)
        linhas.append(f"  │  {label}  {nota:.1f}  {barra} {icon}  │")
    linhas.append("  │" + " " * 46 + "│")
    st = review.score_total
    st_icon = "✅ APROVADO" if review.aprovado else "❌ REPROVADO"
    linhas.append(f"  │  Score Total: {st:.2f}/10   {st_icon:<18}     │")
    linhas.append("  └" + "─" * 46 + "┘")
    return linhas


def _render_comparativo(historico: list[ReviewResult]) -> list[str]:
    if len(historico) < 2:
        return []
    linhas = []
    linhas.append(_sep("─", _W))
    linhas.append("  COMPARATIVO DE TENTATIVAS")
    linhas.append(_sep("─", _W))

    header = f"  {'Dimensão':<26}"
    for h in historico:
        header += f"  T{h.tentativa}  "
    if len(historico) > 1:
        header += "  Delta"
    linhas.append(header)
    linhas.append("  " + "─" * (_W - 4))

    for dim in DIMENSOES:
        label = LABELS[dim]
        row   = f"  {label}"
        notas = [h.scores.get(dim, 0) for h in historico]
        for n in notas:
            row += f"  {n:.1f} "
        if len(notas) >= 2:
            d    = notas[-1] - notas[0]
            row += f"  {d:+.1f} {_delta_icon(d)}"
        linhas.append(row)

    linhas.append("  " + "─" * (_W - 4))
    scores = [h.score_total for h in historico]
    row    = f"  {'SCORE FINAL':<26}"
    for s in scores:
        row += f"  {s:.2f}"
    if len(scores) >= 2:
        d    = scores[-1] - scores[0]
        row += f"  {d:+.2f} {_delta_icon(d)}"
    linhas.append(row)
    return linhas


def _render_correcoes(melhorias: list, tentativa_dest: int) -> list[str]:
    if not melhorias:
        return []
    linhas = [f"  CORRECOES APLICADAS NA TENTATIVA {tentativa_dest}:"]
    for i, m in enumerate(melhorias[:5], 1):
        # quebra linhas longas para caber no relatório
        words, atual, primeira = m.split(), "", True
        for w in words:
            cand = (atual + " " + w).strip()
            if len(cand) <= _W - 8:
                atual = cand
            else:
                prefix = f"  {i}. " if primeira else "      "
                linhas.append(prefix + atual)
                atual    = w
                primeira = False
        if atual:
            prefix = f"  {i}. " if primeira else "      "
            linhas.append(prefix + atual)
    return linhas


def _render_relatorio(
    variacao:  dict,
    segmento:  str,
    historico: list[ReviewResult],
    layouts:   list[str],
    img_path:  str,
    url:       str,
    melhorias_por_tentativa: list[list],
) -> str:
    ts    = datetime.now().strftime("%d/%m/%Y %H:%M")
    linhas = []

    # ── Cabeçalho ──────────────────────────────────────────
    linhas += [
        "",
        _box_top(),
        _box_row(f"RELATORIO DE PRODUCAO  —  ALINA PRETROV"),
        _box_row(f"DarkCred  |  Segmento: {segmento.upper()}  |  {ts}"),
        _box_bot(),
    ]

    # ── Briefing ───────────────────────────────────────────
    linhas += [
        "",
        _sep("━"),
        "  BRIEFING DO CRIATIVO",
        _sep("━"),
        f"  Hook  : \"{variacao.get('hook', '')}\"",
        f"  Corpo : \"{variacao.get('corpo', variacao.get('body', ''))}\"",
        f"  CTA   : \"{variacao.get('cta', '')}\"",
        "  ✅ Compliance de copy: APROVADO (0 violacoes)",
        "",
    ]

    # ── Tentativas ─────────────────────────────────────────
    for i, review in enumerate(historico):
        t = review.tentativa
        linhas += [
            _sep("━"),
            f"  ETAPA {t}  —  TENTATIVA {t}/{MAX_TENTATIVAS}",
            _sep("━"),
            f"  Layout      : {layouts[i]}",
            f"  Fonte hook  : Montserrat Black {88}px   /   Inter Bold corpo",
            f"  Geracao     : GPT-image-1 quality=high ✓",
        ]
        if i > 0 and melhorias_por_tentativa[i - 1]:
            linhas.append(f"  Melhorias aplicadas: {len(melhorias_por_tentativa[i-1])} correcoes")
        linhas.append("")
        linhas.append("  REVISAO DE ARTE (Claude Vision):")
        linhas += _render_scores(review)
        linhas.append("")
        if review.justificativa:
            # quebra justificativa
            words = review.justificativa.split()
            linha_atual = ""
            for w in words:
                cand = (linha_atual + " " + w).strip()
                if len(cand) <= _W - 4:
                    linha_atual = cand
                else:
                    if linha_atual:
                        linhas.append(f"  {linha_atual}")
                    linha_atual = w
            if linha_atual:
                linhas.append(f"  {linha_atual}")
            linhas.append("")

        if not review.aprovado and review.melhorias and t < MAX_TENTATIVAS:
            linhas += _render_correcoes(review.melhorias, t + 1)
            linhas.append("")

    # ── Comparativo ────────────────────────────────────────
    if len(historico) > 1:
        linhas += [""]
        linhas += _render_comparativo(historico)
        linhas += [""]

    # ── Diagnóstico final ──────────────────────────────────
    final   = historico[-1]
    aprovado = final.aprovado
    linhas += [
        _sep("━"),
        "  RESULTADO FINAL",
        _sep("━"),
        f"  Aprovado em  : {'Tentativa ' + str(final.tentativa) + ' de ' + str(MAX_TENTATIVAS) if aprovado else 'Melhor versao apos ' + str(MAX_TENTATIVAS) + ' tentativas'}",
        f"  Score final  : {final.score_total:.2f}/10",
        f"  Arquivo      : {img_path}",
        "  Upload       : ✅ catbox.moe" if url else "  Upload       : ⚠️  local apenas",
        "",
    ]

    # ── Link em destaque ───────────────────────────────────
    if url:
        linhas += [
            _box_top(),
            _box_row(""),
            _box_row(f"  LINK DO CRIATIVO:"),
            _box_row(f"  {url}"),
            _box_row(""),
            _box_bot(),
            "",
        ]
    else:
        linhas += [
            _sep("─"),
            f"  Arquivo local: {img_path}",
            _sep("─"),
            "",
        ]

    return "\n".join(linhas)


# ─────────────────────────────────────────────────────────────
# Upload
# ─────────────────────────────────────────────────────────────

def _upload_catbox(img_path: str) -> Optional[str]:
    try:
        result = subprocess.run(
            ["curl", "-s", "--max-time", "30",
             "-F", "reqtype=fileupload",
             "-F", f"fileToUpload=@{img_path}",
             "https://catbox.moe/user/api.php"],
            capture_output=True, text=True, timeout=40,
        )
        url = result.stdout.strip()
        return url if url.startswith("https://") else None
    except Exception:
        return None


def _sortear_layout(segmento: str, tentativa: int) -> str:
    preferido    = _LAYOUT_POR_SEGMENTO.get(segmento, "TIPOGRAFIA_FORTE")
    if tentativa == 1:
        return preferido
    alternativas = [l for l in _TODOS_LAYOUTS if l != preferido]
    return alternativas[(tentativa - 2) % len(alternativas)]


# ─────────────────────────────────────────────────────────────
# Ponto de entrada
# ─────────────────────────────────────────────────────────────

def executar_pipeline(
    variacao:  dict,
    segmento:  str  = "generico",
    verbose:   bool = True,
) -> PipelineResult:
    """
    Executa o pipeline completo de criativo com revisão automática.

    Parâmetros:
        variacao — dict com keys: hook, corpo, cta
        segmento — chave do segmento (ex: "padaria", "generico")
        verbose  — imprime progresso no terminal (True por padrão)

    Retorna PipelineResult com img_path, url, review, tentativas, historico.
    Levanta ComplianceError se o copy tiver violações de compliance.
    """
    if verbose:
        print(f"\n{'━'*_W}")
        print("  PIPELINE INICIADO — ALINA PRETROV")
        print(f"{'━'*_W}")

    # ── Etapa 1: Compliance ──────────────────────────────────
    if verbose:
        print("\n  [1/5] Validando compliance do copy...")

    violacoes = validar_variacao(variacao)
    if violacoes:
        if verbose:
            print(f"        BLOQUEADO — {len(violacoes)} violacao(oes)")
            for v in violacoes:
                for r in v.razoes:
                    print(f"        ❌ {r}")
        raise ComplianceError(violacoes)

    if verbose:
        print("        ✅ Copy APROVADO — sem violacoes")

    # Score mínimo adaptativo baseado na experiência acumulada
    score_minimo = _score_minimo_atual()
    if verbose:
        print(f"        Score mínimo de aprovação: {score_minimo:.1f} (adaptativo)")

    # ── Loop de tentativas ───────────────────────────────────
    melhorias_acumuladas: list       = []
    historico:            list       = []
    layouts_usados:       list[str]  = []
    melhorias_hist:       list       = []   # melhorias antes de cada tentativa
    img_path = ""

    for tentativa in range(1, MAX_TENTATIVAS + 1):
        layout = _sortear_layout(segmento, tentativa)
        layouts_usados.append(layout)
        melhorias_hist.append(list(melhorias_acumuladas))

        if verbose:
            retent = f"  (retentativa {tentativa})" if tentativa > 1 else ""
            print(f"\n  [2/5] Layout: {layout}{retent}")
            if melhorias_acumuladas:
                print(f"        Aplicando {len(melhorias_acumuladas)} correcao(oes) da revisao anterior")
            print(f"  [3/5] Gerando com GPT-image-1 quality=high...")

        img_path = gerar_criativo_ia(
            variacao,
            segmento_key=segmento,
            layout=layout,
            melhorias=melhorias_acumuladas,
        )

        if verbose:
            print(f"        Salvo em: {img_path}")
            print(f"  [4/5] Revisando com Claude Vision...")

        review = revisar_criativo(img_path, variacao, segmento, tentativa=tentativa,
                                   score_minimo=score_minimo)
        historico.append(review)

        if verbose:
            icon = "✅ APROVADO" if review.aprovado else "❌ REPROVADO"
            print(f"        Score: {review.score_total:.2f}/10  {icon}")

        if review.aprovado:
            break
        else:
            melhorias_acumuladas = review.melhorias
            if tentativa < MAX_TENTATIVAS and verbose:
                print(f"        Gerando nova versao com {len(melhorias_acumuladas)} correcoes...")
            elif tentativa == MAX_TENTATIVAS and verbose:
                print(f"        {MAX_TENTATIVAS} tentativas esgotadas. Subindo melhor versao.")

    # ── Etapa 5: Upload ──────────────────────────────────────
    if verbose:
        print(f"\n  [5/5] Fazendo upload para catbox.moe...")

    url = _upload_catbox(img_path)

    if verbose and url:
        print(f"        ✅ Upload concluido")

    # ── Relatório de Produção ────────────────────────────────
    relatorio = _render_relatorio(
        variacao, segmento, historico, layouts_usados,
        img_path, url or "", melhorias_hist,
    )

    if verbose:
        print(relatorio)

    final = historico[-1]
    return PipelineResult(
        img_path=img_path,
        url=url or "",
        review=final,
        tentativas=tentativa,
        aprovado=final.aprovado,
        historico=historico,
    )
