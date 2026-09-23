#!/usr/bin/env python3
"""
Extracts ALL results from a search query on urlscan.io,
paging via `search_after`, and saves:
  - output/results.json  -> complete dump of each result
  - output/domains.txt   -> single, sorted list of domains
  - output/urls.txt      -> single, sorted list of full URLs

Usage:
    python scripts/urlscan_extract.py --query ‘QUERY’ [--api-key KEY] [--out-dir output]

The API key can also be provided via the URLSCAN_API_KEY environment variable.
It works without an API key as well, but with a lower rate limit.


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

    last_error = None
    for attempt in range(5):
        try:
            with urllib.request.urlopen(req, timeout=60) as resp:
                return json.loads(resp.read().decode())
        except urllib.error.HTTPError as e:
            if e.code == 429:
                wait = 5 * (attempt + 1)
                print(f"Rate limited, à espera {wait}s...")
                time.sleep(wait)
                last_error = e
                continue
            raise
        except (urllib.error.URLError, TimeoutError, ConnectionError, OSError) as e:
            wait = 5 * (attempt + 1)
            print(f"Erro de rede ({e}), tentativa {attempt + 1}/5, à espera {wait}s...")
            time.sleep(wait)
            last_error = e
            continue
    raise RuntimeError(f"Falhou após várias tentativas: {last_error}")


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


def fetch_all_by_day(query: str, api_key: str | None, days: int, size: int = 100, sleep: float = 0.6) -> list[dict]:
    
    import datetime

    all_results = []
    seen_ids = set()
    today = datetime.datetime.now(datetime.timezone.utc).date()

    for i in range(days):
        day = today - datetime.timedelta(days=i)
        day_query = f'({query}) AND date:[{day}T00:00:00 TO {day}T23:59:59]'
        print(f"--- {day} ---")
        try:
            day_results = fetch_all(day_query, api_key=api_key, size=size, sleep=sleep)
        except RuntimeError as e:
            print(f"AVISO: falhou o dia {day} após retries ({e}) — a saltar este dia.")
            continue
        for r in day_results:
            rid = r.get("_id")
            if rid and rid not in seen_ids:
                seen_ids.add(rid)
                all_results.append(r)

    return all_results


def load_existing_results(path: str) -> dict[str, dict]:
  
    if not os.path.exists(path):
        return {}
    try:
        with open(path, "r", encoding="utf-8") as f:
            existing = json.load(f)
    except (json.JSONDecodeError, OSError):
        return {}
    return {r["_id"]: r for r in existing if r.get("_id")}


def load_existing_lines(path: str) -> set[str]:
    if not os.path.exists(path):
        return set()
    with open(path, "r", encoding="utf-8") as f:
        return {line.strip() for line in f if line.strip()}


def main():
    parser = argparse.ArgumentParser(description="Extrai resultados do urlscan.io search API")
    parser.add_argument("--query", required=True, help="Query no formato da search API do urlscan.io")
    parser.add_argument("--api-key", default=os.environ.get("URLSCAN_API_KEY"), help="API key (ou var URLSCAN_API_KEY)")
    parser.add_argument("--out-dir", default="output")
    parser.add_argument("--size", type=int, default=100)
    parser.add_argument(
        "--by-day",
        type=int,
        default=0,
        metavar="N",
        help="Se >0, corre a query separadamente para cada um dos últimos N dias, "
             "para contornar o teto de resultados por query de contas gratuitas.",
    )
    parser.add_argument(
        "--cumulative",
        action="store_true",
        help="Junta os novos resultados aos já existentes em output/ em vez de substituir "
             "(nunca perde um domínio/URL/scan já visto em execuções anteriores).",
    )
    args = parser.parse_args()

    os.makedirs(args.out_dir, exist_ok=True)

    if args.by_day > 0:
        new_results = fetch_all_by_day(args.query, api_key=args.api_key, days=args.by_day, size=args.size)
    else:
        new_results = fetch_all(args.query, api_key=args.api_key, size=args.size)

    results_path = os.path.join(args.out_dir, "results.json")
    domains_path = os.path.join(args.out_dir, "domains.txt")
    urls_path = os.path.join(args.out_dir, "urls.txt")

    if args.cumulative:
        merged = load_existing_results(results_path)
        for r in new_results:
            rid = r.get("_id")
            if rid:
                merged[rid] = r
        results = list(merged.values())

        domains_new, urls_new = extract_domains_and_urls(new_results)
        domains = sorted(load_existing_lines(domains_path) | set(domains_new))
        urls = sorted(load_existing_lines(urls_path) | set(urls_new))
    else:
        results = new_results
        domains, urls = extract_domains_and_urls(results)

    with open(results_path, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)

    with open(domains_path, "w", encoding="utf-8") as f:
        f.write("\n".join(domains) + ("\n" if domains else ""))

    with open(urls_path, "w", encoding="utf-8") as f:
        f.write("\n".join(urls) + ("\n" if urls else ""))

    print(f"\nNesta execução: {len(new_results)} resultados novos processados")
    print(f"Total acumulado: {len(results)} resultados | {len(domains)} domínios únicos | {len(urls)} URLs únicos")


if __name__ == "__main__":
    main()
