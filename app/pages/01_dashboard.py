import streamlit as st
import requests
import pandas as pd
import plotly.graph_objects as go
import time

st.set_page_config(page_title="Digital Twin Dashboard", layout="wide")

st.markdown("""
<style>
    .metric-card {
        background: rgba(30, 41, 59, 0.6);
        border: 1px solid rgba(255, 255, 255, 0.05);
        border-radius: 8px;
        padding: 15px;
        text-align: center;
    }
    .metric-value {
        font-size: 24px;
        font-weight: bold;
        color: #38bdf8;
    }
    .metric-label {
        font-size: 12px;
        color: #94a3b8;
        text-transform: uppercase;
    }
</style>
""", unsafe_allow_html=True)

import os
BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8000")

st.title("📊 MineGuard Digital Twin Dashboard")

# Initialize session state for auto-refresh
if "autorefresh" not in st.session_state:
    st.session_state.autorefresh = False

# Sidebar control
with st.sidebar:
    st.header("🎛️ Панель Диспетчера")
    if st.button("🔄 Начать мониторинг"):
        st.session_state.autorefresh = True
    if st.button("⏹️ Остановить мониторинг"):
        st.session_state.autorefresh = False

# Layout split
col_map, col_info = st.columns([2, 1])

# Fetch data function
def fetch_sim_state():
    try:
        r = requests.get(f"{BACKEND_URL}/api/simulation/state", timeout=1)
        if r.status_code == 200:
            return r.json()
    except Exception:
        pass
    return None

def fetch_recommendations():
    try:
        r = requests.get(f"{BACKEND_URL}/api/recommendations", timeout=1)
        if r.status_code == 200:
            return r.json()
    except Exception:
        pass
    return []

# Process recommendations
recs = fetch_recommendations()
if recs:
    st.warning(f"⚠️ Обнаружено активных предупреждений: {len(recs)}")
    for rec in recs:
        with st.expander(f"🚨 {rec['event_type'].upper()} ({rec['risk_level'].upper()}) - {rec['id']}", expanded=True):
            st.write(f"**Описание:** {rec['description']}")
            st.write(f"**Рекомендация:** {rec['recommendation']}")
            if st.button("Принять и исправить", key=f"accept_{rec['id']}"):
                requests.post(f"{BACKEND_URL}/api/recommendations/{rec['id']}/accept")
                st.rerun()

# Real-time update loop container
map_placeholder = col_map.empty()
kpi_placeholder = col_info.empty()

# Mine layout coordinates
POINTS = {
    "DemoChargingSite": [0.0, 0.0],
    "Shovel-01": [10.0, 20.0],
    "Shovel-02": [-15.0, 30.0],
    "Shovel-03": [5.0, -25.0],
    "Dump-01": [40.0, 0.0],
    "Dump-02": [-40.0, -10.0]
}

def draw_digital_twin(sim_data):
    fig = go.Figure()
    
    # 1. Draw static roads (routes)
    routes = sim_data.get("routes", []) if sim_data else []
    for r in routes:
        # Get start/end points
        r_id = r["route_id"]
        from_pt = r["from_point"]
        to_pt = r["to_point"]
        
        p1 = POINTS.get(from_pt, [0, 0])
        p2 = POINTS.get(to_pt, [0, 0])
        
        # Color based on route status
        color = "red" if r["status"] == "blocked" else "rgba(148, 163, 184, 0.5)"
        width = 4 if r["status"] == "blocked" else 2
        
        fig.add_trace(go.Scatter(
            x=[p1[0], p2[0]], y=[p1[1], p2[1]],
            mode="lines",
            line=dict(color=color, width=width),
            name=f"{r_id} ({r['status']})",
            hoverinfo="text",
            hovertext=f"Маршрут: {r_id}<br>Дистанция: {r['distance_km']} км<br>Статус: {r['status']}<br>Риск: {r['risk_level']}"
        ))
        
    # 2. Draw Shovels & Dumps
    for name, coords in POINTS.items():
        symbol = "triangle-up" if "Shovel" in name else "square"
        if name == "DemoChargingSite": symbol = "circle"
        
        fig.add_trace(go.Scatter(
            x=[coords[0]], y=[coords[1]],
            mode="markers+text",
            marker=dict(size=14, symbol=symbol, color="#38bdf8" if "Shovel" in name else "#e2e8f0"),
            text=[name], textposition="top center",
            name=name,
            showlegend=False
        ))

    # 3. Draw active trucks
    trucks = sim_data.get("trucks", []) if sim_data else []
    for t in trucks:
        tx, ty = t.get("current_position_x", 0.0), t.get("current_position_y", 0.0)
        
        # Color-code by risk level
        t_risk = t.get("risk_level", "low")
        t_color = "green"
        if t_risk == "medium": t_color = "orange"
        elif t_risk == "high": t_color = "red"
        elif t_risk == "critical": t_color = "purple"
        
        fig.add_trace(go.Scatter(
            x=[tx], y=[ty],
            mode="markers+text",
            marker=dict(size=12, color=t_color, symbol="triangle-right"),
            text=[t["equipment_id"]], textposition="bottom center",
            name=t["equipment_id"],
            hoverinfo="text",
            hovertext=f"Самосвал: {t['equipment_id']}<br>Статус: {t['status']}<br>Маршрут: {t['current_route']}<br>Скорость: {t['speed']} км/ч<br>Уровень Риска: {t_risk}<br>Усталость: {t['fatigue_score']}%"
        ))

    fig.update_layout(
        title="Mine Pit & Road Network Map (Digital Twin)",
        xaxis=dict(range=[-55, 55], showgrid=False, zeroline=False),
        yaxis=dict(range=[-35, 45], showgrid=False, zeroline=False),
        width=800, height=600,
        plot_bgcolor="#0d0f12",
        paper_bgcolor="#0d0f12",
        font_color="#e2e8f0",
        margin=dict(l=20, r=20, t=40, b=20)
    )
    return fig

# Render single state
state = fetch_sim_state()

# Plotly map rendering
with map_placeholder.container():
    st.plotly_chart(draw_digital_twin(state), use_container_width=True, key="live_map")
    
# KPI metrics rendering
with kpi_placeholder.container():
    st.markdown("### 📈 Текущие показатели:")
    if state:
        st.markdown(f"**Текущий тик симуляции:** `{state['current_tick']} / {state['max_ticks']}`")
        st.markdown(f"**Тип диспетчера:** `{state['dispatcher']}`")
        
        # Display detailed truck states
        st.markdown("#### Состояние техники:")
        df_trucks = pd.DataFrame(state["trucks"])
        if not df_trucks.empty:
            st.dataframe(df_trucks[["equipment_id", "status", "current_route", "risk_level", "fatigue_score"]], use_container_width=True)
    else:
        st.info("Симуляция не запущена. Перейдите во вкладку Simulation для запуска.")

# Auto-refresh loop via rerun
if st.session_state.autorefresh:
    time.sleep(1.0)
    st.rerun()
