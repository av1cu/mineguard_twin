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
    
    status_text.text("Инициализация окружения OpenMines...")
    # Start on API
    try:
        r = requests.post(f"{BACKEND_URL}/api/simulation/start?dispatcher={dispatcher_type}", timeout=2)
        if r.status_code != 200:
            st.error("Не удалось запустить симуляцию на бэкенде.")
            return False
        
        run_data = r.json()
        run_id = run_data["run_id"]
        
        # We will run 100 steps/ticks
        from simulation.openmines_adapter import MineSimulation
        config_path = "simulation/configs/demo_mine.json"
        
        sim = MineSimulation(config_path, dispatcher_name=dispatcher_type)
        
        # Advanced simulation loops
        total_ticks = 120
        for tick in range(1, total_ticks + 1):
            # Advance simulation step
            sim.step()
            
            # Post progress to API
            # For simplicity, we also notify the API to update tick count
            requests.get(f"{BACKEND_URL}/api/simulation/state", timeout=1)
            
            # Update UI
            progress_bar.progress(tick / total_ticks)
            status_text.text(f"Расчет тика симуляции: {tick} из {total_ticks} (Диспетчер: {dispatcher_type})")
            time.sleep(0.02) # Fast forward simulation for presentation
            
        # Save results to DB
        sim.save_run_kpis(run_id)
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
