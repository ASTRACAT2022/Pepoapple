import asyncio
from html import escape
from typing import Any
from urllib.parse import quote

import httpx
from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import HTMLResponse, JSONResponse
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    panel_api_base_url: str = "http://localhost:8080"
    page_title: str = "Pepoapple Subscription"
    support_url: str = "https://t.me/"
    show_raw_links: bool = True
    custom_sub_prefix: str = ""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


settings = Settings()
app = FastAPI(title="Pepoapple Subscription Page")
custom_prefix = settings.custom_sub_prefix.strip("/")


def client_links(identifier: str) -> dict[str, str]:
    sub = f"{settings.panel_api_base_url.rstrip('/')}/api/v1/subscriptions/{identifier}"
    encoded = quote(sub, safe="")
    return {
        "Subscription URL": sub,
        "Sing-box": f"sing-box://import-remote-profile?url={encoded}#Pepoapple",
        "Hiddify": f"hiddify://import/{sub}",
        "v2rayN": f"v2rayn://install-sub?url={encoded}",
        "v2rayNG": f"v2rayng://install-config?url={encoded}",
        "Clash": f"clash://install-config?url={encoded}",
        "Streisand": f"streisand://import/{sub}",
        "Shadowrocket": f"shadowrocket://add/sub://{encoded}",
    }


async def load_subscription(identifier: str) -> dict[str, Any]:
    url = f"{settings.panel_api_base_url.rstrip('/')}/api/v1/subscriptions/{identifier}"
    async with httpx.AsyncClient(timeout=8) as client:
        try:
            resp = await client.get(url)
        except httpx.HTTPError as exc:
            raise HTTPException(status_code=502, detail=f"upstream_unreachable: {exc}") from exc

    if resp.status_code == 404:
        raise HTTPException(status_code=404, detail="subscription_not_found")
    if resp.status_code >= 400:
        raise HTTPException(status_code=502, detail=f"upstream_error_{resp.status_code}")

    return resp.json()


async def load_links(identifier: str) -> dict[str, str]:
    url = f"{settings.panel_api_base_url.rstrip('/')}/api/v1/subscriptions/{identifier}/links"
    async with httpx.AsyncClient(timeout=8) as client:
        try:
            resp = await client.get(url)
            if resp.status_code < 400 and isinstance(resp.json(), dict):
                return {str(k): str(v) for k, v in resp.json().items()}
        except httpx.HTTPError:
            pass
    return client_links(identifier)


