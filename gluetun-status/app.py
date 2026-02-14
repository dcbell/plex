import os
import time
import requests
from flask import Flask, jsonify, Response

app = Flask(__name__)

GLUETUN_BASE = os.getenv("GLUETUN_BASE", "http://vpn:8000").rstrip("/")
CACHE_SECONDS = int(os.getenv("CACHE_SECONDS", "15"))
GEO_LOOKUP = os.getenv("GEO_LOOKUP", "ip-api")  # ip-api or none

_cache = {"ts": 0.0, "data": None}


def _get_json(path: str, timeout=3):
    r = requests.get(f"{GLUETUN_BASE}{path}", timeout=timeout)
    r.raise_for_status()
    return r.json()


def _geo_lookup(public_ip: str):
    if not public_ip or GEO_LOOKUP == "none":
        return {}

    # Simple, no-key lookup. If you prefer ipinfo (rate limits differ), swap here.
    try:
        r = requests.get(
            f"http://ip-api.com/json/{public_ip}?fields=status,country,regionName,city,query",
            timeout=3,
        )
        r.raise_for_status()
        j = r.json()
        if j.get("status") != "success":
            return {}
        return {
            "country": j.get("country"),
            "region": j.get("regionName"),
            "city": j.get("city"),
        }
    except Exception:
        return {}


def get_status():
    now = time.time()
    if _cache["data"] and (now - _cache["ts"] < CACHE_SECONDS):
        return _cache["data"]

    data = {
        "vpn": {"status": "unknown"},
        "public_ip": None,
        "location": {},
        "port_forward": None,
        "errors": [],
    }

    # VPN status
    try:
        vpn = _get_json("/v1/vpn/status")
        data["vpn"] = vpn  # expected {"status":"running"} etc.
    except Exception as e:
        data["errors"].append(f"vpn/status: {e}")

    # Public IP (some Gluetun builds return only public_ip; others may include geo fields)
    try:
        pip_data = _get_json("/v1/publicip/ip")
        # documented example: {"public_ip":"x.x.x.x"}
        data["public_ip"] = pip_data.get("public_ip") or pip_data.get("public_ip_address") or ""
        # if your build returns more keys (country/region/city), capture them:
        for k in ("country", "region", "city"):
            if k in pip_data and pip_data.get(k):
                data["location"][k] = pip_data.get(k)
    except Exception as e:
        data["errors"].append(f"publicip/ip: {e}")

    # Port forward
    try:
        pf = _get_json("/v1/portforward")  # returns {"port": 5914}
        data["port_forward"] = pf.get("port")
    except Exception as e:
        data["errors"].append(f"portforward: {e}")

    # Geo fallback if Gluetun didn't provide it
    if not data["location"] and data["public_ip"]:
        data["location"] = _geo_lookup(data["public_ip"])

    _cache["ts"] = now
    _cache["data"] = data
    return data


def is_connected(d):
    return (d.get("vpn", {}).get("status") == "running") and bool(d.get("public_ip"))


@app.get("/api/status")
def api_status():
    return jsonify(get_status())


@app.get("/healthz")
def healthz():
    d = get_status()
    if is_connected(d):
        return jsonify({"ok": True, "vpn": d["vpn"], "public_ip": d["public_ip"]}), 200
    return jsonify(
        {"ok": False, "vpn": d["vpn"], "public_ip": d["public_ip"], "errors": d["errors"]}
    ), 503

