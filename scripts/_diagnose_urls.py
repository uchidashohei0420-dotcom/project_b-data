"""TEMPORARY diagnostic script — see prior commit message for context. Second pass:
inspect specific listing pages in more depth now that the first pass found real URLs.
"""
from __future__ import annotations

import sys

import requests
from bs4 import BeautifulSoup

HEADERS = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0 Safari/537.36"}


def dump_repeating_structure(url: str, *, max_links: int = 40) -> None:
    print(f"\n===== {url} =====")
    try:
        resp = requests.get(url, headers=HEADERS, timeout=15, allow_redirects=True)
    except Exception as exc:  # noqa: BLE001
        print(f"FETCH ERROR: {exc}")
        return
    print(f"status={resp.status_code} final_url={resp.url} bytes={len(resp.content)}")

    soup = BeautifulSoup(resp.text, "lxml")

    # Print class attributes of elements that look like repeating list items (article, li).
    from collections import Counter

    class_counter: Counter[str] = Counter()
    for tag_name in ("article", "li", "div"):
        for el in soup.find_all(tag_name):
            classes = el.get("class")
            if classes:
                class_counter[f"{tag_name}.{'.'.join(classes)}"] += 1
    print("Most common repeated tag.class combos (candidates for LISTING_ITEM_SELECTOR):")
    for combo, count in class_counter.most_common(15):
        if count >= 3:
            print(f"  {count:4d}  {combo}")

    print("\nAll links containing '/topics/' or a news-detail-looking path:")
    seen = set()
    n = 0
    for a in soup.select("a[href]"):
        href = a.get("href", "")
        if "/topics" in href or "/news" in href or "/blog" in href:
            text = a.get_text(strip=True)
            key = (href, text[:40])
            if key in seen:
                continue
            seen.add(key)
            print(f"  {href!r}  text={text[:40]!r}")
            n += 1
            if n >= max_links:
                break

    print("\nAll <nav> / menu links (unfiltered, first 30):")
    for nav in soup.select("nav")[:2]:
        for a in nav.select("a[href]")[:30]:
            print(f"  NAV: href={a.get('href')!r} text={a.get_text(strip=True)[:40]!r}")


def main() -> None:
    dump_repeating_structure("https://keraeiko.com/category/topics")
    dump_repeating_structure("https://atashinchi30th-anime.shin-ei-animation.jp/")
    dump_repeating_structure("https://www.loft.co.jp/news/")


if __name__ == "__main__":
    sys.exit(main())
