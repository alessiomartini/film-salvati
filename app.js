// Saved Films: griglia + filtri + scheda (#/t/<id>). Testi del sito in inglese; titoli in lingua originale + inglese. Dati: data/library.json (scripts/enrich.py);
// finché non esiste, data/my-list.json (solo titoli, senza copertine).
'use strict';

const $ = (s) => document.querySelector(s);
const form = $('#filters');
const grid = $('#grid');
const sheet = $('#sheet');
const LANGS = new Intl.DisplayNames(['en'], { type: 'language' });
const KINDS = { flatrate: 'Subscription', free: 'Free', ads: 'Free with ads', rent: 'Rent', buy: 'Buy' };
const COUNTRY = { NL: 'Netherlands', IT: 'Italy' };
// Titolo in lingua originale; quello inglese sotto, se diverso.
const name = (t) => t.original_title || t.title || '';
const english = (t) => (t.original_title && t.title !== t.original_title ? t.title : '');
let all = [];

// Stato modificabile da Alessio: data/overrides.json ({id: stato}) nel repo, scritto con l'API GitHub
// e un token fine-grained (solo Contents di questo repo) salvato nel suo browser. Nessun backend:
// chi non ha il token vede gli stati ma non i pulsanti. Le modifiche non ancora salvate restano nel browser.
const REPO_API = 'https://api.github.com/repos/alessiomartini/film-salvati/contents/data/overrides.json';
const STATUSES = [['to watch', 'To watch'], ['maybe watched', 'Maybe'], ['watched', 'Watched']];
const store = {
  get(k) { try { return localStorage.getItem(k); } catch { return null; } },
  set(k, v) { try { v == null ? localStorage.removeItem(k) : localStorage.setItem(k, v); } catch { /* storage off */ } },
};
let token = store.get('film-salvati.token');
let pending = JSON.parse(store.get('film-salvati.pending') || '{}');
let saveTimer;

