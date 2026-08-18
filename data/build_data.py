"""
One-off, multi-language data pipeline for ovos-skill-wiki-offline.

Fetches the ~10,000 titles in a language's "Level 4 Vital Articles"
equivalent, then fetches a short summary for each title via that
language's own official Wikipedia REST summary API.

Two title-source STRATEGIES, per language (see LANG_CONFIGS below):

- "master_list" (en-us): a single bot-maintained page listing every
  title directly. See DEVELOPMENT.md "Why the master list, not
  category tags" for why this replaced an earlier, incomplete
  category-tag-based approach for English specifically.
- "topic_subpages" (es-es, fr-fr): the language edition splits its
  list across ~10-11 topic subpages instead of one master page (no
  single-page master list exists for these languages) - each
  subpage's wikitext is parsed the same way (raw [[Article]] wikilink
  extraction), just summed across multiple pages instead of one.

Both strategies use the exact same underlying extraction: raw
wikitext, `[[Article Name]]` or `[[Real title|Display text]]`
wikilinks, filtering out non-article namespaces (Wikipedia:,
Category:, Template:, etc). Verified by hand against the actual
fetched wikitext for each language before writing this - not assumed
to generalize from English's format.

de-de and da-dk are NOT covered by this script - neither has a
confirmed comparable-scale native vital-articles list (German only
has a much smaller list; Danish has no confirmed equivalent at all).
See github.com/andlo/ovos-skill-wiki-offline/issues/1 for the
machine-translation approach planned for those two instead.

Usage: python3 build_data.py <lang-code>
e.g.:  python3 build_data.py es-es

Not shipped with the skill - run once per language, output committed
as static per-language JSON (data/titles_<lang>.json,
data/summaries_<lang>.json).

Politely rate-limited (0.5s between summary requests) with retry-on-
429 backoff and incremental checkpointing every 100 articles, so an
interruption doesn't lose progress. Safe to re-run - resumes from
whatever's already in the summaries file.
"""
import json
import re
import signal
import sys
import time
from pathlib import Path

import requests

OUTPUT_DIR = Path(__file__).resolve().parent
REQUEST_DELAY_SECONDS = 0.5
MAX_RETRIES = 5


class HardTimeout(Exception):
    pass


def _alarm_handler(signum, frame):
    raise HardTimeout()


def with_hard_timeout(seconds, func, *args, **kwargs):
    """requests' own timeout= doesn't always reliably bound DNS
    resolution time (a known urllib3/requests limitation) - hit
    exactly this as an unexplained, intermittent hang during
    development (worked instantly in isolation, hung indefinitely
    inside the actual fetch loop, same URL, same process). This is a
    hard backstop via SIGALRM (Unix-only, fine on this Linux box) so
    a single title can never block the whole pipeline indefinitely,
    whatever the underlying cause turns out to be."""
    old_handler = signal.signal(signal.SIGALRM, _alarm_handler)
    signal.alarm(seconds)
    try:
        return func(*args, **kwargs)
    finally:
        signal.alarm(0)
        signal.signal(signal.SIGALRM, old_handler)

WIKILINK_RE = re.compile(r"\[\[([^\]|#]+)")
# Capitalized MediaWiki namespace prefixes (Wikipedia:, Categoría:, etc.)
EXCLUDED_PREFIXES = ("Wikipedia:", "Wikipédia:", "Categoría:", "Catégorie:",
                     "Category:", "Template:", "Modèle:", "Plantilla:",
                     "User:", "Usuario:", "Utilisateur:", "Special:",
                     "File:", "Archivo:", "Fichier:", "Help:", "Ayuda:", "Aide:")
# Interwiki link prefixes (d:Q12345 for Wikidata, wikt: for Wiktionary,
# commons:, en:/fr:/de:/... for other-language editions, etc) - lowercase,
# short, colon-separated - a DIFFERENT syntax convention from namespace
# prefixes above. Caught the hard way: "d:Q28989" (a Wikidata item link
# swept up by the generic [[...]] wikilink regex) sent to the REST summary
# API caused unpredictable hangs rather than a clean 404 - see
# DEVELOPMENT.md "Interwiki links caused hangs, not clean errors".
#
# A LEADING COLON (":en:Alcohol (drug)") is a second, equally common
# form of the same thing: MediaWiki syntax for suppressing an
# interwiki/category link's special behavior in rendering, but the
# target is still just as much an interwiki link - "en:Alcohol
# (drug)" is not a real fr.wikipedia.org article and will never
# resolve via that domain's REST summary API. Caught the hard way,
# again: 33 French titles all of this exact ":xx:..." shape hung the
# build in a permanent per-run timeout loop, one HARD TIMEOUT per
# title per run, forever - not a transient fetch failure that a
# re-run would clear. The `:?` below is the fix - same interwiki
# check, just also matching the colon-prefixed spelling.
INTERWIKI_PREFIX_RE = re.compile(r"^:?[a-z]{1,10}:")

