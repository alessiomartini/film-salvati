"""Legge gli export personali (mai in git) e scrive data/my-list.json (pubblico).

Fonti per ora: raccolte film dei post salvati su Instagram.
Le caption servono solo a riconoscere il titolo: finiscono in cache/ig-posts.json
(gitignored), mai nel sito. Il titolo di ogni post sta in data/matches.json,
scritto a mano/da Claude: { url: [{"title", "year", "type": "movie"|"tv", "check"?}] | null | "?" }
(null = il post non è un film/serie, "?" = titolo non riconoscibile dalla caption,
check = riconosciuto con dubbio, da confermare).

Uso: python -I scripts/import_sources.py [percorso dello zip Instagram]
"""
import glob
import json
import os
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
            key = f'{one["type"]}:{one["title"].lower()}:{one.get("year")}'
            t = titles.setdefault(key, {**one, "status": "da vedere", "instagram": []})
            t["instagram"].append(p["url"])

    with open(os.path.join(ROOT, "data", "my-list.json"), "w", encoding="utf-8") as f:
        json.dump(sorted(titles.values(), key=lambda t: t["title"]), f, ensure_ascii=False, indent=1)
    print(f"Instagram: {len(posts)} post, {len(titles)} titoli, {skipped} non film, "
          f"{len(unknown)} da riconoscere, {len(missing)} senza match")
    for u in unknown:
        print("  titolo da riconoscere:", u)
    for u in missing:
        print("  manca in matches.json:", u)


assert fix_mojibake("piÃ¹") == "più" and fix_mojibake("più") == "più"

if __name__ == "__main__":
    main()
