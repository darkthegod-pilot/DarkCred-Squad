#!/usr/bin/env python3
"""
Dashboard HTML Auto-atualizado — DarkCred Agency
Lê dados de historico.json e aprendizado.json e gera um painel visual.

Uso:
    python scripts/gerar_dashboard.py
    → Gera saidas/dashboard.html
"""

import json
import sys
from datetime import datetime, timedelta
from pathlib import Path

# Caminhos
ROOT         = Path(__file__).parent.parent
HISTORICO    = ROOT / "dados" / "historico.json"
APRENDIZADO  = ROOT / "dados" / "aprendizado.json"
RESULTADOS   = ROOT / "dados" / "resultados"
SAIDAS       = ROOT / "saidas"
IMAGENS_DIR  = ROOT / "saidas" / "imagens"
DASHBOARD    = ROOT / "saidas" / "dashboard.html"


def _carregar(caminho: Path, padrao):
    if caminho.exists():
        try:
            return json.loads(caminho.read_text(encoding="utf-8"))
        except Exception:
            pass
    return padrao


def _semanas_atras(n: int) -> datetime:
    return datetime.now() - timedelta(weeks=n)


def _filtrar_semana(historico: list, semanas: int = 1) -> list:
    corte = _semanas_atras(semanas).isoformat()
    return [e for e in historico if e.get("data", "") >= corte]


