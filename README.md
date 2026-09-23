# urlscan-tracker

Ferramenta de tracking automatizado de infraestrutura maliciosa via [urlscan.io](https://urlscan.io).
Corre uma query de pesquisa em ciclo, acumula domínios e URLs observados ao longo do tempo, e mantém
o histórico versionado num repositório Git.

## Funcionalidades

- Extração paginada da search API do urlscan.io (contorna o limite de 100 resultados por página)
- Particionamento por dia (`--by-day`) para contornar o teto de resultados por query de contas gratuitas
- Modo cumulativo (`--cumulative`) — nunca perde um domínio/URL/scan já visto em execuções anteriores
- Automação via GitHub Actions, com execução agendada e disparo manual
- Retry automático em rate limiting (HTTP 429)

## Estrutura

```
urlscan-tracker/
├── scripts/
│   └── urlscan_extract.py       # script de extração
├── .github/workflows/
│   └── update-domains.yml       # automação (cron + manual)
├── output/
│   ├── domains.txt               # domínios únicos, acumulados
│   ├── urls.txt                  # URLs únicos, acumulados
│   └── results.json              # dump completo de cada scan (indexado por _id)
└── README.md
```

## Requisitos

- Python 3.10+
- (Opcional, recomendado) API key do urlscan.io — sobe o rate limit e o teto de resultados por query

## Setup

1. Cria um repositório no GitHub e faz push destes ficheiros.
2. Gera uma API key em [urlscan.io/user/profile](https://urlscan.io/user/profile/) e adiciona-a
   como secret do repositório:
   `Settings → Secrets and variables → Actions → New repository secret`
   Nome: `URLSCAN_API_KEY`
3. Confirma a query e os parâmetros (`--by-day`, `--cumulative`) em
   `.github/workflows/update-domains.yml`.
4. O workflow corre a cada 6h por defeito. Para testar de imediato:
   `Actions → Atualizar domínios urlscan.io → Run workflow`.

## Uso local

```bash
export URLSCAN_API_KEY="a_tua_key"   # opcional

python scripts/urlscan_extract.py \
  --query 'filename:"ext-b.4f9db6afd06a.js" OR (domain:velvet-otter-glagceis.life AND filename:"t.js")' \
  --out-dir output \
  --by-day 30 \
  --cumulative
```

### Parâmetros

| Flag            | Descrição                                                                 | Default |
|-----------------|----------------------------------------------------------------------------|---------|
| `--query`       | Query no formato Elasticsearch da search API do urlscan.io (obrigatório)  | —       |
| `--api-key`     | API key (ou usa a env var `URLSCAN_API_KEY`)                              | —       |
| `--out-dir`     | Diretório de output                                                        | `output`|
| `--size`        | Resultados por página                                                      | `100`   |
| `--by-day N`    | Corre a query separadamente para cada um dos últimos N dias                | `0`     |
| `--cumulative`  | Junta os novos resultados aos já existentes em vez de substituir           | `false` |

## Teto de resultados por query

Contas gratuitas do urlscan.io limitam o número de resultados devolvidos por query,
independentemente do `total` reportado pela API. Para confirmar o teu teto:

```bash
curl -s https://urlscan.io/user/quotas/ -H "API-Key: <a_tua_key>"
```

Se a query tiver mais matches do que esse teto, usa `--by-day N` para particionar a
pesquisa por dia — cada fatia fica abaixo do limite mesmo que o agregado não fique.

## Limitações conhecidas

- `results.json` cresce indefinidamente em modo cumulativo; sem rotação automática de histórico antigo.
- Sem deduplicação entre variações de domínio (subdomínios distintos contam como entradas separadas).
- Depende da disponibilidade e dos limites de rate/quota da API pública do urlscan.io.
