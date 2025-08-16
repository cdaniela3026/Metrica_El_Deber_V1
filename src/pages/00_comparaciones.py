
# desarrollador del Front: Carla Daniela soruco 
# Descripción: Primera vista con gráfico de líneas (vistas en el tiempo),
#               gráfico "solar" (sunburst), autodetección de fuente por URL
#               (YouTube, Facebook, X, TikTok), perfiles predefinidos con
#               colores por plataforma y variaciones por perfil, filtro para
#               aislar redes y soporte para agregar URL ad-hoc.

import re
from datetime import datetime, timedelta
from typing import Dict, List
import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
import os
import base64, mimetypes
import json
import requests
from dotenv import load_dotenv
from PIL import Image

# ======================== Config básica ========================
st.set_page_config(page_title="Métrica El Deber V2", layout="wide")
load_dotenv()
API_BASE = os.getenv("API_BASE", "")  # ej.: http://127.0.0.1:8001

# ======================== Tema oscuro (CSS) ========================
st.markdown(
    """
    <style>
    [data-testid="stAppViewContainer"] { background-color: #0E1117; color: #E5E7EB; }
    [data-testid="stHeader"] { background: rgba(0,0,0,0); }
    [data-testid="stSidebar"] { background-color: #111827; color: #E5E7EB; }
    .block-container { padding-top: 0.5rem; }
    /* DataFrames */
    div[data-testid="stDataFrame"] { background: #0B1220 !important; color: #E5E7EB !important; }
    div[data-testid="stDataFrame"] * { color: #E5E7EB !important; }
    /* Inputs y selects en gris suave */
    input, textarea, select { background-color:#1F2937 !important; color:#E5E7EB !important; border:1px solid #374151 !important; }
    input::placeholder, textarea::placeholder { color:#9CA3AF !important; }

    /* Multiselect y tags */
    [data-testid="stMultiSelect"] div[data-baseweb="select"] { background-color:#0F172A !important; border:1px solid #1F2937 !important; }
    [data-baseweb="tag"] { background-color:#141A2A !important; color:#F3F4F6 !important; border:1px solid #1F2937 !important; border-radius:10px !important; }
    /* Punto de color por plataforma (●) antes del texto */
    [data-baseweb="tag"]::before { content:"●"; margin-right:6px; font-size:0.9rem; line-height:1; display:inline-block; }
    /* Facebook */
    [data-baseweb="tag"][title*="facebook" i]::before, [data-baseweb="tag"][aria-label*="facebook" i]::before { color:#1877F2; }
    [data-baseweb="tag"][title*="facebook" i] svg, [data-baseweb="tag"][aria-label*="facebook" i] svg { fill:#1877F2 !important; }
    /* YouTube */
    [data-baseweb="tag"][title*="youtube" i]::before, [data-baseweb="tag"][aria-label*="youtube" i]::before { color:#FF0000; }
    [data-baseweb="tag"][title*="youtube" i] svg, [data-baseweb="tag"][aria-label*="youtube" i] svg { fill:#FF0000 !important; }
    /* TikTok */
    [data-baseweb="tag"][title*="tiktok" i]::before, [data-baseweb="tag"][aria-label*="tiktok" i]::before { color:#262626; }
    [data-baseweb="tag"][title*="tiktok" i] svg, [data-baseweb="tag"][aria-label*="tiktok" i] svg { fill:#262626 !important; filter: drop-shadow(0 0 1px #E5E7EB); }
    /* X */
    [data-baseweb="tag"][title*="x" i]::before, [data-baseweb="tag"][aria-label*="x" i]::before { color:#FFFFFF; }
    [data-baseweb="tag"][title*="x" i] svg, [data-baseweb="tag"][aria-label*="x" i] svg { fill:#FFFFFF !important; }

    /* Botones */
    .stButton > button { background:#1F2937 !important; color:#F3F4F6 !important; border:1px solid #374151 !important; box-shadow: 0 2px 8px rgba(0,0,0,0.25); }
    .stButton > button:hover { background:#111827 !important; border-color:#4B5563 !important; }

    /* Sliders */
    [data-testid="stSlider"] [role="slider"] { background:#9CA3AF !important; box-shadow:none !important; }
    [data-testid="stSlider"] .st-dx { background:#374151 !important; }

    /* Tablas/dataframes */
    div[data-testid="stDataFrame"] { background:#0B1220 !important; color:#E5E7EB !important; border:1px solid #1F2937 !important; border-radius:10px; }
    div[data-testid="stDataFrame"] thead tr th { background:#111827 !important; color:#F3F4F6 !important; }
    div[data-testid="stDataFrame"] tbody tr td { background:#0B1220 !important; color:#E5E7EB !important; border-color:#1F2937 !important; }

    /* Checkboxes en gris */
    input[type="checkbox"]{ accent-color:#9CA3AF; }
    /* TextInput (baseweb) en oscuro y alto contraste */
    [data-testid="stTextInput"] div[data-baseweb="input"] > div { background-color:#1F2937 !important; border:1px solid #374151 !important; }
    [data-testid="stTextInput"] input { background-color:#1F2937 !important; color:#F9FAFB !important; }
    div[data-baseweb="input"] { background-color:#1F2937 !important; }
    div[data-baseweb="input"] input::placeholder { color:#9CA3AF !important; }

    /* Oscurecer aún más tablas y marcos */
    div[data-testid="stDataFrame"] { background:#0A0F1A !important; color:#E5E7EB !important; border:1px solid #111827 !important; border-radius:12px; }
    div[data-testid="stDataFrame"] thead tr th { background:#0F172A !important; color:#F3F4F6 !important; }
    div[data-testid="stDataFrame"] tbody tr td { background:#0A0F1A !important; color:#F3F4F6 !important; border-color:#111827 !important; }

    /* Scrollbars oscuros para dataframes */
    div[data-testid="stDataFrame"] ::-webkit-scrollbar { width:10px; height:10px; }
    div[data-testid="stDataFrame"] ::-webkit-scrollbar-track { background:#0F172A; }
    div[data-testid="stDataFrame"] ::-webkit-scrollbar-thumb { background:#374151; border-radius:10px; }
    div[data-testid="stDataFrame"] ::-webkit-scrollbar-thumb:hover { background:#4B5563; }

    /* Checkboxes más oscuros */
    input[type="checkbox"]{ accent-color:#6B7280; background:#111827; }
    /* KPI cards */
    .kpi-card { background:#0F172A; border:1px solid #1F2937; border-radius:14px; padding:14px 16px; box-shadow:0 4px 12px rgba(0,0,0,0.25); }
    .kpi-title { font-size:0.9rem; color:#9CA3AF; margin-bottom:6px; }
    .kpi-value { font-size:1.6rem; font-weight:700; color:#F9FAFB; line-height:1.2; }
    .kpi-sub { font-size:0.8rem; color:#D1D5DB; margin-top:4px; }
    /* Tablas HTML (st.table) en oscuro */
    [data-testid="stTable"] > div { background:#0A0F1A; border:1px solid #111827; border-radius:12px; padding:8px; }
    [data-testid="stTable"] table { color:#F3F4F6; width:100%; border-collapse:separate; border-spacing:0; }
    [data-testid="stTable"] thead th { background:#0F172A; color:#F9FAFB; }
    [data-testid="stTable"] tbody td { background:#0A0F1A; color:#E5E7EB; }

    /* Multiselect: fondo del contenedor AÚN más oscuro y controles internos */
    [data-testid="stMultiSelect"] div[data-baseweb="select"] { background-color:#0B1220 !important; border:1px solid #1F2937 !important; }
    [data-testid="stMultiSelect"] div[data-baseweb="select"] > div { background-color:#0B1220 !important; }
    [data-testid="stMultiSelect"] div[data-baseweb="select"] input { color:#F9FAFB !important; background-color:transparent !important; }
    [data-testid="stMultiSelect"] div[data-baseweb="select"] svg { fill:#9CA3AF !important; }

    /* Lista desplegable (portal) en modo oscuro */
    .stApp [role="listbox"] { background:#0F172A !important; color:#E5E7EB !important; border:1px solid #1F2937 !important; }
    .stApp [role="option"] { background:#0F172A !important; color:#E5E7EB !important; }
    .stApp [role="option"][aria-selected="true"],
    .stApp [role="option"]:hover { background:#111827 !important; color:#F9FAFB !important; }

    /* Chips por plataforma: colorear fondo según red */
    [data-baseweb="tag"][title*="facebook" i], [data-baseweb="tag"][aria-label*="facebook" i]{
      background-color:#1877F2 !important; color:#FFFFFF !important; border-color:#0B4ABF !important;
    }
    [data-baseweb="tag"][title*="facebook" i]::before, [data-baseweb="tag"][aria-label*="facebook" i]::before{ color:#FFFFFF !important; }
    [data-baseweb="tag"][title*="facebook" i] svg, [data-baseweb="tag"][aria-label*="facebook" i] svg{ fill:#FFFFFF !important; }

    [data-baseweb="tag"][title*="youtube" i], [data-baseweb="tag"][aria-label*="youtube" i]{
      background-color:#FF0000 !important; color:#FFFFFF !important; border-color:#B00000 !important;
    }
    [data-baseweb="tag"][title*="youtube" i]::before, [data-baseweb="tag"][aria-label*="youtube" i]::before{ color:#FFFFFF !important; }
    [data-baseweb="tag"][title*="youtube" i] svg, [data-baseweb="tag"][aria-label*="youtube" i] svg{ fill:#FFFFFF !important; }

    [data-baseweb="tag"][title*="tiktok" i], [data-baseweb="tag"][aria-label*="tiktok" i]{
      background-color:#0D0D0D !important; color:#FFFFFF !important; border-color:#2E2E2E !important;
    }
    [data-baseweb="tag"][title*="tiktok" i]::before, [data-baseweb="tag"][aria-label*="tiktok" i]::before{ color:#FFFFFF !important; }
    [data-baseweb="tag"][title*="tiktok" i] svg, [data-baseweb="tag"][aria-label*="tiktok" i] svg{ fill:#FFFFFF !important; }

    [data-baseweb="tag"][title*="x" i], [data-baseweb="tag"][aria-label*="x" i]{
      background-color:#FFFFFF !important; color:#111827 !important; border-color:#E5E7EB !important;
    }
    [data-baseweb="tag"][title*="x" i]::before, [data-baseweb="tag"][aria-label*="x" i]::before{ color:#111827 !important; }
    [data-baseweb="tag"][title*="x" i] svg, [data-baseweb="tag"][aria-label*="x" i] svg{ fill:#111827 !important; }

    /* Sidebar: subtítulos/labels en blanco de alto contraste */
    [data-testid="stSidebar"] label { color:#FFFFFF !important; opacity:1 !important; }
    [data-testid="stSidebar"] p, [data-testid="stSidebar"] span, [data-testid="stSidebar"] small { color:#FFFFFF !important; opacity:1 !important; }

    /* Índices de tablas (st.table): números en blanco */
    [data-testid="stTable"] tbody th { color:#FFFFFF !important; background:#0A0F1A !important; }
    [data-testid="stTable"] thead th:first-child { color:#FFFFFF !important; }

    </style>
    """,
    unsafe_allow_html=True,
)

