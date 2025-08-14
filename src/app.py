## PROYECTO ANALISIS DE METRICAS REDES SOCIALES EL DEBER
## VERSION 1
## FECHA: 09/08/2025
## RESPONSABLE FRONT: CARLA DANIELA SORUCO MAERTENS
#=====================================================================================
# src/app.py — YouTube + TikTok + Facebook
# -> 3 gráficas por pestaña: línea (tiempo real), barras (snapshot) y donut (snapshot)
# -> TikTok y Youtube limpio si no hay usuario consultado
# =====================================================================================


import os
import base64
import datetime as dt
import requests
from requests.adapters import HTTPAdapter, Retry
from dotenv import load_dotenv
import streamlit as st
import re
from streamlit_autorefresh import st_autorefresh
import plotly.express as px
import pandas as pd
import datetime as dt
from pathlib import Path

_YT_ID_RE = re.compile(r"""
    (?:https?://)?
    (?:www\.)?
    (?:
        youtu\.be/(?P<id1>[A-Za-z0-9_-]{11})
        |
        youtube\.com/
            (?:
                (?:watch\?.*?v=|live/|embed/|shorts/)
                (?P<id2>[A-Za-z0-9_-]{11})
            )
    )
""", re.VERBOSE)

def yt_normalize_id(text: str) -> str:
    if not text:
        return ""
    text = text.strip()
    if re.fullmatch(r"[A-Za-z0-9_-]{11}", text):
        return text
    m = _YT_ID_RE.search(text)
    if m:
        return m.group("id1") or m.group("id2") or ""
    if "v=" in text:
        from urllib.parse import urlparse, parse_qs
        qs = parse_qs(urlparse(text).query)
        vid = qs.get("v", [""])[0]
        if re.fullmatch(r"[A-Za-z0-9_-]{11}", vid):
            return vid
    return text
from streamlit_autorefresh import st_autorefresh

import pandas as pd
import plotly.express as px
from pathlib import Path

# =========================
# Configuración & Helpers
# =========================
load_dotenv()

LOCAL_API = os.getenv("LOCAL_API_BASE", "http://127.0.0.1:8001").rstrip("/")
DEFAULT_VIDEO_ID = os.getenv("VIDEO_ID", "").strip()

PLATFORM_COLORS = {
    "YouTube": "#FF0000",
    "TikTok":  "#000000",
    #"Instagram": "#FF4F86",
    "X": "#657786",
    "Facebook": "#1877F2",
}

def http_session() -> requests.Session:
    s = requests.Session()
    retries = Retry(
        total=3,
        backoff_factor=0.4,
        status_forcelist=[429, 500, 502, 503, 504],
        allowed_methods=["GET", "POST"],
    )
    s.mount("http://", HTTPAdapter(max_retries=retries))
    s.mount("https://", HTTPAdapter(max_retries=retries))
    return s

SESSION = http_session()
TIMEOUT = 15

def api_get(path: str, params=None):
    url = f"{LOCAL_API}{path}"
    r = SESSION.get(url, params=params, timeout=TIMEOUT)
    r.raise_for_status()
    return r.json()

def api_get_debug(path: str, params=None):
    """
    Returns (ok, data_or_text, status_code). ok=True if 2xx and JSON parsed,
    otherwise False with text/JSON.
    """
    url = f"{LOCAL_API}{path}"
    try:
        r = SESSION.get(url, params=params, timeout=TIMEOUT)
        status = r.status_code
        try:
            data = r.json()
        except Exception:
            data = r.text
        ok = 200 <= status < 300
        return ok, data, status
    except Exception as e:
        return False, str(e), None


# =========================
# UI - Streamlit
# =========================
st.set_page_config(page_title="EL DEBER — ANÁLISIS DE TRANSMISIÓN EN VIVO", layout="wide")

# Encabezado con logo de EL DEBER
st.set_page_config(page_title="EL DEBER — ANÁLISIS DE TRANSMISIÓN EN VIVO", layout="wide")

import os, base64
from pathlib import Path

ASSETS_DIR = Path(__file__).resolve().parent / "assets"
ELDEBER_LOGO_PATH = os.getenv("ELDEBER_LOGO_PATH", str(ASSETS_DIR / "logo_el_deber.png"))
LIVE_BADGE_PATH   = os.getenv("LIVE_BADGE_PATH",   str(ASSETS_DIR / "logo_en_vivo.png"))

def _img_src(path: str) -> str:
    try:
        p = Path(path)
        if not p.exists():
            return ""
        b64 = base64.b64encode(p.read_bytes()).decode("utf-8")
        ext = "png"
        n = p.name.lower()
        if n.endswith((".jpg", ".jpeg")): ext = "jpeg"
        elif n.endswith(".webp"):         ext = "webp"
        return f"data:image/{ext};base64,{b64}"
    except Exception:
        return ""

el_deber_src = _img_src(ELDEBER_LOGO_PATH)
live_src     = _img_src(LIVE_BADGE_PATH)

