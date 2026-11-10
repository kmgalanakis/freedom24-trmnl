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
  "currency": "USD",
  "positions": 7,
  "updated": "14:05",
  "error": null
}
```

When something fails, the response has only `error` and `updated`.

`GET /raw` returns the untouched Freedom24 response. It works only when `DEBUG=1`.

## Field mapping

| Output | Source |
| --- | --- |
| Position value | `pos[].market_value`, or `pos[].q × pos[].mkt_price` when it is missing |
| Day change per position | `pos[].q × (pos[].mkt_price − pos[].close_price)` |
| Cash | `acc[].s` |
| Conversion to base currency | row `currval` ÷ `currval` of the `acc[]` row whose `curr` is `BASE_CURRENCY` |

`currval` is each currency's rate against one shared internal currency. It is not a rate to `BASE_CURRENCY`.
For example, EUR may show 92.19 and USD 82.14, so 1 USD is 82.14 ÷ 92.19 = 0.891 EUR.
If no `acc[]` row has `curr` equal to `BASE_CURRENCY`, `/portfolio` returns an error.

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

## Security

Do not forward port 8090 on your router. The keys can read your account.
Keep `.env` out of git. The `.gitignore` file already excludes it.
