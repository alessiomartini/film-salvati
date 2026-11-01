# Saved Films (Film salvati)

La mia libreria di film e serie: cosa ho visto, cosa voglio vedere, e per ogni titolo una scheda
con copertina, trama, regista, attori, durata, lingua originale, voti, trailer, dove vederlo in
streaming (Olanda e Italia). Il sito è in inglese, con i titoli in lingua originale + inglese. Ci sono anche i link alle schede su IMDb, Letterboxd, TMDB e ai post Instagram
da cui l'ho salvato.

Sito statico senza build (`index.html`, `app.js`, `style.css`) + due script Python (solo stdlib).

## Come si aggiorna

```bash
python -I scripts/import_sources.py   # export personali -> data/my-list.json
python -I scripts/enrich.py           # TMDB -> data/library.json (serve TMDB_KEY in .env)
```

1. `import_sources.py` legge l'export Instagram più recente in `E:\Alessio\Dati-personali\meta\`
   (le raccolte elencate in `.env` come `IG_COLLECTIONS=nome1|nome2`). Il titolo di ogni post sta in
   `data/matches.json`: i post nuovi vengono elencati come "manca in matches.json" e vanno
   aggiunti lì (a mano o chiedendo a Claude, che legge le caption in `cache/ig-posts.json`).
2. `enrich.py` cerca ogni titolo su TMDB e scrive `data/library.json`. Le risposte restano in
   `cache/` (gitignored); `--refresh` le riscarica, `--limit N` prova su pochi titoli.

Chiave TMDB: themoviedb.org → Impostazioni → API, poi nel file `.env` (mai in git):

```
TMDB_KEY=...
IG_COLLECTIONS=...
```

## Anteprima locale

```bash
python -m http.server 8765
```

e apri http://localhost:8765. Senza `library.json` il sito mostra solo i titoli di `my-list.json`.

## Privacy

Gli export grezzi restano in `E:\Alessio\Dati-personali` e non entrano mai nel repo: qui vanno
solo titoli, stato e link ai post. Le caption Instagram non vengono ripubblicate.

Feedback dal sito: widget in `js/notes-widget.js`, salvato nel backend unico `site-notes`.
