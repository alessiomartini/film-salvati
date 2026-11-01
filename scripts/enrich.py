"""data/my-list.json -> data/library.json, arricchito con TMDB.

Chiave in .env (gitignored): TMDB_KEY=<API key v3 o Read Access Token v4>.
Le risposte grezze restano in cache/tmdb/ (gitignored): rilanciare costa solo i titoli nuovi;
--refresh le riscarica (disponibilità streaming e voti cambiano).

Uso: python -I scripts/enrich.py [--limit N] [--refresh]
"""
import json
import re
import os
import sys
import time
import urllib.parse
import urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CACHE = os.path.join(ROOT, "cache", "tmdb")
COUNTRIES = ("NL", "IT")
IMG = "https://image.tmdb.org/t/p/"
STATUS_RANK = {"to watch": 0, "maybe watched": 1, "watched": 2}  # come in import_sources.py


def load_env():
    path = os.path.join(ROOT, ".env")
    if os.path.exists(path):
        for line in open(path, encoding="utf-8"):
            k, _, v = line.strip().partition("=")
            if k and not k.startswith("#"):
                os.environ.setdefault(k, v.strip())


def tmdb(path, refresh=False, **params):
    """GET su api.themoviedb.org/3 con cache su disco."""
    name = (path.strip("/") + "?" + urllib.parse.urlencode(sorted(params.items()))).replace("/", "_")
    file = os.path.join(CACHE, "".join(c if c.isalnum() or c in "._-=" else "_" for c in name) + ".json")
    if os.path.exists(file) and not refresh:
        with open(file, encoding="utf-8") as f:
            return json.load(f)
    key = os.environ["TMDB_KEY"]
    headers = {"accept": "application/json"}
    if len(key) > 40:  # Read Access Token v4
        headers["Authorization"] = "Bearer " + key
    else:
        params["api_key"] = key
    url = "https://api.themoviedb.org/3" + path + "?" + urllib.parse.urlencode(params)
    with urllib.request.urlopen(urllib.request.Request(url, headers=headers), timeout=30) as r:
        data = json.load(r)
    time.sleep(0.05)  # ponytail: limite TMDB ~50 req/s, una pausa fissa basta per qualche centinaio di titoli
    os.makedirs(CACHE, exist_ok=True)
    with open(file, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False)
    return data


def find(item):
    """Titolo + anno -> id TMDB (primo risultato; con anno, poi senza)."""
    kind = item["type"]
    year_key = "primary_release_year" if kind == "movie" else "first_air_date_year"
    tries = [{year_key: item["year"]}] if item.get("year") else []
    for extra in tries + [{}]:
        res = tmdb(f"/search/{kind}", query=item["title"], language="en-US", **extra)["results"]
        if res:
            return res[0]["id"]
    return None


def trailer(videos):
    """Trailer YouTube: inglese se c'è, altrimenti qualsiasi."""
    vids = [v for v in videos if v["site"] == "YouTube" and v["type"] in ("Trailer", "Teaser")]
    vids.sort(key=lambda v: (v["iso_639_1"] != "en", v["type"] != "Trailer", not v.get("official")))
    return f"https://www.youtube.com/watch?v={vids[0]['key']}" if vids else None


def certification(d, kind, country):
    if kind == "movie":
        for r in d.get("release_dates", {}).get("results", []):
            if r["iso_3166_1"] == country:
                certs = [x["certification"] for x in r["release_dates"] if x["certification"]]
                return certs[0] if certs else None
    else:
        for r in d.get("content_ratings", {}).get("results", []):
            if r["iso_3166_1"] == country:
                return r["rating"] or None
    return None


def providers(d):
    out = {}
    for c in COUNTRIES:
        p = d.get("watch/providers", {}).get("results", {}).get(c)
        if not p:
            continue
        out[c] = {"link": p.get("link")}
        for kind in ("flatrate", "free", "ads", "rent", "buy"):
            if p.get(kind):
                out[c][kind] = [{"name": x["provider_name"], "logo": IMG + "w92" + x["logo_path"]} for x in p[kind]]
    return out


# --- Contenuti (nudità/sesso, violenza) ---
# Fonte principale: Kids-in-Mind (punteggi 0-10, soprattutto film USA dagli anni '90; robots: Allow,
# use=reference). Ripiego: descrittori di classificazione e parole chiave TMDB (solo sì/no).
SEX_WORDS = ("nudity", "sex scene", "explicit sex", "simulated sex", "erotic", "nude", "naked", "softcore")
VIOLENCE_WORDS = ("violence", "gore", "brutality", "torture", "bloody", "splatter")
KIM_THRESHOLD = 5  # punteggio KiM da cui compare il bollino


def tmdb_content(keywords, descriptors):
    words = [w.lower() for w in keywords + descriptors]
    return {
        "sex_flag": any(s in w for w in words for s in SEX_WORDS) or any(w in ("sex", "sexuality", "sexual content") for w in words),
        "violence_flag": any(v in w for w in words for v in VIOLENCE_WORDS),
        "source": "tmdb",
    }


