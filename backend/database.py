import sqlite3
import os

DATABASE_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "mineguard.db")

def get_connection():
    os.makedirs(os.path.dirname(DATABASE_PATH), exist_ok=True)
    conn = sqlite3.connect(DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_connection()
    cursor = conn.cursor()
    
    # 1. events
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS events (
        event_id TEXT PRIMARY KEY,
        event_time TEXT NOT NULL,
        source_module TEXT NOT NULL,
        event_type TEXT NOT NULL,
        risk_level TEXT NOT NULL,
        risk_score INTEGER NOT NULL,
        equipment_id TEXT,
        driver_id TEXT,
        route_id TEXT,
        section_id TEXT,
        description TEXT,
        recommendation TEXT,
        evidence_path TEXT,
        status TEXT DEFAULT 'new'
    )
    """)
    
    # 2. equipment_state
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS equipment_state (
        equipment_id TEXT PRIMARY KEY,
        equipment_type TEXT NOT NULL,
        current_route TEXT,
        current_position_x REAL,
        current_position_y REAL,
        speed REAL,
        status TEXT,
        driver_id TEXT,
        risk_level TEXT DEFAULT 'low',
        fatigue_score INTEGER DEFAULT 0
    )
    """)
    
    # 3. routes
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS routes (
        route_id TEXT PRIMARY KEY,
        route_name TEXT NOT NULL,
        from_point TEXT,
        to_point TEXT,
        distance_km REAL,
        status TEXT DEFAULT 'active',
        risk_level TEXT DEFAULT 'low',
        blocked_reason TEXT
    )
    """)
    
    # 4. simulation_kpi
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS simulation_kpi (
        run_id TEXT PRIMARY KEY,
        dispatcher_name TEXT NOT NULL,
        completed_trips INTEGER DEFAULT 0,
        produced_tons REAL DEFAULT 0.0,
        avg_cycle_time REAL DEFAULT 0.0,
        truck_idle_time REAL DEFAULT 0.0,
        total_fuel REAL DEFAULT 0.0,
        fuel_per_ton REAL DEFAULT 0.0,
        safety_events_count INTEGER DEFAULT 0
    )
    """)
    
    # Pre-populate routes if empty
    cursor.execute("SELECT COUNT(*) FROM routes")
    if cursor.fetchone()[0] == 0:
        default_routes = [
            ("ROUTE-01", "Shovel-01 to Dump-01", "Shovel-01", "Dump-01", 3.2, "active", "low", ""),
            ("ROUTE-02", "Shovel-02 to Dump-01", "Shovel-02", "Dump-01", 4.5, "active", "low", ""),
            ("ROUTE-03", "Shovel-03 to Dump-02", "Shovel-03", "Dump-02", 2.8, "active", "low", ""),
            ("ROUTE-04", "Shovel-01 to Dump-02 (Backup)", "Shovel-01", "Dump-02", 5.1, "active", "low", "")
        ]
        cursor.executemany("""
        INSERT INTO routes (route_id, route_name, from_point, to_point, distance_km, status, risk_level, blocked_reason)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, default_routes)
        
    # Pre-populate equipment_state if empty
    cursor.execute("SELECT COUNT(*) FROM equipment_state")
    if cursor.fetchone()[0] == 0:
        default_equipment = [
            ("TRUCK-01", "OfficalTruck", "ROUTE-01", 0.0, 0.0, 0.0, "idle", "DRIVER-01", "low", 0),
            ("TRUCK-02", "CLTruck", "ROUTE-02", 0.0, 0.0, 0.0, "idle", "DRIVER-02", "low", 0),
            ("TRUCK-03", "XHTruck", "ROUTE-03", 0.0, 0.0, 0.0, "idle", "DRIVER-03", "low", 0),
            ("TRUCK-04", "OfficalTruck", "ROUTE-01", 0.0, 0.0, 0.0, "idle", "DRIVER-04", "low", 0),
            ("TRUCK-05", "CLTruck", "ROUTE-02", 0.0, 0.0, 0.0, "idle", "DRIVER-05", "low", 0)
        ]
        cursor.executemany("""
        INSERT INTO equipment_state (equipment_id, equipment_type, current_route, current_position_x, current_position_y, speed, status, driver_id, risk_level, fatigue_score)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, default_equipment)

    conn.commit()
    conn.close()

if __name__ == "__main__":
    init_db()
    print("Database initialized successfully at:", DATABASE_PATH)