def render_page(identifier: str, payload: dict[str, Any], links: dict[str, str]) -> str:
    endpoints = payload.get("endpoints", [])

    links_html = "".join(
        f'<a class="btn" href="{escape(url)}" target="_blank" rel="noopener noreferrer">{escape(name)}</a>'
        for name, url in links.items()
    )

    endpoint_cards = []
    for endpoint in endpoints:
        uris = endpoint.get("uris", {})
        uri_html = ""
        if settings.show_raw_links and uris:
            rows = "".join(
                f"<div><b>{escape(proto)}</b><code>{escape(uri)}</code></div>" for proto, uri in uris.items()
            )
            uri_html = f'<div class="raw">{rows}</div>'

        endpoint_cards.append(
            "".join(
                [
                    '<div class="card">',
                    f"<h3>{escape(endpoint.get('host', '-'))}</h3>",
                    f"<p>{escape(endpoint.get('region', '-'))} · {escape(endpoint.get('provider', '-'))}</p>",
                    f"<p>Protocols: {escape(', '.join(endpoint.get('protocols', [])))}</p>",
                    uri_html,
                    "</div>",
                ]
            )
        )

    endpoints_html = "".join(endpoint_cards) if endpoint_cards else '<p class="muted">No endpoints assigned.</p>'
    subscription_url = links.get("subscription_url") or links.get("Subscription URL") or ""

    return f"""
<!doctype html>
<html>
<head>
  <meta charset=\"utf-8\" />
  <meta name=\"viewport\" content=\"width=device-width,initial-scale=1\" />
  <title>{escape(settings.page_title)}</title>
  <style>
    body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; background: #0f1318; color: #f4f7fb; margin: 0; }}
    .wrap {{ max-width: 980px; margin: 0 auto; padding: 24px; }}
    .hero {{ border: 1px solid #2a3441; border-radius: 16px; padding: 20px; background: linear-gradient(130deg,#1a2029,#131922); }}
    .muted {{ color: #9fb0c4; }}
    .links {{ display: grid; grid-template-columns: repeat(auto-fill,minmax(160px,1fr)); gap: 10px; margin-top: 14px; }}
    .btn {{ display:block; text-decoration:none; color:#f4f7fb; padding:10px 12px; border-radius:10px; background:#273242; border:1px solid #3a4960; text-align:center; font-size: 14px; }}
    .btn:hover {{ background:#34445d; }}
    .token {{ margin-top:12px; background:#111820; border:1px solid #293444; border-radius:10px; padding:10px; font-family: ui-monospace, SFMono-Regular, Menlo, monospace; font-size:12px; overflow:auto; }}
    .grid {{ margin-top: 18px; display:grid; grid-template-columns: repeat(auto-fill,minmax(260px,1fr)); gap: 12px; }}
    .card {{ border:1px solid #2b3645; border-radius: 12px; padding:12px; background:#141c26; }}
    h1, h2, h3 {{ margin:0 0 8px 0; }}
    p {{ margin: 0 0 7px 0; }}
    code {{ display:block; margin-top:4px; font-size:11px; background:#0e141c; border:1px solid #273347; border-radius:6px; padding:6px; word-break:break-all; }}
    .raw {{ margin-top:8px; }}
    .foot {{ margin-top: 18px; font-size: 13px; color:#9fb0c4; }}
    .foot a {{ color:#9fd8ff; }}
  </style>
</head>
<body>
  <div class=\"wrap\">
    <section class=\"hero\">
      <h1>{escape(settings.page_title)}</h1>
      <p class=\"muted\">User UUID: {escape(str(payload.get('user_uuid', '-')))}</p>
      <p class=\"muted\">Short ID: {escape(str(payload.get('short_id', '-')))}</p>
      <div class=\"links\">{links_html}</div>
      <div class=\"token\" id=\"sub-url\">{escape(subscription_url or '-')}</div>
    </section>

    <section>
      <h2 style=\"margin-top:18px\">Endpoints</h2>
      <div class=\"grid\">{endpoints_html}</div>
    </section>

    <p class=\"foot\">Need help: <a href=\"{escape(settings.support_url)}\" target=\"_blank\" rel=\"noopener noreferrer\">{escape(settings.support_url)}</a></p>
  </div>
</body>
</html>
"""


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}


@app.get("/api/raw/{identifier}")
async def raw(identifier: str) -> JSONResponse:
    payload = await load_subscription(identifier)
    return JSONResponse(payload)


@app.get("/{identifier}", response_class=HTMLResponse)
async def page(identifier: str, raw: bool = Query(default=False)):
    payload, links = await asyncio.gather(load_subscription(identifier), load_links(identifier))
    if raw:
        return JSONResponse(payload)
    return HTMLResponse(render_page(identifier, payload, links))


if custom_prefix:
    @app.get(f"/{custom_prefix}/api/raw" + "/{identifier}")
    async def raw_with_prefix(identifier: str) -> JSONResponse:
        payload = await load_subscription(identifier)
        return JSONResponse(payload)

    @app.get(f"/{custom_prefix}" + "/{identifier}", response_class=HTMLResponse)
    async def page_with_prefix(identifier: str, raw: bool = Query(default=False)):
        payload, links = await asyncio.gather(load_subscription(identifier), load_links(identifier))
        if raw:
            return JSONResponse(payload)
        return HTMLResponse(render_page(identifier, payload, links))