LANG_CONFIGS = {
    "en-us": {
        "domain": "en.wikipedia.org",
        "strategy": "master_list",
        "master_list_page": "Wikipedia:Vital articles/List of all level 1\u20134 vital articles",
        "topic_category": "Category:Wikipedia level-4 vital articles by topic",
    },
    "es-es": {
        "domain": "es.wikipedia.org",
        "strategy": "topic_subpages",
        "subpages": {
            "Personas": "Wikipedia:Lista de art\u00edculos que toda Wikipedia deber\u00eda tener/Expandida/Personas",
            "Historia": "Wikipedia:Lista de art\u00edculos que toda Wikipedia deber\u00eda tener/Expandida/History",
            "Geograf\u00eda": "Wikipedia:Lista de art\u00edculos que toda Wikipedia deber\u00eda tener/Expandida/Geograf\u00eda",
            "Artes": "Wikipedia:Lista de art\u00edculos que toda Wikipedia deber\u00eda tener/Expandida/Artes",
            "Filosof\u00eda y religi\u00f3n": "Wikipedia:Lista de art\u00edculos que toda Wikipedia deber\u00eda tener/Expandida/Filosof\u00eda y religi\u00f3n",
            "Antropolog\u00eda, sicolog\u00eda y vida cotidiana": "Wikipedia:Lista de art\u00edculos que toda Wikipedia deber\u00eda tener/Expandida/Antropolog\u00eda, sicolog\u00eda y vida cotidiana",
            "Sociedad y ciencias sociales": "Wikipedia:Lista de art\u00edculos que toda Wikipedia deber\u00eda tener/Expandida/Sociedad y ciencias sociales",
            "Biolog\u00eda y ciencias de la salud": "Wikipedia:Lista de art\u00edculos que toda Wikipedia deber\u00eda tener/Expandida/Biolog\u00eda y ciencias de la salud",
            "Ciencias f\u00edsicas": "Wikipedia:Lista de art\u00edculos que toda Wikipedia deber\u00eda tener/Expandida/Ciencias f\u00edsicas",
            "Tecnolog\u00eda": "Wikipedia:Lista de art\u00edculos que toda Wikipedia deber\u00eda tener/Expandida/Tecnolog\u00eda",
            "Matem\u00e1ticas": "Wikipedia:Lista de art\u00edculos que toda Wikipedia deber\u00eda tener/Expandida/Matem\u00e1ticas",
        },
    },
    "fr-fr": {
        "domain": "fr.wikipedia.org",
        "strategy": "topic_subpages",
        "subpages": {
            "Personnalit\u00e9s": "Wikipedia:Articles vitaux/Niveau/4/Personnalit\u00e9s",
            "Histoire": "Wikipedia:Articles vitaux/Niveau/4/Histoire",
            "G\u00e9ographie": "Wikipedia:Articles vitaux/Niveau/4/G\u00e9ographie",
            "Arts et culture": "Wikipedia:Articles vitaux/Niveau/4/Arts et culture",
            "Philosophie et religion": "Wikipedia:Articles vitaux/Niveau/4/Philosophie et religion",
            "Vie quotidienne": "Wikipedia:Articles vitaux/Niveau/4/Vie quotidienne",
            "Soci\u00e9t\u00e9 et sciences sociales": "Wikipedia:Articles vitaux/Niveau/4/Soci\u00e9t\u00e9 et sciences sociales",
            "Sant\u00e9 et m\u00e9decine": "Wikipedia:Articles vitaux/Niveau/4/Sant\u00e9 et m\u00e9decine",
            "Science": "Wikipedia:Articles vitaux/Niveau/4/Science",
            "Technologie": "Wikipedia:Articles vitaux/Niveau/4/Technologie",
            "Math\u00e9matiques": "Wikipedia:Articles vitaux/Niveau/4/Math\u00e9matiques",
        },
    },
}


