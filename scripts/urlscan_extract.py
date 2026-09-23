#!/usr/bin/env python3
"""
Extrai TODOS os resultados de uma query de pesquisa do urlscan.io,
paginando via search_after, e guarda:
  - output/results.json  -> dump completo de cada resultado
  - output/domains.txt   -> lista única e ordenada de domínios
  - output/urls.txt      -> lista única e ordenada de URLs completos

Uso:
    python scripts/urlscan_extract.py --query 'QUERY' [--api-key KEY] [--out-dir output]

A API key pode vir também da variável de ambiente URLSCAN_API_KEY.
Sem API key funciona na mesma, mas com rate limit mais baixo.
"""

import argparse
import json
import os
import time
import urllib.error
import urllib.parse
import urllib.request

API_URL = "https://urlscan.io/api/v1/search/"


def fetch_page(query: str, search_after: str | None, size: int, api_key: str | None) -> dict:
    params = {"q": query, "size": size}
    if search_after:
        params["search_after"] = search_after
    url = f"{API_URL}?{urllib.parse.urlencode(params)}"

    req = urllib.request.Request(url)
    if api_key:
        req.add_header("API-Key", api_key)

    for attempt in range(5):
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                return json.loads(resp.read().decode())
        except urllib.error.HTTPError as e:
            if e.code == 429:
                wait = 5 * (attempt + 1)
                print(f"Rate limited, à espera {wait}s...")
                time.sleep(wait)
                continue
            raise
    raise RuntimeError("Falhou após várias tentativas (rate limit persistente).")


def fetch_all(query: str, api_key: str | None, size: int = 100, sleep: float = 0.6) -> list[dict]:
    all_results = []
    search_after = None
    page = 0

    while True:
        data = fetch_page(query, search_after, size, api_key)
        results = data.get("results", [])
        if not results:
            break

        all_results.extend(results)
        page += 1
        print(f"Página {page}: +{len(results)} (total {len(all_results)})")

        sort = results[-1].get("sort")
        if not sort or not data.get("hasMore"):
            break

        search_after = ",".join(str(x) for x in sort)
        time.sleep(sleep)

    return all_results


def extract_domains_and_urls(results: list[dict]) -> tuple[list[str], list[str]]:
    domains, urls = set(), set()
    for r in results:
        page = r.get("page", {})
        if page.get("domain"):
            domains.add(page["domain"])
        if page.get("url"):
            urls.add(page["url"])
    return sorted(domains), sorted(urls)


def main():
    parser = argparse.ArgumentParser(description="Extrai resultados do urlscan.io search API")
    parser.add_argument("--query", required=True, help="Query no formato da search API do urlscan.io")
    parser.add_argument("--api-key", default=os.environ.get("URLSCAN_API_KEY"), help="API key (ou var URLSCAN_API_KEY)")
    parser.add_argument("--out-dir", default="output")
    parser.add_argument("--size", type=int, default=100)
    args = parser.parse_args()

    os.makedirs(args.out_dir, exist_ok=True)

    results = fetch_all(args.query, api_key=args.api_key, size=args.size)
    domains, urls = extract_domains_and_urls(results)

    with open(os.path.join(args.out_dir, "results.json"), "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)

    with open(os.path.join(args.out_dir, "domains.txt"), "w", encoding="utf-8") as f:
        f.write("\n".join(domains) + ("\n" if domains else ""))

    with open(os.path.join(args.out_dir, "urls.txt"), "w", encoding="utf-8") as f:
        f.write("\n".join(urls) + ("\n" if urls else ""))

    print(f"\nTotal: {len(results)} resultados | {len(domains)} domínios únicos | {len(urls)} URLs únicos")


if __name__ == "__main__":
    main()
