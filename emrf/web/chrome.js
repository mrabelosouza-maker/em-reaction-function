/* =====================================================================
   chrome.js — casca editorial JGP (variante dashboard / abas)
   Requer no HTML:
     <div class="scroll-progress" id="scrollProgress"></div>
     <nav class="topnav">…</nav>
     <nav class="tabbar" id="tabs"><button class="tabbtn on" data-tab="X">…</button>…</nav>
     <div class="page-wrapper">
       <nav class="sidebar" id="sidebar"><div class="sidebar-eyebrow">Sumário</div></nav>
       <main class="main-content">
         <header class="page-header">…</header>
         <div id="tab-X" class="tab on">…<h2>Seção</h2>…</div> …
       </main>
     </div>
     <button class="back-to-top" id="backToTop"><span class="arrow">↑</span><span>TOP</span></button>

   A sidebar é gerada a partir dos <h2> da aba ativa (padrão Fiscal: só o
   grupo da aba ativa aparece). Chame JGPChrome.init({onTab}) uma vez.
   `onTab(tabId)` é opcional — use para (re)desenhar gráficos ao abrir a aba.
   ===================================================================== */
window.JGPChrome = (function () {
  const $ = (s, r = document) => r.querySelector(s);
  let cfg = {};

  function tabButtons() { return [].slice.call(document.querySelectorAll('#tabs .tabbtn')); }
  function activeTab() {
    const b = tabButtons().find(b => b.classList.contains('on'));
    return b ? b.dataset.tab : (tabButtons()[0] && tabButtons()[0].dataset.tab);
  }

  function showTab(id) {
    tabButtons().forEach(b => b.classList.toggle('on', b.dataset.tab === id));
    document.querySelectorAll('.tab').forEach(p => p.classList.toggle('on', p.id === 'tab-' + id));
    buildSidebar();
    window.scrollTo({ top: 0 });
    if (typeof cfg.onTab === 'function') cfg.onTab(id);
  }

  function buildSidebar() {
    const sidebar = $('#sidebar'); if (!sidebar) return;
    const at = activeTab();
    sidebar.querySelectorAll('.sidebar-chapter,.sidebar-link').forEach(e => e.remove());
    const btn = tabButtons().find(b => b.dataset.tab === at);
    if (btn) {
      const ch = document.createElement('a');
      ch.className = 'sidebar-chapter active'; ch.href = '#';
      ch.innerHTML = '<span class="name">' + btn.textContent.trim() + '</span>';
      ch.addEventListener('click', e => { e.preventDefault(); window.scrollTo({ top: 0, behavior: 'smooth' }); });
      sidebar.appendChild(ch);
    }
    const pane = document.getElementById('tab-' + at);
    [].slice.call(pane ? pane.querySelectorAll('h2') : []).forEach((h, i) => {
      if (!h.id) h.id = 'sec-' + at + '-' + i;
      const a = document.createElement('a');
      a.className = 'sidebar-link'; a.href = '#' + h.id;
      const txt = (h.textContent || '').replace(/\s+/g, ' ').trim();
      a.title = txt;
      a.innerHTML = '<span>' + txt + '</span><span class="item-num">' + String(i + 1).padStart(2, '0') + '</span>';
      a.addEventListener('click', e => { e.preventDefault(); document.getElementById(h.id).scrollIntoView({ behavior: 'smooth', block: 'start' }); });
      sidebar.appendChild(a);
    });
    updateSpy();
  }

  function updateSpy() {
    const links = [].slice.call(document.querySelectorAll('#sidebar .sidebar-link'));
    if (!links.length) return;
    let cur = '';
    links.forEach(l => { const el = document.getElementById(l.getAttribute('href').slice(1));
      if (el && el.getBoundingClientRect().top - 120 <= 0) cur = l.getAttribute('href').slice(1); });
    links.forEach(l => l.classList.toggle('active', l.getAttribute('href') === '#' + cur));
  }

  function updateProgress() {
    const max = document.documentElement.scrollHeight - window.innerHeight;
    document.documentElement.style.setProperty('--scroll-progress', (max > 0 ? Math.min(100, window.scrollY / max * 100) : 0) + '%');
  }

  function init(options) {
    cfg = options || {};
    const backTop = $('#backToTop');
    // Botão de ocultar/mostrar o sumário (sidebar); estado persistido em localStorage.
    const wrapper = $('.page-wrapper'), navToggle = $('#navToggle');
    if (wrapper && navToggle) {
      const key = 'jgp-nav-collapsed';
      const applyNav = c => {
        wrapper.classList.toggle('nav-collapsed', c);
        navToggle.setAttribute('aria-expanded', String(!c));
        navToggle.title = c ? 'Mostrar sumário' : 'Ocultar sumário';
        updateProgress();
        window.dispatchEvent(new Event('resize'));   // Plotly (responsive) re-flui na nova largura
      };
      // Padrão do analista: sumário FECHADO quando não há estado salvo.
      let col = true;
      try { const v = localStorage.getItem(key); if (v !== null) col = v === '1'; } catch (e) {}
      applyNav(col);
      navToggle.addEventListener('click', () => {
        const c = !wrapper.classList.contains('nav-collapsed');
        applyNav(c); try { localStorage.setItem(key, c ? '1' : '0'); } catch (e) {}
      });
    }
    tabButtons().forEach(b => b.addEventListener('click', () => showTab(b.dataset.tab)));
    window.addEventListener('scroll', () => {
      updateProgress(); updateSpy();
      if (backTop) backTop.classList.toggle('visible', window.scrollY > 350);
    }, { passive: true });
    window.addEventListener('resize', updateProgress, { passive: true });
    if (backTop) backTop.addEventListener('click', () => window.scrollTo({ top: 0, behavior: 'smooth' }));
    buildSidebar(); updateProgress();
    if (typeof cfg.onTab === 'function') cfg.onTab(activeTab());
  }

  return { init, showTab, buildSidebar, activeTab };
})();
