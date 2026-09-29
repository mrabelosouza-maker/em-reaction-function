"""Template do site no formato JGP. Só formatação: toda a lógica está em board.py/build.py.

CSS e JS ficam em emrf/web/ (jgp.css e chrome.js/plotly-jgp.js vêm da skill jgp-html-report;
chrome.js com o sumário fechado por padrão) e são inlinados aqui. Plotly é local:
assets/plotly.min.js, copiado por build() para o lado do HTML.
"""
from __future__ import annotations

import json
from pathlib import Path

WEB = Path(__file__).with_name("web")
JS_FILES = ("chrome.js", "plotly-jgp.js", "app.js")

TEMPLATE = r"""<!doctype html>
<html lang="pt-BR">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>EM Reaction Functions &mdash; JGP Macro</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&display=swap" rel="stylesheet">
<script src="assets/plotly.min.js"></script>
<style>
__CSS__
</style>
</head>
<body data-generated="__GENERATED__">
<div class="scroll-progress" id="scrollProgress"></div>
<nav class="topnav">
  <div class="topnav-left">
    <button class="nav-toggle" id="navToggle" type="button" aria-controls="sidebar" aria-expanded="false" title="Mostrar sumário">&#9776;</button>
    <span class="wordmark">JGP</span>
    <span class="divider">&middot;</span>
    <span class="breadcrumb">Macro EMs &rsaquo; Reaction Functions</span>
  </div>
  <div class="topnav-right"><span class="pill" id="pill">Banxico &middot; v1</span></div>
</nav>
<nav class="tabbar" id="tabs"></nav>
<div class="page-wrapper nav-collapsed">
  <nav class="sidebar" id="sidebar"><div class="sidebar-eyebrow">Sum&aacute;rio</div></nav>
  <main class="main-content">
    <header class="page-header fade-up delay-1">
      <div class="page-eyebrow"><span class="tag">Pol&iacute;tica monet&aacute;ria &middot; EMs</span></div>
      <h1 class="page-title">EM Reaction Functions</h1>
      <p class="lead">Escala hawk-dove da comunica&ccedil;&atilde;o de bancos centrais emergentes: a voz da Junta (comunicados e atas) e a dos membros (falas p&uacute;blicas e calls privados), lado a lado com a taxa de juros.</p>
      <dl class="page-meta">
        <div class="meta-item"><dt>Gerado em</dt><dd id="meta-gen">&mdash;</dd></div>
        <div class="meta-item"><dt>Cobertura</dt><dd id="meta-cov">&mdash;</dd></div>
        <div class="meta-item"><dt>Macro</dt><dd>JGP</dd></div>
      </dl>
    </header>
    <div id="panes"></div>
    <footer class="page-footer">
      <div class="credits">Elabora&ccedil;&atilde;o &middot; <strong>JGP Macro</strong> &middot; classifica&ccedil;&atilde;o pr&oacute;pria</div>
      <div id="foot-year">JGP</div>
    </footer>
  </main>
</div>
<button class="back-to-top" id="backToTop" aria-label="Voltar ao topo"><span class="arrow">&uarr;</span><span>TOP</span></button>
<script id="data" type="application/json">__DATA__</script>
<script>
__JS__
</script>
</body>
</html>
"""


def _read(name: str) -> str:
    return (WEB / name).read_text(encoding="utf-8")


def render(payload: dict, generated: str) -> str:
    blob = json.dumps(payload, ensure_ascii=False).replace("<", "\\u003c")
    js = "\n".join(_read(f) for f in JS_FILES)
    # __DATA__ por último: nada vindo dos documentos é reinterpretado como placeholder.
    return (TEMPLATE.replace("__CSS__", _read("jgp.css")).replace("__JS__", js)
            .replace("__GENERATED__", generated).replace("__DATA__", blob))