def norm(s):
    return re.sub(r"[^a-z0-9]", "", (s or "").lower().replace("&", "and"))


def kids_in_mind(film):
    """Cerca il film su kids-in-mind.com: {sex, violence, language, url} o None. Cache su disco."""
    file = os.path.join(ROOT, "cache", "kim", f'{film["id"]}.json')
    if os.path.exists(file):
        with open(file, encoding="utf-8") as f:
            return json.load(f)
    q = urllib.parse.urlencode({"fwp_keyword": film["title"]})
    req = urllib.request.Request(f"https://kids-in-mind.com/search-desktop.htm?{q}",
                                 headers={"User-Agent": "film-salvati/0.1 (personal catalogue; alemarti.2001@gmail.com)"})
    with urllib.request.urlopen(req, timeout=30) as r:
        html = r.read().decode("utf-8", "replace")
    time.sleep(1)  # ponytail: una richiesta al secondo, ~8 minuti per 450 titoli; poi tutto da cache
    found = None
    for url, text in re.findall(r'href="(https://kids-in-mind\.com/[a-z0-9]/[^"]+)"[^>]*>([^<]+)</a>', html):
        m = re.match(r"(.+?) \[(\d{4})\].*? - (\d+)\.(\d+)\.(\d+)\s*$", text.replace("&#039;", "'").replace("&amp;", "&"))
        if m and abs(int(m[2]) - (film["year"] or 0)) <= 1 and norm(m[1]) in (norm(film["title"]), norm(film["original_title"])):
            found = {"sex": int(m[3]), "violence": int(m[4]), "language": int(m[5]), "url": url}
            break
    os.makedirs(os.path.dirname(file), exist_ok=True)
    with open(file, "w", encoding="utf-8") as f:
        json.dump(found, f)
    return found


def add_content(lib):
    n = 0
    for film in lib.values():
        if film["type"] != "movie":
            continue
        try:
            kim = kids_in_mind(film)
        except OSError as e:  # sito giù o lento: resta il ripiego TMDB, si riprova al prossimo giro
            print("  kids-in-mind:", film["title"], e)
            continue
        if kim:
            n += 1
            film["content"] = {**kim, "source": "kim",
                               "sex_flag": kim["sex"] >= KIM_THRESHOLD, "violence_flag": kim["violence"] >= KIM_THRESHOLD}
    print(f"Kids-in-Mind: {n} film trovati")


# --- Premi e Wikipedia (Wikidata) ---
MAJOR_AWARDS = [("Academy Award", "Oscar"), ("Palme d'Or", "Palme d'Or"), ("Golden Lion", "Golden Lion"),
                ("Golden Bear", "Golden Bear"), ("Golden Globe", "Golden Globe"), ("BAFTA", "BAFTA"),
                ("British Academy", "BAFTA"), ("César Award", "César"), ("David di Donatello", "David di Donatello"),
                ("Primetime Emmy", "Emmy")]


def add_awards(lib):
    by_q = {f["wikidata_id"]: f for f in lib.values() if f.get("wikidata_id")}
    qids = sorted(by_q)
    for i in range(0, len(qids), 80):
        values = " ".join("wd:" + q for q in qids[i:i + 80])
        query = f"""SELECT ?item ?awardLabel ?enwiki WHERE {{
          VALUES ?item {{ {values} }}
          OPTIONAL {{ ?item wdt:P166 ?award. }}
          OPTIONAL {{ ?enwiki schema:about ?item; schema:isPartOf <https://en.wikipedia.org/>. }}
          SERVICE wikibase:label {{ bd:serviceParam wikibase:language "en". }} }}"""
        url = "https://query.wikidata.org/sparql?" + urllib.parse.urlencode({"query": query})
        req = urllib.request.Request(url, headers={"Accept": "application/sparql-results+json",
                                                   "User-Agent": "film-salvati/0.1 (alemarti.2001@gmail.com)"})
        with urllib.request.urlopen(req, timeout=60) as r:
            rows = json.load(r)["results"]["bindings"]
        for row in rows:
            film = by_q[row["item"]["value"].rsplit("/", 1)[-1]]
            if "enwiki" in row:
                film["links"]["wikipedia"] = row["enwiki"]["value"]
            label = row.get("awardLabel", {}).get("value")
            if label and label not in film.setdefault("awards", []):
                film["awards"].append(label)
    for film in lib.values():
        film["awards"] = sorted(film.get("awards", []))
        major = [short for a in film["awards"] for key, short in MAJOR_AWARDS if key in a]
        film["major_awards"] = {s: major.count(s) for s in dict.fromkeys(major)}  # es. {"Oscar": 3}
    print(f"Wikidata: {sum(1 for f in lib.values() if f['major_awards'])} titoli con premi importanti")