# Arriba: solo logo EL DEBER 
top_line = (
    f'<img src="{el_deber_src}" alt="EL DEBER" style="height:120px;display:block;margin-bottom:60px;">'
    if el_deber_src
    else '<span style="font-weight:800;color:#0a6e3a;font-family:system-ui,Segoe UI,Arial;margin-bottom:12px;display:inline-block;">EL DEBER</span>'
)

# Abajo: primero el badge EN VIVO y luego el título
bottom_line = f"""
  <img src="{live_src}" alt="En vivo" style="height:60px;display:block;"> 
  <span style="font-size:2.5rem;font-weight:800;letter-spacing:.3px;">
    ANÁLISIS DE TRANSMISIÓN EN VIVO
  </span>
""" if live_src else """
  <span style="font-size:1.2rem;font-weight:800;letter-spacing:.3px;">
    ANÁLISIS DE TRANSMISIÓN EN VIVO
  </span>
"""

st.markdown(
    f"""
    <div style="display:flex;flex-direction:column;gap:.35rem;">
      <div style="display:flex;align-items:center;">{top_line}</div>
      <div style="display:flex;align-items:center;gap:.35rem;">{bottom_line}</div>
    </div>
    """,
    unsafe_allow_html=True,
)

st.divider()




# =========================
# Resumen comparativo en vivo (arriba de las tabs)
# =========================
import time

PLATFORM_COLOR_MAP = {
    "YouTube": "#FF0000",
    "TikTok":  "#000000",
    #"Instagram": "#FF4F86",
    "X": "#657786",
    "Facebook": "#1877F2",
}

# Cache suave en sesión para no golpear tanto la API
st.session_state.setdefault("_live_cache", {})  # {key: (ts, data)}
def _get_cached(key, ttl=30):
    it = st.session_state["_live_cache"].get(key)
    if not it: return None
    ts, data = it
    return data if (time.time() - ts) < ttl else None

def _set_cached(key, data):
    st.session_state["_live_cache"][key] = (time.time(), data)

def fetch_youtube_concurrent(video_q: str) -> dict:
    """Devuelve {'value': int, 'status': 'ok'|'warn', 'note': str}"""
    vid = yt_normalize_id(video_q or os.getenv("VIDEO_ID", "")) if 'yt_normalize_id' in globals() else (video_q or os.getenv("VIDEO_ID", ""))
    if not vid:
        return {"value": 0, "status": "warn", "note": "Sin VIDEO_ID"}
    cache = _get_cached(f"yt:{vid}", ttl=30)
    if cache: return cache
    try:
        if 'api_get_debug' in globals():
            ok, data, status = api_get_debug("/live-data", params={"video": vid})
        else:
            data = api_get("/live-data", params={"video": vid}); ok=True; status=200
        items = (data.get("items") if isinstance(data, dict) else []) if ok else []
        if not ok:
            out = {"value": 0, "status":"warn", "note": f"YT {status}"}
        elif not items:
            out = {"value": 0, "status":"warn", "note": "Sin datos (¿no está LIVE?)"}
        else:
            node = items[0] or {}
            live = node.get("liveStreamingDetails", {}) or {}
            stats = node.get("statistics", {}) or {}
            concurrent = int(live.get("concurrentViewers") or stats.get("concurrentViewers") or 0)
            out = {"value": concurrent, "status":"ok", "note": ""}
    except Exception as e:
        out = {"value": 0, "status":"warn", "note": f"YT err: {e}"}
    _set_cached(f"yt:{vid}", out)
    return out


def _tt_pick_item(items, req_user:str):
    """Devuelve el item cuya statistics.username coincide con req_user (sin @, case-insensitive).
    Si no hay coincidencia, retorna el primero disponible.
    """
    try:
        ru = (req_user or "").strip().lstrip("@").lower()
        for it in items or []:
            s = (it.get("statistics") or {}) if isinstance(it, dict) else {}
            un = (s.get("username") or s.get("user") or "").strip().lstrip("@").lower()
            if ru and un and (ru == un):
                return it
        return (items or [None])[0]
    except Exception:
        return (items or [None])[0]
def fetch_tiktok_viewers(user_q: str) -> dict:

    """Devuelve {'value': int, 'status': 'ok'|'warn', 'note': str}"""
    user = (user_q or st.session_state.get("tt_user") or os.getenv("TIKTOK_USER","")).strip().lstrip("@")
    if not user:
        return {"value": 0, "status":"warn", "note":"Sin usuario TikTok configurado"}
    cache = _get_cached(f"tt:{user}", ttl=10)
    if cache: return cache
    try:
        import time
        data = api_get("/tiktok-stats", params={"user": user, "username": user, "_": int(time.time())})
        items = data.get("items", []) if isinstance(data, dict) else []
        # Elegir el item que coincide exactamente con el username solicitado
        if items:
            picked = None
            ru = user.strip().lstrip("@").lower()
            for it in items:
                s0 = (it.get("statistics") or {}) if isinstance(it, dict) else {}
                un = (s0.get("username") or s0.get("user") or "").strip().lstrip("@").lower()
                if ru and un and ru == un:
                    picked = it; break
            items = [picked] if picked is not None else []
        if not items:
            out = {"value": 0, "status":"warn", "note":"TT sin datos"}
        else:
            s = items[0].get("statistics", {}) or {}
            val = int(s.get("viewers") or s.get("likes") or 0)
            out = {"value": val, "status":"ok", "note": ""}
    except Exception as e:
        out = {"value": 0, "status":"warn", "note": f"TT err: {e}"}
    _set_cached(f"tt:{user}", out)
    return out


