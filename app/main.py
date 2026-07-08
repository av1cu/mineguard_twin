import streamlit as st

st.set_page_config(
    page_title="MineGuard Twin — Цифровой двойник карьера",
    page_icon="👷",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Premium styling custom CSS
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;600;700&display=swap');
    
    html, body, [class*="css"] {
        font-family: 'Outfit', sans-serif;
    }
    
    .main {
        background: linear-gradient(135deg, #0d0f12 0%, #151922 100%);
        color: #e2e8f0;
    }
    
    h1 {
        background: linear-gradient(90deg, #38bdf8 0%, #3b82f6 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        font-weight: 700;
    }
    
    .stCard {
        background: rgba(30, 41, 59, 0.7);
        border: 1px solid rgba(148, 163, 184, 0.1);
        border-radius: 12px;
        padding: 24px;
        backdrop-filter: blur(10px);
        margin-bottom: 20px;
    }
</style>
""", unsafe_allow_html=True)

st.title("MineGuard Twin ─ AI-Driven Open-Pit Mine Digital Twin")

st.markdown("""
### Цифровой двойник безопасности и эффективности карьера с AI-диспетчером, CV-мониторингом бортов и контролем усталости водителя

MineGuard Twin объединяет симуляцию карьерного транспорта с потоком событий безопасности от камер компьютерного зрения.

#### 🌟 Ключевые возможности:
1. **MineOps Twin**: Пошаговая симуляция движения самосвалов, расчет производственных и энергетических KPI (расход топлива, простои, выбросы) с оптимизацией маршрутов.
2. **Slope/Road CV Monitor**: Выявление опасных геологических аномалий (трещин, оползней, осыпей) на бортах карьера и автоматическое перенаправление техники.
3. **Driver Fatigue CV Monitor**: Контроль состояния водителя в кабине (микросон, закрытие глаз, зевота, телефон) с повышением уровня риска техники до критического.

---

### 🗺️ Карта проекта и навигация:
Используйте боковое меню для переключения между модулями:
* 📊 **01 Dashboard**: Цифровой двойник, интерактивная карта карьера, статусы самосвалов и активные инциденты.
* ⚙️ **02 Simulation**: Запуск и сравнение сценариев Baseline (фиксированные маршруты) и Optimized (умный объезд препятствий и контроль безопасности).
* 🪨 **03 Slope CV**: Инспекция бортов и дорог карьера.
* 👁️ **04 Driver CV**: Видеоаналитика усталости водителей.
* 📋 **05 Events**: Единый центр событий безопасности с кадрами-доказательствами.
""")

st.info("💡 **Демо-сценарий**: Запустите Baseline-симуляцию во вкладке Simulation, выявите трещину на борту в Slope CV, и вы увидите, как система мгновенно среагирует, предложив изменить маршруты техники для предотвращения инцидентов.")
