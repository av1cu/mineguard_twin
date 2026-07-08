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

st.write("---")
st.header("🔮 Моделирование What-if сценариев")
st.markdown("""
Сценарное моделирование позволяет запустить альтернативную копию симуляции с измененными параметрами 
(отключение техники, блокировка дорог, изменение скорости или производительности экскаваторов) 
без влияния на основную симуляцию. Сравните результаты с базовым (Baseline) и оптимизированным (Optimized) прогонами.
""")

# Setup What-if inputs
col_s1, col_s2, col_s3 = st.columns(3)

with col_s1:
    scenario_type = st.selectbox(
        "Выберите тип сценария:",
        [
            "Отключение самосвала",
            "Перекрытие маршрута",
            "Уменьшение скорости самосвала",
            "Увеличение времени загрузки экскаватора"
        ]
    )
    dispatcher_type = st.selectbox("Алгоритм диспетчеризации для сценария:", ["NaiveDispatcher", "SmartDispatcher"])

with col_s2:
    if scenario_type == "Отключение самосвала":
        disabled_truck = st.selectbox("Выберите самосвал для отключения:", ["TRUCK-01", "TRUCK-02", "TRUCK-03", "TRUCK-04", "TRUCK-05"])
    elif scenario_type == "Перекрытие маршрута":
        blocked_route = st.selectbox("Выберите маршрут для перекрытия:", ["ROUTE-01", "ROUTE-02", "ROUTE-03", "ROUTE-04"])
    elif scenario_type == "Уменьшение скорости самосвала":
        reduced_speed_truck = st.selectbox("Выберите самосвал:", ["TRUCK-01", "TRUCK-02", "TRUCK-03", "TRUCK-04", "TRUCK-05"])
        reduced_speed_val = st.slider("Новая скорость самосвала (км/ч):", 1.0, 20.0, 5.0, step=1.0)
    elif scenario_type == "Увеличение времени загрузки экскаватора":
        increased_load_shovel = st.selectbox("Выберите экскаватор:", ["Shovel-01", "Shovel-02", "Shovel-03"])
        increased_load_val = st.slider("Время цикла загрузки (мин):", 1.0, 10.0, 5.0, step=0.5)

with col_s3:
    st.markdown("<br>", unsafe_allow_html=True)
    run_whatif = st.button("🚀 Запустить What-if сценарий", use_container_width=True)

if run_whatif:
    # Build payload
    payload = {"dispatcher": dispatcher_type}
    if scenario_type == "Отключение самосвала":
        payload["disabled_truck"] = disabled_truck
    elif scenario_type == "Перекрытие маршрута":
        payload["blocked_route"] = blocked_route
    elif scenario_type == "Уменьшение скорости самосвала":
        payload["reduced_speed_truck"] = reduced_speed_truck
        payload["reduced_speed_value"] = reduced_speed_val
    elif scenario_type == "Увеличение времени загрузки экскаватора":
        payload["increased_load_shovel"] = increased_load_shovel
        payload["increased_load_value"] = increased_load_val

    with st.spinner("Моделирование альтернативного сценария..."):
        try:
            r = requests.post(f"{BACKEND_URL}/api/scenario/run", json=payload, timeout=5)
            if r.status_code == 200:
                st.success("Альтернативный сценарий смоделирован успешно!")
                st.session_state["whatif_result"] = r.json()
            else:
                st.error(f"Не удалось запустить сценарий: {r.text}")
        except Exception as e:
            st.error(f"Ошибка при подключении к бэкенду: {e}")

# If we have a scenario result, display comparison
if "whatif_result" in st.session_state:
    w = st.session_state["whatif_result"]
    st.subheader("📊 Сравнение KPI: Базовый vs Оптимизированный vs What-if")
    
    # Let's collect DB KPIs
    db_kpis = fetch_kpis()
    baseline_kpi = next((k for k in db_kpis if k["dispatcher_name"] == "NaiveDispatcher"), None)
    optimized_kpi = next((k for k in db_kpis if k["dispatcher_name"] == "SmartDispatcher"), None)
    
    def get_val(kpi_dict, key, default="Нет данных"):
        if not kpi_dict:
            return default
        val = kpi_dict.get(key)
        if isinstance(val, float):
            return round(val, 2)
        return val

    # Prepare DataFrame
    comparison_data = {
        "Показатель KPI": [
            "Добыто руды (тонн)",
            "Выполнено рейсов",
            "Общий расход топлива (л)",
            "Среднее время цикла (мин)",
            "Общее время простоя (ч)"
        ],
        "Baseline (Naive)": [
            get_val(baseline_kpi, "produced_tons"),
            get_val(baseline_kpi, "completed_trips"),
            get_val(baseline_kpi, "total_fuel"),
            get_val(baseline_kpi, "avg_cycle_time"),
            get_val(baseline_kpi, "truck_idle_time")
        ],
        "Optimized (Smart)": [
            get_val(optimized_kpi, "produced_tons"),
            get_val(optimized_kpi, "completed_trips"),
            get_val(optimized_kpi, "total_fuel"),
            get_val(optimized_kpi, "avg_cycle_time"),
            get_val(optimized_kpi, "truck_idle_time")
        ],
        "What-if Scenario": [
            round(w.get("produced_tons", 0.0), 2),
            w.get("completed_trips", 0),
            round(w.get("total_fuel", 0.0), 2),
            round(w.get("average_cycle_time", 0.0), 2),
            round(w.get("idle_time", 0.0), 2)
        ]
    }
    
    df_compare = pd.DataFrame(comparison_data)
    st.table(df_compare)
    
    # Detail scenario info
    details = w.get("scenario_details", {})
    st.info(f"Параметры What-if сценария: {details} | Диспетчер: {w.get('dispatcher')}")