@app.get("/")
def index():
    d = get_status()
    ok = is_connected(d)

    loc = d.get("location") or {}
    loc_str = " / ".join([x for x in [loc.get("city"), loc.get("region"), loc.get("country")] if x]) or "Unknown"
    pf = d.get("port_forward")
    ip = d.get("public_ip") or "Unknown"
    status = d.get("vpn", {}).get("status", "unknown")

    dot = "#22c55e" if ok else "#ef4444"

    # Inner card styling only (outer container is transparent)
    inset_bg = "rgba(255,255,255,0.035)"
    inset_border = "rgba(255,255,255,0.06)"
    text = "rgba(255,255,255,0.92)"
    muted = "rgba(255,255,255,0.70)"

    html = f"""
<!doctype html>
<html>
  <head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>VPN Status</title>
    <style>
      :root {{
        --inset-bg: {inset_bg};
        --inset-border: {inset_border};
        --text: {text};
        --muted: {muted};
        --dot: {dot};
      }}
      * {{ box-sizing: border-box; }}
      html, body {{
        margin: 0;
        padding: 0;
        background: transparent;
        color: var(--text);
        font-family: system-ui, -apple-system, Segoe UI, Roboto, Ubuntu, Cantarell, "Helvetica Neue", Arial, sans-serif;
        color-scheme: dark;
      }}

      .wrap {{
        width: 100%;
        height: 100%;
        padding: 10px;
        background: transparent;
      }}

      /* No “panel” styling at all—just padding container */
      .panel {{
        width: 100%;
        height: 100%;
        background: transparent;
        border: none;
        border-radius: 0;
        padding: 0;
        box-shadow: none;
      }}

      .header {{
        display: flex;
        align-items: center;
        justify-content: space-between;
        gap: 12px;
        margin-bottom: 12px;
      }}

      .title {{
        display: flex;
        align-items: center;
        gap: 10px;
        min-width: 0;
      }}

      .dot {{
        width: 11px;
        height: 11px;
        border-radius: 999px;
        background: var(--dot);
        box-shadow: 0 0 0 5px rgba(34,197,94,0.10);
        flex: 0 0 auto;
      }}

      .state {{
        font-weight: 750;
        font-size: 16px;
        letter-spacing: 0.2px;
        white-space: nowrap;
      }}

      .pill {{
        font-size: 12px;
        color: var(--muted);
        padding: 4px 10px;
        border: 1px solid rgba(255,255,255,0.08);
        border-radius: 999px;
        white-space: nowrap;
        flex: 0 0 auto;
      }}

      .grid {{
        display: grid;
        grid-template-columns: 1fr 1fr;
        gap: 10px;
      }}

      .card {{
        padding: 10px 12px;
        border-radius: 12px;
        background: var(--inset-bg);
        border: 1px solid var(--inset-border);
        min-width: 0;
      }}

      .k {{
        color: var(--muted);
        font-size: 12px;
        margin-bottom: 6px;
      }}

      .v {{
        font-size: 15px;
        font-weight: 700;
        line-height: 1.2;
        overflow: hidden;
        text-overflow: ellipsis;
        white-space: nowrap;
      }}

      .location {{
        grid-column: span 2;
      }}

      .location .v {{
        white-space: normal;
        overflow-wrap: anywhere;
        display: -webkit-box;
        -webkit-line-clamp: 3;
        -webkit-box-orient: vertical;
        overflow: hidden;
      }}

      .meta {{
        margin-top: 10px;
        color: var(--muted);
        font-size: 12px;
        display: flex;
        justify-content: space-between;
        gap: 10px;
      }}

      .err {{
        margin-top: 12px;
        font-size: 12px;
        color: rgba(239,68,68,0.92);
        background: rgba(239,68,68,0.08);
        border: 1px solid rgba(239,68,68,0.18);
        border-radius: 12px;
        padding: 10px 12px;
        white-space: pre-wrap;
        overflow: hidden;
        max-height: 140px;
      }}
    </style>
  </head>

  <body>
    <div class="wrap">
      <div class="panel">
        <div class="header">
          <div class="title">
            <div class="dot"></div>
            <div class="state">VPN: {status}</div>
          </div>
          <div class="pill">{'Connected' if ok else 'Disconnected'}</div>
        </div>

        <div class="grid">
          <div class="card">
            <div class="k">Public IP</div>
            <div class="v">{ip}</div>
          </div>

          <div class="card">
            <div class="k">Port Forward</div>
            <div class="v">{pf if pf else 'None/Unknown'}</div>
          </div>

          <div class="card location">
            <div class="k">Location</div>
            <div class="v">{loc_str}</div>
          </div>
        </div>

        <div class="meta">
          <div>Cache: {CACHE_SECONDS}s</div>
          <div>{'OK' if ok else 'Not connected'}</div>
        </div>

        {("<div class='err'><b>Errors</b>\\n" + "\\n".join(d["errors"]) + "</div>") if d.get("errors") else ""}
      </div>
    </div>
  </body>
</html>
"""
    return Response(html, mimetype="text/html")

if __name__ == "__main__":
    # IMPORTANT: bind to 0.0.0.0 so Traefik/other containers can reach it
    app.run(host="0.0.0.0", port=5000)