def details(kind, tid, refresh):
    extra = "credits,videos,release_dates,external_ids,keywords,watch/providers,recommendations"
    if kind == "tv":
        extra = "aggregate_credits,videos,content_ratings,external_ids,keywords,watch/providers,recommendations"
    d = tmdb(f"/{kind}/{tid}", refresh, language="en-US", append_to_response=extra,
             include_video_language="en,null")
    credits = d.get("credits") or d.get("aggregate_credits") or {}
    if kind == "movie":
        makers = [c["name"] for c in credits.get("crew", []) if c["job"] == "Director"]
    else:
        makers = [c["name"] for c in d.get("created_by", [])]
    date = d.get("release_date") or d.get("first_air_date") or ""
    ext = d.get("external_ids", {})
    keywords = d.get("keywords", {})
    all_keywords = [k["name"] for k in keywords.get("keywords", keywords.get("results", []))]
    descriptors = [s for r in d.get("release_dates", {}).get("results", []) for x in r["release_dates"]
                   for s in x.get("descriptors") or []]
    return {
        "id": f"{kind}-{tid}",
        "tmdb_id": tid,
        "type": kind,
        "title": d.get("title") or d.get("name"),
        "original_title": d.get("original_title") or d.get("original_name"),
        "year": int(date[:4]) if date[:4].isdigit() else None,
        "runtime": d.get("runtime") or (d.get("episode_run_time") or [None])[0],
        "seasons": d.get("number_of_seasons"),
        "episodes": d.get("number_of_episodes"),
        "genres": [g["name"] for g in d.get("genres", [])],
        "directors": makers,
        "cast": [c["name"] for c in credits.get("cast", [])[:8]],
        "original_language": d.get("original_language"),
        "countries": [c["iso_3166_1"] for c in d.get("production_countries", [])] or d.get("origin_country", []),
        "overview": d.get("overview", ""),
        "poster": IMG + "w342" + d["poster_path"] if d.get("poster_path") else None,
        "backdrop": IMG + "w780" + d["backdrop_path"] if d.get("backdrop_path") else None,
        "trailer": trailer(d.get("videos", {}).get("results", [])),
        "certification": {c: certification(d, kind, c) for c in COUNTRIES},
        "providers": providers(d),
        "keywords": all_keywords[:12],
        "content": tmdb_content(all_keywords, descriptors),
        "similar": [r.get("title") or r.get("name") for r in d.get("recommendations", {}).get("results", [])[:6]],
        "collection": (d.get("belongs_to_collection") or {}).get("name"),
        "ratings": {"tmdb": round(d["vote_average"], 1) if d.get("vote_count") else None},
        "imdb_id": ext.get("imdb_id"),
        "wikidata_id": ext.get("wikidata_id"),
        "links": {
            "tmdb": f"https://www.themoviedb.org/{kind}/{tid}",
            "imdb": f"https://www.imdb.com/title/{ext['imdb_id']}/" if ext.get("imdb_id") else None,
            # Letterboxd risolve da solo gli id TMDB (solo film)
            "letterboxd": f"https://letterboxd.com/tmdb/{tid}/" if kind == "movie" else None,
        },
    }


def main():
    load_env()
    if not os.environ.get("TMDB_KEY"):
        sys.exit("Manca TMDB_KEY in .env (themoviedb.org -> Impostazioni -> API).")
    args = sys.argv[1:]
    limit = int(args[args.index("--limit") + 1]) if "--limit" in args else None
    refresh = "--refresh" in args

    with open(os.path.join(ROOT, "data", "my-list.json"), encoding="utf-8") as f:
        mine = json.load(f)[:limit]

    lib, not_found = {}, []
    for item in mine:
        tid = item.get("tmdb_id") or find(item)
        if not tid:
            not_found.append(item)
            continue
        film = lib.get(f'{item["type"]}-{tid}') or details(item["type"], tid, refresh)
        if film["id"] not in lib:
            film.update(status=item["status"], instagram=[], query={"title": item["title"], "year": item.get("year")})
            lib[film["id"]] = film
        # più voci della lista sullo stesso titolo TMDB (fonti diverse): unisci post, stato e dati miei
        film["instagram"] += [u for u in item.get("instagram", []) if u not in film["instagram"]]
        if STATUS_RANK[item["status"]] > STATUS_RANK[film["status"]]:
            film["status"] = item["status"]
        for k in ("my_rating", "liked", "check"):
            if item.get(k):
                film[k] = item[k]
        if item.get("letterboxd"):
            film["links"]["letterboxd"] = item["letterboxd"]

    add_awards(lib)
    add_content(lib)
    out = sorted(lib.values(), key=lambda t: (t["title"] or "").lower())
    with open(os.path.join(ROOT, "data", "library.json"), "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=1)
    print(f"library.json: {len(out)} titoli, {len(not_found)} non trovati su TMDB")
    for item in not_found:
        print("  non trovato:", item["title"], item.get("year"))


if __name__ == "__main__":
    main()