# ========== Helpers de encabezado y secciones con icono/logo ==========

def _header_logo():
    for p in ("src/assets/logo_el_deber.png", "assets/logo_el_deber.png", "logo_el_deber.png"):
        if os.path.exists(p):
            st.image(p, width=260)
            return
    st.title("Métrica El Deber – Versión 2 (MVP)")

def section_header(img_name: str, text: str, img_width: int = 26):
    col_i, col_t = st.columns([0.06, 0.94])
    with col_i:
        shown = False
        for p in (f"src/assets/{img_name}", f"assets/{img_name}", img_name):
            if os.path.exists(p):
                st.image(p, width=img_width)
                shown = True
                break
        if not shown:
            st.markdown("&nbsp;", unsafe_allow_html=True)
    with col_t:
        st.subheader(text)

# Helpers de assets para logos en trazas
def _asset_path(name: str):
    for p in (f"src/assets/{name}", f"assets/{name}", name):
        if os.path.exists(p):
            return p
    return None

def _img_uri(name: str) -> str | None:
    p = _asset_path(name)
    if not p:
        return None
    with open(p, "rb") as f:
        data = f.read()
    mime = mimetypes.guess_type(p)[0] or "image/png"
    b64 = base64.b64encode(data).decode("utf-8")
    return f"data:{mime};base64,{b64}"

