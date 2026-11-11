# Freedom24 → TRMNL Terminus sidecar

This sidecar reads your Freedom24 portfolio and serves a small JSON summary on the LAN.
A Terminus extension polls it and shows the numbers on the TRMNL screen.

It uses the Python standard library only. No image build is needed.

## How it works

The sidecar sends a signed `POST https://freedom24.com/api/getPositionJson` request.

- The body is the compact JSON `{}`.
- `X-NtApi-PublicKey` holds your public key.
- `X-NtApi-Timestamp` holds the current Unix time in seconds.
- `X-NtApi-Sig` is the hex HMAC-SHA256 of `body + timestamp`, keyed with your private key.

The sidecar caches the answer for 5 minutes by default.

## Endpoints

`GET /portfolio` returns:

```json
{
  "total": 12345.67,
  "day_change": 89.01,
  "day_change_pct": 0.73,
  "invested": 12200.00,
  "cash": 145.67,
  "cost": 10000.00,
  "pl": 2200.00,
  "pl_pct": 22.0,
  "currency": "USD",
  "positions": 7,
  "holdings": [
    {
      "ticker": "VUAA.EU",
      "name": "Vanguard S&P 500 UCITS ETF",
      "qty": 50.0,
      "price": 145.2,
      "price_currency": "USD",
      "value": 7260.00,
      "weight": 58.81,
      "day_change": 12.50,
      "day_change_pct": 0.17,
      "pl": 1540.00,
      "pl_pct": 26.92
    }
  ],
  "updated": "14:05",
  "error": null
}
```

`holdings` is sorted by `value`, largest first. All money fields are in `currency`, except `price`, which is in `price_currency`.
`pl` is unrealized profit or loss: market value minus cost basis. `pl_pct` is `null` when a holding has no cost basis, such as free promotional shares.

When something fails, the response has only `error` and `updated`.

`GET /raw` returns the untouched Freedom24 response. It works only when `DEBUG=1`.

## Field mapping

| Output | Source |
| --- | --- |
| Position value | `pos[].q × pos[].mkt_price`, or `pos[].market_value` when the price is missing |
| Day change per position | `pos[].q × (pos[].mkt_price − pos[].close_price)` |
| Cost basis per position | `pos[].s`, which is `q × price_a` |
| Ticker and name | `pos[].i` and `pos[].name` |
| Cash | `acc[].s` |
| Conversion to base currency | none for rows already in `BASE_CURRENCY`; otherwise row `currval` ÷ the `BASE_CURRENCY` `currval` from the same list (`pos[]` or `acc[]`) |

`currval` is each currency's rate against one shared internal currency. It is not a rate to `BASE_CURRENCY`.
For example, EUR may show 92.19 and USD 82.14, so 1 USD is 82.14 ÷ 92.19 = 0.891 EUR.
`pos[]` and `acc[]` carry different `currval` values for the same currency, for example 82.55 and 82.14 for USD.
Mixing them inflated USD holdings by 0.5%, so each list uses its own rate.
If no `acc[]` row has `curr` equal to `BASE_CURRENCY`, `/portfolio` returns an error.

The value uses `q × mkt_price` because Freedom24 computes its own P/L (`profit_close`) from it.
`pl` then matches `profit_close` for every holding with a cost basis.

`total` is position values plus cash. `day_change_pct` divides the change by yesterday's total, which is `total − day_change`.

Cloudflare in front of the API rejects the default `Python-urllib` User-Agent with error 1010.
The sidecar therefore sends its own User-Agent.

## Run

```bash
cp .env.example .env
```

Fill in `F24_PUBLIC_KEY` and `F24_PRIVATE_KEY` in `.env`. Then start it:

```bash
docker compose up -d
```

```bash
curl http://localhost:8090/portfolio
```

## Terminus

The Terminus instance at `http://192.168.1.152:2300` has the extension "Freedom24 Portfolio" (id 28).
It polls `http://192.168.1.152:8090/portfolio` every 15 minutes.
The sidecar must therefore run on the host `192.168.1.152`.

## Setup with Portainer

Use `compose.portainer.yaml` for Portainer. The regular `compose.yaml` does not work there.
Portainer's copy of the repo has no `.env` file, and Portainer cannot bind-mount `./app.py` from it.

The Portainer file builds a small image that contains `app.py`. It reads the keys from `stack.env`.
Portainer creates `stack.env` from the environment variables you enter in the stack editor.

1. In Portainer, open **Stacks**, then **Add stack**. Set **Name** to `freedom24-sidecar`, then choose **Repository**.
2. Set **Repository URL** to `https://github.com/kmgalanakis/freedom24-trmnl`.
   The repo is private, so turn on **Authentication** and enter a GitHub personal access token that can read it.
3. Set **Repository reference** to `refs/heads/main` and **Compose path** to `compose.portainer.yaml`.
4. Under **Environment variables**, add `F24_PUBLIC_KEY` and `F24_PRIVATE_KEY`.
   Optionally add `BASE_CURRENCY`, `CACHE_SECONDS` and `DEBUG`. Keep `DEBUG=0` here.
5. Optional: turn on **GitOps updates**. Portainer then redeploys the stack when you push to `main`.
6. Click **Deploy the stack**.

Check it from any machine on the LAN:

```bash
curl http://192.168.1.152:8090/portfolio
```

## Security

The Freedom24 API keys can place trades, not only read the account. Freedom24 documents no read-only keys.
Do not forward port 8090 on your router.
Keep `.env` and `stack.env` out of git. The `.gitignore` file already excludes both.
