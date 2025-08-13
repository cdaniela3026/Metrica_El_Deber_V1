from fastapi import APIRouter, HTTPException
import os, requests, hmac, hashlib
from typing import Optional

router = APIRouter(prefix="/facebook", tags=["facebook"])

GRAPH_VERSION = os.getenv("FB_GRAPH_VERSION", "v19.0")
ACCESS_TOKEN = os.getenv("FACEBOOK_ACCESS_TOKEN")  # requerido
PAGE_ID = os.getenv("FACEBOOK_PAGE_ID")            # requerido
APP_SECRET = os.getenv("FACEBOOK_APP_SECRET")      # opcional

def _appsecret_proof(token: str, app_secret: Optional[str]) -> Optional[str]:
    if not app_secret:
        return None
    return hmac.new(app_secret.encode("utf-8"), msg=token.encode("utf-8"), digestmod=hashlib.sha256).hexdigest()

def _fb_get(path: str, params: dict, timeout: int = 15):
    if not ACCESS_TOKEN or not PAGE_ID:
        raise HTTPException(status_code=500, detail="Config faltante: FACEBOOK_ACCESS_TOKEN o FACEBOOK_PAGE_ID no definida.")
    params = dict(params or {})
    params["access_token"] = ACCESS_TOKEN
    proof = _appsecret_proof(ACCESS_TOKEN, APP_SECRET)
    if proof:
        params["appsecret_proof"] = proof
    url = f"https://graph.facebook.com/{GRAPH_VERSION}/{path.lstrip('/')}"
    try:
        res = requests.get(url, params=params, timeout=timeout)
    except requests.RequestException as e:
        raise HTTPException(status_code=502, detail=f"Error de red al llamar Graph API: {e}")
    if res.status_code != 200:
        try:
            err = res.json()
        except Exception:
            err = res.text
        raise HTTPException(status_code=res.status_code, detail={"graph_error": err, "endpoint": url})
    return res.json()

@router.get("/live-video")
def live_video():
    """Retorna el LIVE actual de la página y métricas básicas del post."""
    videos_json = _fb_get(f"{PAGE_ID}/videos", params={"fields": "id,title,live_status,permalink_url,created_time", "limit": 25})
    videos = videos_json.get("data", []) or []
    live = next((v for v in videos if v.get("live_status") == "LIVE"), None)
    if not live:
        return {"live": False, "message": "No hay transmisión en vivo."}

    video_id = live["id"]
    detail = _fb_get(f"{video_id}", params={"fields": "id,post_id,permalink_url,created_time,from,title,live_status"})
    post_id = detail.get("post_id") or detail.get("id")

    if not post_id:
        return {
            "live": True,
            "video_id": video_id,
            "post_id": None,
            "title": live.get("title") or detail.get("title") or "Sin título",
            "permalink_url": live.get("permalink_url") or detail.get("permalink_url"),
            "created_time": live.get("created_time") or detail.get("created_time"),
            "likes": None,
            "shares": None,
            "note": "No se encontró post asociado para extraer métricas.",
        }

    metrics = _fb_get(f"{post_id}", params={"fields": "reactions.summary(true),shares"})
    likes = (metrics.get("reactions") or {}).get("summary", {}).get("total_count", 0)
    shares = (metrics.get("shares") or {}).get("count", 0)

    return {
        "live": True,
        "video_id": video_id,
        "post_id": post_id,
        "title": live.get("title") or detail.get("title") or "Sin título",
        "permalink_url": detail.get("permalink_url"),
        "created_time": detail.get("created_time"),
        "likes": likes,
        "shares": shares,
    }

@router.get("/page-posts")
def page_posts(limit: int = 10):
    """Lista últimos posts con reacciones/compartidos para tarjetas/tablas."""
    feed = _fb_get(f"{PAGE_ID}/posts", params={"fields": "id,permalink_url,created_time,message", "limit": max(1, min(limit, 50))})
    items = []
    for p in feed.get("data", []):
        pid = p.get("id")
        if not pid:
            continue
        m = _fb_get(f"{pid}", params={"fields": "reactions.summary(true),shares"})
        likes = (m.get("reactions") or {}).get("summary", {}).get("total_count", 0)
        shares = (m.get("shares") or {}).get("count", 0)
        items.append({
            "post_id": pid,
            "permalink_url": p.get("permalink_url"),
            "created_time": p.get("created_time"),
            "message": p.get("message"),
            "likes": likes,
            "shares": shares,
        })
    return {"count": len(items), "items": items}
