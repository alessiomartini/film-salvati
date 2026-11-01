"""Legge gli export personali (mai in git) e scrive data/my-list.json (pubblico).

Fonti: raccolte film dei post salvati su Instagram, note "Films" di Google Keep.
Le caption servono solo a riconoscere il titolo: finiscono in cache/ig-posts.json
(gitignored), mai nel sito. Il titolo di ogni post sta in data/matches.json,
scritto a mano/da Claude: { url: [{"title", "year", "type": "movie"|"tv", "check"?}] | null | "?" }
(null = il post non è un film/serie, "?" = titolo non riconoscibile dalla caption,
check = riconosciuto con dubbio, da confermare).

Uso: python -I scripts/import_sources.py [percorso dello zip Instagram]
"""
import glob
import csv
import io
import json
import os
import re
import sys
import zipfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATI = r"E:\Alessio\Dati-personali"
# Nomi delle raccolte da importare, separati da "|", in .env (privati: il repo è pubblico).
IG_COLLECTIONS = set()  # riempito da load_env()


def load_env():
    global IG_COLLECTIONS
    path = os.path.join(ROOT, ".env")
    if os.path.exists(path):
        for line in open(path, encoding="utf-8"):
            k, _, v = line.strip().partition("=")
            if k and not k.startswith("#"):
                os.environ.setdefault(k, v.strip())
    IG_COLLECTIONS = set(filter(None, os.environ.get("IG_COLLECTIONS", "").split("|")))


def fix_mojibake(s):
    """Meta scrive l'UTF-8 come se fosse latin-1: 'piÃ¹' -> 'più'."""
    try:
        return s.encode("latin-1").decode("utf-8")
    except (UnicodeEncodeError, UnicodeDecodeError):
        return s


def fields(items):
    """label_values -> {label: value}, più 'owner' dal blocco Owner."""
    out = {}
    for it in items:
        if "label" in it:
            out[it["label"]] = it.get("value", "")
        elif it.get("title") == "Owner" and it.get("dict"):
            for f in it["dict"][0]["dict"]:
                if f.get("label") == "Username":
                    out["owner"] = f.get("value", "")
    return out


def instagram_posts(zip_path):
    with zipfile.ZipFile(zip_path) as z:
        cols = json.loads(z.read("your_instagram_activity/saved/saved_collections.json"))
    posts = {}
    for col in cols:
        meta = fields(col["label_values"])
        if meta.get("Name") not in IG_COLLECTIONS:
            continue
        for lv in col["label_values"]:
            for item in lv.get("dict", []) if "label" not in lv else []:
                f = fields(item["dict"])
                url = f.get("URL")
                if url and url not in posts:
                    posts[url] = {
                        "url": url,
                        "saved": item.get("timestamp") or col.get("timestamp"),
                        "owner": f.get("owner", ""),
                        "caption": fix_mojibake(f.get("Caption", "")),
                    }
    return list(posts.values())


# Più informazione vince: se una fonte dice "watched" e un'altra "to watch", resta "watched".
STATUS_RANK = {"to watch": 0, "maybe watched": 1, "watched": 2}
# Note Keep -> stato (Alessio, 2026-11-01: le liste "Films" sono un misto di visti e da vedere).
KEEP_NOTES = {"Films": "maybe watched", "Films(1)": "maybe watched", "Films Online 1": "maybe watched",
              "Film reviews inglese": "watched"}


def clean_keep(line):
    """'- ‎blade runner 2049 ' -> 'blade runner 2049' (chiave delle correzioni in matches.json)."""
    return line.replace("‎", "").strip().lstrip("-").strip().rstrip(".").strip()


def keep_titles(zip_path):
    """Righe delle note film di Keep: (titolo ripulito, anno dell'intestazione 'FILM 2017' o None, stato)."""
    out = {}
    with zipfile.ZipFile(zip_path) as z:
        for name, status in KEEP_NOTES.items():
            year = None
            for line in json.loads(z.read(f"Takeout/Keep/{name}.json")).get("textContent", "").splitlines():
                head = line.strip().upper()
                if head.startswith("FILM ") and head[5:].isdigit():
                    year = int(head[5:])
                elif clean_keep(line):
                    out.setdefault(clean_keep(line).lower(), (clean_keep(line), year, status))
    return list(out.values())


def csv_rows(z, name):
    return list(csv.DictReader(io.StringIO(z.read(name).decode("utf-8-sig"))))


def letterboxd_titles(zip_path):
    """Export Letterboxd: watched/watchlist -> stato, ratings -> my_rating (0.5-5), likes -> liked."""
    out = {}
    with zipfile.ZipFile(zip_path) as z:
        def one(r):
            return out.setdefault((r["Name"], r["Year"]), {
                "title": r["Name"], "year": int(r["Year"]) if r["Year"] else None, "type": "movie",
                "letterboxd": r["Letterboxd URI"], "status": "to watch"})
        for r in csv_rows(z, "watchlist.csv"):
            one(r)
        for name in ("watched.csv", "ratings.csv", "diary.csv", "likes/films.csv"):
            for r in csv_rows(z, name):
                t = one(r)
                t["status"] = "watched"  # una voto o un like su Letterboxd vuol dire visto
                if r.get("Rating"):
                    t["my_rating"] = float(r["Rating"])
                if name == "likes/films.csv":
                    t["liked"] = True
    return list(out.values())


