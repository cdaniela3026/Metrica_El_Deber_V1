import streamlit as st
import requests
import pandas as pd
from datetime import datetime

def _fmt_dt(dt_str: str) -> str:
    if not dt_str:
        return ""
    try:
        return datetime.fromisoformat(dt_str.replace("Z", "+00:00")).strftime("%Y-%m-%d %H:%M")
    except Exception:
        return dt_str

def render_facebook_tab(api_base_url: str):
    """Renderiza la pestaña de Facebook con la misma estructura que TikTok/YouTube LIVE.

    api_base_url: ej. "http://localhost:8001" (sin slash final)

    - Botón para consultar LIVE

    - Métricas (reacciones, compartidos, ids, fecha)

    - Link al post

    - Botón extra para 'Cargar posts' (opcional, por si tus otras pestañas lo tienen)

    """
    st.header("📘 Facebook LIVE", divider=True)

    col_a, col_b = st.columns([1, 3])
    with col_a:
        consultar = st.button("🔴 Consultar LIVE", use_container_width=True)
    with col_b:
        st.caption("Verifica si hay transmisión en vivo y muestra métricas del post asociado.")

    if consultar:
        with st.spinner("Consultando Facebook LIVE..."):
            try:
                res = requests.get(f"{api_base_url}/facebook/live-video", timeout=30)
                res.raise_for_status()
                data = res.json()
            except Exception as e:
                st.error(f"Error consultando el endpoint: {e}")
                data = None

        if data:
            if not data.get("live"):
                st.warning("No hay transmisión en vivo en este momento.")
            else:
                st.success("¡Transmisión en vivo encontrada!")
                m1, m2, m3, m4 = st.columns(4)
                m1.metric("👍 Reacciones (aprox.)", f"{data.get('likes', 0):,}")
                m2.metric("🔁 Compartidos", f"{data.get('shares', 0):,}")
                m3.metric("🆔 Video ID", data.get("video_id", "-"))
                m4.metric("🗓️ Fecha", _fmt_dt(data.get("created_time")))

                titulo = data.get("title") or "Sin título"
                st.markdown(f"**Título:** {titulo}")
                if data.get("permalink_url"):
                    st.markdown(f"[🔗 Ver en Facebook]({data['permalink_url']})")


    st.subheader("📝 Últimos posts (opcional)")
    c_posts = st.button("📥 Cargar posts", use_container_width=True)
    if c_posts:
        with st.spinner("Cargando posts..."):
            try:
                resp = requests.get(f"{api_base_url}/facebook/page-posts", params={"limit": 10}, timeout=40)
                resp.raise_for_status()
                payload = resp.json()
                items = payload.get("items", [])
                if not items:
                    st.info("No se encontraron posts.")
                else:
                    df = pd.DataFrame(items)
                    if "created_time" in df.columns:
                        df["created_time"] = df["created_time"].map(_fmt_dt)
                    st.dataframe(df, use_container_width=True, hide_index=True)
            except Exception as e:
                st.error(f"Error cargando posts: {e}")