def _img_pil(name: str):
    p = _asset_path(name)
    if not p or not os.path.exists(p):
        return None
    try:
        return Image.open(p)
    except Exception:
        return None



_header_logo()
st.caption("Primera vista con líneas, gráfico solar, autodetección por URL y perfiles.")

# ======================== Constantes / Colores ========================
# Logos por perfil para chapitas al final de las líneas
PROFILE_LOGO = {
    "El Deber": "logo_el_deber.png",
    "Unitel": "logo_unitel.jpg",  # en tus assets está como .jpg
    "Red Uno": "logo_red_uno.png",
}
PLATFORM_COLORS: Dict[str, str] = {
    "facebook": "#1877F2",   # azul Facebook
    "youtube": "#FF0000",    # rojo YouTube
    "tiktok": "#262626",     # negro TikTok con realce
    "x": "#FFFFFF",          # blanco X
}

def shade_color(hex_color: str, factor: float) -> str:
    hex_color = hex_color.lstrip('#')
    r = int(hex_color[0:2], 16)
    g = int(hex_color[2:4], 16)
    b = int(hex_color[4:6], 16)
    r = int(min(255, max(0, r * factor)))
    g = int(min(255, max(0, g * factor)))
    b = int(min(255, max(0, b * factor)))
    return f"#{r:02X}{g:02X}{b:02X}"

def kpi_card(title: str, value: str | int, subtitle: str, accent: str) -> str:
    return f"""
    <div class='kpi-card' style='border-left:6px solid {accent};'>
      <div class='kpi-title'>{title}</div>
      <div class='kpi-value'>{value}</div>
      <div class='kpi-sub'>{subtitle}</div>
    </div>
    """

# ======================== Estado inicial ========================
if "profiles" not in st.session_state:
    st.session_state.profiles = {
        "El Deber": {"facebook": "eldeber", "youtube": "@ELDEBER", "x": "@diarioeldeber", "tiktok": "@eldeber"},
        "Unitel":   {"facebook": "unitelbolivia", "youtube": "@unitelbolivia", "x": "@unitelbolivia", "tiktok": "@unitel"},
        "Red Uno":  {"facebook": "reduno", "youtube": "@redunobolivia", "x": "@RedUnoBolivia", "tiktok": "@reduno"},
    }
if "ad_hoc_urls" not in st.session_state:
    st.session_state.ad_hoc_urls: List[Dict] = []
if "df_data" not in st.session_state:
    st.session_state.df_data = pd.DataFrame()
if "query_active" not in st.session_state:
    st.session_state.query_active = False

# ======================== Detectar plataforma por URL ========================
PLATFORM_PATTERNS = {
    "youtube": re.compile(r"(youtube\.com|youtu\.be)", re.I),
    "facebook": re.compile(r"facebook\.com", re.I),
    "x": re.compile(r"(twitter\.com|x\.com)", re.I),
    "tiktok": re.compile(r"tiktok\.com", re.I),
}

