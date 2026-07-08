import streamlit as st
import requests
import pandas as pd
import os

st.set_page_config(page_title="Event Center Log", layout="wide")

BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8000")

st.title("📋 Единый центр событий безопасности (Event Center)")
st.markdown("""
Централизованный журнал событий от модулей симуляции логистики (MineOps), мониторинга бортов (Slope CV) и состояния водителей (Driver CV).
""")

# Fetch events
def fetch_events():
    try:
        r = requests.get(f"{BACKEND_URL}/api/events", timeout=2)
        if r.status_code == 200:
            return r.json()
    except Exception:
        pass
    return []

events = fetch_events()

if not events:
    st.info("В журнале событий пока нет записей. Создайте события на страницах Slope CV или Driver CV.")
else:
    # Convert to DataFrame
    df = pd.DataFrame(events)
    
    # Filter controls in sidebar
    st.sidebar.header("Фильтрация событий")
    
    modules = ["Все"] + list(df["source_module"].unique())
    selected_module = st.sidebar.selectbox("Источник события:", modules)
    
    risks = ["Все"] + list(df["risk_level"].unique())
    selected_risk = st.sidebar.selectbox("Критичность:", risks)
    
    # Filter data
    filtered_df = df.copy()
    if selected_module != "Все":
        filtered_df = filtered_df[filtered_df["source_module"] == selected_module]
    if selected_risk != "Все":
        filtered_df = filtered_df[filtered_df["risk_level"] == selected_risk]
        
    # Visual Log table
    st.subheader(f"Журнал инцидентов (Показано: {len(filtered_df)})")
    
    display_cols = ["event_id", "event_time", "source_module", "event_type", "risk_level", "risk_score", "equipment_id", "status"]
    
    # Format and present
    st.dataframe(
        filtered_df[display_cols].rename(columns={
            "event_id": "ID",
            "event_time": "Время",
            "source_module": "Модуль",
            "event_type": "Тип",
            "risk_level": "Риск",
            "risk_score": "Баллы",
            "equipment_id": "Техника",
            "status": "Статус"
        }),
        use_container_width=True
    )
    
    # Detail viewing section
    st.divider()
    st.subheader("🔍 Детальный просмотр инцидента")
    
    event_ids = list(filtered_df["event_id"])
    selected_evt_id = st.selectbox("Выберите ID события для просмотра подробностей:", event_ids)
    
    if selected_evt_id:
        evt = filtered_df[filtered_df["event_id"] == selected_evt_id].iloc[0]
        
        col_det, col_img = st.columns(2)
        
        with col_det:
            st.markdown(f"### Событие: **{evt['event_type'].upper()}**")
            st.markdown(f"**ID:** `{evt['event_id']}` | **Время:** `{evt['event_time']}`")
            st.markdown(f"**Критичность:** `{evt['risk_level'].upper()}` (Оценка: `{evt['risk_score']} / 100`)")
            st.markdown(f"**Ответственный модуль:** `{evt['source_module']}`")
            
            if evt['equipment_id']:
                st.markdown(f"**Техника:** `{evt['equipment_id']}` (Водитель: `{evt['driver_id']}`)")
            if evt['route_id']:
                st.markdown(f"**Маршрут / Участок:** `{evt['route_id']}` (Секция: `{evt['section_id']}`)")
                
            st.markdown("#### Описание:")
            st.info(evt['description'])
            
            st.markdown("#### Рекомендации по устранению:")
            st.warning(evt['recommendation'])
            
            st.markdown(f"**Текущий статус обработки:** `{evt['status'].upper()}`")
            
            # Action button to acknowledge or resolve
            if evt['status'] == 'new':
                if st.button("Принять в работу / Подтвердить устранение", type="primary"):
                    r = requests.post(f"{BACKEND_URL}/api/events/{evt['event_id']}/status", json={"status": "resolved"})
                    if r.status_code == 200:
                        st.success("Статус события изменен на RESOLVED!")
                        time.sleep(1)
                        st.rerun()
            else:
                st.info("Инцидент обработан диспетчером.")
                
        with col_img:
            st.markdown("### 🖼️ Evidence (Кадр-доказательство)")
            
            evidence_path = evt['evidence_path']
            if evidence_path and os.path.exists(evidence_path):
                try:
                    img = Image.open(evidence_path)
                    st.image(img, use_container_width=True, caption=f"Кадр события: {evt['event_id']}")
                except Exception as e:
                    st.error(f"Не удалось прочитать изображение: {e}")
            else:
                st.info("Нет доступного кадра-доказательства для данного типа инцидента.")
