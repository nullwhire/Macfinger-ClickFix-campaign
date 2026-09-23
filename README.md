# urlscan-tracker

Automated tracking tool for malicious infrastructure via [urlscan.io](https://urlscan.io).
Runs a search query on a schedule, accumulates observed domains and URLs over time, and
keeps the history versioned in a Git repository.

## Features

- Paginated extraction from the urlscan.io search API (works around the 100-results-per-page limit)
- Day-based partitioning (`--by-day`) to work around the per-query result ceiling on free accounts
- Cumulative mode (`--cumulative`) — never loses a domain/URL/scan already seen in previous runs
- Automation via GitHub Actions, with scheduled and manual triggers
- Automatic retry on rate limiting (HTTP 429)

## Structure

```
urlscan-tracker/
├── scripts/
│   └── urlscan_extract.py       # extraction script
├── .github/workflows/
│   └── update-domains.yml       # automation (cron + manual)
├── output/
│   ├── domains.txt               # unique, accumulated domains
│   ├── urls.txt                  # unique, accumulated URLs
│   └── results.json              # full dump of each scan (indexed by _id)
└── README.md
```

## Requirements

- Python 3.10+
- (Optional, recommended) urlscan.io API key — raises the rate limit and the per-query result ceiling

## Setup

1. Create a GitHub repository and push these files.
2. Generate an API key at [urlscan.io/user/profile](https://urlscan.io/user/profile/) and add it
   as a repository secret:
   `Settings → Secrets and variables → Actions → New repository secret`
   Name: `URLSCAN_API_KEY`
3. Check the query and parameters (`--by-day`, `--cumulative`) in
   `.github/workflows/update-domains.yml`.
4. The workflow runs every 6 hours by default. To test it right away:
   `Actions → Atualizar domínios urlscan.io → Run workflow`.

## Local usage

```bash
export URLSCAN_API_KEY="your_key"   # optional

python scripts/urlscan_extract.py \
  --query 'filename:"ext-b.4f9db6afd06a.js" OR (domain:velvet-otter-glagceis.life AND filename:"t.js")' \
  --out-dir output \
  --by-day 30 \
  --cumulative
```

### Parameters

| Flag            | Description                                                                | Default |
|-----------------|------------------------------------------------------------------------------|---------|
| `--query`       | Query in the urlscan.io search API's Elasticsearch format (required)      | —       |
| `--api-key`     | API key (or use the `URLSCAN_API_KEY` env var)                            | —       |
| `--out-dir`     | Output directory                                                            | `output`|
| `--size`        | Results per page                                                            | `100`   |
| `--by-day N`    | Runs the query separately for each of the last N days                      | `0`     |
| `--cumulative`  | Merges new results with existing ones instead of overwriting               | `false` |

## Per-query result ceiling

Free urlscan.io accounts cap the number of results returned per query, regardless
of the `total` the API reports. To check your ceiling:

```bash
curl -s https://urlscan.io/user/quotas/ -H "API-Key: <your_key>"
```

If your query has more matches than that ceiling, use `--by-day N` to partition
the search by day — each slice stays under the limit even if the aggregate doesn't.

## Known limitations

- `results.json` grows indefinitely in cumulative mode; there's no automatic rotation of old history.
- No deduplication across domain variations (distinct subdomains count as separate entries).
- Depends on the availability and rate/quota limits of urlscan.io's public API.
