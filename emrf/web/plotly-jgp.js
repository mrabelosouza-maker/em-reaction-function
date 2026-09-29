/* ============================================================================
   Camada Plotly do padrão JGP — porte de funcoes_graficas_jgp (tema.py/config.py).
   A lib de referência é matplotlib→PNG; o que se transporta é o PADRÃO VISUAL:
   Inter · grid só horizontal · spines pretas · linha do zero cinza · legenda sem
   moldura · números pt-BR (5,2% · 1.234) · cores só das vars --s1..--s4/--d1..--d3.

   Usada nos dashboards de inflação do México e do Chile. Depende de:
     - as vars do dashboard.css (--surface, --ink, --chart-x, --s1..--d3)
     - plotly.min.js LOCAL (não CDN — o CSP/offline da mesa)

   API:
     card(cont, titulo, {sub, fonte, series})  -> cria a moldura e devolve o div do plot
     lineFig(el, series, opts)                 -> gráfico de linhas padrão
     baseLayout(theme(), extra)                -> layout base p/ qualquer outro tipo (barras etc.)

   `series` = [{name, x[], y[], color, w?, dash?, mode?, noLabel?}]
   `opts`   = {x0, suffix, zero, targetBand, h, noLabel, layout}
   ========================================================================== */
const $=(s,r=document)=>r.querySelector(s);
const cssv=n=>getComputedStyle(document.body).getPropertyValue(n).trim();
const FONT_JGP="Inter,'Segoe UI',system-ui,-apple-system,sans-serif";
const CFG={responsive:true,displaylogo:false,scrollZoom:false,
  modeBarButtonsToRemove:['lasso2d','select2d'],toImageButtonOptions:{format:'png',scale:2}};
const nBR=(v,d=2)=>(v==null||isNaN(v))?'—':(+v).toFixed(d).replace('.',',');   // 5.2 -> "5,2"
const PALETTE_JGP=()=>[cssv('--s1'),cssv('--s2'),cssv('--s3'),cssv('--s4'),
                       cssv('--d1'),cssv('--d2'),cssv('--d3')];

/* Alturas: escalam com a JANELA. Um dashboard é lido de 1080p a ultrawide; altura fixa de
   360px deixa metade da tela vazia. H_FULL = card de largura inteira; H_HALF = card na .grid2. */
const H_FULL=()=>Math.max(380,Math.min(620,Math.round(window.innerHeight*0.68)));
const H_HALF=()=>Math.max(320,Math.min(500,Math.round(window.innerHeight*0.46)));
const _inGrid2=el=>!!(el&&el.closest&&el.closest('.grid2'));   // altura escolhida sozinha

function theme(){return{surface:cssv('--surface'),ink:cssv('--ink'),muted:cssv('--muted'),
  grid:cssv('--chart-grid'),axis:cssv('--chart-axis'),zero:cssv('--chart-zero'),legend:cssv('--chart-legend')};}
/* Eixo no padrão JGP: linha preta, ticks externos, sem grid (o grid é só no Y). */
const axJGP=t=>({linecolor:t.axis,linewidth:1,tickcolor:t.axis,ticks:'outside',ticklen:3,
  tickfont:{size:11,color:t.ink},showgrid:false,zeroline:false});