def detect_platform(url: str) -> str | None:
    for name, pat in PLATFORM_PATTERNS.items():
        if pat.search(url):
            return name
    return None

# --- Helpers para mapear URLs a perfiles ---
HANDLE_PATTERNS = {
    "youtube": [re.compile(r"youtube\.com/@([A-Za-z0-9._-]+)", re.I)],
    "facebook": [re.compile(r"facebook\.com/([A-Za-z0-9._-]+)/?", re.I)],
    "x": [re.compile(r"(?:x\.com|twitter\.com)/([A-Za-z0-9._-]+)", re.I)],
    "tiktok": [re.compile(r"tiktok\.com/@([A-Za-z0-9._-]+)", re.I)],
}

def extract_handle(url: str, platform: str) -> str | None:
    pats = HANDLE_PATTERNS.get(platform, [])
    for p in pats:
        m = p.search(url)
        if m:
            return m.group(1).lstrip('@').lower()
    return None

def map_profile_from_url(url: str) -> tuple[str | None, str | None]:
    """Devuelve (platform, profile) si logramos mapear el handle a un perfil configurado."""
    plat = detect_platform(url)
    if not plat:
        return None, None
    handle = extract_handle(url, plat)
    profile = None
    if handle:
        for prof, ids in st.session_state.profiles.items():
            h = ids.get(plat)
            if h and h.lstrip('@').lower() == handle:
                profile = prof
                break
    return plat, profile

# ======================== Clientes API (datos reales) ========================

def _api_get(path: str, params: dict | None = None, timeout: int = 12):
    if not API_BASE:
        return None
    url = API_BASE.rstrip("/") + path
    try:
        r = requests.get(url, params=params or {}, timeout=timeout)
        r.raise_for_status()
        return r.json()
    except Exception:
        return None

def fetch_timeseries_api(start: datetime, end: datetime, freq: str, platforms_filter: List[str] | None, urls: List[str] | None) -> pd.DataFrame | None:
    payload = {"start": start.isoformat(), "end": end.isoformat(), "resolution": freq}
    if platforms_filter:
        payload["platforms"] = ",".join(platforms_filter)
    if urls:
        try:
            payload["urls"] = json.dumps(urls)
        except Exception:
            payload["urls"] = ",".join(urls)
    if urls:
        try:
            payload["urls"] = json.dumps(urls)
        except Exception:
            payload["urls"] = ",".join(urls)
    if urls:
        try:
            payload["urls"] = json.dumps(urls)
        except Exception:
            payload["urls"] = ",".join(urls)
    data = _api_get("/timeseries", payload)
    if not data:
        return None
    df = pd.DataFrame(data)
    df = df.rename(columns={"time": "timestamp", "value": "views"})
    if "timestamp" in df:
        df["timestamp"] = pd.to_datetime(df["timestamp"], errors="coerce")
    if "platform" in df:
        df["platform"] = df["platform"].astype(str).str.lower()
    if "profile" not in df:
        df["profile"] = df.get("page", "El Deber")
    if "views" not in df:
        df["views"] = df.get("count", 0)
    cols = ["timestamp", "profile", "platform", "views"]
    df = df[[c for c in cols if c in df.columns]]
    return df

def fetch_live_status_api(platforms_filter: List[str] | None, urls: List[str] | None) -> pd.DataFrame | None:
    payload = {}
    if platforms_filter:
        payload["platforms"] = ",".join(platforms_filter)
    if urls:
        try:
            payload["urls"] = json.dumps(urls)
        except Exception:
            payload["urls"] = ",".join(urls)
    data = _api_get("/live-status", payload)
    if not data:
        return None
    df = pd.DataFrame(data)
    df = df.rename(columns={"viewers": "live_viewers", "ts": "checked_at"})
    if "checked_at" in df:
        df["checked_at"] = pd.to_datetime(df["checked_at"], errors="coerce")
    for col, default in {
        "profile": "El Deber",
        "platform": "youtube",
        "is_live": False,
        "live_viewers": 0,
    }.items():
        if col not in df:
            df[col] = default
    return df

def fetch_geo_api(start: datetime, end: datetime, platforms_filter: List[str] | None, urls: List[str] | None) -> pd.DataFrame | None:
    payload = {"start": start.isoformat(), "end": end.isoformat()}
    if platforms_filter:
        payload["platforms"] = ",".join(platforms_filter)
    data = _api_get("/geo", payload)
    if not data:
        return None
    df = pd.DataFrame(data).rename(columns={"value": "views"})
    needed = {"region", "lat", "lon", "platform", "views"}
    if not needed.issubset(df.columns):
        return None
    return df

