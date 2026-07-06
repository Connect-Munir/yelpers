(function () {
  'use strict';

  /* ────────────────────────────────────────────────────────────
     LeadHarvest — Auth (login / signup) modals + nav user menu
     Demo client-side only. Wire the fetch() calls in submit()
     to your FastAPI backend when the endpoints are ready.
  ──────────────────────────────────────────────────────────── */

  const TOKEN_KEY = 'lh.authToken';
  const USER_KEY  = 'lh.user';

  // Same origin when served by the backend; fall back to localhost:8000 if the
  // page was opened straight from disk (file://).
  const API = location.protocol === 'file:' ? 'http://127.0.0.1:8000' : '';

  // Inline SVG icons (Lucide-style)
  const ICON = {
    eye:    '<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M2 12s3-7 10-7 10 7 10 7-3 7-10 7-10-7-10-7Z"/><circle cx="12" cy="12" r="3"/></svg>',
    eyeOff: '<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M9.88 9.88a3 3 0 1 0 4.24 4.24"/><path d="M10.73 5.08A10.43 10.43 0 0 1 12 5c7 0 10 7 10 7a13.16 13.16 0 0 1-1.67 2.68"/><path d="M6.61 6.61A13.526 13.526 0 0 0 2 12s3 7 10 7a9.74 9.74 0 0 0 5.39-1.61"/><line x1="2" x2="22" y1="2" y2="22"/></svg>',
    alert:  '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" class="shrink-0"><circle cx="12" cy="12" r="10"/><line x1="12" x2="12" y1="8" y2="12"/><line x1="12" x2="12.01" y1="16" y2="16"/></svg>',
  };

  const $  = (sel, root = document) => root.querySelector(sel);
  const $$ = (sel, root = document) => Array.from(root.querySelectorAll(sel));

  const loginModal  = $('#loginModal');
  const signupModal = $('#signupModal');
  const loginForm   = $('#loginForm');
  const signupForm  = $('#signupForm');

  let lastFocused = null;
  let activeModal = null;

  /* ── Modal open / close + focus management ── */
  const openModal = (modal) => {
    if (activeModal) activeModal.classList.add('hidden');
    lastFocused = document.activeElement;
    modal.classList.remove('hidden', 'modal-out');
    modal.setAttribute('aria-hidden', 'false');
    document.body.classList.add('modal-open');
    activeModal = modal;
    // focus first field on next frame (after animation start)
    requestAnimationFrame(() => {
      const first = $('input:not([type=checkbox]), input', modal);
      if (first) first.focus();
    });
  };

  const closeModal = (modal) => {
    if (!modal) return;
    modal.classList.add('modal-out');
    setTimeout(() => {
      modal.classList.add('hidden');
      modal.classList.remove('modal-out');
      modal.setAttribute('aria-hidden', 'true');
      document.body.classList.remove('modal-open');
      activeModal = null;
      clearErrors(modal);
      if (lastFocused && lastFocused.focus) lastFocused.focus();
    }, 250);
  };

  const switchModal = (toName) => {
    const from = activeModal;
    const to = toName === 'signup' ? signupModal : loginModal;
    if (from === to) return;
    if (from) {
      from.classList.add('modal-out');
      setTimeout(() => {
        from.classList.add('hidden');
        from.classList.remove('modal-out');
        from.setAttribute('aria-hidden', 'true');
        clearErrors(from);
        openModal(to);
      }, 220);
    } else {
      openModal(to);
    }
  };

  /* ── Focus trap (Tab cycling) ── */
  const trapFocus = (e) => {
    if (e.key !== 'Tab' || !activeModal) return;
    const focusables = $$(
      'a[href], button:not([disabled]), input:not([disabled]), [tabindex]:not([tabindex="-1"])',
      activeModal
    ).filter(el => el.offsetParent !== null);
    if (!focusables.length) return;
    const first = focusables[0];
    const last = focusables[focusables.length - 1];
    if (e.shiftKey && document.activeElement === first) {
      e.preventDefault(); last.focus();
    } else if (!e.shiftKey && document.activeElement === last) {
      e.preventDefault(); first.focus();
    }
  };

  document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape' && activeModal) closeModal(activeModal);
    else trapFocus(e);
  });

  /* ── Triggers ── */
  $('#loginBtn')?.addEventListener('click', () => openModal(loginModal));
  $('#signupBtn')?.addEventListener('click', () => openModal(signupModal));
  $('#loginBtnMobile')?.addEventListener('click', () => { closeMobileMenu(); openModal(loginModal); });
  $('#signupBtnMobile')?.addEventListener('click', () => { closeMobileMenu(); openModal(signupModal); });

  // Close buttons, overlay clicks, switch links
  $$('[data-close-modal]').forEach(btn =>
    btn.addEventListener('click', () => closeModal(btn.closest('.modal')))
  );
  [loginModal, signupModal].forEach(modal => {
    $('.modal-overlay', modal)?.addEventListener('click', () => closeModal(modal));
  });
  $$('[data-switch]').forEach(btn =>
    btn.addEventListener('click', () => switchModal(btn.dataset.switch))
  );

  const closeMobileMenu = () => {
    const menu = $('#mobileMenu');
    const toggle = $('#navToggle');
    if (menu && !menu.classList.contains('hidden')) {
      menu.classList.add('hidden');
      toggle?.setAttribute('aria-expanded', 'false');
    }
  };

  /* ── Password show / hide toggles ── */
  $$('[data-toggle-password]').forEach(btn => {
    btn.innerHTML = ICON.eye;
    btn.addEventListener('click', () => {
      const input = btn.parentElement.querySelector('input');
      const show = input.type === 'password';
      input.type = show ? 'text' : 'password';
      btn.innerHTML = show ? ICON.eyeOff : ICON.eye;
      btn.setAttribute('aria-label', show ? 'Hide password' : 'Show password');
      input.focus();
    });
  });

  /* ── Inline error helpers ── */
  const setError = (field, msg) => {
    const wrap = field.closest('[data-field]') || field.parentElement;
    const input = wrap.querySelector('input');
    const err = wrap.querySelector('[data-error]') ||
                wrap.parentElement.querySelector('[data-error]');
    if (input) input.classList.add('border-coral', 'ring-1', 'ring-coral/40');
    if (err) {
      err.innerHTML = ICON.alert + '<span>' + msg + '</span>';
      err.classList.remove('hidden');
      err.classList.add('flex');
    }
  };

  const clearError = (field) => {
    const wrap = field.closest('[data-field]') || field.parentElement;
    const input = wrap.querySelector('input');
    const err = wrap.querySelector('[data-error]') ||
                wrap.parentElement.querySelector('[data-error]');
    if (input) input.classList.remove('border-coral', 'ring-1', 'ring-coral/40');
    if (err) { err.classList.add('hidden'); err.classList.remove('flex'); err.innerHTML = ''; }
  };

  const clearErrors = (modal) => {
    $$('input', modal).forEach(i => i.classList.remove('border-coral', 'ring-1', 'ring-coral/40'));
    $$('[data-error]', modal).forEach(e => { e.classList.add('hidden'); e.classList.remove('flex'); e.innerHTML = ''; });
    const fe = $('[data-form-error]', modal);
    if (fe) { fe.classList.add('hidden'); fe.classList.remove('flex'); fe.textContent = ''; }
  };

  const showFormError = (form, msg) => {
    const fe = form.querySelector('[data-form-error]');
    if (fe) { fe.innerHTML = ICON.alert + '<span>' + msg + '</span>'; fe.classList.remove('hidden'); fe.classList.add('flex'); }
  };

  const isEmail = (v) => /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(v);

  // Clear a field's error as the user fixes it
  $$('#loginModal input, #signupModal input').forEach(input => {
    input.addEventListener('input', () => clearError(input));
  });

  /* ── Password strength meter (signup) ── */
  const strengthOf = (pw) => {
    let score = 0;
    if (pw.length >= 8) score++;
    if (/[a-z]/.test(pw) && /[A-Z]/.test(pw)) score++;
    if (/\d/.test(pw)) score++;
    if (/[^A-Za-z0-9]/.test(pw)) score++;
    return score; // 0..4
  };

  const STRENGTH = [
    { label: '—',      color: '' },
    { label: 'Weak',   color: 'bg-coral' },
    { label: 'Fair',   color: 'bg-ember' },
    { label: 'Good',   color: 'bg-lime' },
    { label: 'Strong', color: 'bg-lime' },
  ];

  const pwInput = $('#signupPassword');
  const strengthWrap = $('[data-strength]');
  if (pwInput && strengthWrap) {
    const bars = $$('[data-bar]', strengthWrap);
    const label = $('[data-strength-label]', strengthWrap);
    pwInput.addEventListener('input', () => {
      const score = pwInput.value ? strengthOf(pwInput.value) : 0;
      bars.forEach((bar, i) => {
        bar.className = 'h-1 rounded-full transition-colors ' +
          (i < score ? STRENGTH[score].color : 'bg-paper/10');
      });
      label.textContent = pwInput.value ? STRENGTH[score].label : '—';
    });
  }

  /* ── Submit button busy state ── */
  const setBusy = (form, busy, busyText) => {
    const btn = form.querySelector('[data-submit]');
    const spinner = btn.querySelector('[data-spinner]');
    const label = btn.querySelector('[data-label]');
    btn.disabled = busy;
    spinner.classList.toggle('hidden', !busy);
    if (busy) { btn.dataset.prevLabel = label.textContent; label.textContent = busyText; }
    else if (btn.dataset.prevLabel) { label.textContent = btn.dataset.prevLabel; }
  };

  /* ── Login submit ── */
  loginForm.addEventListener('submit', async (e) => {
    e.preventDefault();
    clearErrors(loginModal);
    const email = $('#loginEmail');
    const password = $('#loginPassword');
    let ok = true;
    if (!isEmail(email.value.trim())) { setError(email, 'Enter a valid email address.'); ok = false; }
    if (!password.value) { setError(password, 'Password is required.'); ok = false; }
    if (!ok) return;

    setBusy(loginForm, true, 'Signing in…');
    try {
      const res = await fetch(API + '/api/auth/login', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email: email.value, password: password.value })
      });
      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        throw new Error(err.detail || 'Invalid email or password.');
      }
      const data = await res.json();
      signIn(data.token, data.user);
      closeModal(loginModal);
      loginForm.reset();
    } catch (err) {
      showFormError(loginForm, err.message || 'Sign in failed. Please try again.');
    } finally {
      setBusy(loginForm, false);
    }
  });

  /* ── Signup submit ── */
  signupForm.addEventListener('submit', async (e) => {
    e.preventDefault();
    clearErrors(signupModal);
    const name = $('#signupName');
    const email = $('#signupEmail');
    const password = $('#signupPassword');
    const confirm = $('#signupPasswordConfirm');
    const terms = $('#signupTerms');
    let ok = true;

    if (!name.value.trim()) { setError(name, 'Tell us your name.'); ok = false; }
    if (!isEmail(email.value.trim())) { setError(email, 'Enter a valid email address.'); ok = false; }
    if (password.value.length < 8) { setError(password, 'Use at least 8 characters.'); ok = false; }
    else if (strengthOf(password.value) < 2) { setError(password, 'Add a mix of letters and numbers.'); ok = false; }
    if (confirm.value !== password.value) { setError(confirm, 'Passwords do not match.'); ok = false; }
    if (!terms.checked) { setError(terms, 'Please accept the terms to continue.'); ok = false; }
    if (!ok) return;

    setBusy(signupForm, true, 'Creating account…');
    try {
      const res = await fetch(API + '/api/auth/signup', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ name: name.value, email: email.value, password: password.value })
      });
      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        throw new Error(err.detail || 'Could not create account.');
      }
      const data = await res.json();
      signIn(data.token, data.user);
      closeModal(signupModal);
      signupForm.reset();
      $('[data-strength-label]')?.replaceChildren(document.createTextNode('—'));
    } catch (err) {
      showFormError(signupForm, err.message || 'Sign up failed. Please try again.');
    } finally {
      setBusy(signupForm, false);
    }
  });

  /* ── Auth session state ── */
  const signIn = (token, user) => {
    localStorage.setItem(TOKEN_KEY, token);
    localStorage.setItem(USER_KEY, JSON.stringify(user));
    updateAuthUI();
  };

  const signOut = () => {
    localStorage.removeItem(TOKEN_KEY);
    localStorage.removeItem(USER_KEY);
    closeUserDropdown();
    updateAuthUI();
  };

  const getUser = () => {
    try { return JSON.parse(localStorage.getItem(USER_KEY) || 'null'); }
    catch { return null; }
  };

  const initials = (user) => {
    const base = (user?.name || user?.email || 'U').trim();
    const parts = base.split(/[\s@._-]+/).filter(Boolean);
    return ((parts[0]?.[0] || 'U') + (parts[1]?.[0] || '')).toUpperCase();
  };

  /* ── Nav: logged-out vs user menu ── */
  const loggedOut = $('#authLoggedOut');
  const userMenu  = $('#userMenu');
  const userMenuBtn = $('#userMenuBtn');
  const userDropdown = $('#userDropdown');

  const updateAuthUI = () => {
    const user = getUser();
    const signedIn = !!localStorage.getItem(TOKEN_KEY);
    if (signedIn && user) {
      loggedOut?.classList.add('hidden');
      userMenu?.classList.remove('hidden');
      $('#userAvatar').textContent = initials(user);
      $('#userLabel').textContent = user.name || user.email;
      $('#userMenuName').textContent = user.name || 'Account';
      $('#userMenuEmail').textContent = user.email || '';
      // Admin-only entry to the admin panel
      const adminLink = $('#adminLink');
      if (adminLink) {
        const isAdmin = user.role === 'admin';
        adminLink.classList.toggle('hidden', !isAdmin);
        adminLink.classList.toggle('flex', isAdmin);
      }
    } else {
      loggedOut?.classList.remove('hidden');
      userMenu?.classList.add('hidden');
    }
  };

  const closeUserDropdown = () => {
    userDropdown?.classList.add('hidden');
    userMenuBtn?.setAttribute('aria-expanded', 'false');
  };

  userMenuBtn?.addEventListener('click', (e) => {
    e.stopPropagation();
    const open = userDropdown.classList.toggle('hidden') === false;
    userMenuBtn.setAttribute('aria-expanded', String(open));
  });
  document.addEventListener('click', (e) => {
    if (userMenu && !userMenu.contains(e.target)) closeUserDropdown();
  });
  $('#logoutBtn')?.addEventListener('click', signOut);

  // Sync across tabs
  window.addEventListener('storage', updateAuthUI);

  updateAuthUI();
})();
