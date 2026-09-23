# urlscan-tracker

Extrai e mantém atualizada a lista de domínios/URLs de uma query de pesquisa no urlscan.io.

## Setup

1. Cria um repo novo no GitHub e faz push destes ficheiros.
2. (Opcional mas recomendado) Cria uma API key em https://urlscan.io/user/profile/ e adiciona-a
   como secret do repo: **Settings → Secrets and variables → Actions → New repository secret**,
   com o nome `URLSCAN_API_KEY`.
3. O workflow em `.github/workflows/update-domains.yml` corre a cada 6h e também pode ser
   disparado à mão em **Actions → Atualizar domínios urlscan.io → Run workflow**.
4. Os resultados ficam em `output/`:
   - `domains.txt` — domínios únicos
   - `urls.txt` — URLs únicos
   - `results.json` — dump completo (para análise mais fina)

## Uso local

```bash
pip install --break-system-packages -U pip  # se necessário
export URLSCAN_API_KEY="a_tua_key"           # opcional
python scripts/urlscan_extract.py \
  --query 'filename:"ext-b.4f9db6afd06a.js" OR (domain:velvet-otter-glagceis.life AND filename:"t.js")' \
  --out-dir output
```

## Ajustar a query

Muda a query diretamente no `run:` do workflow (`.github/workflows/update-domains.yml`)
e no exemplo acima.