def fetch_facebook_metric() -> dict:
    """
    Devuelve {'value': int, 'status': 'ok'|'warn', 'note': str}
    Usa /facebook/live-video y toma como métrica rápida: likes + shares (proxy de engagement en vivo).
    """
    cache = _get_cached("fb:live", ttl=20)
    if cache: 
        return cache
    try:
        data = api_get("/facebook/live-video")
        if not isinstance(data, dict):
            out = {"value": 0, "status":"warn", "note":"FB sin datos"}
        elif not data.get("live"):
            out = {"value": 0, "status":"warn", "note":"FB no está LIVE"}
        else:
            likes = int(data.get("likes") or 0)
            shares = int(data.get("shares") or 0)
            value = max(likes + shares, 0)
            out = {"value": value, "status":"ok", "note": ""}
    except Exception as e:
         out = {"value": 0, "status":"warn", "note": "No se pudo conectar con Facebook"}
    _set_cached("fb:live", out)
    return out


#st.subheader("📡 Resumen comparativo en vivo")

# Helper logos (KPIs)
ASSETS_DIR = Path(__file__).resolve().parent / "assets"
LOGOS = {
    "YouTube": ASSETS_DIR / "logo_youtube.jpg",
    "TikTok":  ASSETS_DIR / "logo_tiktok.png",
    "Facebook":ASSETS_DIR / "logo_facebook.jpg",
    "X":       ASSETS_DIR / "logo_x.webp",
}
# Helper para logo de metrica
ASSETS_DIR = Path(__file__).resolve().parent / "assets"  # si ya lo tenés, dejalo como está

METRIC_ICON = ASSETS_DIR / "logo_metrica.png"

def title_with_icon(text: str, img_path: Path, size: int = 24):
    import base64
    data = img_path.read_bytes()
    b64 = base64.b64encode(data).decode("utf-8")
    ext = "png"
    name = str(img_path).lower()
    if name.endswith(".jpg") or name.endswith(".jpeg"):
        ext = "jpeg"
    elif name.endswith(".webp"):
        ext = "webp"

    st.markdown(
        f"""
        <div style="display:flex;align-items:center;gap:10px;margin:4px 0 6px;">
          <img src="data:image/{ext};base64,{b64}"
               width="{size}" height="{size}"
               style="display:block;object-fit:contain;"/>
          <span style="font-weight:700;font-size:1.25rem;">{text}</span>
        </div>
        """,
        unsafe_allow_html=True,
    )

def stat_logo(col, img_path, value, size: int = 56):
    """Logo cuadrado (mismo box 56x56) + número grande. Facebook recibe un leve zoom para compensar padding del asset."""
    with col:
        a, b = st.columns([1, 3])
        try:
            import base64
            img_bytes = Path(img_path).read_bytes()
            b64 = base64.b64encode(img_bytes).decode("utf-8")
            name = str(img_path).lower()
            ext = "png"
            if name.endswith(".jpg") or name.endswith(".jpeg"):
                ext = "jpeg"
            elif name.endswith(".webp"):
                ext = "webp"
            # Ajuste de zoom por marca: Facebook suele venir con más padding interno
            scale = 0.9
            if "facebook" in name:
                scale = 1.18  # ~18% más grande dentro del mismo box
            a.markdown(
                f"<div style='width:{size}px;height:{size}px;display:flex;align-items:center;justify-content:center;'>"
                f"<img src='data:image/{ext};base64,{b64}' "
                f"style='width:{size}px;height:{size}px;object-fit:contain;transform:scale({scale});'/>"
                f"</div>",
                unsafe_allow_html=True
            )
        except Exception:
            a.write("")
        # Número grande, alineado verticalmente al centro del logo
        try:
            num = int(value) if value is not None else 0
            b.markdown(f"<div style='font-size:28px;font-weight:800;line-height:{size}px;'>{num:,}</div>", unsafe_allow_html=True)
        except Exception:
            b.markdown(f"<div style='font-size:28px;font-weight:800;line-height:{size}px;'>{value}</div>", unsafe_allow_html=True)

#helpers para logo comparativo
import base64
from pathlib import Path

ASSETS_DIR = Path(__file__).resolve().parent / "assets"
icon_path = ASSETS_DIR / "logo_resumen_comparativo.png"

def _img_src(path: Path) -> str:
    try:
        data = path.read_bytes()
        b64 = base64.b64encode(data).decode("utf-8")
        ext = "png" if path.suffix.lower() == ".png" else "jpeg"
        return f"data:image/{ext};base64,{b64}"
    except Exception:
        return ""

src = _img_src(icon_path)
st.markdown(
    f"""
    <div style="display:flex;align-items:center;gap:.5rem;margin:4px 0 6px;">
      <img src="{src}" width="50" height="50" style="display:block;object-fit:contain;">
      <span style="font-weight:700;font-size:1.8rem;">Resumen Comparativo en Vivo</span>
    </div>
    """,
    unsafe_allow_html=True,
)



