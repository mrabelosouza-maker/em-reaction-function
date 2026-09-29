"""Template do site. Só formatação: toda a lógica está em board.py/build.py."""
from __future__ import annotations

import json

TEMPLATE = r"""<!doctype html>
<html lang="pt-BR"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>EM Reaction Functions</title>
<script src="https://cdn.plot.ly/plotly-2.35.2.min.js"></script>
<style>
:root{--bg:#faf8f3;--fg:#1d1d1b;--muted:#6b6b66;--card:#fff;--line:#e3dfd5;--hawk:#b2182b;--dove:#2166ac;--accent:#1f5f3f}
@media (prefers-color-scheme:dark){:root{--bg:#141414;--fg:#eee;--muted:#9a9a95;--card:#1e1e1e;--line:#333;--accent:#6fbf8f}}
body{margin:0;background:var(--bg);color:var(--fg);font:15px/1.5 system-ui,-apple-system,Segoe UI,sans-serif}
header{padding:16px;border-bottom:1px solid var(--line)}header h1{margin:0;font-size:20px}header p{margin:4px 0 0;color:var(--muted);font-size:13px}
nav{display:flex;gap:4px;padding:8px 16px;border-bottom:1px solid var(--line);position:sticky;top:0;background:var(--bg);z-index:5;overflow-x:auto}
nav button{border:1px solid var(--line);background:var(--card);color:var(--fg);padding:6px 14px;border-radius:999px;cursor:pointer}
nav button.on{background:var(--accent);color:#fff;border-color:var(--accent)}
main{max-width:1100px;margin:0 auto;padding:16px}section.tab{display:none}section.tab.on{display:block}
h2{font-size:17px;margin:28px 0 8px}.kpis{display:grid;grid-template-columns:repeat(auto-fit,minmax(160px,1fr));gap:10px}
.kpi,.card{background:var(--card);border:1px solid var(--line);border-radius:8px;padding:12px}
.kpi b{display:block;font-size:22px}.kpi span{color:var(--muted);font-size:12px}
.cards{display:grid;grid-template-columns:repeat(auto-fit,minmax(230px,1fr));gap:10px}
.card q{display:block;color:var(--muted);font-size:13px;margin-top:6px}.tag{font-size:11px;border:1px solid var(--line);border-radius:4px;padding:0 5px;margin-left:4px}
.pos{color:var(--hawk)}.neg{color:var(--dove)}.chart{background:var(--card);border:1px solid var(--line);border-radius:8px;min-height:360px}
.filters{display:flex;gap:8px;flex-wrap:wrap;margin-bottom:8px}.filters input,.filters select{padding:6px;border:1px solid var(--line);border-radius:6px;background:var(--card);color:var(--fg)}
details{background:var(--card);border:1px solid var(--line);border-radius:8px;padding:8px 12px;margin-bottom:6px}
details pre{white-space:pre-wrap;font-size:13px;line-height:1.45;font-family:inherit;max-height:420px;overflow:auto}
</style></head><body>
<header><h1>EM Reaction Functions</h1><p>Escala hawk-dove de comunicação de BCs emergentes · colegiado × membros · gerado em __GENERATED__</p></header>
<nav id="nav"></nav><main id="main"></main>
<script id="data" type="application/json">__DATA__</script>
<script>
const DATA = JSON.parse(document.getElementById('data').textContent);
const DOC = {comunicado:'Comunicado', ata:'Ata', rti:'RTI', fala_publica:'Fala pública', call_privado:'Call privado'};
const SYM = {comunicado:'circle', ata:'square', rti:'triangle-up'};
const ACT = {cut:'corte', hold:'manutenção', hike:'alta'};
const fmt = v => v == null ? '—' : (v > 0 ? '+' : '') + v.toFixed(1);
const cls = v => v == null ? '' : v > 0 ? 'pos' : v < 0 ? 'neg' : '';
const esc = s => String(s ?? '').replace(/[&<>"]/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]));
const dark = matchMedia('(prefers-color-scheme: dark)').matches;
const LAYOUT = {paper_bgcolor:'rgba(0,0,0,0)', plot_bgcolor:'rgba(0,0,0,0)', font:{color: dark ? '#eee' : '#1d1d1b'},
  margin:{l:50, r:20, t:20, b:40}, legend:{orientation:'h', y:-0.15}};

function kpiHtml(k) {
  return `<div class="kpis">
    <div class="kpi"><span>Taxa</span><b>${esc(k.rate ?? '—')}</b><span>${esc(ACT[k.action] ?? '')} em ${esc(k.meeting_date ?? '')}</span></div>
    <div class="kpi"><span>Votação</span><b>${esc(k.vote ?? '—')}</b><span>${esc((k.dissents || []).join('; '))}</span></div>
    <div class="kpi"><span>Nível do Board</span><b class="${cls(k.board_level)}">${fmt(k.board_level)}</b><span>${esc(DOC[k.last_doc_type] ?? '')} de ${esc(k.last_doc_date ?? '')}</span></div>
    <div class="kpi"><span>Δ vs documento anterior</span><b class="${cls(k.board_delta)}">${fmt(k.board_delta)}</b></div></div>`;
}

function boardChart(el, b) {
  const traces = [{x: b.series.map(p => p.date), y: b.series.map(p => p.level), name: 'Board',
    mode: 'lines', line: {shape: 'hv', width: 3, color: '#1f5f3f'}, hoverinfo: 'skip'}];
  for (const t of [...new Set(b.series.map(p => p.doc_type))]) {
    const ps = b.series.filter(p => p.doc_type === t);
    traces.push({x: ps.map(p => p.date), y: ps.map(p => p.level), name: DOC[t] || t, mode: 'markers',
      marker: {size: 10, symbol: SYM[t] || 'circle', color: '#1f5f3f'},
      text: ps.map(p => DOC[p.doc_type] + ' (reunião ' + p.meeting_date + ')'), hovertemplate: '%{text}<br>%{y:+.1f}<extra>Board</extra>'});
  }
  for (const m of b.members) {
    const ps = b.points.filter(p => p.member_id === m.member_id);
    if (!ps.length) continue;
    traces.push({x: ps.map(p => p.date), y: ps.map(p => p.composite), name: m.name, mode: 'markers',
      marker: {size: 9, symbol: ps.map(p => p.doc_type === 'call_privado' ? 'diamond' : 'circle-open')},
      text: ps.map(p => DOC[p.doc_type] + ' · desvio ' + fmt(p.deviation)), hovertemplate: '%{text}<br>%{y:+.1f}<extra>' + esc(m.name) + '</extra>'});
  }
  Plotly.newPlot(el, traces, {...LAYOUT, yaxis: {range: [-5, 5], zeroline: true, title: 'dove ← → hawk'}}, {responsive: true, displayModeBar: false});
}

function heatChart(el, b, mode) {
  const h = b.heatmap, dev = mode === 'deviation';
  const rows = [...(dev ? [] : ['Board']), ...b.members.map(m => m.name)];
  const z = [...(dev ? [] : [h.board]), ...b.members.map(m => (dev ? h.deviation : h.level)[m.member_id])];
  const lim = mode === 'deviation' ? 3 : 5;
  Plotly.newPlot(el, [{type: 'heatmap', x: h.columns, y: rows, z, zmin: -lim, zmax: lim,
    colorscale: [[0, '#2166ac'], [0.5, '#f7f7f7'], [1, '#b2182b']], hoverongaps: false,
    text: z.map(r => r.map(fmt)), texttemplate: '%{text}', hovertemplate: '%{y} · ciclo %{x}<br>%{text}<extra></extra>'}],
    {...LAYOUT, yaxis: {autorange: 'reversed'}, xaxis: {type: 'category'}}, {responsive: true, displayModeBar: false});
}

function cardsHtml(b) {
  return '<div class="cards">' + b.cards.map(c => `<div class="card"><b>${esc(c.name)}</b> <span class="tag">${esc(c.role)}</span><br>
    ${c.latest == null ? '<span style="color:var(--muted)">sem falas na base</span>' :
    `<span class="${cls(c.latest)}">${fmt(c.latest)}</span> · Δ ${fmt(c.delta)} · desvio vs Board <span class="${cls(c.deviation)}">${fmt(c.deviation)}</span>
     <span class="tag">${esc(DOC[c.doc_type])}</span> <span class="tag">${esc(c.date)}</span><q>${esc(c.quote)}</q>`}</div>`).join('') + '</div>';
}

function docsHtml(bc) {
  return `<div class="filters"><input id="q-${bc}" placeholder="buscar"><select id="t-${bc}"><option value="">todos os tipos</option>
    ${[...new Set(DATA.bcs[bc].docs.map(d => d.doc_type))].map(k => `<option value="${k}">${esc(DOC[k] || k)}</option>`).join('')}</select>
    <select id="tr-${bc}"><option value="">todas as trilhas</option><option value="colegiado">Colegiado</option><option value="membro">Membros</option></select></div><div id="list-${bc}"></div>`;
}

function renderDocs(bc) {
  const q = document.getElementById('q-' + bc).value.toLowerCase(), t = document.getElementById('t-' + bc).value,
    tr = document.getElementById('tr-' + bc).value;
  const docs = DATA.bcs[bc].docs.filter(d => (!t || d.doc_type === t) && (!tr || d.track === tr) &&
    (!q || (d.title + d.summary + d.text + d.member_id).toLowerCase().includes(q))).reverse();
  document.getElementById('list-' + bc).innerHTML = docs.map(d => `<details><summary>${esc(d.date)} · ${esc(DOC[d.doc_type])} ·
    ${esc(d.member_id === 'board' ? 'Board' : d.member_id)} · <b class="${cls(d.llm_scores.composite_hawk_dove)}">${fmt(d.llm_scores.composite_hawk_dove)}</b> — ${esc(d.title)}</summary>
    <p>${esc(d.summary)}</p><ul>${d.key_quotes.map(q => `<li><i>${esc(q.quote)}</i></li>`).join('')}</ul>
    ${/^https?:\/\//.test(d.url || '') ? `<p><a href="${esc(d.url)}" target="_blank" rel="noopener">fonte</a></p>` : ''}<pre>${esc(d.text)}</pre></details>`).join('');
}

const METODO = `<h2>Metodologia</h2>
<p><b>Rubrica.</b> Cada documento é classificado por um modelo de linguagem na rubrica 1.0-generic (projeto de reaction functions do FOMC, drivers adaptados a EMs): composto hawk-dove em [−5, +5] (positivo = hawk), peso no mandato de preços, convicção sobre inflação, preocupação com atividade, leitura do stance, viés de curto prazo e seis drivers. Dimensão não tratada no texto fica em branco, nunca zero.</p>
<p><b>Duas trilhas.</b> <i>Colegiado</i> (comunicado e ata) é a voz oficial da Junta. <i>Membros</i> (falas públicas e calls privados) é a voz individual.</p>
<p><b>Série do Board.</b> Degrau: o nível em cada data é o composto do último documento colegiado publicado até ali (comunicado ou ata). Documento sem composto não move o degrau. <b>Ressalva:</b> comunicado e ata são gêneros diferentes — a ata é mais longa e explicita divisões —, então parte do salto comunicado→ata pode ser gênero, não mudança de postura. O marcador (● comunicado, ■ ata) permite separar.</p>
<p><b>Desvio do membro.</b> Composto da fala ou call menos o nível do Board vigente na data dela.</p>
<p><b>Heatmap.</b> Cada coluna é um ciclo entre duas reuniões. Board = nível no fim do ciclo (já com a ata). Membro = média das falas no ciclo; no modo desvio, média dos desvios.</p>
<p><b>Calibração.</b> Os scores são inteiros ou terminam em .5. A escala lê o que o documento pede da política, não o quanto ele reclama da inflação. Régua para comunicados do Banxico, usada como ordem de grandeza: corte grande ou aceleração do ritmo (ex.: 50 bp) sinalizando novos cortes de magnitude similar −3; corte grande sem sinalizar repetição, ou corte de 25 bp com guidance claro de continuidade e maioria folgada −2 a −2,5; corte com porta aberta a mais cortes e maioria dividida −1,5; corte sinalizado como último ou pausa à frente −0,5; manutenção neutra, dependente de dados 0; manutenção com balanço de riscos inclinado para cima e ênfase na inflação +0,5; alta ou viés explícito de alta +2 ou mais. A régua foi calibrada no próprio Banxico 2025–26 e está sujeita a revisão. Diferenças de 0,5 são ruído: confie no ranking e na direção da mudança.</p>
<p><b>Escopo.</b> Banxico, comunicados e atas desde janeiro de 2025; as datas do primeiro e do último documento de cada BC aparecem abaixo dos indicadores da aba. Outros BCs, RTIs e histórico de calls entram depois.</p>`;

function renderBC(bc, sec) {
  const b = DATA.bcs[bc];
  const cv = b.coverage;
  sec.innerHTML = kpiHtml(b.kpis) + (cv ? `<p style="color:var(--muted);font-size:13px">Datas cobertas: ${esc(cv.first)} a ${esc(cv.last)} · ${esc(cv.n_docs)} documentos</p>` : '') + `<h2>Board e membros</h2><div class="chart" id="bchart-${bc}"></div>
    <h2>Heatmap <select id="hm-${bc}"><option value="level">nível</option><option value="deviation">desvio vs Board</option></select></h2>
    <div class="chart" id="hchart-${bc}"></div><h2>Membros</h2>${cardsHtml(b)}<h2>Base de documentos</h2>${docsHtml(bc)}`;
  boardChart(document.getElementById('bchart-' + bc), b);
  const hm = document.getElementById('hm-' + bc);
  const drawHm = () => heatChart(document.getElementById('hchart-' + bc), b, hm.value);
  hm.onchange = drawHm; drawHm();
  document.getElementById('q-' + bc).oninput = () => renderDocs(bc);
  document.getElementById('t-' + bc).onchange = () => renderDocs(bc);
  document.getElementById('tr-' + bc).onchange = () => renderDocs(bc);
  renderDocs(bc);
}

const nav = document.getElementById('nav'), main = document.getElementById('main');
const tabs = [...Object.keys(DATA.bcs).map(bc => [bc, DATA.bcs[bc].label]), ['metodologia', 'Metodologia']];
const rendered = {};
function show(id) {
  for (const [k] of tabs) {
    document.getElementById('tab-' + k).classList.toggle('on', k === id);
    document.getElementById('btn-' + k).classList.toggle('on', k === id);
  }
  if (id !== 'metodologia' && !rendered[id]) { renderBC(id, document.getElementById('tab-' + id)); rendered[id] = true; }
  history.replaceState(null, '', '#' + id);
}
for (const [k, label] of tabs) {
  nav.insertAdjacentHTML('beforeend', `<button id="btn-${k}">${esc(label)}</button>`);
  main.insertAdjacentHTML('beforeend', `<section class="tab" id="tab-${k}">${k === 'metodologia' ? METODO : ''}</section>`);
  document.getElementById('btn-' + k).onclick = () => show(k);
}
show(tabs.some(([k]) => k === location.hash.slice(1)) ? location.hash.slice(1) : tabs[0][0]);
</script></body></html>
"""


def render(payload: dict, generated: str) -> str:
    blob = json.dumps(payload, ensure_ascii=False).replace("<", "\\u003c")
    return TEMPLATE.replace("__GENERATED__", generated).replace("__DATA__", blob)