def _gerar_html(historico: list, aprendizado: dict, resultados: list) -> str:
    total_geracoes  = aprendizado.get("total_gerações", 0)
    total_analises  = aprendizado.get("total_analises", 0)
    segmentos_ativos = aprendizado.get("segmentos_ativos", [])
    padroes_venc    = aprendizado.get("padroes_vencedores", [])
    padroes_evitar  = aprendizado.get("padroes_a_evitar", [])
    hooks_perf      = aprendizado.get("hooks_performance", {})
    metricas_hist   = aprendizado.get("metricas_historicas", {})
    ultima_atualizacao = aprendizado.get("ultima_atualizacao") or "—"

    # Gerações da última semana
    semana  = _filtrar_semana(historico, semanas=1)
    n_semana = len(semana)
    aprovados_semana = sum(e.get("aprovados", 0) for e in semana)
    reprovados_semana = sum(e.get("reprovados", 0) for e in semana)

    # Top hooks
    top_hooks = sorted(hooks_perf.items(), key=lambda x: x[1], reverse=True)[:8]
    top_hooks_pos = [(h, s) for h, s in top_hooks if s > 0]
    top_hooks_neg = [(h, s) for h, s in top_hooks if s < 0]

    # Métricas médias
    custo_medio = ""
    ctr_medio = ""
    freq_media = ""
    custos = metricas_hist.get("custo_medio_mensagem", [])
    ctrs   = metricas_hist.get("ctr_medio", [])
    freqs  = metricas_hist.get("frequencia_media", [])
    if custos:
        custo_medio = f"R$ {sum(custos)/len(custos):.2f}"
    if ctrs:
        ctr_medio = f"{sum(ctrs)/len(ctrs):.2f}%"
    if freqs:
        freq_media = f"{sum(freqs)/len(freqs):.1f}"

    # Resultados de campanha (últimos 5)
    resultados_html = ""
    for r in resultados[:5]:
        m = r.get("metricas_extraidas", {})
        data = r.get("data", "—")
        custo = m.get("custo_mensagem")
        ctr   = m.get("ctr")
        freq  = m.get("frequencia")
        diag  = r.get("diagnostico", "")[:120]

        status_custo = ""
        if custo:
            if custo < 1.5:    status_custo = "excelente"
            elif custo < 2.5:  status_custo = "bom"
            elif custo < 3.5:  status_custo = "aceitavel"
            elif custo < 5.0:  status_custo = "ruim"
            else:              status_custo = "pausar"

        resultados_html += f"""
        <tr>
            <td class="td-data">{data[:10]}</td>
            <td class="td-metrica {status_custo}">{f'R$ {custo:.2f}' if custo else '—'}</td>
            <td class="td-metrica">{f'{ctr:.2f}%' if ctr else '—'}</td>
            <td class="td-metrica">{f'{freq:.1f}' if freq else '—'}</td>
            <td class="td-diag">{diag}</td>
        </tr>"""

    # Gerações recentes
    geracoes_html = ""
    for entrada in reversed(historico[-10:]):
        data     = entrada.get("data", "—")[:10]
        seg      = entrada.get("segmento", "—")
        aprov    = entrada.get("aprovados", 0)
        reprov   = entrada.get("reprovados", 0)
        copies   = entrada.get("copies", [])
        hooks    = [c.get("hook", "") for c in copies[:2]]
        hook_txt = " · ".join(f'"{h}"' for h in hooks if h)[:80]

        geracoes_html += f"""
        <tr>
            <td class="td-data">{data}</td>
            <td class="td-seg">{seg}</td>
            <td class="td-aprov">✅ {aprov}</td>
            <td class="td-reprov">{'❌ ' + str(reprov) if reprov else '—'}</td>
            <td class="td-hooks">{hook_txt}</td>
        </tr>"""

    # Hooks chart (barra simples com CSS)
    hooks_chart_html = ""
    max_score = max((s for _, s in top_hooks_pos), default=1) or 1
    for hook, score in top_hooks_pos[:6]:
        pct = int(score / max_score * 100)
        hooks_chart_html += f"""
        <div class="hook-row">
            <div class="hook-label">"{hook[:60]}"</div>
            <div class="hook-bar-wrap">
                <div class="hook-bar" style="width:{pct}%"></div>
                <span class="hook-score">+{score}</span>
            </div>
        </div>"""

    # Segmentos pills
    segs_html = " ".join(f'<span class="seg-pill">{s}</span>' for s in segmentos_ativos)

    ts_gerado = datetime.now().strftime("%d/%m/%Y %H:%M")

    return f"""<!DOCTYPE html>
<html lang="pt-BR">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Dashboard — DarkCred Agency</title>
<style>
  :root {{
    --bg: #0a0705;
    --card: #12100e;
    --card2: #1a1714;
    --amber: #ffaf1e;
    --dourado: #ffcd32;
    --branco: #fff8eb;
    --cinza: #888;
    --verde: #22c55e;
    --amarelo: #facc15;
    --laranja: #f97316;
    --vermelho: #ef4444;
    --roxo: #a855f7;
    --borda: rgba(255,175,30,0.15);
  }}
  * {{ box-sizing: border-box; margin: 0; padding: 0; }}
  body {{
    font-family: 'Inter', 'Segoe UI', system-ui, sans-serif;
    background: var(--bg);
    color: var(--branco);
    min-height: 100vh;
    padding: 24px 16px;
  }}
  .header {{
    border-bottom: 1px solid var(--borda);
    padding-bottom: 16px;
    margin-bottom: 24px;
    display: flex;
    justify-content: space-between;
    align-items: flex-end;
  }}
  .header h1 {{
    font-size: 22px;
    font-weight: 800;
    color: var(--amber);
    letter-spacing: -0.5px;
  }}
  .header .sub {{ font-size: 13px; color: var(--cinza); margin-top: 4px; }}
  .header .ts {{ font-size: 12px; color: var(--cinza); }}
  .grid-kpi {{
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(160px, 1fr));
    gap: 12px;
    margin-bottom: 24px;
  }}
  .kpi {{
    background: var(--card);
    border: 1px solid var(--borda);
    border-radius: 10px;
    padding: 16px;
  }}
  .kpi .label {{ font-size: 11px; color: var(--cinza); text-transform: uppercase;
                  letter-spacing: 0.5px; margin-bottom: 6px; }}
  .kpi .value {{ font-size: 28px; font-weight: 800; color: var(--amber); }}
  .kpi .sub   {{ font-size: 12px; color: var(--cinza); margin-top: 4px; }}
  .kpi.verde .value {{ color: var(--verde); }}
  .kpi.cinza .value {{ color: var(--cinza); }}
  .grid-2 {{ display: grid; grid-template-columns: 1fr 1fr; gap: 16px;
              margin-bottom: 24px; }}
  @media (max-width: 700px) {{ .grid-2 {{ grid-template-columns: 1fr; }} }}
  .card {{
    background: var(--card);
    border: 1px solid var(--borda);
    border-radius: 10px;
    padding: 16px;
  }}
  .card h2 {{
    font-size: 13px; font-weight: 700; text-transform: uppercase;
    letter-spacing: 0.5px; color: var(--amber); margin-bottom: 14px;
  }}
  table {{ width: 100%; border-collapse: collapse; }}
  th {{ font-size: 11px; color: var(--cinza); text-align: left;
        border-bottom: 1px solid var(--borda); padding: 6px 8px; }}
  td {{ font-size: 12px; color: var(--branco); padding: 7px 8px;
        border-bottom: 1px solid rgba(255,255,255,0.04); vertical-align: top; }}
  .td-data  {{ color: var(--cinza); white-space: nowrap; width: 90px; }}
  .td-seg   {{ color: var(--amber); font-weight: 600; }}
  .td-aprov {{ color: var(--verde); }}
  .td-reprov {{ color: var(--vermelho); }}
  .td-hooks {{ color: var(--cinza); font-size: 11px; max-width: 260px; }}
  .td-diag  {{ color: var(--cinza); font-size: 11px; }}
  .td-metrica {{ font-weight: 700; }}
  .td-metrica.excelente {{ color: var(--verde); }}
  .td-metrica.bom       {{ color: var(--amarelo); }}
  .td-metrica.aceitavel {{ color: var(--laranja); }}
  .td-metrica.ruim      {{ color: var(--vermelho); }}
  .td-metrica.pausar    {{ color: var(--vermelho); font-weight: 900; }}
  .hook-row {{ margin-bottom: 10px; }}
  .hook-label {{ font-size: 12px; color: var(--cinza); margin-bottom: 4px;
                  white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }}
  .hook-bar-wrap {{ display: flex; align-items: center; gap: 8px; }}
  .hook-bar {{ height: 8px; background: var(--amber); border-radius: 4px;
                min-width: 4px; transition: width 0.3s; }}
  .hook-score {{ font-size: 11px; color: var(--verde); font-weight: 700; }}
  .padrao-list {{ list-style: none; }}
  .padrao-list li {{ font-size: 12px; color: var(--cinza); padding: 5px 0;
                      border-bottom: 1px solid rgba(255,255,255,0.04); }}
  .padrao-list li::before {{ content: "✅ "; }}
  .padrao-list.neg li::before {{ content: "❌ "; }}
  .seg-pill {{
    display: inline-block; background: var(--card2); border: 1px solid var(--borda);
    border-radius: 999px; padding: 3px 10px; font-size: 11px; color: var(--amber);
    margin: 3px;
  }}
  .empty {{ color: var(--cinza); font-size: 13px; text-align: center; padding: 24px; }}
  .footer {{ margin-top: 32px; text-align: center; font-size: 11px; color: var(--cinza); }}
</style>
</head>
<body>

<div class="header">
  <div>
    <h1>DarkCred Agency Dashboard</h1>
    <div class="sub">Alina Pretrov · Vera · Dasha · Mila · Igor</div>
  </div>
  <div class="ts">Atualizado: {ts_gerado}</div>
</div>

<!-- KPIs -->
<div class="grid-kpi">
  <div class="kpi">
    <div class="label">Gerações totais</div>
    <div class="value">{total_geracoes}</div>
    <div class="sub">{n_semana} esta semana</div>
  </div>
  <div class="kpi verde">
    <div class="label">Aprovados (semana)</div>
    <div class="value">{aprovados_semana}</div>
    <div class="sub">{reprovados_semana} reprovados</div>
  </div>
  <div class="kpi">
    <div class="label">Campanhas analisadas</div>
    <div class="value">{total_analises}</div>
    <div class="sub">resultados com Mila</div>
  </div>
  <div class="kpi">
    <div class="label">Custo médio/msg</div>
    <div class="value" style="font-size:22px">{custo_medio or '—'}</div>
    <div class="sub">CTR: {ctr_medio or '—'}</div>
  </div>
  <div class="kpi cinza">
    <div class="label">Frequência média</div>
    <div class="value" style="font-size:22px">{freq_media or '—'}</div>
    <div class="sub">Saturação: &gt;2.5</div>
  </div>
  <div class="kpi">
    <div class="label">Segmentos ativos</div>
    <div class="value">{len(segmentos_ativos)}</div>
    <div class="sub">de 35+ disponíveis</div>
  </div>
</div>

<!-- Gerações + Resultados -->
<div class="grid-2">
  <div class="card">
    <h2>📋 Últimas Gerações</h2>
    {'<div class="empty">Nenhuma geração registrada ainda.</div>' if not historico else f'''
    <table>
      <thead><tr>
        <th>Data</th><th>Segmento</th><th>Aprov.</th><th>Rep.</th><th>Hooks</th>
      </tr></thead>
      <tbody>{geracoes_html}</tbody>
    </table>'''}
  </div>
  <div class="card">
    <h2>📊 Resultados de Campanha (Mila)</h2>
    {'<div class="empty">Nenhuma análise de campanha ainda.<br>Use /analise-resultado para adicionar.</div>' if not resultados else f'''
    <table>
      <thead><tr>
        <th>Data</th><th>Custo/msg</th><th>CTR</th><th>Freq.</th><th>Diagnóstico</th>
      </tr></thead>
      <tbody>{resultados_html}</tbody>
    </table>'''}
  </div>
</div>

<!-- Hooks + Padrões -->
<div class="grid-2">
  <div class="card">
    <h2>⭐ Hooks com Melhor Histórico</h2>
    {'<div class="empty">Nenhum hook registrado ainda.</div>' if not top_hooks_pos else hooks_chart_html}
  </div>
  <div class="card">
    <h2>💡 Padrões de Aprendizado</h2>
    {'<div class="empty">Gere copies e analise campanhas para acumular padrões.</div>' if not padroes_venc and not padroes_evitar else f'''
    <p style="font-size:11px;color:var(--cinza);margin-bottom:8px;">VENCEDORES</p>
    <ul class="padrao-list">
      {''.join(f'<li>{p}</li>' for p in padroes_venc[:5]) or '<li style="color:var(--cinza)">Nenhum ainda</li>'}
    </ul>
    <p style="font-size:11px;color:var(--cinza);margin:12px 0 8px;">A EVITAR</p>
    <ul class="padrao-list neg">
      {''.join(f'<li>{p}</li>' for p in padroes_evitar[:3]) or '<li style="color:var(--cinza)">Nenhum ainda</li>'}
    </ul>
    '''}
  </div>
</div>

<!-- Segmentos ativos -->
<div class="card" style="margin-bottom:24px">
  <h2>🗂 Segmentos Usados</h2>
  <div style="margin-top:8px">
    {segs_html or '<span style="color:var(--cinza);font-size:13px">Nenhum segmento usado ainda.</span>'}
  </div>
</div>

<div class="footer">
  DarkCred Agency · Sistema gerado automaticamente por scripts/gerar_dashboard.py
  · Última atualização: {ts_gerado}
</div>

</body>
</html>"""


def main():
    SAIDAS.mkdir(parents=True, exist_ok=True)

    historico   = _carregar(HISTORICO, [])
    aprendizado = _carregar(APRENDIZADO, {})

    # Carrega resultados de campanha
    resultados = []
    if RESULTADOS.exists():
        for arq in sorted(RESULTADOS.glob("resultado_*.json"), reverse=True)[:10]:
            try:
                resultados.append(json.loads(arq.read_text(encoding="utf-8")))
            except Exception:
                pass

    html = _gerar_html(historico, aprendizado, resultados)
    DASHBOARD.write_text(html, encoding="utf-8")

    print(f"✅ Dashboard gerado: {DASHBOARD}")
    print(f"   Gerações: {aprendizado.get('total_gerações', 0)} | "
          f"Análises: {aprendizado.get('total_analises', 0)} | "
          f"Segmentos: {len(aprendizado.get('segmentos_ativos', []))}")


if __name__ == "__main__":
    main()