c1, c2, c3 = st.columns([1,1,6])
auto_refresh_top = c1.toggle("Auto-actualizar 30s", value=True, key="top_auto_refresh")
interval_top = 30000  # ms
if auto_refresh_top:
    try:
        st_autorefresh(interval=interval_top, key="top_live_auto")
    except Exception:
        pass

dbg_err = None

try:
    yt_video_q = st.session_state.get("yt_q", os.getenv("VIDEO_ID", "")) if 'st' in globals() else os.getenv("VIDEO_ID", "")
    tt_user_q  = st.session_state.get("tt_user", os.getenv("TIKTOK_USER", "")) if 'st' in globals() else os.getenv("TIKTOK_USER", "")

    yt = fetch_youtube_concurrent(yt_video_q) if 'fetch_youtube_concurrent' in globals() else {"value": 0, "status":"warn", "note":"función faltante"}
    tt = fetch_tiktok_viewers(tt_user_q) if 'fetch_tiktok_viewers' in globals() else {"value": 0, "status":"warn", "note":"función faltante"}
    fb = fetch_facebook_metric() if 'fetch_facebook_metric' in globals() else {"value": 0, "status":"warn", "note":"función faltante"}
    
    # Layout: izquierda (donut global agregado después) / derecha (logos + barras)
    left_col, right_col = st.columns([2,3])

    with left_col:
        # Placeholder del donut global (se renderiza al final de la página)
        st.session_state['donut_ph'] = st.empty()

    with right_col:
        # Ajuste fino: AQUI AJUSTAMOS DE IZQUIERDA O DERECHA LA LINEA DONDE ESTAN LOS LOGOS
        try:
            _kpi_offset = float(os.getenv("KPI_OFFSET_FRAC", "0.60"))
        except Exception:
            _kpi_offset = 0.60
        spacer, k1, k2, k3, k4 = st.columns([_kpi_offset, 1, 1, 1, 1])
        stat_logo(k1, LOGOS["YouTube"],  yt.get("value",0))
        stat_logo(k2, LOGOS["TikTok"],   tt.get("value",0))
        stat_logo(k3, LOGOS["Facebook"], fb.get("value",0))
        stat_logo(k4, LOGOS["X"],        0)

        df_live = pd.DataFrame([
            {"platform":"YouTube", "viewers": yt.get("value",0)},
            {"platform":"TikTok",  "viewers": tt.get("value",0)},
            {"platform":"Facebook","viewers": fb.get("value",0)},
            {"platform":"X", "viewers": 0},
        ])
        fig_top = px.bar(
            df_live, x="platform", y="viewers", text="viewers",
            title="Tráfico en vivo por plataforma",
            color="platform",
            color_discrete_map=PLATFORM_COLOR_MAP if 'PLATFORM_COLOR_MAP' in globals() else None,
        )
        fig_top.update_xaxes(categoryorder='array', categoryarray=['YouTube','TikTok','Facebook','X'])
        fig_top.update_traces(textposition="outside", cliponaxis=False)
        _ymax = max(1, int(df_live["viewers"].max() or 0))
        fig_top.update_yaxes(range=[0, _ymax * 1.2])
        fig_top.update_layout(margin=dict(l=10,r=10,t=40,b=20), height=320, showlegend=False, yaxis_title="viewers")
        st.plotly_chart(fig_top, use_container_width=True)

    


    notes = []
    if yt.get("status") != "ok" and yt.get("note"):
        notes.append(f"YouTube: {yt['note']}")
    if tt.get("status") != "ok" and tt.get("note"):
        notes.append(f"TikTok: {tt['note']}")
    if fb.get("status") != "ok" and fb.get("note"):
        notes.append(f"Facebook: {fb['note']}")
    if notes:
        st.caption(" · ".join(notes))

except Exception:
        st.warning("No se pudo renderizar el resumen comparativo en este momento.")

#with st.expander("🔎 Debug resumen (temporal)"):
#    st.write("Error:", repr(dbg_err))
st.divider()
# Health
hc1, _ = st.columns([1, 5])
try:
    _ = api_get("/health")
    hc1.success("API local OK ✅")
except Exception as e:
    hc1.error(f"API local no responde: {e}")

st.divider()

# =========================
# Tabs: YouTube + TikTok + Facebook
# =========================
tab_yt, tab_tt, tab_fb = st.tabs(["YouTube", "TikTok", "Facebook"])

# --------- util gráficos snapshot
def _bar_and_pie_from_last(df_long, title_prefix, color_map):
    """
    df_long: DataFrame con columnas ['metric','value'] del último snapshot.
    Devuelve (fig_bar, fig_pie)
    """
    fig_bar = px.bar(
        df_long, x="metric", y="value",
        text="value",
        title=f"{title_prefix} — snapshot actual (barras)",
        color="metric",
        color_discrete_map=color_map,
    )
    fig_bar.update_traces(textposition="outside", cliponaxis=False)
    fig_bar.update_layout(margin=dict(l=10, r=10, t=40, b=0), height=320, showlegend=False)

    fig_pie = px.pie(
        df_long,
        names="metric",
        values="value",
        hole=0.55,
        title=f"{title_prefix} — snapshot actual (donut)",
        color="metric",
        color_discrete_map=color_map,
    )
    fig_pie.update_traces(textposition="inside", texttemplate='%{percent:.1%}')
    fig_pie.update_layout(margin=dict(l=10, r=10, t=40, b=0), height=320, legend_title_text="")

    return fig_bar, fig_pie


