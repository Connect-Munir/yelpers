/* LeadHarvest — Admin dashboard.
 * Lists all users and lets an admin promote/demote, activate/deactivate,
 * and delete accounts. Every call sends the JWT as a Bearer token and the
 * backend re-checks role == 'admin', so this page is a convenience UI, not
 * the security boundary.
 */
(function () {
  'use strict';

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
        'Authorization': 'Bearer ' + token,
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

  /* ── Gate: only admins past this point ── */
  async function gate() {
    if (!token) return denied('You need to sign in first.');
    try {
      const me = await api('/api/auth/me');
      if (me.role !== 'admin') return denied('Admin access required.');
      $('meLabel').textContent = me.email + ' · admin';
      $('gate').classList.add('hidden');
      $('panel').classList.remove('hidden');
      loadUsers();
    } catch (err) {
      denied(err.message || 'Could not verify access.');
    }
  }

  function denied(msg) {
    $('gateErrorMsg').textContent = msg;
    $('gateError').classList.remove('hidden');
  }

  /* ── Toast ── */
  let toastTimer;
  function toast(msg, ok = true) {
    const t = $('toast');
    t.textContent = msg;
    t.className = 'fixed bottom-6 right-6 rounded-xl border hairline px-4 py-3 text-sm shadow-2xl bg-coal ' +
      (ok ? 'text-lime' : 'text-coral');
    t.classList.remove('hidden');
    clearTimeout(toastTimer);
    toastTimer = setTimeout(() => t.classList.add('hidden'), 2600);
  }

  /* ── Users table ── */
  const PAGE = 50;
  let offset = 0;
  let total = 0;

  const roleBadge = (role) => role === 'admin'
    ? '<span class="font-mono text-[11px] rounded-full bg-lime/15 text-lime px-2 py-0.5">admin</span>'
    : '<span class="font-mono text-[11px] rounded-full bg-paper/10 text-muted px-2 py-0.5">user</span>';

  const statusBadge = (active) => active
    ? '<span class="font-mono text-[11px] text-lime">● active</span>'
    : '<span class="font-mono text-[11px] text-coral">○ inactive</span>';

  function fmtDate(iso) {
    if (!iso) return '—';
    try { return new Date(iso).toLocaleDateString(undefined, { year: 'numeric', month: 'short', day: 'numeric' }); }
    catch { return iso; }
  }

  async function loadUsers() {
    const q = encodeURIComponent($('searchInput').value.trim());
    try {
      const data = await api(`/api/admin/users?limit=${PAGE}&offset=${offset}&search=${q}`);
      total = data.total;
      renderStats(data.items);
      const body = $('usersBody');
      body.innerHTML = '';
      if (!data.items.length) {
        body.innerHTML = '<tr><td colspan="5" class="px-5 py-10 text-center text-muted">No users found.</td></tr>';
      } else {
        for (const u of data.items) body.appendChild(rowFor(u));
      }
      const from = total ? offset + 1 : 0;
      const to = Math.min(offset + PAGE, total);
      $('usersCount').textContent = `${total} user${total === 1 ? '' : 's'}`;
      $('pageInfo').textContent = total ? `${from}–${to} of ${total}` : 'page 1';
      $('prevPage').disabled = offset === 0;
      $('nextPage').disabled = offset + PAGE >= total;
    } catch (err) {
      $('usersBody').innerHTML =
        `<tr><td colspan="5" class="px-5 py-10 text-center text-coral">${esc(err.message)}</td></tr>`;
    }
  }

  // Stats are computed from the current page (cheap, no extra endpoint).
  function renderStats(items) {
    $('statTotal').textContent = total;
    $('statAdmins').textContent = items.filter((u) => u.role === 'admin').length;
    $('statInactive').textContent = items.filter((u) => !u.is_active).length;
  }

  function rowFor(u) {
    const tr = document.createElement('tr');
    tr.className = 'hover:bg-paper/[0.03] transition-colors';
    const toggleRole = u.role === 'admin' ? 'Demote' : 'Make admin';
    const toggleActive = u.is_active ? 'Deactivate' : 'Activate';
    tr.innerHTML = `
      <td class="px-5 py-3">
        <div class="font-semibold text-paper">${esc(u.name)}</div>
        <div class="font-mono text-[11px] text-muted">${esc(u.email)}</div>
      </td>
      <td class="px-5 py-3">${roleBadge(u.role)}</td>
      <td class="px-5 py-3">${statusBadge(u.is_active)}</td>
      <td class="px-5 py-3 text-muted text-[13px]">${fmtDate(u.created_at)}</td>
      <td class="px-5 py-3">
        <div class="flex items-center justify-end gap-2 font-mono text-[11px]">
          <button data-act="role" data-id="${u.id}" data-role="${u.role}" class="rounded-lg border hairline px-2.5 py-1 text-muted hover:text-lime hover:border-lime/40 transition-colors">${toggleRole}</button>
          <button data-act="active" data-id="${u.id}" data-active="${u.is_active}" class="rounded-lg border hairline px-2.5 py-1 text-muted hover:text-ember hover:border-ember/40 transition-colors">${toggleActive}</button>
          <button data-act="delete" data-id="${u.id}" class="rounded-lg border hairline px-2.5 py-1 text-muted hover:text-coral hover:border-coral/40 transition-colors">Delete</button>
        </div>
      </td>`;
    return tr;
  }

  /* ── Row actions ── */
  $('usersBody').addEventListener('click', async (e) => {
    const btn = e.target.closest('button[data-act]');
    if (!btn) return;
    const id = btn.dataset.id;
    const act = btn.dataset.act;
    btn.disabled = true;
    try {
      if (act === 'role') {
        const next = btn.dataset.role === 'admin' ? 'user' : 'admin';
        await api(`/api/admin/users/${id}/role`, { method: 'PATCH', body: JSON.stringify({ role: next }) });
        toast(`Role updated to ${next}.`);
      } else if (act === 'active') {
        const next = btn.dataset.active !== 'true';
        await api(`/api/admin/users/${id}/active`, { method: 'PATCH', body: JSON.stringify({ is_active: next }) });
        toast(next ? 'User activated.' : 'User deactivated.');
      } else if (act === 'delete') {
        if (!confirm('Delete this user permanently? This cannot be undone.')) { btn.disabled = false; return; }
        await api(`/api/admin/users/${id}`, { method: 'DELETE' });
        toast('User deleted.');
      }
      loadUsers();
    } catch (err) {
      toast(err.message || 'Action failed.', false);
      btn.disabled = false;
    }
  });

  /* ── Controls ── */
  let searchTimer;
  $('searchInput').addEventListener('input', () => {
    clearTimeout(searchTimer);
    searchTimer = setTimeout(() => { offset = 0; loadUsers(); }, 300);
  });
  $('refreshBtn').addEventListener('click', loadUsers);
  $('prevPage').addEventListener('click', () => { if (offset > 0) { offset -= PAGE; loadUsers(); } });
  $('nextPage').addEventListener('click', () => { if (offset + PAGE < total) { offset += PAGE; loadUsers(); } });
  $('logoutBtn').addEventListener('click', () => {
    localStorage.removeItem(TOKEN_KEY);
    localStorage.removeItem(USER_KEY);
    location.href = 'index.html';
  });

  gate();
})();
