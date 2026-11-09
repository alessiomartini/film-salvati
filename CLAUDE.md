# Claude Code instructions

## Project

Catalogo pubblico di film e serie di Alessio. Sito statico senza build (`index.html`, `app.js`,
`style.css`, `js/notes-widget.js`) che legge `data/library.json`, generato da due script Python
stdlib: `scripts/import_sources.py` (export personali -> `data/my-list.json`) e
`scripts/enrich.py` (TMDB -> `data/library.json`). Dettagli in `README.md`.

## Regole

- Gli export personali (`E:\Alessio\Dati-personali`) non entrano mai in git; le caption Instagram
  stanno solo in `cache/` (gitignored). Nel repo e sul sito: titoli, stato, voti, link ai post.
- Il sito è pubblico: niente nomi di persone o dettagli privati (i nomi delle raccolte Instagram
  non si pubblicano, nessun tag di provenienza).
- `data/matches.json`: post Instagram -> lista di titoli `{title, year, type, check?}`, `null` se
  non è un film, `"?"` se il titolo non si capisce dalla caption. Per i post nuovi leggi le
  caption in `cache/ig-posts.json` e aggiungi le righe; i casi dubbi con `"check": true`.
- Script con `python -I`; chiavi API solo in `.env`.
- Verifica: anteprima `film-salvati` in `.claude/launch.json` (porta 8765).
