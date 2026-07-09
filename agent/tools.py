"""
Инструменты (tools) агента-диспетчера.

Разделены на две категории по важному архитектурному ограничению (ТЗ §16,
Decision Support System, не Decision Making System):

1. READ-ONLY инструменты — агент может вызывать их свободно и многократно
   в цикле рассуждений (get_equipment, get_events, get_routes, get_kpi,
   get_predictive_risks, run_what_if). Они не изменяют состояние системы.

2. PROPOSAL-инструменты (propose_*) — агент может только СФОРМУЛИРОВАТЬ
   предложение опасного действия (остановка техники, блокировка маршрута).
   Эти функции ничего не пишут в БД — они лишь возвращают структурированный
   объект, который попадает в поле `proposed_actions` ответа API. Реальное
   применение действия выполняется отдельными существующими (или новыми,
   но explicit) эндпоинтами backend/api.py только по нажатию кнопки
   «Применить» диспетчером на фронтенде.

Модуль намеренно не импортирует и не модифицирует ничего в backend/*Non
кроме чтения через get_connection — существующая архитектура не меняется,
агент работает поверх неё.
"""
from __future__ import annotations

import os
import sys
from typing import Any, Dict, List, Optional

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.database import get_connection

_CONFIG_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "simulation", "configs", "demo_mine.json"
)


# --- READ-ONLY TOOLS ---------------------------------------------------

def get_equipment() -> List[Dict[str, Any]]:
    """Текущее состояние всей техники (грузовики): позиция, скорость, статус,
    уровень риска, показатель усталости водителя."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM equipment_state")
    rows = [dict(r) for r in cursor.fetchall()]
    conn.close()
    return rows


def get_events(
    limit: int = 20,
    source_module: Optional[str] = None,
    equipment_id: Optional[str] = None,
    route_id: Optional[str] = None,
    risk_level: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """Последние события безопасности/логистики, с опциональной фильтрацией
    по модулю-источнику, технике, маршруту или уровню риска."""
    conn = get_connection()
    cursor = conn.cursor()
    query = "SELECT * FROM events WHERE 1=1"
    params: List[Any] = []
    if source_module:
        query += " AND source_module = ?"
        params.append(source_module)
    if equipment_id:
        query += " AND equipment_id = ?"
        params.append(equipment_id)
    if route_id:
        query += " AND route_id = ?"
        params.append(route_id)
    if risk_level:
        query += " AND risk_level = ?"
        params.append(risk_level)
    query += " ORDER BY event_time DESC LIMIT ?"
    params.append(limit)
    cursor.execute(query, params)
    rows = [dict(r) for r in cursor.fetchall()]
    conn.close()
    return rows


def get_routes() -> List[Dict[str, Any]]:
    """Состояние всех маршрутов: статус (active/blocked), уровень риска,
    причина блокировки."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM routes")
    rows = [dict(r) for r in cursor.fetchall()]
    conn.close()
    return rows


