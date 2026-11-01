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
- Ogni modifica a CSS/JS: alza `?v=` in `index.html` (cache-busting).
- Verifica: anteprima `film-salvati` in `.claude/launch.json` (porta 8765), controlla anche 375px.

## Roadmap, idee e progressi

`ROADMAP.md` nella root è l'**unico** file per todo, idee, decisioni e diario del progetto
(niente `FUTURE-ARCHITECTURE.md`, `IDEE.md`, `TODO.md`). È letto da https://alessiomartini.github.io/projects-overview/.
Sezioni: `## <fase>` (checkbox, contano nella percentuale), `## Idee` (checkbox, non contano),
`## Decisioni e cose provate` (prosa: scartato/rimandato e perché, provato e annullato, limiti e bug noti), `## Log`.

- Alla fine di ogni sessione di lavoro (prima del commit finale), aggiorna `ROADMAP.md`:
  - spunta (`- [x]`) i punti completati in questa sessione;
  - aggiungi come `- [ ]` i nuovi compiti nella fase giusta, e le idee non decise in `## Idee`;
  - annota in `## Decisioni e cose provate` ciò che è stato scartato, rimandato o annullato, col perché;
  - aggiungi in cima a `## Log` una riga `- AAAA-MM-GG: <cosa è stato fatto, in una frase>`
    (se esiste già una riga con la data di oggi, estendila invece di crearne un'altra).
- Non riscrivere né riordinare le voci esistenti senza motivo; non cancellare le voci completate.
- Includi l'aggiornamento di `ROADMAP.md` nello stesso commit del lavoro.