def prime_titles(zip_path):
    """Prime Video: cronologia (minuti visti per titolo; episodi raggruppati in serie) e watchlist."""
    with zipfile.ZipFile(zip_path) as z:
        files = {n.rsplit("/", 1)[-1]: n for n in z.namelist() if "Prime Video" in n}
        history = csv_rows(z, files["Viewing History.csv"])
        watchlist = csv_rows(z, files["Watchlist.csv"])
    # Episodi: "Pilot-Bosch - Season 1", "Pilot-House". Il nome della serie è dopo il primo "-"
    # attaccato al titolo, e conta solo se dice "Season" o compare in più righe.
    names = [r["Title"].strip('"') for r in history if r["Material Type Description"].strip('"') == "Full"]
    right = [re.split(r"(?<=\S)-(?=\S)", n, maxsplit=1)[-1] for n in names if re.search(r"(?<=\S)-(?=\S)", n)]
    shows = {r for r in right if right.count(r) > 1 or "Season" in r}
    minutes = {}
    for n, r in zip(names, (r for r in history if r["Material Type Description"].strip('"') == "Full")):
        parts = re.split(r"(?<=\S)-(?=\S)", n, maxsplit=1)
        show = parts[-1] if len(parts) == 2 and parts[-1] in shows else None
        key = (re.sub(r"\s*[-–]\s*Season \d+$", "", show), "tv") if show else (n, "movie")
        minutes[key] = minutes.get(key, 0) + float(r["Seconds Viewed"] or 0) / 60
    out = []
    for (title, kind), m in minutes.items():
        # ponytail: soglie fisse sui minuti visti (senza durata del film); film >= 45 min o serie >= 2
        # episodi interi = visto, sotto i 3 minuti è solo un'anteprima
        if m >= 3:
            done = m >= 45 if kind == "movie" else m >= 80
            out.append({"title": title, "year": None, "type": kind, "status": "watched" if done else "maybe watched"})
    for r in watchlist:
        t = re.sub(r"\s*\((\d{4})\)$", "", r["Catalog Title"])
        kind = "tv" if " - Season" in t else "movie"
        out.append({"title": re.sub(r" - Season \d+$", "", t), "year": None, "type": kind, "status": "to watch"})
    return out


def add(titles, one, status, url=None):
    key = f'{one["type"]}:{one["title"].lower()}:{one.get("year")}'
    t = titles.setdefault(key, {**one, "status": status, "instagram": []})
    t.update({k: v for k, v in one.items() if k in ("my_rating", "liked", "letterboxd")})
    if STATUS_RANK[status] > STATUS_RANK[t["status"]]:
        t["status"] = status
    if url:
        t["instagram"].append(url)


def main():
    load_env()
    if not IG_COLLECTIONS:
        sys.exit('Manca IG_COLLECTIONS in .env (es. IG_COLLECTIONS=Movies|movie).')
    zips = sys.argv[1:] or sorted(glob.glob(os.path.join(DATI, "meta", "instagram-*.zip")))[-1:]
    posts = instagram_posts(zips[0])
    os.makedirs(os.path.join(ROOT, "cache"), exist_ok=True)
    with open(os.path.join(ROOT, "cache", "ig-posts.json"), "w", encoding="utf-8") as f:
        json.dump(posts, f, ensure_ascii=False, indent=1)

    with open(os.path.join(ROOT, "data", "matches.json"), encoding="utf-8") as f:
        matches = json.load(f)

    titles, missing, unknown, skipped = {}, [], [], 0
    for p in posts:
        if p["url"] not in matches:
            missing.append(p["url"])
            continue
        m = matches[p["url"]]
        if m is None:
            skipped += 1
            continue
        if m == "?":
            unknown.append(p["url"])
            continue
        for one in m:
            add(titles, one, "to watch", p["url"])
    n_ig = len(titles)

    # Keep: senza correzione in matches.json ("keep:<riga>") la riga è cercata così com'è su TMDB.
    keep = keep_titles(sorted(glob.glob(os.path.join(DATI, "google-takeout", "*_keep.zip")))[-1])
    for raw, year, status in keep:
        m = matches.get("keep:" + raw.lower(), [{"title": raw, "year": year, "type": "movie"}])
        for one in m or []:
            add(titles, one, status)

    lb = letterboxd_titles(sorted(glob.glob(os.path.join(DATI, "letterboxd-*.zip")))[-1])
    pv = prime_titles(os.path.join(DATI, "amazon", "All Data Categories.zip"))
    for one in lb + pv:
        m = matches.get(f'{one["type"]}:{one["title"].lower()}', [one])  # correzioni come per Keep
        for fixed in m or []:
            add(titles, {**one, **fixed}, one["status"])

    with open(os.path.join(ROOT, "data", "my-list.json"), "w", encoding="utf-8") as f:
        json.dump(sorted(titles.values(), key=lambda t: t["title"]), f, ensure_ascii=False, indent=1)
    print(f"Instagram: {len(posts)} post, {n_ig} titoli, {skipped} non film, "
          f"{len(unknown)} da riconoscere, {len(missing)} senza match")
    print(f"Keep: {len(keep)} righe; Letterboxd: {len(lb)}; Prime Video: {len(pv)}; totale {len(titles)} voci")
    for u in unknown:
        print("  titolo da riconoscere:", u)
    for u in missing:
        print("  manca in matches.json:", u)


assert fix_mojibake("piÃ¹") == "più" and fix_mojibake("più") == "più"
assert clean_keep("- ‎pirati dei caraibi: la vendetta di...") == "pirati dei caraibi: la vendetta di"

if __name__ == "__main__":
    main()
