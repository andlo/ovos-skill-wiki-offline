"""
One-off data pipeline for ovos-skill-wiki-offline.

Fetches the ~10,000 titles in Wikipedia's "Level 4 Vital Articles"
list, then fetches a short summary for each title via Wikipedia's own
official REST summary API.

Title source: Wikipedia's own bot-maintained master list page
("Wikipedia:Vital articles/List of all level 1-4 vital articles" -
note the page title uses an en-dash, not a hyphen, in "1-4"), parsed
from its wikitext. This REPLACES an earlier version of this script
that built the title list from the 11 topic subcategories (tagged on
each article's Talk page) - that approach turned out to be
INCOMPLETE: spot-checking found "Photosynthesis" (confirmed present
in the master list) missing from the category-based extraction
entirely. Wikipedia's own category-tag tracking and its master list
page are two parallel, imperfectly-synced mechanisms (the master
list's own header explicitly calls itself "a temporary solution until
phab:T117122 is resolved") - the master list is the authoritative,
complete one. See DEVELOPMENT.md "Why the master list, not category
tags" for the full story, including the concrete Photosynthesis gap
that caught this.

Topic labels (Arts/Geography/People/etc, used only for informational
grouping, not required for the skill to function) are still sourced
from the 11 category pages as a best-effort enrichment - any master-
list title not found in a category is labeled "Uncategorized" rather
than dropped.

Not shipped with the skill - run once, output committed as static
JSON. Same convention as ovos-skill-geography's data/build_data.py.

Politely rate-limited (0.5s between summary requests) with retry-on-
429 backoff and incremental checkpointing every 100 articles, so an
interruption doesn't lose progress.
"""
import json
import re
import time
import sys
from pathlib import Path

import requests

HEADERS = {"User-Agent": "ovos-skill-wiki-offline data pipeline (contact: andlo@outlook.dk)"}
API_URL = "https://en.wikipedia.org/w/api.php"
SUMMARY_URL_TMPL = "https://en.wikipedia.org/api/rest_v1/page/summary/{}"

OUTPUT_DIR = Path(__file__).resolve().parent
TITLES_FILE = OUTPUT_DIR / "titles.json"
SUMMARIES_FILE = OUTPUT_DIR / "summaries.json"
PROGRESS_FILE = OUTPUT_DIR / "progress.log"

MASTER_LIST_PAGE = "Wikipedia:Vital articles/List of all level 1\u20134 vital articles"
TOPIC_CATEGORY = "Category:Wikipedia level-4 vital articles by topic"

REQUEST_DELAY_SECONDS = 0.5
MAX_RETRIES = 5


def log(msg):
    print(msg, flush=True)
    with open(PROGRESS_FILE, "a", encoding="utf-8") as f:
        f.write(msg + "\n")


WIKILINK_RE = re.compile(r"\[\[([^\]|#]+)")


def get_master_list_titles():
    """The authoritative, complete, bot-maintained list - see module
    docstring for why this replaced the category-based approach."""
    r = requests.get(API_URL, params={
        "action": "parse", "page": MASTER_LIST_PAGE,
        "prop": "wikitext", "format": "json",
    }, headers=HEADERS, timeout=30)
    r.raise_for_status()
    data = r.json()
    text = data["parse"]["wikitext"]["*"]

    marker = "<!-- report begin -->"
    idx = text.find(marker)
    body = text[idx + len(marker):] if idx != -1 else text

    titles = []
    for m in WIKILINK_RE.finditer(body):
        title = m.group(1).strip()
        if title and not title.startswith(("Wikipedia:", "Category:", "Template:",
                                            "User:", "Special:", "File:", "Help:")):
            titles.append(title)
    return titles


def get_topic_subcategories():
    r = requests.get(API_URL, params={
        "action": "query", "list": "categorymembers",
        "cmtitle": TOPIC_CATEGORY, "cmlimit": 50, "format": "json",
    }, headers=HEADERS, timeout=30)
    r.raise_for_status()
    return [m["title"] for m in r.json()["query"]["categorymembers"]]