# ======================== Stubs de obtención de datos (demo) ========================
def fetch_mock_timeseries(start: datetime, end: datetime, freq: str, profiles: Dict[str, Dict[str, str]], platforms_filter: List[str] | None) -> pd.DataFrame:
    rng = pd.date_range(start, end, freq=freq)
    rows = []
    for perfil in profiles.keys():
        for platform in ["facebook", "youtube", "x", "tiktok"]:
            if platforms_filter and platform not in platforms_filter:
                continue
            base = {"facebook": 1800, "youtube": 3000, "x": 650, "tiktok": 2200}[platform]
            noise = np.abs(np.random.normal(0, base * 0.2, size=len(rng))).astype(int)
            for ts, vv in zip(rng, base + noise):
                rows.append({"timestamp": ts, "profile": perfil, "platform": platform, "views": int(vv)})
    return pd.DataFrame(rows)

def fetch_mock_live_status(profiles: Dict[str, Dict[str, str]], platforms_filter: List[str] | None) -> pd.DataFrame:
    rows = []
    now = datetime.utcnow()
    for perfil in profiles.keys():
        for platform in ["facebook", "youtube", "x", "tiktok"]:
            if platforms_filter and platform not in platforms_filter:
                continue
            has_live = np.random.rand() < 0.25
            rows.append({"profile": perfil, "platform": platform, "is_live": has_live, "live_viewers": int(np.random.randint(0, 8000)) if has_live else 0, "checked_at": now})
    return pd.DataFrame(rows)

def build_geo_from_timeseries(df_ts: pd.DataFrame) -> pd.DataFrame:
    """Distribución geográfica simulada por plataforma y región.
    Devuelve filas por (region, platform) con lat/lon y 'views'.
    """
    regions = [
        {"region": "North America", "lat": 40, "lon": -100},
        {"region": "South America", "lat": -15, "lon": -60},
        {"region": "Europe", "lat": 54, "lon": 15},
        {"region": "Africa", "lat": 0, "lon": 20},
        {"region": "Asia", "lat": 30, "lon": 100},
        {"region": "Oceania", "lat": -25, "lon": 135},
    ]
    platforms = ["facebook", "youtube", "x", "tiktok"]
    totals = df_ts.groupby("platform")["views"].sum().reindex(platforms).fillna(0).to_numpy()
    rng = np.random.default_rng(42)
    weights = rng.dirichlet(np.ones(len(regions)), size=len(platforms))  # por plataforma
    rows = []
    for p_idx, platform in enumerate(platforms):
        region_alloc = weights[p_idx] * totals[p_idx]
        for r_idx, r in enumerate(regions):
            rows.append({
                "region": r["region"],
                "lat": r["lat"],
                "lon": r["lon"],
                "platform": platform,
                "views": float(region_alloc[r_idx]),
            })
    return pd.DataFrame(rows)

# ======================== Sidebar: filtros y opciones ========================
st.sidebar.header("⚙️ Controles")
api_ok = bool(API_BASE)
use_real = st.sidebar.checkbox("Usar datos reales (.env)", value=api_ok)
if use_real and not api_ok:
    st.sidebar.warning("No se encontró API_BASE en .env — usando demo.")
platform_pick = st.sidebar.multiselect("Mostrar redes (puedes aislar una):", ["facebook", "youtube", "x", "tiktok"], ["facebook", "youtube", "x", "tiktok"])
minutes_back = st.sidebar.slider("Ventana de tiempo (horas hacia atrás)", 1, 72, 12)
refresh_seconds = st.sidebar.slider("Auto-actualizar cada (segundos)", 0, 120, 30)
auto_refresh = refresh_seconds > 0

st.sidebar.markdown("---")
# Si se marcó limpiar inputs en el ciclo anterior, borra antes de instanciar widgets
if st.session_state.get("_clear_inputs", False):
    st.session_state["_clear_inputs"] = False
    st.session_state["adhoc_url"] = ""
    for k in ("chk_eldeber", "chk_unitel", "chk_reduno"):
        st.session_state[k] = False

url = st.sidebar.text_input("Pega una URL (YouTube, X, Facebook o TikTok)", key="adhoc_url")
st.sidebar.caption("Selecciona el perfil")
c1, c2, c3 = st.sidebar.columns(3)
with c1:
    chk_el = st.checkbox("El Deber", key="chk_eldeber")
with c2:
    chk_un = st.checkbox("Unitel", key="chk_unitel")
with c3:
    chk_ru = st.checkbox("Red Uno", key="chk_reduno")

col_add1, col_add2 = st.sidebar.columns([1,1])
with col_add1:
    add_url = st.button("➕ Agregar URL")
with col_add2:
    clear_urls = st.button("🗑️ Limpiar URLs ad-hoc")