def make_headers():
    return {"User-Agent": "ovos-skill-wiki-offline data pipeline (contact: andlo@outlook.dk)"}


def log(progress_file, msg):
    print(msg, flush=True)
    with open(progress_file, "a", encoding="utf-8") as f:
        f.write(msg + "\n")


def extract_titles_from_wikitext(text):
    titles = []
    for m in WIKILINK_RE.finditer(text):
        title = m.group(1).strip()
        if not title:
            continue
        if title.startswith(EXCLUDED_PREFIXES):
            continue
        if INTERWIKI_PREFIX_RE.match(title):
            continue
        titles.append(title)
    return titles


def fetch_page_wikitext(domain, page_title):
    r = requests.get(f"https://{domain}/w/api.php", params={
        "action": "parse", "page": page_title,
        "prop": "wikitext", "format": "json",
    }, headers=make_headers(), timeout=30)
    r.raise_for_status()
    data = r.json()
    if "error" in data:
        raise RuntimeError(f"{domain} parse error for {page_title!r}: {data['error']}")
    return data["parse"]["wikitext"]["*"]


def get_master_list_titles(domain, page_title):
    text = fetch_page_wikitext(domain, page_title)
    marker = "<!-- report begin -->"
    idx = text.find(marker)
    body = text[idx + len(marker):] if idx != -1 else text
    return extract_titles_from_wikitext(body)


def get_topic_subcategories(domain, category_title):
    r = requests.get(f"https://{domain}/w/api.php", params={
        "action": "query", "list": "categorymembers",
        "cmtitle": category_title, "cmlimit": 50, "format": "json",
    }, headers=make_headers(), timeout=30)
    r.raise_for_status()
    return [m["title"] for m in r.json()["query"]["categorymembers"]]


def get_articles_in_subcategory(domain, subcat_title):
    titles = []
    cmcontinue = None
    while True:
        params = {
            "action": "query", "list": "categorymembers",
            "cmtitle": subcat_title, "cmlimit": 500,
            "cmnamespace": 1, "format": "json",
        }
        if cmcontinue:
            params["cmcontinue"] = cmcontinue
        r = requests.get(f"https://{domain}/w/api.php", params=params,
                         headers=make_headers(), timeout=30)
        r.raise_for_status()
        data = r.json()
        for m in data["query"]["categorymembers"]:
            title = m["title"]
            if title.startswith("Talk:"):
                titles.append(title[len("Talk:"):])
        if "continue" in data:
            cmcontinue = data["continue"]["cmcontinue"]
            time.sleep(0.3)
        else:
            break
    return titles


def build_title_list(lang, progress_file, titles_file):
    if titles_file.exists():
        log(progress_file, f"{titles_file.name} already exists, loading it")
        with open(titles_file, encoding="utf-8") as f:
            return json.load(f)

    config = LANG_CONFIGS[lang]
    domain = config["domain"]
    all_titles = {}

    if config["strategy"] == "master_list":
        log(progress_file, f"[{lang}] Fetching the master vital-articles list...")
        master_titles = get_master_list_titles(domain, config["master_list_page"])
        log(progress_file, f"[{lang}] Master list: {len(master_titles)} titles")

        topic_of = {}
        if "topic_category" in config:
            log(progress_file, f"[{lang}] Fetching topic subcategories (best-effort labels)...")
            subcats = get_topic_subcategories(domain, config["topic_category"])
            for subcat in subcats:
                topic = subcat.split(" in ", 1)[-1]
                titles = get_articles_in_subcategory(domain, subcat)
                log(progress_file, f"  {subcat}: {len(titles)} articles")
                for t in titles:
                    if t not in topic_of:
                        topic_of[t] = topic
                time.sleep(0.5)

        for title in master_titles:
            if title not in all_titles:
                all_titles[title] = topic_of.get(title, "Uncategorized")

    elif config["strategy"] == "topic_subpages":
        log(progress_file, f"[{lang}] Fetching {len(config['subpages'])} topic subpages...")
        for topic, page_title in config["subpages"].items():
            try:
                text = fetch_page_wikitext(domain, page_title)
            except RuntimeError as e:
                log(progress_file, f"  {topic}: SKIPPED - page not found ({page_title!r}). "
                                    f"Likely a broken/red link on the index page - Wikipedia's own "
                                    f"index tables can drift out of sync with actual page existence, "
                                    f"same class of issue as the en-us master-list-vs-category gap. "
                                    f"Error: {e}")
                time.sleep(0.5)
                continue
            titles = extract_titles_from_wikitext(text)
            log(progress_file, f"  {topic}: {len(titles)} raw links extracted")
            for t in titles:
                if t not in all_titles:
                    all_titles[t] = topic
            time.sleep(0.5)

    else:
        raise ValueError(f"Unknown strategy for {lang}: {config['strategy']}")

    log(progress_file, f"[{lang}] Total unique titles: {len(all_titles)}")
    with open(titles_file, "w", encoding="utf-8") as f:
        json.dump(all_titles, f, ensure_ascii=False, indent=2)
    return all_titles