function baseLayout(t,extra){
  const e=extra||{};
  const lay=Object.assign({
    margin:{l:52,r:56,t:28,b:28},height:H_FULL(),hovermode:'x unified',dragmode:'zoom',
    separators:',.',                       // pt-BR: decimal vírgula, milhar ponto
    showlegend:true,
    legend:{orientation:'h',yanchor:'bottom',y:1.0,xanchor:'left',x:0,
            font:{size:11,color:t.legend},bgcolor:'rgba(0,0,0,0)',borderwidth:0},  // frameon=False
    paper_bgcolor:t.surface,plot_bgcolor:t.surface,
    font:{family:FONT_JGP,color:t.ink,size:11},colorway:PALETTE_JGP(),
    hoverlabel:{bgcolor:t.surface,bordercolor:t.axis,font:{size:11,color:t.ink,family:FONT_JGP}}
  },e);
  // merge raso dos eixos: `extra` só sobrescreve as chaves que declara
  lay.xaxis=Object.assign(axJGP(t),e.xaxis||{});
  lay.yaxis=Object.assign(axJGP(t),{showgrid:true,gridcolor:t.grid,gridwidth:1},e.yaxis||{});
  if(e.yaxis2)lay.yaxis2=Object.assign(axJGP(t),e.yaxis2);
  return lay;
}
/* Extensão do Y no X visível (autoscale ao dar pan/zoom-x). */
function yExtent(series,x0,x1,zero,inc){let lo=Infinity,hi=-Infinity;
  series.forEach(s=>{for(let i=0;i<s.x.length;i++){const v=s.y[i];if(v==null||isNaN(v))continue;
    if(x0!=null){const tt=Date.parse(s.x[i]);if(tt<x0||tt>x1)continue;}
    if(v<lo)lo=v;if(v>hi)hi=v;}});
  if(!isFinite(lo)){lo=0;hi=1;}if(zero){lo=Math.min(lo,0);hi=Math.max(hi,0);}
  if(inc){lo=Math.min(lo,inc[0]);hi=Math.max(hi,inc[1]);}    // garante a banda-meta visível
  const pad=(hi-lo)*0.08||0.5;return[lo-pad,hi+pad];}
/* Última data com valor não-nulo, 'MM/YYYY' (tema.py: _formatar_last_data). */
function lastDataOf(series){let best=null;
  (series||[]).forEach(s=>{if(!s||!s.x||!s.y)return;
    for(let i=s.y.length-1;i>=0;i--){if(s.y[i]!=null&&!isNaN(s.y[i])){
      if(best===null||String(s.x[i])>best)best=String(s.x[i]);break;}}});
  const m=best&&/(\d{4})-(\d{2})/.exec(best);return m?m[2]+'/'+m[1]:null;}
/* card(cont, titulo, opts?) — replica aplicar_tema: título 14 bold, subtítulo 11 cinza
   (com "| Last data: MM/YYYY" anexado se `opts.series` vier), caption de fonte 11. */
function card(container,title,opts){opts=opts||{};
  const c=document.createElement('div');c.className='card';
  const h=document.createElement('h3');h.textContent=title;c.appendChild(h);
  let sub=opts.sub||'';
  if(opts.series&&opts.lastDataAuto!==false){const ld=lastDataOf(opts.series);
    if(ld&&sub.indexOf('Last data:')<0)sub=sub?sub+'  |  Last data: '+ld:'Last data: '+ld;}
  if(sub){const s=document.createElement('p');s.className='csub';s.textContent=sub;c.appendChild(s);}
  const p=document.createElement('div');p.className='plot';c.appendChild(p);
  if(opts.fonte){const f=document.createElement('p');f.className='cfonte';f.textContent=opts.fonte;c.appendChild(f);}
  container.appendChild(c);return p;}

/* lineFig — o gráfico de linhas padrão. Traz de graça:
     · rótulo do último valor de cada série, à direita, na cor da série
     · DE-COLISÃO vertical desses rótulos (séries que terminam no mesmo nível se
       empilham em vez de se sobrepor) — sem isso, duas linhas a 4,36% e 4,38%
       imprimem um rótulo por cima do outro
     · banda-meta opcional (targetBand: banco central com meta 3%±1pp)
     · re-autoscale do Y ao X visível em pan/zoom-x
     · o rótulo some quando a série é ocultada pela legenda                        */
