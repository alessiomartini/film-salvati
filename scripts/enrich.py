"""data/my-list.json -> data/library.json, arricchito con TMDB.

Chiave in .env (gitignored): TMDB_KEY=<API key v3 o Read Access Token v4>.
Le risposte grezze restano in cache/tmdb/ (gitignored): rilanciare costa solo i titoli nuovi;
--refresh le riscarica (disponibilità streaming e voti cambiano).

Uso: python -I scripts/enrich.py [--limit N] [--refresh]
"""
import json
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
        "keywords": [k["name"] for k in keywords.get("keywords", keywords.get("results", []))][:12],
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

    out = sorted(lib.values(), key=lambda t: (t["title"] or "").lower())
    with open(os.path.join(ROOT, "data", "library.json"), "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=1)
    print(f"library.json: {len(out)} titoli, {len(not_found)} non trovati su TMDB")
    for item in not_found:
        print("  non trovato:", item["title"], item.get("year"))


if __name__ == "__main__":
    main()