# -------------------------
# TAB 2 — TikTok
# -------------------------
with tab_tt:
    st.markdown("""
    <style>
    #tt-scope .stButton>button{background:#000000!important;border-color:#000000!important;color:#fff!important}
    </style>
    """, unsafe_allow_html=True)
    st.markdown("<div id='tt-scope'>", unsafe_allow_html=True)
    st.markdown(
    "<span style='font-size:1.8rem; font-weight:800; color:#000000; -webkit-text-stroke: 1px white;'>TIKTOK en vivo</span>",
    unsafe_allow_html=True
)

    if "tt_user" not in st.session_state:
        st.session_state["tt_user"] = ""
    if "tt_run" not in st.session_state:
        st.session_state["tt_run"] = False
    st.session_state.setdefault("tt_hist", [])

    colU, colBtn, colAuto = st.columns([3, 1, 2])
    def _tt_on_change():
        st.session_state["tt_user"] = st.session_state.get("tt_input","").strip().lstrip("@")
        st.session_state["tt_run"] = True
        st.session_state["tt_hist"] = []

    user_input = colU.text_input(
        "Usuario de TikTok (sin @)",
        value=st.session_state["tt_user"],
        placeholder="ej. jorgepadilla_01",
        key="tt_input",
        on_change=_tt_on_change,
    )
    run_tt = colBtn.button("Consultar", key="tt_btn")
    tt_auto = colAuto.toggle("Auto-actualizar cada 30s", value=True, key="tt_auto")

    if run_tt and user_input:
        _tt_on_change()

    tt_user = st.session_state.get("tt_user", "")

    if tt_auto and st.session_state.get("tt_run") and tt_user:
        st_autorefresh(interval=30000, key=f"tt_live_auto:{tt_user}")

    tt_snap = None

    # TikTok limpio si no hay usuario consultado
    if st.session_state.get("tt_run") and tt_user:
        try:
            import time
            data = api_get("/tiktok-stats", params={"user": tt_user, "username": tt_user, "_": int(time.time())})
            st.caption(f"Backend: {LOCAL_API} — /tiktok-stats  user={tt_user}")
            if isinstance(data, dict) and data.get("error"):
                st.error(data["error"])
            else:
                items = data.get("items", []) if isinstance(data, dict) else []
                if not items:
                    st.info("Sin datos disponibles (¿el script Node está corriendo y escribiendo el JSON?).")
                else:
                    # Elegir el item cuyo username coincide con el solicitado
                    picked = None
                    ru = (tt_user or "").strip().lstrip("@").lower()
                    for it in items:
                        s0 = (it.get("statistics") or {}) if isinstance(it, dict) else {}
                        un = (s0.get("username") or s0.get("user") or "").strip().lstrip("@").lower()
                        if ru and un and ru == un:
                            picked = it; break
                    if picked is None:
                        st.warning(f"El backend devolvió otro usuario. Solicité @{tt_user}. Verifica el capturador.")
                    else:
                        s = picked.get("statistics", {}) or {}
                        username   = s.get("username", tt_user)
                        likes      = int(s.get("likes", 0))
                        comments   = int(s.get("comments", 0))
                        viewers    = int(s.get("viewers", 0))
                        diamonds   = int(s.get("diamonds", 0))
                        shares     = int(s.get("shares", 0))
                        gifts_cnt  = int(s.get("giftsCount", 0))
                        if username:
                            st.caption(f"Streamer: @{username}")
                        d1, d2, d3, d4, d5, d6 = st.columns(6)
                        d1.metric("❤️ Me gusta", f"{likes}")
                        d2.metric("💬 Comentarios", f"{comments}")
                        d3.metric("👀 Espectadores", f"{viewers}")
                        d4.metric("💎 Diamantes", f"{diamonds}")
                        d5.metric("🔁 Acciones", f"{shares}")
                        d6.metric("🎁 Regalos", f"{gifts_cnt}")
                        st.caption(f"Última actualización: {dt.datetime.now():%H:%M:%S}")
                        tt_snap = {
                            "ts": pd.Timestamp.utcnow(),
                            "viewers": viewers,
                            "likes": likes,
                            "comments": comments,
                            "diamonds": diamonds,
                        }


        except requests.HTTPError as http_err:
            try:
                j = http_err.response.json()
                st.error(f"Error de API ({http_err.response.status_code}): {j}")
            except Exception:
                st.error(f"Error de API: {http_err}")
        except Exception as e:
            st.error(f"No se pudo obtener datos: {e}")
    else:
        st.info("Escribe un usuario de TikTok (sin @) y pulsa **Consultar**. "
                "Asegúrate de que tu capturador Node esté corriendo.")

    # --- SERIES + SNAPSHOT (3 gráficas)
    if tt_snap is not None:
        st.session_state["tt_hist"] = (st.session_state["tt_hist"] + [tt_snap])[-200:]

    if st.session_state["tt_hist"]:
        df_t = pd.DataFrame(st.session_state["tt_hist"])

        # 1) LÍNEAS con markers (evolución)
        y_cols = [c for c in ["viewers", "likes", "comments", "diamonds"] if c in df_t.columns]
        if y_cols:
            fig_t = px.line(
                df_t, x="ts", y=y_cols,
                title="Evolución en vivo — TikTok",
                color_discrete_map={
                    "viewers": "#000000",
                    "likes": "#3F3D3D",
                    "comments": "#949191",
                    "diamonds": "#D1CDCD",
                },
                markers=True,
            )
            fig_t.update_layout(margin=dict(l=10, r=10, t=40, b=0), height=320, legend_title_text="")
            st.plotly_chart(fig_t, use_container_width=True)

            # DF del último snapshot
            row = df_t.iloc[-1]
            df_t_last = pd.DataFrame({
                "metric": [m for m in y_cols],
                "value":  [int(row.get(m, 0)) for m in y_cols]
            })
            
            st.session_state["agg_tt"] = int(df_t_last["value"].sum())
            color_map_t = {
                "viewers": "#000000",
                "likes": "#3F3D3D",
                "comments": "#949191",
                "diamonds": "#D1CDCD",
            }

            # 2) BARRAS + 3) DONUT
            cb1, cb2 = st.columns(2)
            fig_bar_t, fig_pie_t = _bar_and_pie_from_last(df_t_last, "TikTok", color_map_t)
            fig_bar_t.update_layout(title_text="TikTok — GRAFICO (barras)")
            fig_pie_t.update_layout(title_text="TikTok — GRAFICO (donut)")
            cb1.plotly_chart(fig_bar_t, use_container_width=True)
            cb2.plotly_chart(fig_pie_t, use_container_width=True)