function lineFig(el,series,opts){opts=opts||{};const t=theme();
  const suf=opts.suffix!==undefined?opts.suffix:'%';
  const tb=opts.targetBand, HH=opts.h||(_inGrid2(el)?H_HALF():H_FULL());
  let last='2018-01-01';series.forEach(s=>{const lx=s.x[s.x.length-1];if(lx&&lx>last)last=lx;});
  const traces=series.map(s=>{const tr={x:s.x,y:s.y,name:s.name,type:'scatter',mode:s.mode||'lines',
    connectgaps:false,line:{color:s.color,width:s.w||2,dash:s.dash||'solid',shape:'linear'},
    hovertemplate:'%{y:.2f}'+suf+'<extra></extra>'};
    if(s.mode&&s.mode.indexOf('markers')>=0)tr.marker={size:s.msize||7,color:s.color,
      symbol:s.symbol||'circle',line:s.mline||{width:0}};  // marker:undefined quebra o Plotly
    return tr;});
  const x0v=opts.x0||'2018-01-01';
  const y0=yExtent(series,Date.parse(x0v),Date.parse(last),opts.zero,tb?[2,4]:null);
  const shapes=[];
  if(tb){                                  // faixa 2–4% + linha central 3%, fixas no eixo y
    shapes.push({type:'rect',xref:'paper',yref:'y',x0:0,x1:1,y0:2,y1:4,
      fillcolor:cssv('--jgp-green-tint'),line:{width:0},layer:'below'});
    shapes.push({type:'line',xref:'paper',yref:'y',x0:0,x1:1,y0:3,y1:3,
      line:{color:cssv('--green'),width:1,dash:'dot'},layer:'below'});
  }
  const ann=[],annTr=[];                   // annTr[k] = índice da trace a que o rótulo k pertence
  if(!opts.noLabel)series.forEach((s,i)=>{if(s.noLabel)return;
    let li=-1;for(let j=s.y.length-1;j>=0;j--){if(s.y[j]!=null&&!isNaN(s.y[j])){li=j;break;}}
    if(li<0)return;
    ann.push({x:s.x[li],y:s.y[li],xref:'x',yref:'y',xanchor:'left',xshift:6,align:'left',
      text:'<b>'+nBR(s.y[li],2)+suf+'</b>',showarrow:false,
      font:{size:11,color:s.color||'#666',family:FONT_JGP}});
    annTr.push(i);});
  if(ann.length>1){                        // de-colisão vertical (em px, via yshift)
    const H=HH-60, rng=(y0[1]-y0[0])||1, pxPer=H/rng, MIN=13;
    const px=a=>(a.y-y0[0])*pxPer;
    const ord=ann.map((a,k)=>({k,p:px(a)})).sort((a,b)=>b.p-a.p);
    for(let i=1;i<ord.length;i++)if(ord[i-1].p-ord[i].p<MIN)ord[i].p=ord[i-1].p-MIN;
    ord.forEach(o=>{ann[o.k].yshift=Math.round(o.p-px(ann[o.k]));});
  }
  if(tb){ann.push({xref:'paper',yref:'y',x:0.008,y:3,xanchor:'left',yanchor:'bottom',
    text:'meta 3%±1pp',showarrow:false,font:{size:9,color:cssv('--muted')}});annTr.push(-1);}
  const layout=baseLayout(t,Object.assign({shapes:shapes,annotations:ann,height:HH,
    xaxis:{type:'date',range:[x0v,last],tickangle:0,
      tickformatstops:[{dtickrange:[null,7776000000],value:'%d/%b'},
        {dtickrange:[7776000000,378432000000],value:'%b/%y'},
        {dtickrange:[378432000000,null],value:'%Y'}]},
    yaxis:{range:y0,ticksuffix:suf,zeroline:!!opts.zero,zerolinecolor:t.zero,zerolinewidth:.9}},
    opts.layout||{}));
  Plotly.newPlot(el,traces,layout,CFG).then(gd=>{
    gd.on('plotly_relayout',ev=>{          // reajusta Y ao X visível em pan/zoom-x
      if(gd._lock)return;
      const px=k=>ev[k]!==undefined;
      if(px('yaxis.range[0]')||px('yaxis.range')||px('yaxis.autorange'))return;  // box-zoom c/ Y é respeitado
      let a,b;
      if(px('xaxis.range[0]')){a=Date.parse(String(ev['xaxis.range[0]']).replace(' ','T'));
                               b=Date.parse(String(ev['xaxis.range[1]']).replace(' ','T'));}
      else if(px('xaxis.range')){a=Date.parse(String(ev['xaxis.range'][0]).replace(' ','T'));
                                 b=Date.parse(String(ev['xaxis.range'][1]).replace(' ','T'));}
      else return;
      gd._lock=true;
      Plotly.relayout(gd,{'yaxis.range':yExtent(series,a,b,opts.zero,tb?[2,4]:null)})
        .then(()=>{gd._lock=false;});
    });
    if(ann.length)gd.on('plotly_restyle',()=>{   // esconde o rótulo da série ocultada na legenda
      const upd=ann.map((a,k)=>{const v=gd.data[annTr[k]]&&gd.data[annTr[k]].visible;
        return Object.assign({},a,{visible:(v===undefined||v===true)});});
      Plotly.relayout(gd,{annotations:upd});
    });
  });
}
