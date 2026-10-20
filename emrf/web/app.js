/* =====================================================================
   EM Reaction Functions — app (monta as abas a partir do payload, desenha
   o gráfico, o heatmap em tabela, os cards e a base de documentos).
   Depende de chrome.js (JGPChrome) e plotly-jgp.js (card, baseLayout, theme,
   H_FULL, CFG, cssv), inlinados antes deste arquivo.
   Toda string vinda dos documentos passa por esc(); links só http(s).
   ===================================================================== */
const DATA = JSON.parse(document.getElementById('data').textContent);
const GENERATED = document.body.dataset.generated;
const DOC = {comunicado: 'Comunicado', ata: 'Ata', rti: 'RTI', fala_publica: 'Fala pública', call_privado: 'Call privado'};
const SYM = {comunicado: 'circle', ata: 'square', rti: 'triangle-up'};
const ACT = {cut: 'Corte', hold: 'Manutenção', hike: 'Alta'};
const MESES = ['jan', 'fev', 'mar', 'abr', 'mai', 'jun', 'jul', 'ago', 'set', 'out', 'nov', 'dez'];
const MEMBER_COLORS = ['--s4', '--d3', '--d2', '--s3', '--d1'];   // azul, laranja, azul-claro, cinza, verde-claro

const esc = s => String(s ?? '').replace(/[&<>"']/g, c => ({'&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;'}[c]));
const fmt = v => v == null ? '—' : (v > 0 ? '+' : v < 0 ? '−' : '') + Math.abs(v).toFixed(1).replace('.', ',');
const pct = v => v == null ? '—' : v.toFixed(2).replace('.', ',') + '%';
const dBR = s => s ? s.slice(8, 10) + '/' + s.slice(5, 7) + '/' + s.slice(0, 4) : '—';
const mmmaa = s => MESES[+s.slice(5, 7) - 1] + '/' + s.slice(2, 4);
const cls = v => v == null ? '' : v > 0 ? 'hawk' : v < 0 ? 'dove' : '';
const who = (b, id) => id === 'board' ? 'Junta' : ((b.members.find(m => m.member_id === id) || {}).name || id);
const addDays = (s, n) => { const d = new Date(s + 'T00:00:00Z'); d.setUTCDate(d.getUTCDate() + n); return d.toISOString().slice(0, 10); };

Plotly.register({moduleType: 'locale', name: 'pt-BR', dictionary: {}, format: {
  days: ['domingo', 'segunda', 'terça', 'quarta', 'quinta', 'sexta', 'sábado'],
  shortDays: ['dom', 'seg', 'ter', 'qua', 'qui', 'sex', 'sáb'],
  months: ['janeiro', 'fevereiro', 'março', 'abril', 'maio', 'junho', 'julho', 'agosto', 'setembro', 'outubro', 'novembro', 'dezembro'],
  shortMonths: MESES, date: '%d/%m/%Y', decimal: ',', thousands: '.'}});

/* ---------- 01 Visão geral ---------- */
function kpiHtml(b) {
  const k = b.kpis, r = b.rates.length ? b.rates[b.rates.length - 1].rate : null;
  const dis = (k.dissents || []).length ? 'Dissidência: ' + esc(k.dissents.join('; ')) : 'Decisão unânime';
  return `<div class="kpis">
    <div class="kpi"><div class="k">Taxa de referência</div><div class="v">${pct(r)}</div>
      <div class="d">${esc(ACT[k.action] || '')} em ${dBR(k.meeting_date)}</div></div>
    <div class="kpi"><div class="k">Última decisão · placar</div><div class="v">${esc(ACT[k.action] || '—')} · ${esc(k.vote || '—')}</div>
      <div class="d">${dis}</div></div>
    <div class="kpi"><div class="k">Nível da Junta</div><div class="v ${cls(k.board_level)}">${fmt(k.board_level)}</div>
      <div class="d">${esc(DOC[k.last_doc_type] || '')} de ${dBR(k.last_doc_date)} · escala −5 dove · +5 hawk</div></div>
    <div class="kpi"><div class="k">Δ vs documento anterior</div><div class="v ${cls(k.board_delta)}">${fmt(k.board_delta)}</div>
      <div class="d">variação do nível da Junta</div></div></div>`;
}

/* ---------- 02 Tom da Junta e taxa de juros ---------- */
function boardChart(host, bc) {
  const b = DATA.bcs[bc], t = theme(), s = b.series, rt = b.rates, gen = GENERATED;
  const rub = [...new Set(b.docs.map(d => d.rubric_version))].join(', ');
  const plot = card(host, b.headline, {
    sub: 'Escala hawk-dove da comunicação (−5 dove · +5 hawk). Degrau = último comunicado ou ata publicado. Taxa de referência no eixo direito.',
    fonte: `Fonte: ${b.fonte}; classificação própria (rubrica ${rub}).`,
    series: [{x: s.map(p => p.date), y: s.map(p => p.level)}]});
  plot.parentNode.classList.add('hero');
  const green = cssv('--s1'), black = cssv('--s2'), surf = cssv('--surface');
  const traces = [];
  if (rt.length) {
    traces.push({x: [...rt.map(p => p.date), gen], y: [...rt.map(p => p.rate), rt[rt.length - 1].rate],
      yaxis: 'y2', name: 'Taxa de referência (dir.)', type: 'scatter', mode: 'lines',
      line: {shape: 'hv', width: 2, color: black},
      text: [...rt.map(p => 'Comunicado · ' + dBR(p.date)), 'Vigente em ' + dBR(gen)],
      hovertemplate: '<b>Taxa de referência</b><br>%{text}<br>%{y:.2f}%<extra></extra>'});
  }
  traces.push({x: [...s.map(p => p.date), gen], y: [...s.map(p => p.level), s[s.length - 1].level],
    name: 'Junta (nível vigente)', type: 'scatter', mode: 'lines', line: {shape: 'hv', width: 3.5, color: green},
    hoverinfo: 'skip'});
  for (const dt of [...new Set(s.map(p => p.doc_type))]) {
    const ps = s.filter(p => p.doc_type === dt);
    traces.push({x: ps.map(p => p.date), y: ps.map(p => p.level), name: DOC[dt] || dt, type: 'scatter', mode: 'markers',
      marker: {size: dt === 'ata' ? 8 : 10, symbol: SYM[dt] || 'circle', color: green, line: {width: 1.5, color: surf}},
      text: ps.map(p => `<b>${DOC[p.doc_type] || p.doc_type}</b> · ${dBR(p.date)}<br>reunião de ${dBR(p.meeting_date)}<br>Nível: ${fmt(p.level)}`),
      hovertemplate: '%{text}<extra></extra>'});
  }
  b.members.forEach((m, i) => {
    const ps = b.points.filter(p => p.member_id === m.member_id);
    if (!ps.length) return;
    const c = cssv(MEMBER_COLORS[i % MEMBER_COLORS.length]);
    traces.push({x: ps.map(p => p.date), y: ps.map(p => p.composite), name: m.name, type: 'scatter', mode: 'markers',
      marker: {size: 10, color: c, symbol: ps.map(p => p.doc_type === 'call_privado' ? 'diamond' : 'circle'), line: {width: 1, color: surf}},
      text: ps.map(p => `<b>${esc(m.name)}</b> · ${DOC[p.doc_type]} · ${dBR(p.date)}<br>Nível: ${fmt(p.composite)} · desvio vs Junta ${fmt(p.deviation)}`),
      hovertemplate: '%{text}<extra></extra>'});
  });
  const band = (y0, y1, c) => ({type: 'rect', xref: 'paper', yref: 'y', x0: 0, x1: 1, y0, y1,
    fillcolor: c, opacity: 0.05, line: {width: 0}, layer: 'below'});
  const lastLvl = s[s.length - 1].level;
  const ann = [{x: gen, y: lastLvl, xref: 'x', yref: 'y', xanchor: 'left', xshift: 6, showarrow: false,
    text: '<b>' + fmt(lastLvl) + '</b>', font: {size: 12, color: green}}];
  let y2 = null;
  if (rt.length) {
    const lo = Math.min(...rt.map(p => p.rate)), hi = Math.max(...rt.map(p => p.rate));
    y2 = [Math.floor(lo) - 1, Math.ceil(hi) + 1];
    ann.push({x: gen, y: rt[rt.length - 1].rate, xref: 'x', yref: 'y2', xanchor: 'left', xshift: 6,
      showarrow: false, text: '<b>' + pct(rt[rt.length - 1].rate) + '</b>', font: {size: 12, color: black}});
  }
  const ticks = [-5, -4, -3, -2, -1, 0, 1, 2, 3, 4, 5];
  const layout = baseLayout(t, {
    height: H_FULL(), hovermode: 'closest', margin: {l: 76, r: 56, t: 34, b: 34},
    shapes: [band(0, 5.4, cssv('--hawk')), band(-5.4, 0, cssv('--dove')),
      {type: 'line', xref: 'paper', yref: 'y', x0: 0, x1: 1, y0: 0, y1: 0, line: {color: t.zero, width: 1}, layer: 'below'}],
    annotations: ann,
    xaxis: {type: 'date', range: [addDays(s[0].date, -20), addDays(gen, 40)], tickformat: '%b/%y'},
    yaxis: {range: [-5.4, 5.4], tickvals: ticks, ticktext: ticks.map(v => v === -5 ? 'dove −5' : v === 5 ? 'hawk +5' : fmt(v).replace(',0', '')),
      fixedrange: true},
    yaxis2: y2 ? {overlaying: 'y', side: 'right', range: y2, ticksuffix: '%', showgrid: false, fixedrange: true} : undefined,
  });
  Plotly.newPlot(plot, traces, layout, Object.assign({}, CFG, {locale: 'pt-BR'}));
}

/* ---------- 03 Heatmap por reunião (tabela) ---------- */
function heatHtml(b, mode) {
  const h = b.heatmap, dev = mode === 'deviation', lim = dev ? 3 : 5;
  const rows = [...(dev ? [] : [['Junta (Board)', h.board, true]]),
    ...b.members.map(m => [m.name, (dev ? h.deviation : h.level)[m.member_id] || [], false])];
  const cell = v => v == null ? '<td class="nd">—</td>'
    : `<td class="hm" style="--c:var(--${v > 0 ? 'hawk' : 'dove'});--w:${Math.round(Math.min(1, Math.abs(v) / lim) * 62)}%">${fmt(v)}</td>`;
  return `<table class="heat"><thead><tr><th class="lbl left">${dev ? 'Desvio vs Junta' : 'Nível médio no ciclo'}</th>
    ${h.columns.map(c => `<th title="Reunião de ${dBR(c)}">${mmmaa(c)}</th>`).join('')}</tr></thead><tbody>
    ${rows.map(([name, vals, isB]) => `<tr${isB ? ' class="board"' : ''}><td class="lbl">${esc(name)}</td>${h.columns.map((_, i) => cell(vals[i])).join('')}</tr>`).join('')}
    </tbody></table>`;
}

/* ---------- 04 Membros ---------- */
function cardsHtml(b) {
  return '<div class="mcards">' + b.cards.map(c => `<div class="card mcard"><h3>${esc(c.name)}</h3><p class="csub">${esc(c.role)}</p>` +
    (c.latest == null ? '<p class="sub">Sem falas ou calls na base.</p>' :
      `<div class="mrow"><span class="big ${cls(c.latest)}">${fmt(c.latest)}</span><span>Δ ${fmt(c.delta)}</span>
        <span>desvio vs Junta <b class="${cls(c.deviation)}">${fmt(c.deviation)}</b></span></div>
       <p class="csub"><span class="tagx ${c.doc_type === 'call_privado' ? 'priv' : 'pub'}">${esc(DOC[c.doc_type] || c.doc_type)}</span>${dBR(c.date)}</p>
       ${c.quote ? `<blockquote>${esc(c.quote)}</blockquote>` : ''}`) + '</div>').join('') + '</div>';
}

/* ---------- 05 Base de documentos (altura fixa) ---------- */
function docsHtml(bc) {
  const b = DATA.bcs[bc];
  return `<div class="docbase"><div class="filters">
    <input type="search" id="q-${bc}" placeholder="Buscar no título, resumo ou texto…" aria-label="Buscar">
    <select id="tr-${bc}" aria-label="Trilha"><option value="">Todas as trilhas</option><option value="colegiado">Colegiado</option><option value="membro">Membros</option></select>
    <select id="t-${bc}" aria-label="Tipo"><option value="">Todos os tipos</option>
      ${[...new Set(b.docs.map(d => d.doc_type))].map(k => `<option value="${esc(k)}">${esc(DOC[k] || k)}</option>`).join('')}</select>
    <span class="count" id="n-${bc}"></span></div><div id="list-${bc}"></div></div>`;
}

function renderDocs(bc) {
  const b = DATA.bcs[bc];
  const q = document.getElementById('q-' + bc).value.toLowerCase(), t = document.getElementById('t-' + bc).value,
    tr = document.getElementById('tr-' + bc).value;
  const docs = b.docs.map((d, i) => [d, i]).filter(([d]) => (!t || d.doc_type === t) && (!tr || d.track === tr) &&
    (!q || (d.title + ' ' + d.summary + ' ' + d.text + ' ' + d.member_id).toLowerCase().includes(q)))
    .sort((a, c) => c[0].date.localeCompare(a[0].date));
  document.getElementById('n-' + bc).textContent = docs.length + ' de ' + b.docs.length + ' documentos';
  document.getElementById('list-' + bc).innerHTML = docs.length ? docs.map(([d, i]) => {
    const sc = d.llm_scores.composite_hawk_dove;
    return `<details class="doc" data-i="${i}"><summary><span class="dd">${dBR(d.date)}</span><span class="tp">${esc(DOC[d.doc_type] || d.doc_type)}</span>
      <span class="who">${esc(who(b, d.member_id))}</span><span class="sc ${cls(sc)}">${fmt(sc)}</span><span class="ti">${esc(d.title)}</span></summary>
      <div class="body"><p>${esc(d.summary)}</p>${d.key_quotes.length ? `<ul>${d.key_quotes.map(k => `<li><i>${esc(k.quote)}</i></li>`).join('')}</ul>` : ''}
      ${/^https?:\/\//i.test(d.url || '') ? `<p><a href="${esc(d.url)}" target="_blank" rel="noopener">Fonte original ↗</a></p>` : ''}<pre></pre></div></details>`;
  }).join('') : '<div class="empty">Nenhum documento com esses filtros.</div>';
}

/* ---------- aba do BC ---------- */
function bcPane(bc) {
  const b = DATA.bcs[bc];
  const top = `<h2>Visão geral</h2>${kpiHtml(b)}
    <h2>Tom da Junta e taxa de juros</h2><div id="chart-${bc}"></div>`;
  if (!b.members.length) return `${top}<h2>Base de documentos</h2>${docsHtml(bc)}`;  // BC só com documentos colegiados
  return `${top}
    <h2>Heatmap por reunião</h2>
    <div class="hmctl"><div class="seg" id="hm-${bc}"><button type="button" data-mode="level" class="on">Nível</button><button type="button" data-mode="deviation">Desvio vs Junta</button></div>
      <p class="sub">Coluna = ciclo aberto pela reunião. Junta = nível no fim do ciclo (já com a ata); membro = média das falas no ciclo. Azul = dove, vermelho = hawk.</p></div>
    <div class="wrap" id="heat-${bc}"></div>
    <h2>Membros</h2>${cardsHtml(DATA.bcs[bc])}
    <h2>Base de documentos</h2>${docsHtml(bc)}`;
}

function wireBC(bc) {
  const b = DATA.bcs[bc], seg = document.getElementById('hm-' + bc), heat = document.getElementById('heat-' + bc);
  if (seg) {
    const drawHeat = mode => {
      heat.innerHTML = heatHtml(b, mode);
      seg.querySelectorAll('button').forEach(x => x.classList.toggle('on', x.dataset.mode === mode));
    };
    seg.querySelectorAll('button').forEach(x => x.addEventListener('click', () => drawHeat(x.dataset.mode)));
    drawHeat('level');
  }
  for (const id of ['q-', 't-', 'tr-']) document.getElementById(id + bc).addEventListener(id === 'q-' ? 'input' : 'change', () => renderDocs(bc));
  const list = document.getElementById('list-' + bc);
  list.addEventListener('toggle', e => {       // texto integral só quando o documento é aberto
    const d = e.target;
    if (d.open && d.dataset.i && !d.dataset.full) { d.querySelector('pre').textContent = b.docs[+d.dataset.i].text; d.dataset.full = '1'; }
  }, true);
  renderDocs(bc);
}

/* ---------- Metodologia ---------- */
const METODO = [
  ['Rubrica', 'Cada documento é classificado por um modelo de linguagem na rubrica 1.0-generic (projeto de reaction functions do FOMC, drivers adaptados a EMs): composto hawk-dove em [−5, +5] (positivo = hawk), peso no mandato de preços, convicção sobre inflação, preocupação com atividade, leitura do stance, viés de curto prazo e seis drivers. Dimensão não tratada no texto fica em branco, nunca zero.'],
  ['Duas trilhas', '<i>Colegiado</i> (comunicado e ata) é a voz oficial da Junta. <i>Membros</i> (falas públicas e calls privados) é a voz individual.'],
  ['Série do Board', 'Degrau: o nível em cada data é o composto do último documento colegiado publicado até ali (comunicado ou ata). Documento sem composto não move o degrau. <b>Ressalva:</b> comunicado e ata são gêneros diferentes — a ata é mais longa e explicita divisões —, então parte do salto comunicado→ata pode ser gênero, não mudança de postura. O marcador (● comunicado, ■ ata) permite separar.'],
  ['Taxa de referência', 'Taxa anunciada em cada comunicado, em degrau a partir da data do comunicado e estendida até a data de geração do site. Eixo direito do gráfico.'],
  ['Desvio do membro', 'Composto da fala ou call menos o nível do Board vigente na data dela.'],
  ['Heatmap', 'Cada coluna é um ciclo entre duas reuniões. Board = nível no fim do ciclo (já com a ata). Membro = média das falas no ciclo; no modo desvio, média dos desvios.'],
  ['Calibração', 'Os scores são inteiros ou terminam em .5. A escala lê o que o documento pede da política, não o quanto ele reclama da inflação. A régua dos documentos colegiados é a calibração da skill de classificação de falas (exemplos do Fed em 2026) espelhada para o lado dovish, usada como ordem de grandeza: corte grande (ex.: 50 bp) sinalizando novos cortes de magnitude similar −4,5; corte grande com mais afrouxamento como cenário claro −4; corte com mais cortes como cenário base −3,5; corte com algum afrouxamento adicional modesto −3; corte com guidance mais cauteloso ou colegiado dividido −2,5; corte sinalizado como último, ou manutenção em que a maioria já discute o próximo corte, −1,5 a −2; manutenção com a porta aberta a corte −1; manutenção confortável, dependente de dados, 0 a +0,5; manutenção com a suficiência da política em questão +1 a +2; alta ou endosso de alta +2,5 ou mais. Votos divergentes puxam a nota no sentido deles. Diferenças de 0,5 são ruído: confie no ranking e na direção da mudança.'],
  ['Escopo', 'Desde janeiro de 2025. Banxico: comunicados e atas, mais falas e calls de membros. SARB: só os statements do MPC (o SARB não publica ata, e o placar do statement não tem nomes). As datas do primeiro e do último documento aparecem no cabeçalho da página. RTIs, outros BCs e falas de membros do SARB entram depois.'],
].map(([h, p]) => `<h2>${h}</h2><div class="card metodo"><p>${p}</p></div>`).join('');

/* ---------- casca ---------- */
(function boot() {
  const ids = Object.keys(DATA.bcs), tabs = [...ids.map(bc => [bc, DATA.bcs[bc].label]), ['metodologia', 'Metodologia']];
  const start = tabs.some(([k]) => k === location.hash.slice(1)) ? location.hash.slice(1) : tabs[0][0];
  const bar = document.getElementById('tabs'), panes = document.getElementById('panes');
  for (const [k, label] of tabs) {
    bar.insertAdjacentHTML('beforeend', `<button class="tabbtn${k === start ? ' on' : ''}" data-tab="${esc(k)}" type="button">${esc(label)}</button>`);
    panes.insertAdjacentHTML('beforeend', `<div id="tab-${esc(k)}" class="tab${k === start ? ' on' : ''}">${k === 'metodologia' ? METODO : bcPane(k)}</div>`);
  }
  ids.forEach(wireBC);
  const cov = ids.map(bc => DATA.bcs[bc].coverage);
  const first = cov.map(c => c.first).sort()[0], last = cov.map(c => c.last).sort().slice(-1)[0];
  document.getElementById('pill').textContent = ids.map(bc => DATA.bcs[bc].label).join(' · ') + ' · v1';
  document.getElementById('meta-gen').textContent = dBR(GENERATED);
  document.getElementById('meta-cov').textContent = `${dBR(first)}–${dBR(last)} · ${cov.reduce((a, c) => a + c.n_docs, 0)} documentos`;
  document.getElementById('foot-year').textContent = 'JGP · ' + GENERATED.slice(0, 4);
  const drawn = {};
  JGPChrome.init({onTab(tab) {
    history.replaceState(null, '', '#' + tab);
    if (DATA.bcs[tab] && !drawn[tab]) { drawn[tab] = true;
      // Inter precisa estar carregada: o Plotly mede a legenda com a fonte do momento.
      (document.fonts ? document.fonts.ready : Promise.resolve()).then(() => boardChart(document.getElementById('chart-' + tab), tab));
    }
  }});
})();
