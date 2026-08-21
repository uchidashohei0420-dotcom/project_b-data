"""TEMPORARY diagnostic script, pass 3: Loft's actual online store search."""
from __future__ import annotations

import sys

import requests
from bs4 import BeautifulSoup

HEADERS = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0 Safari/537.36"}


def inspect(url: str) -> None:
    print(f"\n===== {url} =====")
    try:
        resp = requests.get(url, headers=HEADERS, timeout=15, allow_redirects=True)
    except Exception as exc:  # noqa: BLE001
        print(f"FETCH ERROR: {exc}")
        return
    print(f"status={resp.status_code} final_url={resp.url} bytes={len(resp.content)}")

    soup = BeautifulSoup(resp.text, "lxml")
    for form in soup.select("form"):
        print(f"  FORM: action={form.get('action')!r} method={form.get('method')!r}")
        for inp in form.select("input"):
            print(f"    INPUT: name={inp.get('name')!r} type={inp.get('type')!r} placeholder={inp.get('placeholder')!r}")

    for a in soup.select("a[href]"):
        href = a.get("href", "")
        text = a.get_text(strip=True)
        if any(k in (href + text).lower() for k in ("search", "検索", "item", "product", "goods", "keyword")):
            print(f"  LINK: href={href!r} text={text[:40]!r}")


def main() -> None:
    inspect("https://www.loft.co.jp/store/")


if __name__ == "__main__":
    sys.exit(main())