def get_kpi() -> List[Dict[str, Any]]:
    """Сохранённые KPI по завершённым запускам симуляции (тонны, топливо,
    цикл, простой) — для сравнения диспетчеров/периодов."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM simulation_kpi")
    rows = [dict(r) for r in cursor.fetchall()]
    conn.close()
    return rows


def get_predictive_risks(lookahead_seconds: float = 5.0) -> List[Dict[str, Any]]:
    """Прогнозируемые риски столкновения/опасного сближения техники по
    текущей телеметрии (см. simulation/predictive_safety.py)."""
    from simulation.predictive_safety import PredictiveSafety

    trucks = get_equipment()
    ps = PredictiveSafety(safe_threshold=8.0)
    try:
        return ps.analyze_telemetry(trucks, lookahead_seconds=lookahead_seconds)
    except Exception as exc:  # noqa: BLE001
        return [{"error": str(exc)}]


def run_what_if(
    dispatcher: str = "NaiveDispatcher",
    disabled_truck: Optional[str] = None,
    blocked_route: Optional[str] = None,
    reduced_speed_truck: Optional[str] = None,
    reduced_speed_value: float = 5.0,
    increased_load_shovel: Optional[str] = None,
    increased_load_value: float = 5.0,
) -> Dict[str, Any]:
    """Запускает изолированный прогон симуляции со сценарием (не влияет на
    БД и текущий "живой" прогон — scenario runs никогда не пишутся в
    simulation_kpi/equipment_state, см. MineSimulation.step()/save_run_kpis()
    guard на `if not self.scenario`). Возвращает KPI прогона."""
    from simulation.openmines_adapter import MineSimulation

    scenario: Dict[str, Any] = {}
    if disabled_truck:
        scenario["disabled_truck"] = disabled_truck
    if blocked_route:
        scenario["blocked_route"] = blocked_route
    if reduced_speed_truck:
        scenario["reduced_speed_truck"] = reduced_speed_truck
        scenario["reduced_speed_value"] = reduced_speed_value
    if increased_load_shovel:
        scenario["increased_load_shovel"] = increased_load_shovel
        scenario["increased_load_value"] = increased_load_value

    sim = MineSimulation(_CONFIG_PATH, dispatcher_name=dispatcher, scenario=scenario)
    completed_trips = sim.completed_trips
    produced_tons = sim.produced_tons
    total_fuel = sim.total_fuel
    avg_cycle_time = (sim.truck_idle_time * 60 + 20) / max(completed_trips, 1)
    idle_time = sim.truck_idle_time

    return {
        "dispatcher": dispatcher,
        "scenario_details": scenario,
        "produced_tons": float(produced_tons),
        "completed_trips": int(completed_trips),
        "total_fuel": float(total_fuel),
        "average_cycle_time": float(avg_cycle_time),
        "idle_time": float(idle_time),
    }


def get_baseline_kpi(dispatcher: str = "NaiveDispatcher") -> Dict[str, Any]:
    """Прогон без изменений (baseline) — используется для сравнения с
    what-if сценарием ("что будет ЕСЛИ" против "как есть сейчас")."""
    return run_what_if(dispatcher=dispatcher)


READ_ONLY_TOOLS = {
    "get_equipment": get_equipment,
    "get_events": get_events,
    "get_routes": get_routes,
    "get_kpi": get_kpi,
    "get_predictive_risks": get_predictive_risks,
    "run_what_if": run_what_if,
    "get_baseline_kpi": get_baseline_kpi,
}

# Человекочитаемое описание инструментов для системного промпта.
TOOL_DESCRIPTIONS = """\
- get_equipment() — состояние всей техники (позиция, скорость, статус, risk_level, fatigue_score).
- get_events(limit=20, source_module=None, equipment_id=None, route_id=None, risk_level=None) — последние события.
- get_routes() — состояние маршрутов (active/blocked, risk_level, blocked_reason).
- get_kpi() — сохранённые KPI по прогонам симуляции.
- get_predictive_risks(lookahead_seconds=5.0) — прогноз риска столкновения по телеметрии.
- run_what_if(dispatcher="NaiveDispatcher", disabled_truck=None, blocked_route=None, reduced_speed_truck=None, reduced_speed_value=5.0, increased_load_shovel=None, increased_load_value=5.0) — прогон сценария "что если".
- get_baseline_kpi(dispatcher="NaiveDispatcher") — базовый прогон без изменений, для сравнения с what-if.
"""


# --- PROPOSAL BUILDERS (ничего не пишут в БД) --------------------------

def propose_block_route(route_id: str, reason: str) -> Dict[str, Any]:
    return {"type": "block_route", "route_id": route_id, "reason": reason,
            "label": f"Заблокировать {route_id}"}


def propose_unblock_route(route_id: str, reason: str = "") -> Dict[str, Any]:
    return {"type": "unblock_route", "route_id": route_id, "reason": reason,
            "label": f"Разблокировать {route_id}"}


def propose_stop_equipment(equipment_id: str, reason: str) -> Dict[str, Any]:
    return {"type": "stop_equipment", "equipment_id": equipment_id, "reason": reason,
            "label": f"Остановить {equipment_id}"}


def propose_resume_equipment(equipment_id: str, reason: str = "") -> Dict[str, Any]:
    return {"type": "resume_equipment", "equipment_id": equipment_id, "reason": reason,
            "label": f"Возобновить движение {equipment_id}"}


def propose_replace_driver(equipment_id: str, driver_id: Optional[str], reason: str) -> Dict[str, Any]:
    return {"type": "replace_driver", "equipment_id": equipment_id, "driver_id": driver_id,
            "reason": reason, "label": f"Заменить водителя на {equipment_id}"}


PROPOSAL_DESCRIPTIONS = """\
Опасные действия НЕЛЬЗЯ выполнять напрямую — только предложить в поле proposed_actions
финального ответа (диспетчер сам нажимает «Применить» в интерфейсе):
- {"type": "block_route", "route_id": "...", "reason": "..."}
- {"type": "unblock_route", "route_id": "...", "reason": "..."}
- {"type": "stop_equipment", "equipment_id": "...", "reason": "..."}
- {"type": "resume_equipment", "equipment_id": "...", "reason": "..."}
- {"type": "replace_driver", "equipment_id": "...", "driver_id": "...", "reason": "..."}
"""
