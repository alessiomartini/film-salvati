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

const esc = (s) => String(s ?? '').replace(/[&<>"']/g, (c) => `&#${c.charCodeAt(0)};`);
const lang = (code) => { try { return LANGS.of(code); } catch { return code; } };
const hours = (m) => (m ? (m >= 60 ? `${Math.floor(m / 60)}h${String(m % 60).padStart(2, '0')}` : `${m} min`) : '');

async function load() {
  for (const file of ['data/library.json', 'data/my-list.json']) {
    const r = await fetch(file + '?v=1', { cache: 'no-cache' });
    if (r.ok) {
      const data = await r.json();
      return data.map((t, i) => ({ id: t.id || `t${i}`, genres: [], cast: [], directors: [], providers: {}, links: {}, ratings: {}, ...t }));
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
    (!f.lang || t.original_language === f.lang));
  const by = {
    title: (a, b) => name(a).localeCompare(name(b)),
    year: (a, b) => (b.year || 0) - (a.year || 0),
    rating: (a, b) => (b.ratings.tmdb || 0) - (a.ratings.tmdb || 0),
    saves: (a, b) => (b.instagram?.length || 0) - (a.instagram?.length || 0),
    mine: (a, b) => (b.my_rating || 0) - (a.my_rating || 0) || (b.liked ? 1 : 0) - (a.liked ? 1 : 0),
  };
  return list.sort(by[f.sort]);
}

function render() {
  const list = filtered();
  $('#count').textContent = `${list.length} of ${all.length} titles`;
  grid.innerHTML = list.map((t) => `
    <button class="card" type="button" data-id="${esc(t.id)}">
      <div class="poster">
        ${t.type === 'tv' ? '<span class="badge">Series</span>' : ''}
        ${t.check ? '<span class="badge check" title="Title guessed from the saved post, to be confirmed">?</span>' : ''}
        ${t.poster ? `<img src="${esc(t.poster)}" alt="" loading="lazy">` : esc(name(t))}
      </div>
      <div class="name">${esc(name(t))}</div>
      ${english(t) ? `<div class="en">${esc(english(t))}</div>` : ''}
      <div class="meta">${[t.year, hours(t.runtime), t.ratings.tmdb && `★ ${t.ratings.tmdb}`, t.my_rating && `me ${t.my_rating}/5`, t.liked && '♥'].filter(Boolean).join(' · ')}</div>
    </button>`).join('');
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
        ${t.check ? '<p class="muted">Title guessed from the saved post: to be confirmed.</p>' : ''}
      </div>
    </div>
    ${t.overview ? `<section><h3>Plot</h3><p>${esc(t.overview)}</p></section>` : ''}
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

// Allegato automatico al Feedback (js/notes-widget.js).
window.feedbackContext = () => {
  const f = Object.fromEntries([...new FormData(form)].filter(([, v]) => v));
  const id = location.hash.match(/^#\/t\/(.+)/)?.[1];
  return { filters: f, title: id && name(all.find((x) => x.id === decodeURIComponent(id)) || {}) };
};

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
  render();
  route();
});
