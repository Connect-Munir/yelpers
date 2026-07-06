/* LeadHarvest — frontend ⇄ FastAPI backend.
 * Talks to the API mounted at /api (same origin when served by uvicorn).
 * Owns: the Run/Stop form actions, live job polling, the hero lead stream,
 * the results table, stats and CSV export.
 */
(function () {
  'use strict';

  // Same origin when served by FastAPI; falls back to localhost:8000 if the
  // page is opened straight from disk (file://) during development.
  const API = location.protocol === 'file:' ? 'http://127.0.0.1:8000' : '';

  const $ = (id) => document.getElementById(id);
  const esc = (s) => String(s == null ? '' : s).replace(/[&<>"']/g, (c) => (
    { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]
  ));

  async function api(path, opts) {
    const res = await fetch(API + path, opts);
    if (!res.ok) {
      let detail = res.statusText;
      try { detail = (await res.json()).detail || detail; } catch (_) {}
      throw new Error(detail);
    }
    return res.status === 204 ? null : res.json();
  }

  /* ── Elements ── */
  const form = $('runForm');
  const runBtn = $('runBtn');
  const runBtnLabel = $('runBtnLabel');
  const stopBtn = $('stopBtn');
  const runStatus = $('runStatus');
  const termInput = $('termInput');
  const locInput = $('locInput');
  const maxInput = $('maxInput');
  const maxAllInput = $('maxAllInput');
  const headlessInput = $('headlessInput');

  const stream = $('leadStream');
  const rowCount = $('rowCount');

  const resultsBody = $('resultsBody');
  const resultsCount = $('resultsCount');
  const searchInput = $('searchInput');
  const refreshBtn = $('refreshBtn');
  const exportBtn = $('exportBtn');
  const prevPage = $('prevPage');
  const nextPage = $('nextPage');
  const pageInfo = $('pageInfo');

  const logPanel = $('logPanel');
  const logOut = $('logOut');
  const logStatus = $('logStatus');

  /* ── Stats ── */
  async function loadStats() {
    try {
      const s = await api('/api/stats');
      $('statLeads').textContent = s.total_leads;
      $('statNiches').textContent = s.total_niches;
      $('statWebsites').textContent = s.with_website;
      $('statPhones').textContent = s.with_phone;
    } catch (_) { /* DB may be down; health surfaces it */ }
  }

  /* ── Results table ── */
  const PAGE = 10;
  let offset = 0;
  let lastTotal = 0;

  function siteHref(url) {
    if (!url) return '';
    return /^https?:\/\//i.test(url) ? url : 'http://' + url;
  }

  async function loadResults() {
    const q = encodeURIComponent(searchInput.value.trim());
    try {
      const data = await api(`/api/businesses?limit=${PAGE}&offset=${offset}&search=${q}`);
      lastTotal = data.total;
      resultsBody.innerHTML = '';
      if (!data.items.length) {
        resultsBody.innerHTML =
          '<tr><td colspan="6" class="px-5 py-10 text-center text-muted">No leads found.</td></tr>';
      } else {
        for (const b of data.items) {
          const tr = document.createElement('tr');
          tr.className = 'hover:bg-paper/[0.03] transition-colors';
          const site = b.website_url
            ? `<a href="${esc(siteHref(b.website_url))}" target="_blank" rel="noopener" class="text-ember hover:text-coral break-all">${esc(b.website_url)}</a>`
            : '<span class="text-muted">—</span>';
          tr.innerHTML = `
            <td class="px-5 py-3 font-semibold text-paper">${esc(b.company_name) || '—'}</td>
            <td class="px-5 py-3"><span class="font-mono text-[11px] text-lime">${esc(b.niche)}</span></td>
            <td class="px-5 py-3 font-mono text-[12px] text-muted whitespace-nowrap">${esc(b.phone) || '—'}</td>
            <td class="px-5 py-3 text-muted text-[13px]">${esc(b.location) || '—'}</td>
            <td class="px-5 py-3 text-[12px]">${site}</td>
            <td class="px-5 py-3 text-right">
              <button data-del="${b.id}" class="font-mono text-[11px] text-muted hover:text-coral transition-colors">✕</button>
            </td>`;
          resultsBody.appendChild(tr);
        }
      }
      const from = data.total ? offset + 1 : 0;
      const to = Math.min(offset + PAGE, data.total);
      resultsCount.textContent = `${data.total} lead${data.total === 1 ? '' : 's'}`;
      pageInfo.textContent = data.total ? `${from}–${to} of ${data.total}` : 'page 1';
      prevPage.disabled = offset === 0;
      nextPage.disabled = offset + PAGE >= data.total;
    } catch (err) {
      resultsBody.innerHTML =
        `<tr><td colspan="6" class="px-5 py-10 text-center text-coral">Could not load leads: ${esc(err.message)}</td></tr>`;
    }
  }

  resultsBody.addEventListener('click', async (e) => {
    const btn = e.target.closest('button[data-del]');
    if (!btn) return;
    btn.disabled = true;
    try {
      await api('/api/businesses/' + btn.dataset.del, { method: 'DELETE' });
      loadResults();
      loadStats();
    } catch (err) { btn.disabled = false; }
  });

  let searchTimer;
  searchInput.addEventListener('input', () => {
    clearTimeout(searchTimer);
    searchTimer = setTimeout(() => { offset = 0; loadResults(); }, 300);
  });
  refreshBtn.addEventListener('click', () => { loadResults(); loadStats(); });
  prevPage.addEventListener('click', () => { if (offset > 0) { offset -= PAGE; loadResults(); } });
  nextPage.addEventListener('click', () => { if (offset + PAGE < lastTotal) { offset += PAGE; loadResults(); } });
  exportBtn.addEventListener('click', (e) => {
    const q = searchInput.value.trim();
    exportBtn.href = '/api/businesses.csv' + (q ? '?search=' + encodeURIComponent(q) : '');
  });

  /* ── Hero live stream (real job previews) ── */
  function renderStream(previews) {
    if (!stream) return;
    stream.innerHTML = '';
    previews.slice(-6).forEach((p) => {
      const li = document.createElement('li');
      li.className = 'row-in px-5 py-3.5';
      li.innerHTML = `
        <div class="flex items-center justify-between gap-3">
          <span class="font-display font-semibold text-paper truncate">${esc(p.name)}</span>
          <span class="font-mono text-[11px] text-lime shrink-0">✓ saved</span>
        </div>
        <div class="mt-1.5 flex flex-wrap items-center gap-x-4 gap-y-1 font-mono text-[11px] text-muted">
          <span>${esc(p.phone) || '—'}</span>
          <span class="text-ember">${esc(p.website) || '—'}</span>
        </div>`;
      stream.appendChild(li);
    });
    if (rowCount) rowCount.textContent = `rows written: ${previews.length}`;
  }

  /* ── Run / poll a scrape job ── */
  let pollTimer = null;
  let activeJob = null;

  function setRunning(on) {
    runBtn.disabled = on;
    runBtnLabel.textContent = on ? 'Scraping…' : 'Run scrape now';
    stopBtn.classList.toggle('hidden', !on);
  }

  async function startScrape(e) {
    e.preventDefault();
    const body = {
      term: termInput.value.trim() || 'plumbers',
      location: locInput.value.trim() || 'Austin, TX',
      max_results: parseInt(maxInput.value, 10) || 20,
      max_all: maxAllInput.checked,
      headless: headlessInput.checked,
    };
    setRunning(true);
    runStatus.textContent = 'starting…';
    logPanel.classList.remove('hidden');
    logOut.textContent = '';
    try {
      const job = await api('/api/scrape', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
      });
      activeJob = job.id;
      runStatus.textContent = 'a Chrome window will open — solve the CAPTCHA there if asked.';
      pollJob();
    } catch (err) {
      setRunning(false);
      runStatus.textContent = 'error: ' + err.message;
    }
  }

  async function pollJob() {
    if (!activeJob) return;
    try {
      const job = await api('/api/scrape/' + activeJob);
      logOut.textContent = job.log.join('\n');
      logOut.scrollTop = logOut.scrollHeight;
      renderStream(job.previews);
      runStatus.textContent = `${job.status} · ${job.scraped} found`;

      const finished = ['done', 'error', 'stopped'].includes(job.status);
      if (finished) {
        setRunning(false);
        logStatus.innerHTML = job.status === 'done'
          ? '<span class="h-1.5 w-1.5 rounded-full bg-lime"></span> done'
          : '<span class="h-1.5 w-1.5 rounded-full bg-coral"></span> ' + job.status;
        logStatus.className = 'flex items-center gap-1.5 font-mono text-[11px] ' +
          (job.status === 'done' ? 'text-lime' : 'text-coral');
        runStatus.textContent = job.message;
        activeJob = null;
        offset = 0;
        loadResults();
        loadStats();
        return;
      }
      pollTimer = setTimeout(pollJob, 1500);
    } catch (err) {
      runStatus.textContent = 'lost job: ' + err.message;
      setRunning(false);
      activeJob = null;
    }
  }

  async function stopScrape() {
    if (!activeJob) return;
    stopBtn.disabled = true;
    runStatus.textContent = 'stopping — saving what we have…';
    try { await api('/api/scrape/' + activeJob + '/stop', { method: 'POST' }); } catch (_) {}
    stopBtn.disabled = false;
  }

  if (form) form.addEventListener('submit', startScrape);
  if (stopBtn) stopBtn.addEventListener('click', stopScrape);

  /* ── Init ── */
  loadStats();
  loadResults();
})();