def get_articles_in_subcategory(subcat_title):
    """Members are tagged on the article's Talk page (namespace 1) -
    a WikiProject assessment convention, not a reader-facing
    category. Strip the 'Talk:' prefix to get the real article
    title."""
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
        r = requests.get(API_URL, params=params, headers=HEADERS, timeout=30)
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


def build_title_list():
    if TITLES_FILE.exists():
        log(f"titles.json already exists, loading {TITLES_FILE}")
        with open(TITLES_FILE, encoding="utf-8") as f:
            return json.load(f)

    log("Fetching the master vital-articles list (authoritative title source)...")
    master_titles = get_master_list_titles()
    log(f"Master list: {len(master_titles)} titles")

    log("Fetching the 11 topic subcategories (best-effort topic labels only)...")
    subcats = get_topic_subcategories()
    topic_of = {}  # title -> topic, from category tags (may not cover everything)
    for subcat in subcats:
        topic = subcat.split(" in ", 1)[-1]
        titles = get_articles_in_subcategory(subcat)
        log(f"  {subcat}: {len(titles)} articles")
        for t in titles:
            if t not in topic_of:
                topic_of[t] = topic
        time.sleep(0.5)

    all_titles = {}
    uncategorized = 0
    for title in master_titles:
        if title not in all_titles:
            if title in topic_of:
                all_titles[title] = topic_of[title]
            else:
                all_titles[title] = "Uncategorized"
                uncategorized += 1

    log(f"Total unique titles from master list: {len(all_titles)} "
        f"({uncategorized} without a category-tag topic label)")
    with open(TITLES_FILE, "w", encoding="utf-8") as f:
        json.dump(all_titles, f, ensure_ascii=False, indent=2)
    return all_titles


def fetch_summary(title, retries=0):
    url = SUMMARY_URL_TMPL.format(title.replace(" ", "_"))
    try:
        r = requests.get(url, headers=HEADERS, timeout=15)
    except requests.RequestException as e:
        if retries < MAX_RETRIES:
            time.sleep(2 ** retries)
            return fetch_summary(title, retries + 1)
        log(f"  FAILED (network) after retries: {title!r}: {e}")
        return None

    if r.status_code == 429:
        wait = min(60, 2 ** (retries + 2))
        log(f"  429 rate limited on {title!r}, backing off {wait}s")
        time.sleep(wait)
        if retries < MAX_RETRIES:
            return fetch_summary(title, retries + 1)
        return None

    if r.status_code == 404:
        log(f"  404 not found: {title!r} (redirect/renamed article, skipping)")
        return None

    if r.status_code != 200:
        if retries < MAX_RETRIES:
            time.sleep(2 ** retries)
            return fetch_summary(title, retries + 1)
        log(f"  FAILED (HTTP {r.status_code}) after retries: {title!r}")
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


def build_summaries(all_titles):
    summaries = {}
    if SUMMARIES_FILE.exists():
        with open(SUMMARIES_FILE, encoding="utf-8") as f:
            summaries = json.load(f)
        log(f"Resuming: {len(summaries)} summaries already fetched")

    remaining = [t for t in all_titles if t not in summaries]
    log(f"{len(remaining)} titles left to fetch (of {len(all_titles)} total)")

    for i, title in enumerate(remaining):
        result = fetch_summary(title)
        if result:
            result["topic"] = all_titles[title]
            summaries[title] = result
        time.sleep(REQUEST_DELAY_SECONDS)

        if (i + 1) % 100 == 0:
            with open(SUMMARIES_FILE, "w", encoding="utf-8") as f:
                json.dump(summaries, f, ensure_ascii=False, indent=2)
            log(f"  progress: {i + 1}/{len(remaining)} fetched this run, "
                f"{len(summaries)} total saved")

    with open(SUMMARIES_FILE, "w", encoding="utf-8") as f:
        json.dump(summaries, f, ensure_ascii=False, indent=2)
    log(f"DONE. {len(summaries)} summaries saved to {SUMMARIES_FILE}")


if __name__ == "__main__":
    titles = build_title_list()
    build_summaries(titles)
