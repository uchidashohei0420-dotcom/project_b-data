"""TEMPORARY diagnostic script — not part of the pipeline. Run via a throwaway workflow
step to discover real URLs from inside GitHub Actions (this repo's dev sandbox has no
general internet egress, so this is the only way to learn real site structure).
Delete this file once the real scraper URLs/selectors are fixed.
"""
from __future__ import annotations

import sys

import requests
from bs4 import BeautifulSoup

HEADERS = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0 Safari/537.36"}

TARGETS = [
    "https://keraeiko.com/",
    "https://atashinchi30th-anime.shin-ei-animation.jp/",
    "https://www.loft.co.jp/",
    "https://www.animate-onlineshop.jp/",
]

KEYWORDS = ("news", "お知らせ", "イベント", "event", "search", "検索", "商品", "product", "goods")


def main() -> None:
    for url in TARGETS:
        print(f"\n===== {url} =====")
        try:
            resp = requests.get(url, headers=HEADERS, timeout=15, allow_redirects=True)
        except Exception as exc:  # noqa: BLE001
            print(f"FETCH ERROR: {exc}")
            continue
        print(f"status={resp.status_code} final_url={resp.url} bytes={len(resp.content)}")

        soup = BeautifulSoup(resp.text, "lxml")
        seen = set()
        for a in soup.select("a[href]"):
            href = a.get("href", "")
            text = a.get_text(strip=True)
            haystack = (href + " " + text).lower()
            if any(k.lower() in haystack for k in KEYWORDS):
                key = (href, text[:40])
                if key in seen:
                    continue
                seen.add(key)
                print(f"  LINK: href={href!r} text={text[:40]!r}")

        forms = soup.select("form")
        for form in forms[:5]:
            print(f"  FORM: action={form.get('action')!r} method={form.get('method')!r}")
            for inp in form.select("input[name]"):
                print(f"    INPUT: name={inp.get('name')!r} type={inp.get('type')!r}")


if __name__ == "__main__":
    sys.exit(main())