if add_url and url:
    # Validar selección (exactamente un check)
    selected = [name for name, ok in [("El Deber", st.session_state.get("chk_eldeber", False)),
                                      ("Unitel", st.session_state.get("chk_unitel", False)),
                                      ("Red Uno", st.session_state.get("chk_reduno", False))] if ok]
    if len(selected) != 1:
        st.sidebar.warning("Selecciona exactamente un perfil (El Deber, Unitel o Red Uno).")
    else:
        # Detectar plataforma
        plat = detect_platform(url) or None
        if not plat:
            plat, _ = map_profile_from_url(url)
        plat = (plat or "desconocida").lower()

        # No permitir duplicados por (profile, platform)
        existing_pairs = {(u.get("profile"), (u.get("platform") or "").lower()) for u in st.session_state.ad_hoc_urls}
        if (selected[0], plat) in existing_pairs:
            st.sidebar.warning("Ese perfil ya tiene una URL para esa plataforma. Elimina la anterior si deseas cambiarla.")
        else:
            # Evitar URLs duplicadas exactas (normalizadas)
            norm = url.strip().rstrip('/').lower()
            existing_urls = {u["url"].strip().rstrip('/').lower() for u in st.session_state.ad_hoc_urls}
            if norm in existing_urls:
                st.sidebar.info("Esa URL ya fue agregada.")
            else:
                st.session_state.ad_hoc_urls.append({
                    "url": url,
                    "platform": plat,
                    "profile": selected[0],
                    "added_at": datetime.utcnow(),
                })
                st.sidebar.success(f"URL agregada como {plat.title()} → perfil: {selected[0]}")
                st.rerun()

if clear_urls:
    st.session_state.ad_hoc_urls = []
    st.session_state.query_active = False
    st.session_state["_clear_inputs"] = True
    st.sidebar.info("Se limpiaron las URLs ad-hoc.")
    st.rerun()

# Botón general para consultar
consultar = st.sidebar.button("▶️ Consultar", type="primary")
detener = st.sidebar.button("⏸️ Detener consulta")

if consultar:
    if len(st.session_state.ad_hoc_urls) == 0:
        st.sidebar.warning("Agrega al menos 1 URL antes de consultar.")
        st.session_state.query_active = False
    else:
        st.session_state.query_active = True
        # marca limpieza de inputs
        st.session_state["_clear_inputs"] = True
    st.rerun()

if detener:
    st.session_state.query_active = False
    st.rerun()

# (limpieza duplicada eliminada)

# Auto-refresh manual con st.rerun() usando contador simple
auto_refresh_key = "_last_refresh"
if auto_refresh and st.session_state.get("query_active", False):
    import time
    last = st.session_state.get(auto_refresh_key, 0)
    if time.time() - last > refresh_seconds:
        st.session_state[auto_refresh_key] = time.time()
        st.rerun()

# ======================== Carga/actualización de datos ========================
start = datetime.utcnow() - timedelta(hours=minutes_back)
end = datetime.utcnow()

urls_selected = [u["url"] for u in st.session_state.ad_hoc_urls]
platforms_from_urls = sorted({(u.get("platform") or "").lower() for u in st.session_state.ad_hoc_urls if u.get("platform")})

should_query_real = use_real and st.session_state.get("query_active", False) and len(urls_selected) > 0

if should_query_real:
    df_ts = fetch_timeseries_api(start, end, "15min", platform_pick or None, urls_selected)
    if df_ts is None or df_ts.empty:
        st.warning("/timeseries vacío — usando demo.")
        df_ts = fetch_mock_timeseries(start, end, "15min", st.session_state.profiles, platform_pick or None)
    df_live = fetch_live_status_api(platform_pick or None, urls_selected)
    if df_live is None or df_live.empty:
        df_live = fetch_mock_live_status(st.session_state.profiles, platform_pick or None)
    df_geo = fetch_geo_api(start, end, platform_pick or None, urls_selected)
    if df_geo is None or df_geo.empty:
        df_geo = build_geo_from_timeseries(df_ts)
else:
    if use_real:
        df_ts = pd.DataFrame()
        df_live = pd.DataFrame(columns=["profile","platform","is_live","live_viewers","checked_at"]).astype({"is_live":bool})
        df_geo = pd.DataFrame(columns=["region","lat","lon","platform","views"])
        st.info("Agrega URLs y presiona ▶️ Consultar para traer datos reales. Mientras tanto no se consulta al backend.")
    else:
        df_ts = fetch_mock_timeseries(start, end, "15min", st.session_state.profiles, platform_pick or None)
        df_live = fetch_mock_live_status(st.session_state.profiles, platform_pick or None)
        df_geo = build_geo_from_timeseries(df_ts)

st.session_state.df_data = df_ts.copy()

# === (Sin alias manuales) Usamos el perfil elegido en la sidebar ===
# No aplicamos reemplazos de 'profile_auto' → alias; el usuario selecciona directamente el perfil.

# === Filtrar SOLO perfiles/plataformas consultados cuando la consulta está activa ===
if st.session_state.get("query_active", False) and len(st.session_state.ad_hoc_urls) > 0:
    active_profiles = {u.get("profile") for u in st.session_state.ad_hoc_urls if u.get("profile")}
    active_platforms = {(u.get("platform") or "").lower() for u in st.session_state.ad_hoc_urls if u.get("platform")}

    if isinstance(df_ts, pd.DataFrame) and not df_ts.empty:
        if "profile" in df_ts.columns:
            df_ts = df_ts[df_ts["profile"].isin(active_profiles)].copy()
        if "platform" in df_ts.columns:
            df_ts = df_ts[df_ts["platform"].str.lower().isin(active_platforms)].copy()

    if isinstance(df_live, pd.DataFrame) and not df_live.empty:
        if "profile" in df_live.columns:
            df_live = df_live[df_live["profile"].isin(active_profiles)].copy()
        if "platform" in df_live.columns:
            df_live = df_live[df_live["platform"].str.lower().isin(active_platforms)].copy()

    if isinstance(df_geo, pd.DataFrame) and not df_geo.empty:
        # df_geo usualmente no trae profile, pero sí platform
        if "platform" in df_geo.columns:
            df_geo = df_geo[df_geo["platform"].str.lower().isin(active_platforms)].copy()

