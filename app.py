"""Freedom24 portfolio summary for Terminus.

Signs a Tradernet API v3 request (getPositionJson) and serves a small JSON
summary on the LAN: total value and day change. Standard library only.

Endpoints
  GET /portfolio  -> {"total", "day_change", "day_change_pct", "currency", "positions", "updated", "error"}
  GET /raw        -> the untouched Freedom24 response (only when DEBUG=1)
"""

import hashlib
import hmac
import json
import os
import time
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

PUBLIC_KEY = os.environ.get("F24_PUBLIC_KEY", "")
PRIVATE_KEY = os.environ.get("F24_PRIVATE_KEY", "")
API_URL = os.environ.get("F24_API_URL", "https://freedom24.com/api")
CURRENCY = os.environ.get("BASE_CURRENCY", "USD")
CACHE_SECONDS = int(os.environ.get("CACHE_SECONDS", "300"))
DEBUG = os.environ.get("DEBUG", "0") == "1"
PORT = int(os.environ.get("PORT", "8090"))

_cache = {"at": 0.0, "raw": None, "error": None}


def call(cmd, params=None):
    """POST a signed Tradernet v3 command and return the decoded JSON."""
    payload = json.dumps(params or {}, separators=(",", ":"))
    timestamp = str(int(time.time()))
    signature = hmac.new(
        PRIVATE_KEY.encode(), (payload + timestamp).encode(), hashlib.sha256
    ).hexdigest()
    request = urllib.request.Request(
        f"{API_URL}/{cmd}",
        data=payload.encode(),
        method="POST",
        headers={
            "Content-Type": "application/json",
            "User-Agent": "freedom24-trmnl/1.0",  # Cloudflare blocks the default Python-urllib agent (error 1010)
            "X-NtApi-PublicKey": PUBLIC_KEY,
            "X-NtApi-Timestamp": timestamp,
            "X-NtApi-Sig": signature,
        },
    )
    with urllib.request.urlopen(request, timeout=20) as response:
        return json.loads(response.read().decode())


def num(value):
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def fetch_raw():
    """Return the latest getPositionJson response, cached for CACHE_SECONDS."""
    if time.time() - _cache["at"] < CACHE_SECONDS and (_cache["raw"] or _cache["error"]):
        return _cache["raw"], _cache["error"]
    try:
        raw = call("getPositionJson")
        error = raw.get("errMsg") or raw.get("error") if isinstance(raw, dict) else None
    except Exception as exc:  # network, HTTP or JSON errors
        raw, error = None, f"{type(exc).__name__}: {exc}"
    _cache.update(at=time.time(), raw=raw, error=error)
    return raw, error


def summarize(raw):
    """Total value and day change in BASE_CURRENCY.

    currval is each row's rate against one shared internal currency, not a
    rate to BASE_CURRENCY. pos[] and acc[] carry different currval values for
    the same currency, so each list is converted with its own BASE_CURRENCY
    rate, and rows already in BASE_CURRENCY are never converted.
    """
    result = raw.get("result", raw) if isinstance(raw, dict) else {}
    portfolio = result.get("ps", result) if isinstance(result, dict) else {}
    positions = portfolio.get("pos") or []
    accounts = portfolio.get("acc") or []

    def base_rate(rows):
        return next(
            (num(r.get("currval")) for r in rows if r.get("curr") == CURRENCY), None
        )

    acc_base = base_rate(accounts)
    pos_base = base_rate(positions) or acc_base
    if not acc_base:
        return {"error": f"no {CURRENCY} row in acc[] to convert with"}

    def factor(row, base):
        if row.get("curr") == CURRENCY:
            return 1.0
        return (num(row.get("currval")) or base) / base

    def pct(part, whole):
        return round(part / whole * 100, 2) if whole else 0.0

    holdings = []
    invested = cost = change = 0.0
    for p in positions:
        qty = num(p.get("q")) or 0.0
        price = num(p.get("mkt_price"))
        close = num(p.get("close_price"))
        # Freedom24 computes its own P/L (profit_close) from q × mkt_price, so the
        # value uses it too. market_value is only a fallback; it differs slightly.
        value = qty * price if price is not None else num(p.get("market_value"))
        if value is None:
            continue
        f = factor(p, pos_base)
        # s is the position's cost basis (q × average price) in its own currency.
        row_cost = (num(p.get("s")) or 0.0) * f
        row_change = qty * (price - close) * f if price is not None and close else 0.0
        invested += value * f
        cost += row_cost
        change += row_change
        holdings.append({
            "ticker": p.get("i") or "",
            "name": p.get("name") or "",
            "qty": qty,
            "price": price,
            "price_currency": p.get("curr") or "",
            "value": round(value * f, 2),
            "day_change": round(row_change, 2),
            "day_change_pct": pct(price - close, close) if price is not None and close else 0.0,
            "pl": round(value * f - row_cost, 2),
            # None for positions with no cost basis, such as free promotional shares.
            "pl_pct": pct(value * f - row_cost, row_cost) if row_cost else None,
        })

    cash = sum((num(a.get("s")) or 0.0) * factor(a, acc_base) for a in accounts)
    total = invested + cash
    previous = total - change
    holdings.sort(key=lambda h: h["value"], reverse=True)
    for h in holdings:
        h["weight"] = pct(h["value"], total)

    return {
        "total": round(total, 2),
        "day_change": round(change, 2),
        "day_change_pct": pct(change, previous),
        "invested": round(invested, 2),
        "cash": round(cash, 2),
        "cost": round(cost, 2),
        "pl": round(invested - cost, 2),
        "pl_pct": pct(invested - cost, cost),
        "currency": CURRENCY,
        "positions": len(holdings),
        "holdings": holdings,
        "error": None,
    }


class Handler(BaseHTTPRequestHandler):
    def _send(self, status, body):
        data = json.dumps(body).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self):
        path = self.path.split("?")[0]
        if path == "/raw" and DEBUG:
            raw, error = fetch_raw()
            return self._send(200, raw if raw is not None else {"error": error})
        if path != "/portfolio":
            return self._send(404, {"error": "not found"})
        if not PUBLIC_KEY or not PRIVATE_KEY:
            return self._send(200, {"error": "F24_PUBLIC_KEY / F24_PRIVATE_KEY not set"})
        raw, error = fetch_raw()
        body = {"error": error} if error or raw is None else summarize(raw)
        body["updated"] = time.strftime("%H:%M", time.localtime(_cache["at"]))
        self._send(200, body)

    def log_message(self, fmt, *args):  # keep the container log quiet
        pass


if __name__ == "__main__":
    ThreadingHTTPServer(("0.0.0.0", PORT), Handler).serve_forever()
