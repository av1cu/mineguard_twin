import streamlit as st
import requests
import pandas as pd
import plotly.express as px
import time
import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))


st.set_page_config(page_title="Simulation Control", layout="wide")

import os
BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8000")

st.title("⚙️ OpenMines Simulation Control")

st.markdown("""
На этой странице вы можете настроить и запустить симуляцию логистики карьера на базе SimPy среды **OpenMines**.
Вы можете сравнить базовую диспетчеризацию с оптимизированным AI-диспетчером, учитывающим риски безопасности и расход топлива.
""")

# Simulation run helper
def run_simulation(dispatcher_type: str):
    progress_bar = st.progress(0)
    status_text = st.empty()
    
    status_text.text("Инициализация окружения OpenMines на сервере...")
    try:
        # Start on API with speed = 30.0 for quick dashboard run
        r = requests.post(f"{BACKEND_URL}/api/simulation/start?dispatcher={dispatcher_type}&speed=30.0", timeout=2)
        if r.status_code != 200:
            st.error("Не удалось запустить симуляцию на бэкенде.")
            return False
        
        total_ticks = 120
        while True:
            # Poll state
            state_r = requests.get(f"{BACKEND_URL}/api/simulation/state", timeout=1)
            if state_r.status_code != 200:
                break
                
            state = state_r.json()
            tick = state.get("current_tick", 0)
            is_running = state.get("is_running", False)
            
            progress_bar.progress(min(tick / total_ticks, 1.0))
            status_text.text(f"Расчет тика симуляции: {tick} из {total_ticks} (Диспетчер: {dispatcher_type})")
            
            if not is_running or tick >= total_ticks:
                break
            time.sleep(0.1)
            
        status_text.success(f"Симуляция {dispatcher_type} успешно завершена! KPI сохранены в БД.")
        return True
    except Exception as e:
        st.error(f"Ошибка во время работы симулятора: {e}")
        return False

# UI Layout
col1, col2 = st.columns(2)

with col1:
    st.subheader("1. Baseline Scenario (Базовый)")
    st.markdown("""
    * **Диспетчер**: Naive / Fixed Dispatcher
    * **Учет рисков**: Игнорирует осыпи, трещины и закрытые дороги
    * **Контроль водителей**: Не блокирует движение при усталости
    * **Эффективность**: Повышенный простой в очередях и на холостом ходу
    """)
    if st.button("🚀 Запустить Baseline симуляцию", use_container_width=True):
        if run_simulation("NaiveDispatcher"):
            st.success("Базовый прогон завершен!")

with col2:
    st.subheader("2. Optimized Scenario (Оптимизированный)")
    st.markdown("""
    * **Диспетчер**: EnergyAwareSafetyDispatcher
    * **Учет рисков**: Динамический объезд опасных участков
    * **Контроль водителей**: Автоматический останов техники при детекции микросна
    * **Эффективность**: Минимизация простоев и оптимальный расход топлива
    """)
    if st.button("🚀 Запустить Optimized симуляцию", use_container_width=True):
        if run_simulation("SmartDispatcher"):
            st.success("Оптимизированный прогон завершен!")

st.divider()

st.subheader("📊 Сравнение результатов (Baseline vs Optimized)")

# Fetch and display comparison
def fetch_kpis():
    try:
        r = requests.get(f"{BACKEND_URL}/api/simulation/kpi", timeout=2)
        if r.status_code == 200:
            return r.json()
    except Exception:
        pass
    return []

kpis = fetch_kpis()
if kpis:
    df_kpi = pd.DataFrame(kpis)
    
    # Rename columns for presentation
    df_kpi_display = df_kpi.rename(columns={
        "dispatcher_name": "Диспетчер",
        "completed_trips": "Выполнено рейсов",
        "produced_tons": "Добыто руды, тонн",
        "avg_cycle_time": "Время цикла, мин",
        "truck_idle_time": "Время простоя, час",
        "total_fuel": "Расход топлива, л",
        "fuel_per_ton": "Литров на тонну",
        "safety_events_count": "Инциденты безопасности"
    })
    
    st.dataframe(df_kpi_display, use_container_width=True)
    
    # Visual comparison charts
    col_chart1, col_chart2 = st.columns(2)
    
    with col_chart1:
        fig_fuel = px.bar(
            df_kpi, x="dispatcher_name", y="fuel_per_ton",
            title="Эффективность: Расход топлива на тонну руды (л/т)",
            labels={"fuel_per_ton": "Литров на тонну", "dispatcher_name": "Сценарий"},
            color="dispatcher_name",
            color_discrete_map={"NaiveDispatcher": "#ef4444", "SmartDispatcher": "#22c55e"}
        )
        st.plotly_chart(fig_fuel, use_container_width=True)
        
    with col_chart2:
        fig_safety = px.bar(
            df_kpi, x="dispatcher_name", y="safety_events_count",
            title="Безопасность: Количество опасных сближений и рисков",
            labels={"safety_events_count": "Число инцидентов", "dispatcher_name": "Сценарий"},
            color="dispatcher_name",
            color_discrete_map={"NaiveDispatcher": "#ef4444", "SmartDispatcher": "#22c55e"}
        )
        st.plotly_chart(fig_safety, use_container_width=True)

else:
    st.info("Пока нет сохраненных результатов симуляции. Запустите оба сценария выше для сравнения.")