def render_youtube_tab(tab_container, DEFAULT_VIDEO_ID=""):
    with tab_container:
        #st.subheader("YouTube en vivo")
        st.markdown(
    "<span style='font-size:1.8rem; font-weight:900; color:#FF0000;'>YouTube vivo</span>",
    unsafe_allow_html=True
)
        st.markdown("""
        <style>
        #yt-scope .stButton>button{background:#FF0000!important;border-color:#FF0000!important;color:#fff!important}
        </style>
        """, unsafe_allow_html=True)
        st.markdown("<div id='yt-scope'>", unsafe_allow_html=True)
        if "yt_q" not in st.session_state:
            st.session_state["yt_q"] = ""
        if "yt_run" not in st.session_state:
            st.session_state["yt_run"] = False
        st.session_state.setdefault("yt_hist", [])
        q = st.text_input(
            "Pega la URL o ID de un video en vivo (también acepta youtu.be).",
            value=DEFAULT_VIDEO_ID,
            placeholder="https://www.youtube.com/watch?v=VIDEO_ID o VIDEO_ID",
            key="yt_input_v2",
        )
        colA, colB, colC = st.columns([1, 1, 2])
        run_click = colA.button("Consultar", type="primary", key="yt_btn_v2")
        yt_auto   = colB.toggle("Auto-actualizar 30s", value=True, key="yt_auto_v2")
        yt_debug  = colC.toggle("Debug", value=False, key="yt_dbg_v2")
        if run_click and q:
            st.session_state["yt_q"] = q
            st.session_state["yt_run"] = True
            st.session_state["yt_hist"] = []
        raw_query = st.session_state.get("yt_q", "")
        video_id = yt_normalize_id(raw_query)
        st.caption(f"Backend: {LOCAL_API} — Consultando video_id: {video_id or '—'}")
        if yt_auto and st.session_state.get("yt_run") and video_id:
            st_autorefresh(interval=30000, key="yt_live_auto_v2")
        title_with_icon("Métricas en vivo", METRIC_ICON, size=26)
        yt_snap = None
        dbg_raw = None
        if st.session_state.get("yt_run") and video_id:
            try:
                ok, data, status = api_get_debug("/live-data", params={"video": video_id})
                dbg_raw = {"ok": ok, "status": status, "payload": data}
                items = []
                if isinstance(data, dict):
                    if isinstance(data.get("items"), list):
                        items = data.get("items")
                    else:
                        items = [data]
                if not ok:
                    st.error(f"Backend respondió con estado {status}. Revisa el Debug para ver detalles.")
                elif not items:
                    st.warning("No se recibieron datos del live (¿está realmente en vivo? ¿API key válida?).")
                else:
                    node = items[0] or {}
                    stats = (node.get("statistics") or {}) if isinstance(node, dict) else {}
                    live  = (node.get("liveStreamingDetails") or {}) if isinstance(node, dict) else {}
                    view_count   = int(stats.get("viewCount") or node.get("viewCount") or 0)
                    like_count   = int(stats.get("likeCount") or node.get("likeCount") or 0)
                    concurrent   = int(live.get("concurrentViewers") or stats.get("concurrentViewers") or node.get("concurrentViewers") or 0)
                    live_comments = int(node.get("liveCommentCount") or stats.get("liveCommentCount") or 0)
                    if not live_comments:
                        live_comments = int(len(data.get("comentarios", []))) if isinstance(data, dict) else 0
                    c1, c2, c3, c4 = st.columns(4)
                    c1.metric("👀 Vistas", f"{view_count}")
                    c2.metric("👍 Me gusta", f"{like_count}")
                    c3.metric("🟢 Concurrentes", f"{concurrent}")
                    c4.metric("💬 Comentarios (live)", f"{live_comments}")
                    st.caption(f"Última actualización: {dt.datetime.now():%H:%M:%S}")
                    yt_snap = {
                        "ts": pd.Timestamp.utcnow(),
                        "viewers": concurrent or view_count,
                        "likes": like_count,
                        "comments": live_comments,
                    }
            except Exception as e:
                st.error(f"No se pudo obtener datos: {e}")
        else:
            st.info("Pega una URL/ID de un video en vivo y presiona **Consultar**.")
        #if yt_debug and dbg_raw is not None:
        #    with st.expander("🔎 Debug de respuesta de la API"):
        #        st.json(dbg_raw)
        if yt_snap is not None:
            st.session_state["yt_hist"] = (st.session_state["yt_hist"] + [yt_snap])[-200:]
        if st.session_state["yt_hist"]:
            df_y = pd.DataFrame(st.session_state["yt_hist"])
            fig_y = px.line(
                df_y, x="ts", y=["viewers", "likes", "comments"],
                title="Evolución en vivo — YouTube",
                markers=True,
            )
            fig_y.update_layout(margin=dict(l=10, r=10, t=40, b=0), height=320, legend_title_text="")
            fig_y.update_traces(line=dict(color="#FF0000"))
            st.plotly_chart(fig_y, use_container_width=True)
            row = df_y.iloc[-1]
            df_y_last = pd.DataFrame({
                "metric": ["viewers", "likes", "comments"],
                "value":  [int(row.get("viewers", 0)), int(row.get("likes", 0)), int(row.get("comments", 0))]
            })
            
            st.session_state["agg_y"] = int(df_y_last["value"].sum())
            cb1, cb2 = st.columns(2)
            fig_bar = px.bar(df_y_last, x="metric", y="value", text="value", title="YouTube — snapshot (barras)")
            fig_bar.update_traces(textposition="outside", cliponaxis=False, marker_color="#FF0000")
            fig_bar.update_layout(margin=dict(l=10, r=10, t=40, b=0), height=320, showlegend=False)
            cb1.plotly_chart(fig_bar, use_container_width=True)
            fig_pie = px.pie(df_y_last, names="metric", values="value", hole=0.55, title="YouTube — snapshot (donut)")
            fig_pie.update_traces(textposition="inside", texttemplate='%{percent:.1%}', marker=dict(colors=["#fecaca","#f87171","#ef4444"]))
            fig_pie.update_layout(margin=dict(l=10, r=10, t=40, b=0), height=320)
            cb2.plotly_chart(fig_pie, use_container_width=True)
        st.markdown("</div>", unsafe_allow_html=True)