if use_real and api_ok:
    st.success(f"API (.env) OK → {API_BASE}")
elif use_real:
    st.error("API desactivada: faltó API_BASE en .env")

# ======================== UI principal ========================
# ---- KPI superiores ----
perfiles_cnt = len(st.session_state.profiles)
redes_activas = len(platform_pick)
lives_activos = int(df_live["is_live"].sum()) if (not df_live.empty and "is_live" in df_live) else 0
urls_cnt = len(st.session_state.ad_hoc_urls)
last_chk_str = pd.to_datetime(df_live["checked_at"].max()).strftime("%H:%M:%S UTC") if not df_live.empty else "-"

k1, k2, k3, k4 = st.columns(4)
k1.markdown(kpi_card("Redes activas", redes_activas, "Seleccionadas a la izquierda", "#3B82F6"), unsafe_allow_html=True)
k2.markdown(kpi_card("Perfiles monitoreados", perfiles_cnt, "Colores por plataforma", "#F59E0B"), unsafe_allow_html=True)
k3.markdown(kpi_card("Lives activos", lives_activos, f"Última verificación {last_chk_str}", "#EF4444"), unsafe_allow_html=True)
k4.markdown(kpi_card("URLs ad‑hoc", urls_cnt, "Agregadas manualmente", "#8B5CF6"), unsafe_allow_html=True)

# ---- Arriba: Sunburst y Mapa centrados ----
spacerL, colSun, colMap, spacerR = st.columns([1, 3.6, 2.4, 1], gap="large")
with colSun:
    section_header("logo_solar.webp", "Gráfico solar (Sunburst)")
    # Guardas: si no hay datos o falta la columna 'timestamp', no intentamos calcular
    if df_ts.empty or ("timestamp" not in df_ts.columns):
        st.info("Sin datos recientes para el sunburst.")
    else:
        try:
            last_ts = df_ts["timestamp"].max()
            df_last = df_ts[df_ts["timestamp"] == last_ts].copy()
        except Exception:
            df_last = pd.DataFrame()
        if df_last.empty:
            st.info("Sin datos recientes para el sunburst.")
        else:
            df_last["value"] = df_last["views"]
            fig_sun = px.sunburst(
                df_last,
                path=["platform", "profile"],
                values="value",
                color="platform",
                color_discrete_map=PLATFORM_COLORS,
            )
            fig_sun.update_traces(
                texttemplate='%{label}<br>%{percentRoot:.1%}',
                hovertemplate='%{label}<br>%{value:,} vistas<br>%{percentRoot:.1%} del total<extra></extra>'
            )
            fig_sun.update_layout(
                template="plotly_dark",
                paper_bgcolor='rgba(0,0,0,0)',
                plot_bgcolor='rgba(0,0,0,0)',
                height=420,
                margin=dict(l=0, r=0, t=20, b=0)
            )
            st.plotly_chart(fig_sun, use_container_width=True)

with colMap:
    section_header("logo_geo.png", "Distribución geográfica (simulada)")
    if df_geo.empty or df_geo["views"].sum() <= 0:
        st.info("Sin datos para el mapa.")
    else:
        fig_map = px.scatter_geo(
            df_geo,
            lat="lat",
            lon="lon",
            size="views",
            hover_name="region",
            color="platform",
            size_max=40,
            color_discrete_map=PLATFORM_COLORS,
        )
        fig_map.update_layout(template="plotly_dark", paper_bgcolor='rgba(0,0,0,0)', margin=dict(l=0, r=0, t=20, b=0))
        fig_map.update_geos(bgcolor='rgba(0,0,0,0)', landcolor='#0F172A', oceancolor='#0B1220', lakecolor='#0B1220', coastlinecolor='#374151', showland=True, showocean=True, showcountries=True, countrycolor='#374151')
        # Mejorar visibilidad del punto negro (TikTok) sobre fondo oscuro
        for tr in fig_map.data:
            if str(tr.name).lower() == "tiktok":
                tr.marker.line = dict(color="#E5E7EB", width=1.5)
                tr.marker.opacity = 0.95
        fig_map.update_layout(legend=dict(font=dict(color="#FFFFFF")), font=dict(color="#FFFFFF"))
        st.plotly_chart(fig_map, use_container_width=True)

