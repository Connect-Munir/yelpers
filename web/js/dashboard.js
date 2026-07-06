/* LeadHarvest — Dashboard.
 * The signed-in workspace: compose a scrape, watch it run live, and browse the
 * de-duplicated leads in MySQL. Adapted from the old in-page sections of
 * index.html so the marketing landing page stays lean.
 *
 * Auth is a client-side convenience gate (the scrape/results endpoints are
 * public for now); the JWT is still sent so the backend can enforce later.
 */
(function () {
  'use strict';

  // Same origin when served by FastAPI; fall back to localhost:8000 when the
  // page is opened straight from disk (file://) during development.
  const API = location.protocol === 'file:' ? 'http://127.0.0.1:8000' : '';
  const TOKEN_KEY = 'lh.authToken';
  const USER_KEY = 'lh.user';

  const $ = (id) => document.getElementById(id);
  const esc = (s) => String(s == null ? '' : s).replace(/[&<>"']/g, (c) => (
    { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]
  ));

  const token = localStorage.getItem(TOKEN_KEY);

  async function api(path, opts = {}) {
    const res = await fetch(API + path, {
      ...opts,
      headers: {
        'Content-Type': 'application/json',
        ...(token ? { 'Authorization': 'Bearer ' + token } : {}),
        ...(opts.headers || {}),
      },
    });
    if (!res.ok) {
      let detail = res.statusText;
      try { detail = (await res.json()).detail || detail; } catch (_) {}
      const err = new Error(detail);
      err.status = res.status;
      throw err;
    }
    return res.status === 204 ? null : res.json();
  }

  /* ── Auth gate: any signed-in user may enter ──────────────────────────── */
  function storedUser() {
    try { return JSON.parse(localStorage.getItem(USER_KEY) || 'null'); }
    catch { return null; }
  }

  function denied(msg) {
    $('gateErrorMsg').textContent = msg;
    $('gateError').classList.remove('hidden');
    $('gateSpinner').classList.add('hidden');
  }

  function enter(user) {
    $('meLabel').textContent = user.email || user.name || 'signed in';
    $('adminLink').classList.toggle('hidden', user.role !== 'admin');
    $('gate').classList.add('hidden');
    $('panel').classList.remove('hidden');
    init();
  }

  async function gate() {
    if (!token) return denied('Please sign in from the home page to open your dashboard.');
    try {
      const me = await api('/api/auth/me');
      enter(me);
    } catch (err) {
      // Only a clearly-invalid token should lock the user out; if the auth
      // service is merely unreachable, fall back to the stored profile so the
      // dashboard (and the public scrape/results API) still work.
      if (err.status === 401 || err.status === 403) {
        return denied('Your session has expired — please sign in again.');
      }
      const u = storedUser();
      if (u) enter(u);
      else denied(err.message || 'Could not verify access.');
    }
  }

  /* ── Sign out ─────────────────────────────────────────────────────────── */
  function wireSignOut() {
    $('logoutBtn').addEventListener('click', () => {
      localStorage.removeItem(TOKEN_KEY);
      localStorage.removeItem(USER_KEY);
      location.href = 'index.html';
    });
  }

  /* ── Run controls ─────────────────────────────────────────────────────── */
  const termInput = () => $('termInput');
  const locInput = () => $('locInput');
  const maxInput = () => $('maxInput');
  const maxAllInput = () => $('maxAllInput');
  const headlessInput = () => $('headlessInput');

  // Keep the "Max results" label and the slider's enabled state in sync with
  // the "scrape ALL" toggle.
  function syncMaxLabel() {
    const all = maxAllInput().checked;
    $('maxVal').textContent = all ? 'all' : maxInput().value;
    maxInput().disabled = all;
  }

  function wireMaxControls() {
    [maxInput(), maxAllInput()].forEach((el) => el.addEventListener('input', syncMaxLabel));
    syncMaxLabel();
  }

  /* ── Stats ────────────────────────────────────────────────────────────── */
  async function loadStats() {
    try {
      const s = await api('/api/stats');
      $('statLeads').textContent = s.total_leads;
      $('statNiches').textContent = s.total_niches;
      $('statWebsites').textContent = s.with_website;
      $('statPhones').textContent = s.with_phone;
    } catch (_) { /* DB may be down; the results table surfaces the error */ }
  }

  /* ── Results table ────────────────────────────────────────────────────── */
  const PAGE = 10;
  let offset = 0;
  let lastTotal = 0;

  const siteHref = (url) => (!url ? '' : /^https?:\/\//i.test(url) ? url : 'http://' + url);

  async function loadResults() {
    const q = encodeURIComponent($('searchInput').value.trim());
    const body = $('resultsBody');
    try {
      const data = await api(`/api/businesses?limit=${PAGE}&offset=${offset}&search=${q}`);
      lastTotal = data.total;
      body.innerHTML = '';
      if (!data.items.length) {
        body.innerHTML =
          '<tr><td colspan="6" class="px-5 py-10 text-center text-muted">No leads yet — run a scrape above.</td></tr>';
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
          body.appendChild(tr);
        }
      }
      const from = data.total ? offset + 1 : 0;
      const to = Math.min(offset + PAGE, data.total);
      $('resultsCount').textContent = `${data.total} lead${data.total === 1 ? '' : 's'}`;
      $('pageInfo').textContent = data.total ? `${from}–${to} of ${data.total}` : 'page 1';
      $('prevPage').disabled = offset === 0;
      $('nextPage').disabled = offset + PAGE >= data.total;
    } catch (err) {
      body.innerHTML =
        `<tr><td colspan="6" class="px-5 py-10 text-center text-coral">Could not load leads: ${esc(err.message)}</td></tr>`;
    }
  }

  function wireResults() {
    $('resultsBody').addEventListener('click', async (e) => {
      const btn = e.target.closest('button[data-del]');
      if (!btn) return;
      btn.disabled = true;
      try {
        await api('/api/businesses/' + btn.dataset.del, { method: 'DELETE' });
        loadResults();
        loadStats();
      } catch (_) { btn.disabled = false; }
    });

    let searchTimer;
    $('searchInput').addEventListener('input', () => {
      clearTimeout(searchTimer);
      searchTimer = setTimeout(() => { offset = 0; loadResults(); }, 300);
    });
    $('refreshBtn').addEventListener('click', () => { loadResults(); loadStats(); });
    $('prevPage').addEventListener('click', () => { if (offset > 0) { offset -= PAGE; loadResults(); } });
    $('nextPage').addEventListener('click', () => { if (offset + PAGE < lastTotal) { offset += PAGE; loadResults(); } });
    $('exportBtn').addEventListener('click', () => {
      const q = $('searchInput').value.trim();
      $('exportBtn').href = (API || '') + '/api/businesses.csv' + (q ? '?search=' + encodeURIComponent(q) : '');
    });
  }

  /* ── Run / poll a scrape job ──────────────────────────────────────────── */
  let pollTimer = null;
  let activeJob = null;

  function setRunning(on) {
    $('runBtn').disabled = on;
    $('runBtnLabel').textContent = on ? 'Scraping…' : 'Run scrape now';
    $('stopBtn').classList.toggle('hidden', !on);
  }

  /* ── Progress bar + elapsed timer ─────────────────────────────────────── *
   * The timer counts the seconds the run is actively working. When a one-time
   * verification (or any block) interrupts the run, the timer freezes and the
   * bar holds; once it clears, both pick up from exactly where they paused.   */
  let timerInt = null;
  let elapsedSec = 0;   // accumulated *working* seconds (paused time excluded)
  let runPaused = false;
  let runTarget = 0;    // target lead count; 0 = unknown total (scrape ALL)

  function fmtTime(total) {
    const h = Math.floor(total / 3600);
    const m = Math.floor((total % 3600) / 60);
    const s = total % 60;
    const mm = String(m).padStart(2, '0');
    const ss = String(s).padStart(2, '0');
    return h ? `${h}:${mm}:${ss}` : `${mm}:${ss}`;
  }

  function startTimer() {
    elapsedSec = 0;
    $('progTimer').textContent = fmtTime(0);
    if (timerInt) clearInterval(timerInt);
    timerInt = setInterval(() => {
      if (runPaused) return;            // frozen while a problem is being cleared
      elapsedSec += 1;
      $('progTimer').textContent = fmtTime(elapsedSec);
    }, 1000);
  }

  function stopTimer() {
    if (timerInt) { clearInterval(timerInt); timerInt = null; }
  }

  // Read the run log to tell whether we're currently held up by a verification
  // or block. The most recent matching line wins, so a "cleared" line resumes.
  const PAUSE_RE = /detected a block|verify you are human|verify you are a human|waiting for you to solve|bot challenge|hard-blocked|showing a 'verify/i;
  const RESUME_RE = /cleared|continuing/i;
  function detectPaused(log) {
    let paused = false;
    for (const line of log || []) {
      if (RESUME_RE.test(line)) paused = false;
      else if (PAUSE_RE.test(line)) paused = true;
    }
    return paused;
  }

  const BAR_COLORS = { running: 'bg-coral', paused: 'bg-ember', done: 'bg-lime', error: 'bg-coral' };
  const NOTES = {
    running: 'Harvesting leads…',
    paused: 'Paused — finishing a quick verification. We’ll resume automatically.',
    done: 'All done.',
    error: 'Run ended early — saved everything collected so far.',
  };

  function setProgress(scraped, state) {
    const bar = $('progBar');
    if (state === 'done') {
      bar.style.width = '100%';
      $('progPct').textContent = '100%';
    } else if (runTarget > 0) {
      const pct = Math.max(0, Math.min(100, Math.round((scraped / runTarget) * 100)));
      bar.style.width = pct + '%';
      $('progPct').textContent = pct + '%';
    } else {
      // No fixed target (scrape ALL): show the running count, ease the bar along.
      bar.style.width = (scraped ? Math.min(95, 8 + scraped * 3) : 6) + '%';
      $('progPct').textContent = scraped + ' found';
    }
    bar.className = 'h-full rounded-full transition-all duration-500 ' + (BAR_COLORS[state] || 'bg-coral');
    $('progNote').textContent = NOTES[state] || '';
  }

  function resetProgress() {
    stopTimer();
    runPaused = false;
    $('progTimer').textContent = '00:00';
    $('progBar').style.width = '0%';
    $('progBar').className = 'h-full w-0 rounded-full bg-coral transition-all duration-500';
    $('progPct').textContent = '0%';
    $('progNote').textContent = 'Ready when you are.';
  }

  function renderStream(previews) {
    const stream = $('leadStream');
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
    $('rowCount').textContent = `rows written: ${previews.length}`;
  }

  async function startScrape(e) {
    e.preventDefault();
    const body = {
      term: termInput().value.trim() || 'plumbers',
      location: locInput().value.trim() || 'Austin, TX',
      max_results: parseInt(maxInput().value, 10) || 20,
      max_all: maxAllInput().checked,
      headless: headlessInput().checked,
    };
    setRunning(true);
    $('runStatus').textContent = 'starting…';
    $('logPanel').classList.remove('hidden');
    $('logOut').textContent = '';
    runTarget = body.max_all ? 0 : (body.max_results || 0);
    runPaused = false;
    setProgress(0, 'running');
    startTimer();
    try {
      const job = await api('/api/scrape', { method: 'POST', body: JSON.stringify(body) });
      activeJob = job.id;
      $('runStatus').textContent = 'a browser window will open — just complete the quick verification if asked.';
      pollJob();
    } catch (err) {
      setRunning(false);
      stopTimer();
      $('runStatus').textContent = 'error: ' + err.message;
    }
  }

  async function pollJob() {
    if (!activeJob) return;
    try {
      const job = await api('/api/scrape/' + activeJob);
      $('logOut').textContent = job.log.join('\n');
      $('logOut').scrollTop = $('logOut').scrollHeight;
      renderStream(job.previews);
      $('runStatus').textContent = `${job.status} · ${job.scraped} found`;

      runPaused = detectPaused(job.log);
      setProgress(job.scraped, runPaused ? 'paused' : 'running');

      if (['done', 'error', 'stopped'].includes(job.status)) {
        setRunning(false);
        stopTimer();
        const ok = job.status === 'done';
        setProgress(job.scraped, ok ? 'done' : 'error');
        $('logStatus').innerHTML = ok
          ? '<span class="h-1.5 w-1.5 rounded-full bg-lime"></span> done'
          : '<span class="h-1.5 w-1.5 rounded-full bg-coral"></span> ' + job.status;
        $('logStatus').className = 'flex items-center gap-1.5 font-mono text-[11px] ' +
          (ok ? 'text-lime' : 'text-coral');
        $('runStatus').textContent = job.message;
        activeJob = null;
        offset = 0;
        loadResults();
        loadStats();
        return;
      }
      pollTimer = setTimeout(pollJob, 1500);
    } catch (err) {
      $('runStatus').textContent = 'lost job: ' + err.message;
      setRunning(false);
      stopTimer();
      activeJob = null;
    }
  }

  async function stopScrape() {
    if (!activeJob) return;
    $('stopBtn').disabled = true;
    $('runStatus').textContent = 'stopping — saving what we have…';
    try { await api('/api/scrape/' + activeJob + '/stop', { method: 'POST' }); } catch (_) {}
    $('stopBtn').disabled = false;
  }

  function wireRun() {
    $('runForm').addEventListener('submit', startScrape);
    $('stopBtn').addEventListener('click', stopScrape);
  }

  /* ── Boot (after the gate clears) ─────────────────────────────────────── */
  function init() {
    wireMaxControls();
    resetProgress();
    wireResults();
    wireRun();
    loadStats();
    loadResults();
  }

  wireSignOut();
  gate();
})();
