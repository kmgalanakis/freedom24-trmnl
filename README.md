# Freedom24 → TRMNL Terminus sidecar

This project shows your [Freedom24](https://freedom24.com) portfolio on an e-ink screen run by [Terminus](https://github.com/usetrmnl/terminus), the self-hosted TRMNL server.

It has two parts:

- **The sidecar** (`app.py`) reads your portfolio from the Freedom24 API and serves a JSON summary on your LAN.
- **The Terminus extension** (`terminus/`) polls that JSON and renders it as a screen with totals, profit or loss, and one row per holding.

The sidecar uses the Python standard library only. It has no dependencies.

```text
Freedom24 API  ──signed POST──▶  sidecar :8090  ◀──GET /portfolio, every 15 min──  Terminus  ──▶  e-ink device
```

## Contents

| Path | Purpose |
| --- | --- |
| `app.py` | The sidecar |
| `compose.yaml` | Runs the sidecar with Docker Compose on any machine |
| `compose.portainer.yaml` | Runs the sidecar as a Portainer stack built from this repo |
| `Dockerfile` | Image used by the Portainer stack |
| `.env.example` | Settings template. Copy it to `.env` |
| `terminus/` | The Terminus extension: template, settings and setup steps |

## Requirements

- A Freedom24 account with API keys.
- Docker, or Python 3.10 or later.
- A Terminus server on the same network as the sidecar.

## 1. Create Freedom24 API keys

1. Sign in at [freedom24.com](https://freedom24.com).
2. Open the [API key page](https://freedom24.com/tradernet-api/auth-api) in the same browser and generate a key pair.
3. Copy the public key and the private key. Freedom24 may show the private key only once.

> [!WARNING]
> Freedom24 documents no read-only keys. Assume the keys can place trades.
> The sidecar only reads positions, but anyone with the keys could trade on your account.
> Read [Security](#security) before you deploy.

## 2. Configure

```bash
cp .env.example .env
```

Edit `.env`:

| Variable | Default | Meaning |
| --- | --- | --- |
| `F24_PUBLIC_KEY` | none | Your Freedom24 public key. Required. |
| `F24_PRIVATE_KEY` | none | Your Freedom24 private key. Required. |
| `BASE_CURRENCY` | `USD` | Currency for all totals. Your account needs a cash row in this currency. |
| `CACHE_SECONDS` | `300` | Seconds to reuse the last Freedom24 answer. |
| `TZ` | `UTC` | Time zone for the `updated` time, for example `Europe/London`. |
| `DEBUG` | `0` | Set to `1` to enable `/raw`. Turn it off again afterwards. |
| `PORT` | `8090` | Port the sidecar listens on inside the container. |
| `F24_API_URL` | `https://freedom24.com/api` | API base URL. `https://tradernet.com/api` also works. |

Put values right after `=`, without quotes.

## 3. Run the sidecar

### With Docker Compose

`compose.yaml` runs the stock `python:3.12-alpine` image and mounts `app.py` into it, so no build is needed.
It reads your settings from `.env` and publishes port 8090.

Run these commands from the repo folder. Start the sidecar in the background:

```bash
docker compose up -d
```

Check that it answers:

```bash
curl http://localhost:8090/portfolio
```

Useful commands:

| Task | Command |
| --- | --- |
| Show status | `docker compose ps` |
| Show logs | `docker compose logs -f` |
| Apply a changed `app.py`, for example after `git pull` | `docker compose restart` |
| Apply a changed `.env` | `docker compose up -d --force-recreate` |
| Stop and remove | `docker compose down` |

`docker compose restart` does not reread `.env`. Compose reads it only when it creates the container, so use `--force-recreate` after you edit it.
The sidecar logs almost nothing. When a request fails, the reason appears in the `error` field of `/portfolio`.

### With the Docker CLI

Build the image from the `Dockerfile` and start a container:

```bash
docker build -t freedom24-sidecar .
```

```bash
docker run -d --name freedom24-sidecar --restart unless-stopped --env-file .env -p 8090:8090 freedom24-sidecar
```

```bash
curl http://localhost:8090/portfolio
```

The image contains `app.py`, so rebuild it after every change:

```bash
git pull && docker build -t freedom24-sidecar . && docker rm -f freedom24-sidecar
```

Then run the same `docker run` command again.

To skip the build, mount `app.py` into the stock Python image. Run this from the repo folder:

```bash
docker run -d --name freedom24-sidecar --restart unless-stopped --env-file .env -p 8090:8090 -v "$PWD/app.py:/app/app.py:ro" -w /app python:3.12-alpine python -u app.py
```

With the mount, `docker restart freedom24-sidecar` picks up changes to `app.py`.

Useful commands:

| Task | Command |
| --- | --- |
| Show logs | `docker logs freedom24-sidecar` |
| Apply a changed `.env` | `docker rm -f freedom24-sidecar`, then run `docker run` again |
| Stop and remove | `docker rm -f freedom24-sidecar` |

`docker restart` does not reread `.env`. Docker reads `--env-file` only when it creates the container.
Write values in `.env` without quotes, because `--env-file` keeps quotes as part of the value.

### Without Docker

```bash
set -a; . ./.env; set +a; python3 app.py
```

To run it on a server with Portainer, see [Deploy with Portainer](#deploy-with-portainer).

## 4. Add the Terminus extension

Follow [terminus/README.md](terminus/README.md).
Terminus must reach the sidecar, so use the sidecar host's LAN address in the exchange URL, not `localhost`.

## Deploy with Portainer

Use `compose.portainer.yaml`. The regular `compose.yaml` does not work in Portainer, for two reasons.
Portainer's copy of the repo has no `.env` file, and Portainer cannot bind-mount `./app.py` from that copy.

The Portainer file builds a small image that contains `app.py`. It reads its settings from `stack.env`.
Portainer creates `stack.env` from the environment variables you enter in the stack editor.

1. In Portainer, open **Stacks**, then **Add stack**. Name it, for example `freedom24-sidecar`, and choose **Repository**.
2. Set **Repository URL** to this repo's URL.
   If your copy of the repo is private, turn on **Authentication** and enter a GitHub token that can read it.
3. Set **Repository reference** to `refs/heads/main` and **Compose path** to `compose.portainer.yaml`.
4. Under **Environment variables**, add `F24_PUBLIC_KEY` and `F24_PRIVATE_KEY`.
   Add any other variable from the table above, for example `TZ`. Keep `DEBUG=0`.
5. Optional: turn on **GitOps updates**, so Portainer redeploys when `main` changes.
6. Click **Deploy the stack**.

To update, click **Pull and redeploy**. Portainer rebuilds the image from the repo.
The service has no image name on purpose. With a name, "Re-pull image" tries to pull it from Docker Hub and fails.

## API

### `GET /portfolio`

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
  "positions": 1,
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

These numbers are made up for the example.

| Field | Meaning |
| --- | --- |
| `total` | Holdings plus cash |
| `invested` | Market value of all holdings |
| `cash` | Cash in all currencies |
| `cost` | Cost basis of all holdings |
| `pl`, `pl_pct` | Unrealized profit or loss: `invested − cost` |
| `day_change`, `day_change_pct` | Change since the previous close. The percentage is relative to `total − day_change` |
| `holdings` | One row per holding, largest `value` first |
| `holdings[].weight` | Share of `total`, in percent |
| `holdings[].pl_pct` | `null` when the holding has no cost basis, such as free promotional shares |
| `updated` | Time of the last Freedom24 call, in `TZ` |
| `error` | `null`, or a message. On an error, the response has only `error` and `updated` |

All money fields are in `currency`, except `holdings[].price`, which is in `price_currency`.

### `GET /raw`

Returns the untouched Freedom24 response. It is off unless `DEBUG=1`, and it then answers `404`.

## How it works

The sidecar sends `POST https://freedom24.com/api/getPositionJson`, signed as the [Freedom24 API docs](https://freedom24.com/tradernet-api/auth-api) describe:

- The body is the compact JSON `{}`, sent with `Content-Type: application/json`.
- `X-NtApi-PublicKey` holds the public key.
- `X-NtApi-Timestamp` holds the current Unix time in seconds.
- `X-NtApi-Sig` is the hex HMAC-SHA256 of `body + timestamp`, keyed with the private key.

### Field mapping

| Output | Freedom24 source |
| --- | --- |
| Holding value | `pos[].q × pos[].mkt_price`, or `pos[].market_value` when the price is missing |
| Day change | `pos[].q × (pos[].mkt_price − pos[].close_price)` |
| Cost basis | `pos[].s`, which equals `q × price_a` |
| Ticker and name | `pos[].i` and `pos[].name` |
| Cash | `acc[].s`, one row per currency in `acc[].curr` |
| Currency conversion | See below |

The value uses `q × mkt_price` because Freedom24 computes its own profit (`profit_close`) the same way.
`pl` therefore matches `profit_close` for every holding with a cost basis.

`currval` is each row's rate against one shared internal currency. It is not a rate to `BASE_CURRENCY`.
For example, EUR may show 92.19 and USD 82.14, so 1 USD is 82.14 ÷ 92.19 = 0.891 EUR.
The sidecar converts a row by dividing its `currval` by the `currval` of `BASE_CURRENCY`.

Two details matter here:

- Rows already in `BASE_CURRENCY` are never converted.
- `pos[]` and `acc[]` can carry different `currval` values for the same currency. Each list therefore uses its own `BASE_CURRENCY` rate.

## Troubleshooting

| Symptom | Cause and fix |
| --- | --- |
| `HTTPError: HTTP Error 403: Forbidden` | Cloudflare blocks the default `Python-urllib` User-Agent with error 1010. The sidecar sends its own User-Agent. If the error returns, check that your copy still sends it. |
| `F24_PUBLIC_KEY / F24_PRIVATE_KEY not set` | `.env` or the Portainer variables are empty or not saved. Recreate the container after you change them. |
| `no USD row in acc[] to convert with` | Your account has no cash row in `BASE_CURRENCY`. Choose a currency your account holds. |
| Portainer: `pull access denied for ...` | The service in `compose.portainer.yaml` has an image name. Remove it, so Portainer builds the image and never pulls it. |
| Numbers lag the Freedom24 website | The sidecar caches for `CACHE_SECONDS`, and Terminus polls every 15 minutes. Allow up to about 20 minutes. |
| Rows cut off on the screen | The device model's scale factor shrinks the space. See [terminus/README.md](terminus/README.md#screen-size). |

## Security

- **The keys can trade.** Keep them only in `.env` or in Portainer's stack variables. Both `.env` and `stack.env` are in `.gitignore`.
- **The sidecar has no login.** Anyone on your network can read `/portfolio`, which lists your holdings and balances.
  Run it only on a trusted network, and never forward port 8090 on your router.
- **Keep `DEBUG=0`** except while debugging. `/raw` exposes the full Freedom24 response.
- **Revoke leaked keys** on the [Freedom24 API key page](https://freedom24.com/tradernet-api/auth-api) right away.

## License

[MIT](LICENSE)

## Disclaimer

This project is not affiliated with Freedom24, Freedom Finance, Tradernet or TRMNL.
It reads data only and gives no investment advice. Check important numbers on the Freedom24 website.
