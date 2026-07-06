(function () {
  'use strict';
  const reduce = window.matchMedia('(prefers-reduced-motion: reduce)').matches;

  /* ── Mobile menu ── */
  const toggle = document.getElementById('navToggle');
  const menu = document.getElementById('mobileMenu');
  toggle.addEventListener('click', () => {
    const open = menu.classList.toggle('hidden') === false;
    toggle.setAttribute('aria-expanded', String(open));
  });
  menu.querySelectorAll('a').forEach(a => a.addEventListener('click', () => {
    menu.classList.add('hidden');
    toggle.setAttribute('aria-expanded', 'false');
  }));

  /* ── Count-up stats (on view) ── */
  const counters = document.querySelectorAll('[data-count]');
  const animateCount = (el) => {
    const target = +el.dataset.count;
    if (reduce || target === 0) { el.textContent = target; return; }
    const dur = 1100, start = performance.now();
    const tick = (now) => {
      const p = Math.min((now - start) / dur, 1);
      const eased = 1 - Math.pow(1 - p, 3);
      el.textContent = Math.round(eased * target);
      if (p < 1) requestAnimationFrame(tick);
    };
    requestAnimationFrame(tick);
  };
  const statObserver = new IntersectionObserver((entries) => {
    entries.forEach(e => {
      if (e.isIntersecting) { animateCount(e.target); statObserver.unobserve(e.target); }
    });
  }, { threshold: 0.6 });
  counters.forEach(c => statObserver.observe(c));

  /* ── Live results stream is driven by the real backend (see api.js) ── */

  /* ── Command builder ── */
  const termInput = document.getElementById('termInput');
  const locInput  = document.getElementById('locInput');
  const maxInput  = document.getElementById('maxInput');
  const maxVal    = document.getElementById('maxVal');
  const cmdOut    = document.getElementById('cmdOut');
  const termEcho  = document.getElementById('termEcho');
  const locEcho   = document.getElementById('locEcho');

  const esc = (s) => s.replace(/"/g, '');
  const buildCmd = () => {
    const t = esc(termInput.value.trim() || 'plumbers');
    const l = esc(locInput.value.trim() || 'Austin, TX');
    const m = maxInput.value;
    maxVal.textContent = m;
    cmdOut.textContent = `python scraper.py --term "${t}" --location "${l}" --max ${m}`;
    termEcho.textContent = `"${t}"`;
    locEcho.textContent = `"${l}"`;
  };
  [termInput, locInput, maxInput].forEach(el => el.addEventListener('input', buildCmd));
  buildCmd();

  /* ── Copy command ── */
  const copyBtn = document.getElementById('copyBtn');
  copyBtn.addEventListener('click', async () => {
    try {
      await navigator.clipboard.writeText(cmdOut.textContent);
      const prev = copyBtn.textContent;
      copyBtn.textContent = 'copied ✓';
      copyBtn.classList.add('text-paper');
      setTimeout(() => { copyBtn.textContent = prev; copyBtn.classList.remove('text-paper'); }, 1600);
    } catch (_) {
      copyBtn.textContent = 'press ⌘C';
    }
  });
})();
