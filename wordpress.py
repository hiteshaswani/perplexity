"""
WordPress publishing helper.
Posts AI search results to WordPress via REST API.
"""

import base64
import html
import os
from requests.auth import HTTPBasicAuth
import requests


def _get_wp_config() -> tuple[str, str, str]:
    site_url = os.getenv("WP_SITE_URL", "").strip().rstrip("/")
    username = os.getenv("WP_USERNAME", "").strip()
    app_password = os.getenv("WP_APP_PASSWORD", "").strip()

    if not site_url or not username or not app_password:
        raise ValueError("WordPress configuration missing. Set WP_SITE_URL, WP_USERNAME, WP_APP_PASSWORD")

    return site_url, username, app_password


def _build_post_content(answer: str, sources: list[dict], image_url: str | None = None) -> str:
    escaped_answer = html.escape(answer or "").replace("\n", "<br>")

    html_parts = []

    if image_url:
        html_parts.append(
            f'<figure><img src="{html.escape(image_url, quote=True)}" '
            f'alt="AI generated illustration" style="max-width:100%;height:auto;" /></figure>'
        )

    html_parts += [
        f"<p>{escaped_answer}</p>",
    ]

    if sources:
        html_parts.append("<h3>Sources</h3>")
        html_parts.append("<ul>")
        for source in sources:
            title = html.escape(source.get("title") or "Untitled")
            url = (source.get("url") or "").strip()
            if not url:
                continue
            safe_url = html.escape(url, quote=True)
            html_parts.append(
                f'<li><a href="{safe_url}" target="_blank" rel="noopener noreferrer">{title}</a></li>'
            )
        html_parts.append("</ul>")

    return "\n".join(html_parts)


def upload_image(image_data_url: str, title: str) -> dict:
    """
    Upload a base64 data-URL image to the WordPress media library.
    Returns dict with 'media_id' and 'source_url'.
    """
    site_url, username, app_password = _get_wp_config()

    header, encoded = image_data_url.split(",", 1)
    mime_type = header.split(":")[1].split(";")[0]       # e.g. image/jpeg
    ext = mime_type.split("/")[1].replace("jpeg", "jpg") # jpg / png / webp

    image_bytes = base64.b64decode(encoded)
    safe_name = "".join(c if c.isalnum() or c in "-_" else "-" for c in title[:60]).strip("-")
    filename = f"{safe_name or 'image'}.{ext}"

    print(f"  📤 Uploading image to WordPress media library ({len(image_bytes):,} bytes)...")

    response = requests.post(
        f"{site_url}/wp-json/wp/v2/media",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
            "Content-Type": mime_type,
        },
        data=image_bytes,
        auth=HTTPBasicAuth(username, app_password),
        timeout=60,
    )

    if response.status_code >= 400:
        raise RuntimeError(f"Media upload failed ({response.status_code}): {response.text[:300]}")

    data = response.json()
    media_id = data["id"]
    source_url = data.get("source_url", "")
    print(f"  ✅ Image uploaded (media ID: {media_id})")
    return {"media_id": media_id, "source_url": source_url}


def publish_search_result(
    query: str,
    answer: str,
    sources: list[dict],
    status: str = "draft",
    media_id: int | None = None,
    image_url: str | None = None,
) -> dict:
    site_url, username, app_password = _get_wp_config()

    title = (query or "AI Research Result").strip() or "AI Research Result"
    content = _build_post_content(answer, sources, image_url)

    payload: dict = {
        "title": title,
        "content": content,
        "status": status,
    }

    if media_id:
        payload["featured_media"] = media_id

    response = requests.post(
        f"{site_url}/wp-json/wp/v2/posts",
        json=payload,
        auth=HTTPBasicAuth(username, app_password),
        timeout=30,
    )

    if response.status_code >= 400:
        raise RuntimeError(f"WordPress publish failed ({response.status_code}): {response.text[:500]}")

    data = response.json()
    return {
        "id": data.get("id"),
        "status": data.get("status"),
        "link": data.get("link"),
    }