const esc = (s) => String(s ?? '').replace(/[&<>"']/g, (c) => `&#${c.charCodeAt(0)};`);
const lang = (code) => { try { return LANGS.of(code); } catch { return code; } };
const hours = (m) => (m ? (m >= 60 ? `${Math.floor(m / 60)}h${String(m % 60).padStart(2, '0')}` : `${m} min`) : '');

async function load() {
  for (const file of ['data/library.json', 'data/my-list.json']) {
    const r = await fetch(file + '?v=1', { cache: 'no-cache' });
    if (r.ok) {
      const data = await r.json();
      const ov = await fetch('data/overrides.json', { cache: 'no-cache' }).then((x) => (x.ok ? x.json() : {})).catch(() => ({}));
      Object.assign(ov, pending);
      return data.map((t, i) => {
        const x = { id: t.id || `t${i}`, genres: [], cast: [], directors: [], providers: {}, links: {}, ratings: {}, ...t };
        if (ov[x.id]) x.status = ov[x.id];
        return x;
      });
    }
  }
  return [];
}

function fillSelect(name, values, label = (v) => v) {
  const sel = form.elements[name];
  for (const v of [...new Set(values)].filter(Boolean).sort((a, b) => String(label(a)).localeCompare(label(b)))) {
    sel.add(new Option(label(v), v));
  }
}

function services(t, country) {
  const p = t.providers[country] || {};
  return ['flatrate', 'free', 'ads'].flatMap((k) => (p[k] || []).map((x) => x.name));
}

function filtered() {
  const f = Object.fromEntries(new FormData(form));
  const q = f.q.trim().toLowerCase();
  const list = all.filter((t) =>
    (!q || [t.title, t.original_title, ...t.cast, ...t.directors].join(' ').toLowerCase().includes(q)) &&
    (!f.status || t.status === f.status) &&
    (!f.type || t.type === f.type) &&
    (!f.genre || t.genres.includes(f.genre)) &&
    (!f.service || services(t, f.country).includes(f.service)) &&
    (!f.runtime || (t.runtime && t.runtime <= +f.runtime)) &&
    (!f.decade || (t.year && Math.floor(t.year / 10) * 10 === +f.decade)) &&
    (!f.lang || t.original_language === f.lang) &&
    (!f.awards || (f.awards === 'oscar' ? t.major_awards?.Oscar : awardText(t))) &&
    (!f.content || (f.content === 'no-sex' ? !hasSex(t) : f.content === 'no-violence' ? !hasViolence(t) : !hasSex(t) && !hasViolence(t))));
  const by = {
    title: (a, b) => name(a).localeCompare(name(b)),
    year: (a, b) => (b.year || 0) - (a.year || 0),
    rating: (a, b) => (b.ratings.tmdb || 0) - (a.ratings.tmdb || 0),
    saves: (a, b) => (b.instagram?.length || 0) - (a.instagram?.length || 0),
    mine: (a, b) => (b.my_rating || 0) - (a.my_rating || 0) || (b.liked ? 1 : 0) - (a.liked ? 1 : 0),
  };
  return list.sort(by[f.sort]);
}

function setStatus(id, status) {
  const t = all.find((x) => x.id === id);
  if (!t || t.status === status) return;
  t.status = status;
  pending[id] = status;
  store.set('film-salvati.pending', JSON.stringify(pending));
  saveInfo(`${Object.keys(pending).length} unsaved…`);
  clearTimeout(saveTimer);
  saveTimer = setTimeout(flush, 2500); // un solo commit per una raffica di clic
  render();
  if (sheet.open) openSheet(t);
}

function saveInfo(text) { $('#save-info').textContent = text; }

const b64 = (s) => btoa(String.fromCharCode(...new TextEncoder().encode(s)));
const unb64 = (s) => new TextDecoder().decode(Uint8Array.from(atob(s.replace(/\n/g, '')), (c) => c.charCodeAt(0)));

async function flush() {
  const batch = { ...pending };
  const n = Object.keys(batch).length;
  if (!n || !token) return;
  const headers = { Authorization: `Bearer ${token}`, Accept: 'application/vnd.github+json' };
  saveInfo('Saving…');
  try {
    const cur = await fetch(REPO_API + '?ref=main', { headers, cache: 'no-store' });
    if (!cur.ok) throw new Error(`GitHub ${cur.status}`);
    const file = await cur.json();
    const data = { ...JSON.parse(unb64(file.content)), ...batch };
    const sorted = Object.fromEntries(Object.keys(data).sort().map((k) => [k, data[k]]));
    const put = await fetch(REPO_API, {
      method: 'PUT', headers,
      body: JSON.stringify({ message: `Stato di ${n} titoli dal sito`, content: b64(JSON.stringify(sorted, null, 1) + '\n'), sha: file.sha, branch: 'main' }),
    });
    if (!put.ok) throw new Error(`GitHub ${put.status}`);
    for (const k in batch) if (pending[k] === batch[k]) delete pending[k];
    store.set('film-salvati.pending', JSON.stringify(pending));
    const left = Object.keys(pending).length;
    saveInfo(left ? `${left} unsaved…` : 'Saved');
    if (left) saveTimer = setTimeout(flush, 2500);
  } catch (err) {
    // mai perdere un clic: restano nel browser e si riprova al prossimo cambio o ricaricamento
    saveInfo(`Not saved (${err.message}), kept in this browser`);
  }
}

function statusButtons(t) {
  return `<div class="status-row">${STATUSES.map(([s, label]) =>
    `<button type="button" data-set="${s}" data-id="${esc(t.id)}" class="${t.status === s ? 'on' : ''}">${label}</button>`).join('')}</div>`;
}

// Bollini: premi importanti (Wikidata), nudità/sesso e violenza (Kids-in-Mind >= 5/10, o TMDB).
function awardText(t) {
  const m = t.major_awards || {};
  return Object.entries(m).map(([k, n]) => (n > 1 ? `${n} ${k}s` : k)).join(', ');
}
const hasSex = (t) => !!t.content?.sex_flag;
const hasViolence = (t) => !!t.content?.violence_flag;

function flags(t) {
  return [
    t.type === 'tv' && '<span class="flag">Series</span>',
    awardText(t) && `<span class="flag award" title="${esc(awardText(t))}">🏆</span>`,
    hasSex(t) && '<span class="flag" title="Nudity / sex">🔞</span>',
    hasViolence(t) && '<span class="flag" title="Violence">🩸</span>',
  ].filter(Boolean).join('');
}

function contentHtml(t) {
  const c = t.content;
  if (!c) return '';
  if (c.source === 'kim') {
    return `<p>Sex/nudity <strong>${c.sex}/10</strong> · Violence/gore <strong>${c.violence}/10</strong> · Language <strong>${c.language}/10</strong>
      · <a href="${esc(c.url)}" target="_blank" rel="noopener">Kids-in-Mind</a></p>`;
  }
  const what = [c.sex_flag && 'nudity/sex', c.violence_flag && 'violence'].filter(Boolean).join(' and ');
  return what ? `<p>Contains ${what} (from TMDB keywords and age-rating descriptors, no detailed score).</p>` : '';
}

const STATUS_BADGE = {
  watched: '<span class="status s-watched">✓ Watched</span>',
  'maybe watched': '<span class="status s-maybe">Maybe watched</span>',
};

function render() {
  const list = filtered();
  $('#count').textContent = `${list.length} of ${all.length} titles`;
  grid.innerHTML = list.map((t) => `
    <div class="cell ${t.status === 'watched' ? 'is-watched' : ''}">
    <button class="card" type="button" data-id="${esc(t.id)}">
      <div class="poster">
        ${STATUS_BADGE[t.status] || ''}
        <div class="flags">${flags(t)}</div>
        ${t.check ? '<span class="badge check" title="Title guessed from the saved post, to be confirmed">?</span>' : ''}
        ${t.poster ? `<img src="${esc(t.poster)}" alt="" loading="lazy">` : esc(name(t))}
      </div>
      <div class="name">${esc(name(t))}</div>
      ${english(t) ? `<div class="en">${esc(english(t))}</div>` : ''}
      <div class="meta">${[t.year, hours(t.runtime), t.ratings.tmdb && `★ ${t.ratings.tmdb}`, t.my_rating && `me ${t.my_rating}/5`, t.liked && '♥'].filter(Boolean).join(' · ')}</div>
    </button>
    ${token ? statusButtons(t) : ''}
    </div>`).join('');
}

function chips(items) {
  return items?.length ? `<ul class="chips">${items.map((x) => `<li>${esc(x)}</li>`).join('')}</ul>` : '';
}

function providersHtml(t) {
  const out = ['NL', 'IT'].map((c) => {
    const p = t.providers[c];
    if (!p) return `<p class="muted">${COUNTRY[c]}: not available to stream.</p>`;
    const rows = Object.entries(KINDS).filter(([k]) => p[k]).map(([k, label]) => `
      <div class="prov"><span class="kind">${label}</span>
        ${p[k].map((x) => `<img src="${esc(x.logo)}" alt="${esc(x.name)}" title="${esc(x.name)}" loading="lazy">`).join('')}
      </div>`).join('');
    return `<p><strong>${COUNTRY[c]}</strong>${p.link ? ` · <a href="${esc(p.link)}" target="_blank" rel="noopener">where to watch</a>` : ''}</p>${rows}`;
  });
  return out.join('');
}

function openSheet(t) {
  const facts = [
    t.year, t.type === 'tv' ? (t.seasons && `${t.seasons} season${t.seasons > 1 ? 's' : ''}`) : hours(t.runtime),
    t.original_language && `original language: ${lang(t.original_language)}`,
    ...Object.entries(t.certification || {}).filter(([, v]) => v).map(([c, v]) => `${c} ${v}`),
  ].filter(Boolean).join(' · ');
  const links = [
    ['Wikipedia', t.links.wikipedia], ['IMDb', t.links.imdb], ['Letterboxd', t.links.letterboxd], ['TMDB', t.links.tmdb],
  ].filter(([, u]) => u).map(([n, u]) => `<a href="${esc(u)}" target="_blank" rel="noopener">${n}</a>`).join(' · ');
  const ratings = Object.entries(t.ratings).filter(([, v]) => v).map(([k, v]) => `${k.toUpperCase()} ${v}`);

  $('#sheet-body').innerHTML = `
    <button class="close" type="button" aria-label="Close">×</button>
    <div class="sheet-head">
      <div class="poster">${t.poster ? `<img src="${esc(t.poster)}" alt="Poster of ${esc(name(t))}">` : esc(name(t))}</div>
      <div>
        <h2>${esc(name(t))}</h2>
        ${english(t) ? `<p class="orig">${esc(english(t))}</p>` : ''}
        <p class="muted">${esc(facts)}</p>
        ${chips(t.genres)}
        ${t.directors.length ? `<p><strong>${t.type === 'tv' ? 'Created by' : 'Director'}:</strong> ${esc(t.directors.join(', '))}</p>` : ''}
        ${ratings.length ? `<p><strong>Ratings:</strong> ${esc(ratings.join(' · '))}</p>` : ''}
        ${t.my_rating || t.liked ? `<p><strong>Me:</strong> ${esc([t.my_rating && `${t.my_rating}/5`, t.liked && '♥ liked'].filter(Boolean).join(' · '))}</p>` : ''}
        ${t.trailer ? `<a class="btn" href="${esc(t.trailer)}" target="_blank" rel="noopener">▶ Trailer</a>` : ''}
        <p><strong>Status:</strong> ${esc(t.status[0].toUpperCase() + t.status.slice(1))}</p>
        ${token ? statusButtons(t) : ''}
        ${t.check ? '<p class="muted">Title guessed from the saved post: to be confirmed.</p>' : ''}
      </div>
    </div>
    ${t.overview ? `<section><h3>Plot</h3><p>${esc(t.overview)}</p></section>` : ''}
    ${awardText(t) || t.awards?.length ? `<section><h3>Awards</h3>
      ${awardText(t) ? `<p>🏆 <strong>${esc(awardText(t))}</strong></p>` : ''}
      ${t.awards?.length ? `<details><summary>All ${t.awards.length} awards (Wikidata)</summary>${chips(t.awards)}</details>` : ''}</section>` : ''}
    ${contentHtml(t) ? `<section><h3>Content</h3>${contentHtml(t)}</section>` : ''}
    ${t.cast.length ? `<section><h3>Cast</h3>${chips(t.cast)}</section>` : ''}
    ${t.tmdb_id ? `<section><h3>Where to watch</h3>${providersHtml(t)}</section>` : ''}
    ${links ? `<section><h3>Pages</h3><p>${links}</p></section>` : ''}
    ${t.instagram?.length ? `<section><h3>Saved Instagram posts</h3><p>${t.instagram.map((u, i) =>
      `<a href="${esc(u)}" target="_blank" rel="noopener">Post ${i + 1}</a>`).join(' · ')}</p></section>` : ''}
    ${t.collection ? `<section><h3>Collection</h3><p>${esc(t.collection)}</p></section>` : ''}
    ${t.similar?.length ? `<section><h3>Similar</h3>${chips(t.similar)}</section>` : ''}
    ${t.keywords?.length ? `<section><h3>Keywords</h3>${chips(t.keywords)}</section>` : ''}`;
  $('#sheet-body .close').onclick = () => sheet.close();
  if (!sheet.open) sheet.showModal();
  sheet.scrollTop = 0;
}

function route() {
  const id = decodeURIComponent(location.hash.match(/^#\/t\/(.+)/)?.[1] || '');
  const t = all.find((x) => x.id === id);
  if (t) openSheet(t);
  else if (sheet.open) sheet.close();
}

// Allegato automatico al Feedback (js/notes-widget.js, SiteNotes.setContext).
window.SiteNotes.setContext(() => {
  const f = Object.fromEntries([...new FormData(form)].filter(([, v]) => v));
  const id = location.hash.match(/^#\/t\/(.+)/)?.[1];
  return { filters: f, title: id && name(all.find((x) => x.id === decodeURIComponent(id)) || {}) };
});

document.addEventListener('click', (e) => {
  const b = e.target.closest('[data-set]');
  if (b) setStatus(b.dataset.id, b.dataset.set);
});
$('#edit').addEventListener('click', () => {
  if (token) {
    if (!confirm('Stop editing on this browser? The GitHub token will be removed from it.')) return;
    token = null;
  } else {
    token = (prompt('GitHub token (fine-grained, Contents read/write on film-salvati only):') || '').trim() || null;
  }
  store.set('film-salvati.token', token);
  $('#edit').textContent = token ? 'Stop editing' : 'Edit';
  render();
  if (token) flush();
});

grid.addEventListener('click', (e) => {
  const card = e.target.closest('.card');
  if (card) location.hash = `#/t/${encodeURIComponent(card.dataset.id)}`;
});
sheet.addEventListener('close', () => { if (location.hash) history.pushState('', '', location.pathname + location.search); });
sheet.addEventListener('click', (e) => { if (e.target === sheet) sheet.close(); });
form.addEventListener('input', render);
form.elements.country.addEventListener('change', () => {
  const sel = form.elements.service;
  sel.length = 1;
  fillSelect('service', all.flatMap((t) => services(t, form.elements.country.value)));
});
window.addEventListener('hashchange', route);

load().then((data) => {
  all = data;
  fillSelect('status', all.map((t) => t.status), (s) => s[0].toUpperCase() + s.slice(1));
  fillSelect('genre', all.flatMap((t) => t.genres));
  fillSelect('service', all.flatMap((t) => services(t, form.elements.country.value)));
  fillSelect('decade', all.map((t) => t.year && Math.floor(t.year / 10) * 10), (d) => `${d}s`);
  fillSelect('lang', all.map((t) => t.original_language), lang);
  $('#edit').textContent = token ? 'Stop editing' : 'Edit';
  if (Object.keys(pending).length) saveInfo(`${Object.keys(pending).length} unsaved…`);
  render();
  route();
  flush();
});
