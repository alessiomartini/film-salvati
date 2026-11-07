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
- [ ] Alessio corregge gli stati "maybe watched" (le liste Keep sono un misto di visti e da vedere)
- [ ] Alessio controlla i titoli dubbi (badge "?") e i 6 post non riconosciuti

## Arricchimento completo
- [ ] OMDb: voti IMDb, Rotten Tomatoes, Metacritic
- [x] Wikidata: premi vinti e link Wikipedia (EN)
- [ ] Wikidata: nomination, link a Rotten Tomatoes/Metacritic/MUBI/MYmovies
- [x] Contenuti: bollini nudità/sesso e violenza (Kids-in-Mind, ripiego TMDB) e filtri
- [ ] Voto Letterboxd

## Import personali
- [x] Google Keep: liste "Films" (2014-2017 + "Films Online 1" + 4 recensioni), stato "maybe watched"
- [ ] Watchlist di Google (Google Play Movies & TV, nel Takeout del 2026-10-18)
- [x] Letterboxd (Settings → Data → Export): visti, voti, watchlist, like
- [ ] IMDb (voti e watchlist, Export CSV)
- [ ] Netflix (netflix.com/viewingactivity → scarica tutto; episodi raggruppati in serie)
- [x] Prime Video (richiesta dati Amazon, `amazon/All Data Categories.zip`): cronologia e watchlist
- [ ] RaiPlay (a mano)
- [x] Fusione delle fonti: stato "watched" vince su "to watch", mio voto e like da Letterboxd
- [ ] Data di visione

## Personalizzazione
- [x] Stato visibile su ogni copertina (Watched verde, Maybe watched arancione)
- [x] Cambiare lo stato dal sito (pulsante Edit, solo con il token di Alessio)
- [ ] I miei abbonamenti evidenziati e filtro "solo i miei servizi"
- [ ] Filtro "stasera": da vedere + durata + disponibile sui miei servizi
- [ ] Statistiche: ore viste, generi, decenni, registi
- [ ] Filtro: bottone per escludere i film già visti, mantenendo quelli "forse" e "non visti" (da Google Tasks, 2026-11-04)

## Aggiornamento automatico
- [ ] GitHub Action settimanale: riaggiorna disponibilità streaming e voti (chiavi come secrets)

## Idee
- [ ] Compositore della colonna sonora, con link a music-library
- [ ] "Tratto da" (libro, storia vera, opera teatrale)
- [ ] Location delle riprese
- [ ] Bechdel test (bechdeltest.com)
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

Lingua (Alessio, 2026-11-01): sito in inglese; titoli in lingua originale con la traduzione inglese
sotto; trama, generi e trailer da TMDB in inglese. Stati nei dati: `to watch`, `maybe watched`, `watched`.

Keep: le righe sono scritte a mano (titoli troncati con "...", refusi): le correzioni stanno in
`data/matches.json` con chiave `keep:<riga>`; senza correzione la riga è cercata così com'è.

Prime Video: la cronologia ha solo i minuti visti, non la durata. Soglie fisse: film >= 45 min o
serie >= 80 min = watched, 3-45 min = maybe watched, sotto = anteprima scartata. Gli episodi
("Pilot-Bosch - Season 1") sono raggruppati per serie; i falsi positivi ("Half-Blood Prince") si
correggono in `data/matches.json` con chiave `tv:<nome>`. Altri dati in Dati-personali guardati e
non usati: estratti conto (un solo pagamento al cinema), YouTube (video, non film).

Modifica dello stato dal sito: niente backend. Il sito scrive `data/overrides.json` ({id: stato})
nel repo con l'API GitHub e un token fine-grained (solo Contents di film-salvati) che Alessio
incolla una volta nel suo browser (pulsante Edit). I clic ravvicinati diventano un solo commit; se
il salvataggio fallisce restano nel browser. `overrides.json` vince sugli stati calcolati dagli
script. Scartato un Worker su site-notes: serviva login e deploy per una sola persona.

Contenuti: IMDb Parents Guide scartato, blocca le richieste automatiche (403 / sfida anti-bot) e
non va aggirato. Usato Kids-in-Mind (robots: Allow, `use=reference`): punteggi 0-10 per
sesso/nudità, violenza, linguaggio, letti dai risultati di ricerca; bollino da 5/10. Copre
soprattutto film USA dagli anni '90: per gli altri ripiego su descrittori di classificazione e parole
chiave TMDB (solo sì/no, copertura parziale: un film senza bollino non è garantito "pulito").
Premi da Wikidata (P166); "importanti" = Oscar, Palma d'oro, Leone d'oro, Orso d'oro, Golden Globe,
BAFTA, César, David di Donatello, Emmy.

Repo reso pubblico il 2026-11-01 (con l'account free GitHub Pages richiede un repo pubblico).
Pages servito direttamente dal branch main, senza workflow: non c'è build.

## Log

- 2026-11-07: aggiunte a mano Her (2013) e Perfect Days (2023) da Google Tasks; nuova sorgente `data/manual.json` letta da import_sources.py.
- 2026-11-06: widget note v2 canonico (site-notes/widget) al posto del vecchio Feedback; contesto via SiteNotes.setContext; CSS vecchia rimossa. widget note allineato alla versione finale (migrazione key#field, dedupe), ?v=3.
- 2026-11-01: bollini premi (Wikidata) e contenuti (Kids-in-Mind/TMDB), filtri relativi, link Wikipedia.
- 2026-11-01: stato visibile sulle copertine e modificabile dal sito (overrides.json via API GitHub).
- 2026-11-01: import di Keep, Letterboxd e Prime Video (445 titoli), sito in inglese con titoli originali + inglese; arricchimento TMDB dei 145 titoli (copertine, trama, cast, trailer, streaming NL/IT), Feedback attivo; progetto avviato: import Instagram (145 titoli), script TMDB, sito con griglia, filtri e schede; repo pubblico e sito online su GitHub Pages.