render_youtube_tab(tab_yt, DEFAULT_VIDEO_ID if 'DEFAULT_VIDEO_ID' in globals() else '')
# -------------------------
# TAB 3 — Facebook (NUEVA PESTAÑA)
# -------------------------
st.markdown("</div>", unsafe_allow_html=True)
with tab_fb:
    st.markdown("""
    <style>
    #fb-scope .stButton>button{background:#1877F2!important;border-color:#1877F2!important;color:#fff!important}
    </style>
    """, unsafe_allow_html=True)
    st.markdown("<div id='fb-scope'>", unsafe_allow_html=True)
    st.markdown(
    "<span style='font-size:1.8rem; font-weight:800; color:#1877F2;'>FACEBOOK en vivo</span>",
    unsafe_allow_html=True
)

    # Estado y controles: sin usuario, solo botón + auto
    if "fb_q" not in st.session_state:
        st.session_state["fb_q"] = ""
    if "fb_run" not in st.session_state:
        st.session_state["fb_run"] = False
    st.session_state.setdefault("fb_hist", [])

    colUrl, colBtn, colAuto = st.columns([3,1,2])
    fb_input = colUrl.text_input(
        "URL de Facebook (video o post)",
        value=st.session_state["fb_q"],
        placeholder="https://www.facebook.com/.../videos/...",
        key="fb_input",
    )
    run_fb = colBtn.button("Consultar", key="fb_btn")
    fb_auto = colAuto.toggle("Auto-actualizar cada 30s", value=True, key="fb_auto")

    if run_fb:
        st.session_state["fb_q"] = (fb_input or "").strip()
        st.session_state["fb_run"] = True
        st.session_state["fb_hist"] = []  # reset historial

    if fb_auto and st.session_state.get("fb_run"):
        st_autorefresh(interval=30000, key="fb_live_auto")

    fb_snap = None

    if st.session_state.get("fb_run"):
        try:
            params = {"url": st.session_state.get("fb_q")} if st.session_state.get("fb_q") else None
            data = api_get("/facebook/live-video", params=params)
            st.caption(
    f"Backend: {LOCAL_API} — facebook/live-video  "
    f"{('url=' + st.session_state.get('fb_q')) if st.session_state.get('fb_q') else ''}"
)
            if isinstance(data, dict) and not data.get("live"):
                st.warning("No hay transmisión en vivo en este momento.")
            elif isinstance(data, dict):
                likes = int(data.get("likes") or 0)
                shares = int(data.get("shares") or 0)
                video_id = data.get("video_id") or "-"
                created_time = data.get("created_time") or ""
                title = data.get("title") or "Sin título"
                permalink = data.get("permalink_url")

                c1, c2, c3, c4 = st.columns(4)
                c1.metric("👍 Reacciones (aprox.)", f"{likes}")
                c2.metric("🔁 Compartidos", f"{shares}")
                c3.metric("🆔 Video ID", f"{video_id}")
                c4.metric("🗓️ Fecha", f"{created_time or '—'}")

                if title:
                    st.caption(f"Título: {title}")
                if permalink:
                    st.markdown(f"[🔗 Ver en Facebook]({permalink})")

                st.caption(f"Última actualización: {dt.datetime.now():%H:%M:%S}")

                fb_snap = {
                    "ts": pd.Timestamp.utcnow(),
                    "likes": likes,
                    "shares": shares,
                }
        except requests.HTTPError as http_err:
            try:
                j = http_err.response.json()
                st.error(f"Error de API ({http_err.response.status_code}): {j}")
            except Exception:
                st.error(f"Error de API: {http_err}")
        except Exception as e:
            st.error(f"No se pudo obtener datos: {e}")
    else:
        st.info("Pulsa **Consultar** para verificar si hay LIVE en la página configurada en tu API (puerto 8001).")

    # --- SERIES + SNAPSHOT (3 gráficas) para Facebook
    if fb_snap is not None:
        st.session_state["fb_hist"] = (st.session_state["fb_hist"] + [fb_snap])[-200:]

    if st.session_state["fb_hist"]:
        df_f = pd.DataFrame(st.session_state["fb_hist"])

        # 1) LÍNEAS con markers (evolución de likes y shares)
        y_cols_f = [c for c in ["likes", "shares"] if c in df_f.columns]
        if y_cols_f:
            fig_f = px.line(
                df_f, x="ts", y=y_cols_f,
                title="Evolución en vivo — Facebook",
                color_discrete_map={
                    "likes": "#1877F2",
                    "shares": "#60A5FA",
                },
                markers=True,
            )
            fig_f.update_layout(margin=dict(l=10, r=10, t=40, b=0), height=320, legend_title_text="")
            st.plotly_chart(fig_f, use_container_width=True)

            # Snapshot
            rowf = df_f.iloc[-1]
            df_f_last = pd.DataFrame({
                "metric": [m for m in y_cols_f],
                "value":  [int(rowf.get(m, 0)) for m in y_cols_f]
            })
            
            st.session_state["agg_fb"] = int(df_f_last["value"].sum())
            color_map_f = {
                "likes": "#1877F2",
                "shares": "#60A5FA",
            }

            cbf1, cbf2 = st.columns(2)
            fig_bar_f, fig_pie_f = _bar_and_pie_from_last(df_f_last, "Facebook", color_map_f)
            cbf1.plotly_chart(fig_bar_f, use_container_width=True)
            cbf2.plotly_chart(fig_pie_f, use_container_width=True)
    st.markdown("</div>", unsafe_allow_html=True)



