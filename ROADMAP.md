# Roadmap

<!--
Unico file per il futuro e il passato del progetto, letto da Projects Overview
(https://alessiomartini.github.io/projects-overview/). Sezioni:
- "## <fase>": checkbox "- [ ]" / "- [x]", danno la percentuale di avanzamento
- "## Idee": checkbox, mostrate a parte, NON contano nella percentuale
- "## Decisioni e cose provate": prosa (scartato/rimandato e perché, provato e annullato, limiti e bug noti);
  niente checkbox, così non conta. Documenti di progetto lunghi in docs/, con un link da qui
- "## Log": diario, "- AAAA-MM-GG: testo", una riga per giorno, la più recente in alto
-->

## Setup
- [x] Repo `film-salvati` con README, CLAUDE.md, ROADMAP
- [x] Scheda in projects-overview e link in home.html
- [x] Rendere pubblico il repo e attivare GitHub Pages (dal branch main): https://alessiomartini.github.io/film-salvati/
- [x] Aggiungere `film-salvati` a `SITES` in site-notes
- [x] `wrangler deploy` di site-notes (lo lancia Alessio), poi provare il Feedback dal sito

## Primo risultato: post Instagram
- [x] Import delle 3 raccolte Instagram (189 post, 145 titoli)
- [x] Titoli riconosciuti dalle caption in `data/matches.json`
- [x] Sito: griglia, filtri, scheda per titolo, Feedback
- [x] Chiave TMDB in `.env` e primo `enrich.py` (copertine, trama, cast, trailer, streaming NL/IT)
- [ ] Alessio controlla i titoli dubbi (badge "?") e i 6 post non riconosciuti

## Arricchimento completo
- [ ] OMDb: voti IMDb, Rotten Tomatoes, Metacritic
- [ ] Wikidata: link Wikipedia IT/EN, premi vinti e nomination, link a Rotten Tomatoes/Metacritic/MUBI/MYmovies
- [ ] Contenuti: violenza, nudo, sesso (IMDb Parents Guide), con età consigliata come fallback
- [ ] Voto Letterboxd

## Import personali
- [ ] Google Keep: liste "Films" (visti per anno, dal 2017)
- [ ] Watchlist di Google (Google Play Movies & TV, nel Takeout del 2026-10-18)
- [ ] Letterboxd (Settings → Data → Export)
- [ ] IMDb (voti e watchlist, Export CSV)
- [ ] Netflix (netflix.com/viewingactivity → scarica tutto; episodi raggruppati in serie)
- [ ] Prime Video (richiesta dati Amazon) e RaiPlay (a mano)
- [ ] Fusione delle fonti: stato "visto" vince su "da vedere", mio voto, data di visione

## Personalizzazione
- [ ] I miei abbonamenti evidenziati e filtro "solo i miei servizi"
- [ ] Filtro "stasera": da vedere + durata + disponibile sui miei servizi
- [ ] Statistiche: ore viste, generi, decenni, registi

## Aggiornamento automatico
- [ ] GitHub Action settimanale: riaggiorna disponibilità streaming e voti (chiavi come secrets)

## Idee
- [ ] Compositore della colonna sonora, con link a music-library
- [ ] "Tratto da" (libro, storia vera, opera teatrale)
- [ ] Location delle riprese
- [ ] Bechdel test (bechdeltest.com)
- [ ] Premi come badge (Oscar, Cannes, Venezia, Berlino)
- [ ] Film simili che ho già visto
- [ ] Film e serie in olandese per esercitarsi con la lingua
- [ ] Uscite al cinema in arrivo dei titoli salvati
- [ ] Deep link diretti ai servizi (oggi il link va alla pagina "dove guardarlo" di TMDB/JustWatch)
- [ ] Budget e incassi

## Decisioni e cose provate
Fonti dati: TMDB (gratis, con attribuzione) per scheda, trailer e disponibilità streaming (dati
JustWatch); OMDb per i voti IMDb/RT/Metacritic; Wikidata per Wikipedia, premi e ID degli altri siti.
La ricerca TMDB per titolo+anno sbaglia a volte (anno di uscita diverso, omonimi): 4 casi fissati
con `tmdb_id` esplicito in `data/matches.json` (Red, Enemy, Demolition, Tuner).
Letterboxd non ha API pubblica: per ora solo il link (`letterboxd.com/tmdb/<id>` porta alla scheda).

Instagram: le tre raccolte di film vengono importate tutte (nomi solo in `.env`), senza
tag di provenienza (scelta di Alessio, 2026-11-01). Le caption non vengono pubblicate (copyright),
solo il link al post. Il riconoscimento dei titoli l'ha fatto Claude leggendo le caption: 14 post
non sono film (musica, motivazionali, pubblicità), 6 non si capiscono dalla caption (serve il video).

Repo reso pubblico il 2026-11-01 (con l'account free GitHub Pages richiede un repo pubblico).
Pages servito direttamente dal branch main, senza workflow: non c'è build.

## Log
- 2026-11-01: arricchimento TMDB dei 145 titoli (copertine, trama, cast, trailer, streaming NL/IT), Feedback attivo; progetto avviato: import Instagram (145 titoli), script TMDB, sito con griglia, filtri e schede; repo pubblico e sito online su GitHub Pages.
