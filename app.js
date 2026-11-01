// Film salvati: griglia + filtri + scheda (#/t/<id>). Dati: data/library.json (scripts/enrich.py);
// finché non esiste, data/my-list.json (solo titoli, senza copertine).
'use strict';

const $ = (s) => document.querySelector(s);
const form = $('#filters');
const grid = $('#grid');
const sheet = $('#sheet');
const LANGS = new Intl.DisplayNames(['it'], { type: 'language' });
const KINDS = { flatrate: 'Abbonamento', free: 'Gratis', ads: 'Gratis con pub', rent: 'Noleggio', buy: 'Acquisto' };
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
    title: (a, b) => (a.title || '').localeCompare(b.title || ''),
    year: (a, b) => (b.year || 0) - (a.year || 0),
    rating: (a, b) => (b.ratings.tmdb || 0) - (a.ratings.tmdb || 0),
    saves: (a, b) => (b.instagram?.length || 0) - (a.instagram?.length || 0),
  };
  return list.sort(by[f.sort]);
}

function render() {
  const list = filtered();
  $('#count').textContent = `${list.length} di ${all.length} titoli`;
  grid.innerHTML = list.map((t) => `
    <button class="card" type="button" data-id="${esc(t.id)}">
      <div class="poster">
        ${t.type === 'tv' ? '<span class="badge">Serie</span>' : ''}
        ${t.check ? '<span class="badge check" title="Titolo riconosciuto dal post con un dubbio">?</span>' : ''}
        ${t.poster ? `<img src="${esc(t.poster)}" alt="" loading="lazy">` : esc(t.title)}
      </div>
      <div class="name">${esc(t.title)}</div>
      <div class="meta">${[t.year, hours(t.runtime), t.ratings.tmdb && `★ ${t.ratings.tmdb}`].filter(Boolean).join(' · ')}</div>
    </button>`).join('');
}

function chips(items) {
  return items?.length ? `<ul class="chips">${items.map((x) => `<li>${esc(x)}</li>`).join('')}</ul>` : '';
}

function providersHtml(t) {
  const out = ['NL', 'IT'].map((c) => {
    const p = t.providers[c];
    if (!p) return `<p class="muted">${c === 'NL' ? 'Olanda' : 'Italia'}: non disponibile in streaming.</p>`;
    const rows = Object.entries(KINDS).filter(([k]) => p[k]).map(([k, label]) => `
      <div class="prov"><span class="kind">${label}</span>
        ${p[k].map((x) => `<img src="${esc(x.logo)}" alt="${esc(x.name)}" title="${esc(x.name)}" loading="lazy">`).join('')}
      </div>`).join('');
    return `<p><strong>${c === 'NL' ? 'Olanda' : 'Italia'}</strong>${p.link ? ` · <a href="${esc(p.link)}" target="_blank" rel="noopener">dove guardarlo</a>` : ''}</p>${rows}`;
  });
  return out.join('');
}

function openSheet(t) {
  const facts = [
    t.year, t.type === 'tv' ? (t.seasons && `${t.seasons} stagioni`) : hours(t.runtime),
    t.original_language && `lingua originale: ${lang(t.original_language)}`,
    ...Object.entries(t.certification || {}).filter(([, v]) => v).map(([c, v]) => `${c} ${v}`),
  ].filter(Boolean).join(' · ');
  const links = [
    ['Wikipedia', t.links.wikipedia], ['IMDb', t.links.imdb], ['Letterboxd', t.links.letterboxd], ['TMDB', t.links.tmdb],
  ].filter(([, u]) => u).map(([n, u]) => `<a href="${esc(u)}" target="_blank" rel="noopener">${n}</a>`).join(' · ');
  const ratings = Object.entries(t.ratings).filter(([, v]) => v).map(([k, v]) => `${k.toUpperCase()} ${v}`);

  $('#sheet-body').innerHTML = `
    <button class="close" type="button" aria-label="Chiudi">×</button>
    <div class="sheet-head">
      <div class="poster">${t.poster ? `<img src="${esc(t.poster)}" alt="Copertina di ${esc(t.title)}">` : esc(t.title)}</div>
      <div>
        <h2>${esc(t.title)}</h2>
        ${t.original_title && t.original_title !== t.title ? `<p class="orig">${esc(t.original_title)}</p>` : ''}
        <p class="muted">${esc(facts)}</p>
        ${chips(t.genres)}
        ${t.directors.length ? `<p><strong>${t.type === 'tv' ? 'Ideata da' : 'Regia'}:</strong> ${esc(t.directors.join(', '))}</p>` : ''}
        ${ratings.length ? `<p><strong>Voti:</strong> ${esc(ratings.join(' · '))}</p>` : ''}
        ${t.trailer ? `<a class="btn" href="${esc(t.trailer)}" target="_blank" rel="noopener">▶ Trailer</a>` : ''}
        ${t.check ? '<p class="muted">Titolo riconosciuto dal post con un dubbio: da confermare.</p>' : ''}
      </div>
    </div>
    ${t.overview ? `<section><h3>Trama</h3><p>${esc(t.overview)}</p></section>` : ''}
    ${t.cast.length ? `<section><h3>Attori</h3>${chips(t.cast)}</section>` : ''}
    ${t.tmdb_id ? `<section><h3>Dove vederlo</h3>${providersHtml(t)}</section>` : ''}
    ${links ? `<section><h3>Schede</h3><p>${links}</p></section>` : ''}
    ${t.instagram?.length ? `<section><h3>Post Instagram salvati</h3><p>${t.instagram.map((u, i) =>
      `<a href="${esc(u)}" target="_blank" rel="noopener">Post ${i + 1}</a>`).join(' · ')}</p></section>` : ''}
    ${t.collection ? `<section><h3>Saga</h3><p>${esc(t.collection)}</p></section>` : ''}
    ${t.similar?.length ? `<section><h3>Simili</h3>${chips(t.similar)}</section>` : ''}
    ${t.keywords?.length ? `<section><h3>Temi</h3>${chips(t.keywords)}</section>` : ''}`;
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
  return { filters: f, title: id && all.find((x) => x.id === decodeURIComponent(id))?.title };
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
  fillSelect('status', all.map((t) => t.status));
  fillSelect('genre', all.flatMap((t) => t.genres));
  fillSelect('service', all.flatMap((t) => services(t, form.elements.country.value)));
  fillSelect('decade', all.map((t) => t.year && Math.floor(t.year / 10) * 10), (d) => `Anni ${d}`);
  fillSelect('lang', all.map((t) => t.original_language), lang);
  render();
  route();
});