# ========================
# Donut global al tope con suma de plataformas
# (Se renderiza en el placeholder creado arriba)
# ========================
try:
    ph = st.session_state.get('donut_ph')
    if ph is not None:
        total_vals = {
            'YouTube': int(st.session_state.get('agg_y', 0) or 0),
            'TikTok': int(st.session_state.get('agg_tt', 0) or 0),
            'Facebook': int(st.session_state.get('agg_fb', 0) or 0),
            'X': int(st.session_state.get('agg_x', 0) or 0),
        }
        # si no hay ningún dato, generar fallback simétrico
        if sum(total_vals.values()) <= 0:
            total_vals = {k: 1 for k in total_vals.keys()}

        import pandas as pd, plotly.express as px
        order = ['YouTube','Facebook','TikTok','X']
        df_total = pd.DataFrame([{'platform': k, 'value': total_vals.get(k, 0)} for k in order])

        fig_total = px.pie(
            df_total,
            names='platform', values='value', hole=0.55,
            title='Participación por plataforma (suma de métricas de los snapshots)',
            color='platform',
            color_discrete_map={
                'YouTube': '#FF0000',
                'Facebook': '#1877F2',
                'TikTok': '#000000',
                'X': '#657786',
            },
        )
        fig_total.update_traces(textposition='inside', texttemplate='%{percent:.1%}')
        fig_total.update_layout(margin=dict(l=10,r=10,t=40,b=0), height=320)
        ph.plotly_chart(fig_total, use_container_width=True)
except Exception as _e:
    # no romper la app si algo falla aquí
    pass
