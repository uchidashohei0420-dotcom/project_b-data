"""TEMPORARY diagnostic script, pass 4: dump raw HTML of one keraeiko.com listing card."""
from __future__ import annotations

import sys

import requests
from bs4 import BeautifulSoup

HEADERS = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0 Safari/537.36"}


def main() -> None:
    resp = requests.get("https://keraeiko.com/category/topics", headers=HEADERS, timeout=15)
    soup = BeautifulSoup(resp.text, "lxml")
    cards = soup.select("div.uk-card.uk-grid-collapse")
    print(f"found {len(cards)} cards")
    if cards:
        print(cards[0].prettify()[:3000])


if __name__ == "__main__":
    sys.exit(main())
