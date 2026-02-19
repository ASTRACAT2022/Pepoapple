from html import escape

from fastapi import APIRouter, Depends
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.core.config import get_settings
from app.services.subscription import build_subscription_payload, resolve_user_by_subscription_identifier, subscription_links

router = APIRouter(tags=["subscription"])
settings = get_settings()


@router.get("/subscriptions/{identifier}")
def subscription(identifier: str, db: Session = Depends(get_db)) -> dict:
    user = resolve_user_by_subscription_identifier(db, identifier)
    return build_subscription_payload(db, user)


@router.get("/subscriptions/{identifier}/links")
def subscription_client_links(identifier: str) -> dict:
    return subscription_links(settings.public_api_base_url, identifier)


@router.get("/sub/{identifier}", response_class=HTMLResponse)
def subscription_page(identifier: str, db: Session = Depends(get_db)) -> HTMLResponse:
    user = resolve_user_by_subscription_identifier(db, identifier)
    payload = build_subscription_payload(db, user)
    links = subscription_links(settings.public_api_base_url, identifier)

    links_html = "".join(
        f'<a style="display:block;padding:9px 10px;background:#263143;color:#f4f6fb;text-decoration:none;border-radius:8px;" href="{escape(url)}">{escape(name)}</a>'
        for name, url in links.items()
    )
    endpoints_html = "".join(
        f'<li style="margin-bottom:8px;"><b>{escape(item.get("host", "-"))}</b> · {escape(item.get("region", "-"))} · {escape(item.get("provider", "-"))}</li>'
        for item in payload.get("endpoints", [])
    ) or "<li>No endpoints</li>"

    html = f"""
<!doctype html>
<html>
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>Pepoapple Subscription</title>
</head>
<body style="margin:0;background:#0f141b;color:#f0f4fb;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;">
  <div style="max-width:900px;margin:0 auto;padding:20px;">
    <div style="border:1px solid #2d3748;border-radius:14px;padding:18px;background:#161e28;">
      <h1 style="margin:0 0 10px 0;">Pepoapple Subscription</h1>
      <p style="margin:0 0 4px 0;color:#a9b6c9;">User UUID: {escape(payload.get("user_uuid", "-"))}</p>
      <p style="margin:0 0 12px 0;color:#a9b6c9;">Short ID: {escape(payload.get("short_id", "-"))}</p>
      <div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(180px,1fr));gap:8px;">{links_html}</div>
    </div>
    <div style="border:1px solid #2d3748;border-radius:14px;padding:18px;background:#161e28;margin-top:12px;">
      <h2 style="margin:0 0 10px 0;">Endpoints</h2>
      <ul style="margin:0;padding-left:18px;">{endpoints_html}</ul>
    </div>
  </div>
</body>
</html>
"""
    return HTMLResponse(html)