# ---- Abajo: Vistas por tiempo (líneas) a todo el ancho ----
with st.container():
    section_header("logo_metrica.png", "Vistas por tiempo (líneas)")
    if df_ts.empty:
        st.info("No hay datos. Ajusta los filtros.")
    else:
        LINE_PLATFORM_COLORS = {"youtube": "#FF0000", "facebook": "#1877F2", "tiktok": "#262626", "x": "#FFFFFF"}
        df_ts_sorted = df_ts.sort_values("timestamp")
        df_ts_sorted["serie"] = df_ts_sorted["profile"] + " – " + df_ts_sorted["platform"].str.title()
        fig_line = px.line(
            df_ts_sorted,
            x="timestamp",
            y="views",
            color="serie",
            line_group="serie",
            hover_data={"profile": True, "platform": True, "views": ":,", "timestamp": True},
        )
        # Asignar color por plataforma (fijo) y grosor para dar realce al negro de TikTok
        for trace in fig_line.data:
            serie = trace.name
            try:
                platform_label = serie.split(" – ")[-1].strip().lower()
            except Exception:
                platform_label = "facebook"
            color = LINE_PLATFORM_COLORS.get(platform_label, "#888888")
            trace.line.color = color
            trace.line.width = 3 if platform_label == "tiktok" else 2.4
        fig_line.update_layout(
            template="plotly_dark",
            paper_bgcolor='rgba(0,0,0,0)',
            plot_bgcolor='rgba(0,0,0,0)',
            height=420,
            margin=dict(l=20, r=120, t=20, b=20),
            legend_title_text="Serie",
            legend=dict(font=dict(color="#FFFFFF")),
            font=dict(color="#FFFFFF"),
        )
        # —— Estilos por perfil (dash) ——
        PROFILE_DASH = {"El Deber": "solid", "Unitel": "dash", "Red Uno": "dot"}
        for tr in fig_line.data:
            try:
                prof = tr.name.split(" – ")[0].strip()
            except Exception:
                prof = ""
            tr.line.dash = PROFILE_DASH.get(prof, "solid")
        # Colocar logos a la derecha (coordenadas 'paper')
        ymin = float(df_ts_sorted["views"].min())
        ymax = float(df_ts_sorted["views"].max())
        yrange = max(ymax - ymin, 1.0)
        for serie in df_ts_sorted["serie"].unique():
            sub = df_ts_sorted[df_ts_sorted["serie"] == serie]
            if sub.empty:
                continue
            last = sub.iloc[-1]
            prof = last["profile"]
            logo_name = PROFILE_LOGO.get(prof)
            img_pil = _img_pil(logo_name) if logo_name else None
            if img_pil is None:
                continue
            sizex = 0.05
            sizey = float(min(max(yrange * 0.06, 28.0), yrange * 0.15))
            fig_line.add_layout_image(
                dict(
                    source=img_pil,
                    xref="paper",
                    yref="y",
                    x=0.995,
                    y=float(last["views"]),
                    sizex=sizex,
                    sizey=sizey,
                    xanchor="right",
                    yanchor="middle",
                    sizing="contain",
                    layer="above",
                    opacity=1.0,
                )
            )
        st.plotly_chart(fig_line, use_container_width=True)

st.markdown("---")

# ======================== Tarjetas Live + URLs ad-hoc ========================
col1, col2 = st.columns([2, 1], gap="large")
with col1:
    st.subheader(f"🔴 Monitoreo de emisiones en vivo{' (simulado)' if not should_query_real else ''}")
    if df_live.empty:
        st.info("No se encontraron estados de live")
    else:
        # ===== KPI CARDS =====
        # (Quitamos card de 'Lives activos' aquí; solo mostramos tarjetas por plataforma y la tabla en dos columnas)
        cA, cB = st.columns([1,2], gap="large")

        with cA:
            active_platforms = [(u.get("platform") or "").lower() for u in st.session_state.ad_hoc_urls]
            # Solo YouTube y TikTok, distribuidos en columnas
            plat_order = [p for p in ["youtube", "tiktok"] if p in set(active_platforms)]
            if len(plat_order) == 0:
                st.info("Agrega URLs y presiona ▶️ Consultar para ver plataformas en vivo.")
            else:
                cols = st.columns(len(plat_order))
                for i, platform in enumerate(plat_order):
                    dfp = df_live[df_live["platform"].str.lower() == platform]
                    on_p = int(dfp["is_live"].sum())
                    viewers_p = int(dfp.loc[dfp["is_live"], "live_viewers"].sum())
                    name = platform.title()
                    with cols[i]:
                        st.markdown(
                            kpi_card(name, on_p, f"👁️ {viewers_p:,} viewers", PLATFORM_COLORS.get(platform, "#6B7280")),
                            unsafe_allow_html=True,
                        )

        with cB:
            # ===== Tabla detalle =====
            df_live_disp = df_live.copy()
            df_live_disp["platform"] = df_live_disp["platform"].str.title()
            st.table(df_live_disp)
with col2:
    st.subheader("🔗 URLs ad-hoc agregadas")
    if len(st.session_state.ad_hoc_urls) == 0:
        st.info("Aún no agregaste URLs.")
    else:
        df_urls = pd.DataFrame(st.session_state.ad_hoc_urls)
        if not df_urls.empty:
            df_urls["platform"] = df_urls["platform"].fillna("desconocida").str.title()
            # ordenar columnas y formatear fecha
            if "added_at" in df_urls.columns:
                df_urls["added_at"] = pd.to_datetime(df_urls["added_at"]).dt.strftime("%Y-%m-%d %H:%M:%S")
            cols = [c for c in ["profile", "platform", "url", "added_at"] if c in df_urls.columns]
            df_urls = df_urls[cols]
        st.table(df_urls)