def fetch_summary(domain, title, retries=0):
    url = f"https://{domain}/api/rest_v1/page/summary/{title.replace(' ', '_')}"
    try:
        r = requests.get(url, headers=make_headers(), timeout=(5, 15))
    except requests.RequestException as e:
        if retries < MAX_RETRIES:
            time.sleep(2 ** retries)
            return fetch_summary(domain, title, retries + 1)
        return None

    if r.status_code == 429:
        wait = min(60, 2 ** (retries + 2))
        time.sleep(wait)
        if retries < MAX_RETRIES:
            return fetch_summary(domain, title, retries + 1)
        return None

    if r.status_code == 404:
        return None

    if r.status_code != 200:
        if retries < MAX_RETRIES:
            time.sleep(2 ** retries)
            return fetch_summary(domain, title, retries + 1)
        return None

    d = r.json()
    extract = d.get("extract", "").strip()
    if not extract:
        return None
    return {
        "title": d.get("title", title),
        "extract": extract,
        "description": d.get("description", ""),
    }


def build_summaries(lang, all_titles, progress_file, summaries_file):
    domain = LANG_CONFIGS[lang]["domain"]
    summaries = {}
    if summaries_file.exists():
        with open(summaries_file, encoding="utf-8") as f:
            summaries = json.load(f)
        log(progress_file, f"[{lang}] Resuming: {len(summaries)} summaries already fetched")

    remaining = [t for t in all_titles if t not in summaries]
    log(progress_file, f"[{lang}] {len(remaining)} titles left to fetch (of {len(all_titles)} total)")

    for i, title in enumerate(remaining):
        if i % 20 == 0:
            log(progress_file, f"  [{lang}] ...fetching #{i} ({title!r})")
        try:
            result = with_hard_timeout(25, fetch_summary, domain, title)
        except HardTimeout:
            log(progress_file, f"  [{lang}] HARD TIMEOUT on {title!r} - skipping, will retry on next run")
            result = None
        if result:
            result["topic"] = all_titles[title]
            summaries[title] = result
        time.sleep(REQUEST_DELAY_SECONDS)

        if (i + 1) % 100 == 0:
            with open(summaries_file, "w", encoding="utf-8") as f:
                json.dump(summaries, f, ensure_ascii=False, indent=2)
            log(progress_file, f"  [{lang}] progress: {i + 1}/{len(remaining)} fetched this run, "
                                f"{len(summaries)} total saved")

    with open(summaries_file, "w", encoding="utf-8") as f:
        json.dump(summaries, f, ensure_ascii=False, indent=2)
    log(progress_file, f"[{lang}] DONE. {len(summaries)} summaries saved to {summaries_file}")


if __name__ == "__main__":
    if len(sys.argv) != 2 or sys.argv[1] not in LANG_CONFIGS:
        print(f"Usage: python3 build_data.py <lang-code>")
        print(f"Available: {list(LANG_CONFIGS.keys())}")
        sys.exit(1)

    lang = sys.argv[1]
    progress_file = OUTPUT_DIR / f"progress_{lang}.log"
    titles_file = OUTPUT_DIR / f"titles_{lang}.json"
    summaries_file = OUTPUT_DIR / f"summaries_{lang}.json"

    titles = build_title_list(lang, progress_file, titles_file)
    build_summaries(lang, titles, progress_file, summaries_file)
