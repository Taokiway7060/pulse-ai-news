/* =========================================================
   Pulse — AI News  (frontend logic)
   - loads data/news.json
   - renders hero + card grid
   - category filter, search, theme toggle (in-memory only;
     localStorage intentionally avoided per host constraints)
   ========================================================= */

(() => {
  const $ = (sel) => document.querySelector(sel);
  const grid = $('#grid');
  const heroWrap = $('#hero-card-wrap');
  const chipsEl = $('#chips');
  const searchInput = $('#search');
  const emptyMsg = $('#empty');
  const generatedAtEl = $('#generated-at');
  const themeToggle = $('#theme-toggle');

  const state = {
    items: [],
    filtered: [],
    category: 'All',
    query: '',
    generatedAt: null,
  };

  // ---------- helpers ----------
  function escapeHtml(s) {
    return (s ?? '').replace(/[&<>"']/g, (c) => ({
      '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;'
    }[c]));
  }

  function relativeTime(iso) {
    if (!iso) return 'recent';
    const then = new Date(iso);
    const now = new Date();
    const diffMs = now - then;
    const mins = Math.floor(diffMs / 60000);
    if (mins < 1) return 'just now';
    if (mins < 60) return `${mins}m ago`;
    const hrs = Math.floor(mins / 60);
    if (hrs < 24) return `${hrs}h ago`;
    const days = Math.floor(hrs / 24);
    if (days < 7) return `${days}d ago`;
    return then.toLocaleDateString(undefined, { month: 'short', day: 'numeric' });
  }

  function applyFilter() {
    const q = state.query.trim().toLowerCase();
    state.filtered = state.items.filter((it) => {
      const catOk = state.category === 'All' || it.category === state.category;
      if (!catOk) return false;
      if (!q) return true;
      const hay = `${it.title} ${it.summary} ${it.source} ${it.category}`.toLowerCase();
      return hay.includes(q);
    });
    render();
  }

  // ---------- rendering ----------
  function renderHero(item) {
    if (!item) {
      heroWrap.innerHTML = '';
      return;
    }
    const bg = item.image
      ? `style="background-image:linear-gradient(135deg, rgba(7,7,13,0.0), rgba(7,7,13,0.55)), url('${escapeHtml(item.image)}')"`
      : '';
    heroWrap.innerHTML = `
      <a class="hero-card glass" href="${escapeHtml(item.url)}" target="_blank" rel="noopener">
        <div class="hero-image" ${bg}></div>
        <div class="hero-body">
          <div class="meta-row">
            <span class="cat-badge" data-cat="${escapeHtml(item.category)}">${escapeHtml(item.category)}</span>
            <span>·</span>
            <span>${escapeHtml(item.source)}</span>
            <span>·</span>
            <span>${relativeTime(item.published)}</span>
          </div>
          <h3>${escapeHtml(item.title)}</h3>
          <p>${escapeHtml(item.summary || '')}</p>
        </div>
      </a>
    `;
  }

  function renderGrid(items) {
    grid.innerHTML = items.map((it) => `
      <a class="card" href="${escapeHtml(it.url)}" target="_blank" rel="noopener">
        <div class="meta-row">
          <span class="cat-badge" data-cat="${escapeHtml(it.category)}">${escapeHtml(it.category)}</span>
        </div>
        <h4>${escapeHtml(it.title)}</h4>
        <p>${escapeHtml(it.summary || '')}</p>
        <div class="card-footer">
          <span class="card-source">${escapeHtml(it.source)}</span>
          <span>${relativeTime(it.published)}</span>
        </div>
      </a>
    `).join('');
  }

  function render() {
    const items = state.filtered;
    if (items.length === 0) {
      heroWrap.innerHTML = '';
      grid.innerHTML = '';
      emptyMsg.classList.remove('hidden');
      return;
    }
    emptyMsg.classList.add('hidden');

    // Hero only when nothing is filtering (clean default view)
    const isDefault = state.category === 'All' && !state.query;
    if (isDefault) {
      renderHero(items[0]);
      renderGrid(items.slice(1));
    } else {
      renderHero(null);
      renderGrid(items);
    }
  }

  function renderChips(categories) {
    const all = ['All', ...categories];
    chipsEl.innerHTML = all.map((c) => `
      <button class="chip ${c === state.category ? 'is-active' : ''}" data-cat="${escapeHtml(c)}">
        ${escapeHtml(c)}
      </button>
    `).join('');
    chipsEl.querySelectorAll('.chip').forEach((btn) => {
      btn.addEventListener('click', () => {
        state.category = btn.dataset.cat;
        renderChips(categories);
        applyFilter();
      });
    });
  }

  // ---------- theme toggle ----------
  themeToggle.addEventListener('click', () => {
    const cur = document.documentElement.dataset.theme || 'dark';
    document.documentElement.dataset.theme = cur === 'dark' ? 'light' : 'dark';
  });

  // ---------- search ----------
  let searchT;
  searchInput.addEventListener('input', (e) => {
    clearTimeout(searchT);
    searchT = setTimeout(() => {
      state.query = e.target.value;
      applyFilter();
    }, 120);
  });

  // ---------- load ----------
  // Prefer the inline data shim (works over file://); fall back to fetch over HTTP.
  const dataPromise = window.NEWS_DATA
    ? Promise.resolve(window.NEWS_DATA)
    : fetch('data/news.json', { cache: 'no-store' }).then((r) => {
        if (!r.ok) throw new Error('news.json missing — run build.py');
        return r.json();
      });

  dataPromise
    .then((data) => {
      state.items = data.items || [];
      state.filtered = state.items.slice();
      state.generatedAt = data.generated_at;

      if (state.generatedAt) {
        const d = new Date(state.generatedAt);
        const fmt = d.toLocaleString(undefined, {
          weekday: 'long', month: 'short', day: 'numeric',
          hour: 'numeric', minute: '2-digit'
        });
        generatedAtEl.textContent = `Live · updated ${fmt}`;
      } else {
        generatedAtEl.textContent = 'Live · just now';
      }

      const cats = data.categories || Array.from(new Set(state.items.map((it) => it.category)));
      renderChips(cats);
      render();
    })
    .catch((err) => {
      console.error(err);
      generatedAtEl.textContent = 'Could not load news.json yet';
      grid.innerHTML = `
        <div class="card glass" style="grid-column: 1 / -1;">
          <h4>News data not generated yet</h4>
          <p>Run <code>python build.py</code> in the project folder to fetch and generate the latest stories. Once <code>data/news.json</code> exists, this page will populate automatically.</p>
        </div>`;
    });
})();
