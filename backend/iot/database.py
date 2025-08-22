import sqlite3
import json
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Any

def get_db_connection():
    conn = sqlite3.connect('pdm_platform.db')
    conn.row_factory = sqlite3.Row
    return conn

async def store_sensor_reading(client_id: str, data):
    conn = get_db_connection()
    try:
        # Update client last seen
        conn.execute(
            "UPDATE iot_clients SET last_seen = CURRENT_TIMESTAMP WHERE client_id = ?",
            (client_id,)
        )
        
        # Insert sensor reading
        conn.execute("""
            INSERT INTO real_sensor_readings (
                client_id, machine_id, machine_name, timestamp, 
                temperature, pressure, vibration, power_consumption,
                spindle_speed, conveyor_speed, efficiency, status,
                location, timezone, raw_data
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            client_id,
            data.machine_id,
            data.machine_name,
            data.timestamp,
            data.sensors.temperature,
            data.sensors.pressure,
            data.sensors.vibration,
            data.sensors.power_consumption,
            data.sensors.spindle_speed,
            data.sensors.conveyor_speed,
            data.sensors.efficiency,
            data.sensors.status,
            data.location,
            data.timezone,
            json.dumps(data.sensors.dict())
        ))
        conn.commit()
    except Exception as e:
        conn.rollback()
        raise
    finally:
        conn.close()

async def get_client_machines(client_id: str) -> List[Dict]:
    conn = get_db_connection()
    try:
        machines = conn.execute("""
            SELECT DISTINCT 
                machine_id,
                machine_name,
                MAX(timestamp) as last_reading,
                temperature,
                pressure,
                vibration,
                power_consumption,
                spindle_speed,
                conveyor_speed,
                efficiency,
                status,
                location
            FROM real_sensor_readings 
            WHERE client_id = ? 
            GROUP BY machine_id
            ORDER BY last_reading DESC
        """, (client_id,)).fetchall()
        
        return [dict(machine) for machine in machines]
    finally:
        conn.close()
