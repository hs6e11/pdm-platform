from fastapi import FastAPI, HTTPException, Depends, Header
from fastapi.middleware.cors import CORSMiddleware
from typing import Dict, Any, Optional
from datetime import datetime, timedelta
import aiohttp
import asyncio
from collections import deque
import json
import sqlite3
from pydantic import BaseModel
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# IoT Models
class SensorData(BaseModel):
    temperature: Optional[float] = None
    pressure: Optional[float] = None
    vibration: Optional[float] = None
    power_consumption: Optional[float] = None
    spindle_speed: Optional[int] = None
    conveyor_speed: Optional[float] = None
    efficiency: Optional[float] = None
    status: Optional[str] = "running"

class IoTDataPayload(BaseModel):
    client_id: str
    machine_id: str
    machine_name: str
    timestamp: str
    location: str
    timezone: str
    sensors: SensorData

# FastAPI App
app = FastAPI(title="PdM Platform API", description="Industrial IoT Predictive Maintenance Platform", version="2.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global Data Storage
latest_sensor_data = {}
ml_predictions = {}
machine_history = {}

# Configuration
ML_SERVICE_URL = "http://localhost:8001"
HISTORY_SIZE = 100

# Database Helper Functions
def get_iot_db():
    """Get IoT database connection"""
    try:
        conn = sqlite3.connect('pdm_platform.db')
        conn.row_factory = sqlite3.Row
        return conn
    except Exception as e:
        logger.error(f"Database connection error: {e}")
        raise HTTPException(status_code=500, detail="Database connection failed")

# IoT Authentication
async def verify_iot_key(authorization: Optional[str] = Header(None)):
    """Verify IoT client API key"""
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing API key")
    
    api_key = authorization.replace("Bearer ", "")
    
    # Valid API keys for IoT clients
    valid_keys = {
        "egypt_secure_api_key_2024": "egypt_client_001",
        # Add more client API keys here as needed
    }
    
    if api_key not in valid_keys:
        raise HTTPException(status_code=401, detail="Invalid API key")
    
    return valid_keys[api_key]

# ML Service Helper
async def send_to_ml_service(endpoint: str, data: Dict[str, Any]) -> Optional[Dict]:
    """Send data to ML service and return response"""
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"{ML_SERVICE_URL}/{endpoint}",
                json=data,
                timeout=aiohttp.ClientTimeout(total=5)
            ) as response:
                if response.status == 200:
                    return await response.json()
                else:
                    logger.warning(f"ML service error: {response.status}")
                    return None
    except Exception as e:
        logger.warning(f"ML service unavailable: {e}")
        return None

# ========================================
# IoT API ENDPOINTS
# ========================================

@app.get("/api/iot/test")
async def test_iot_endpoint():
    """Test IoT API functionality"""
    return {
        "status": "working",
        "message": "IoT API is operational!",
        "timestamp": datetime.now().isoformat(),
        "supported_clients": ["egypt_client_001"],
        "endpoints": [
            "GET /api/iot/test",
            "POST /api/iot/data/{client_id}",
            "GET /api/iot/clients/{client_id}/machines",
            "GET /api/iot/clients/{client_id}/status"
        ]
    }

@app.post("/api/iot/data/{client_id}")
async def receive_iot_data(
    client_id: str,
    data: IoTDataPayload,
    verified_client: str = Depends(verify_iot_key)
):
    """Receive real-time IoT data from international clients"""
    if client_id != verified_client:
        raise HTTPException(status_code=403, detail="Client ID mismatch")
    
    conn = get_iot_db()
    try:
        # Update client last seen timestamp
        conn.execute(
            "UPDATE iot_clients SET last_seen = CURRENT_TIMESTAMP WHERE client_id = ?",
            (client_id,)
        )
        
        # Insert sensor reading into IoT table
        conn.execute("""
            INSERT INTO real_sensor_readings (
                client_id, machine_id, machine_name, timestamp, 
                temperature, pressure, vibration, power_consumption,
                spindle_speed, conveyor_speed, efficiency, status,
                location, timezone, raw_data
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            client_id, data.machine_id, data.machine_name, data.timestamp,
            data.sensors.temperature, data.sensors.pressure, data.sensors.vibration,
            data.sensors.power_consumption, data.sensors.spindle_speed,
            data.sensors.conveyor_speed, data.sensors.efficiency,
            data.sensors.status, data.location, data.timezone,
            json.dumps(data.sensors.dict())
        ))
        conn.commit()
        
        # Convert IoT data to ML format for integration with existing ML system
        machine_full_id = f"{client_id}_{data.machine_id}"
        ml_data = {
            "machine_id": machine_full_id,
            "client_id": client_id,
            "sensor_data": {
                "temperature_c": data.sensors.temperature or 0,
                "power_w": (data.sensors.power_consumption or 0) * 1000,  # Convert kW to W
                "vibration_x_g": data.sensors.vibration or 0,
            },
            "metadata": {
                "status": "online" if data.sensors.status == "running" else "offline",
                "health_score": data.sensors.efficiency or 90,
                "location": data.location,
                "machine_name": data.machine_name,
                "timezone": data.timezone
            },
            "timestamp": data.timestamp
        }
        
        # Store in existing ML system format
        latest_sensor_data[machine_full_id] = {
            **ml_data,
            "received_at": datetime.now().isoformat()
        }
        
        # Add to ML training history
        if machine_full_id not in machine_history:
            machine_history[machine_full_id] = deque(maxlen=HISTORY_SIZE)
        machine_history[machine_full_id].append(ml_data)
        
        # Send to ML service for analysis
        ml_result = await send_to_ml_service("ingest", ml_data)
        if ml_result and "prediction" in ml_result:
            ml_predictions[machine_full_id] = ml_result["prediction"]
            
            # Log ML analysis results
            prediction = ml_result["prediction"]
            if prediction.get("anomaly_detected"):
                logger.warning(f"🚨 ANOMALY DETECTED for {client_id}/{data.machine_id}!")
                logger.warning(f"   Anomaly Score: {prediction.get('anomaly_score', 0):.3f}")
        
        # Log successful data ingestion
        logger.info(f"📡 IoT data stored: {client_id}/{data.machine_id}")
        logger.info(f"   🌡️ Temperature: {data.sensors.temperature}°C")
        logger.info(f"   ⚡ Power: {data.sensors.power_consumption}kW")
        logger.info(f"   📍 Location: {data.location}")
        
        return {
            "status": "success",
            "message": "Data stored and analyzed successfully",
            "client_id": client_id,
            "machine_id": data.machine_id,
            "timestamp": datetime.now().isoformat(),
            "ml_analysis": ml_result is not None,
            "anomaly_detected": ml_predictions.get(machine_full_id, {}).get("anomaly_detected", False)
        }
        
    except Exception as e:
        conn.rollback()
        logger.error(f"❌ Error storing IoT data: {e}")
        raise HTTPException(status_code=500, detail=f"Data storage error: {str(e)}")
    finally:
        conn.close()

@app.get("/api/iot/clients/{client_id}/machines")
async def get_iot_client_machines(client_id: str):
    """Get all machines for an IoT client with latest readings"""
    conn = get_iot_db()
    try:
        machines = conn.execute("""
            SELECT DISTINCT 
                machine_id, machine_name, MAX(timestamp) as last_reading,
                temperature, pressure, vibration, power_consumption,
                spindle_speed, conveyor_speed, efficiency, status, location
            FROM real_sensor_readings 
            WHERE client_id = ? 
            GROUP BY machine_id
            ORDER BY last_reading DESC
        """, (client_id,)).fetchall()
        
        # Enhance with ML predictions
        enhanced_machines = []
        for machine in machines:
            machine_dict = dict(machine)
            machine_full_id = f"{client_id}_{machine['machine_id']}"
            
            # Add ML prediction data if available
            if machine_full_id in ml_predictions:
                machine_dict["ml_prediction"] = ml_predictions[machine_full_id]
                machine_dict["anomaly_detected"] = ml_predictions[machine_full_id].get("anomaly_detected", False)
                machine_dict["anomaly_score"] = ml_predictions[machine_full_id].get("anomaly_score", 0)
            
            # Calculate time since last reading
            if machine_dict["last_reading"]:
                try:
                    last_reading_time = datetime.fromisoformat(machine_dict["last_reading"])
                    time_diff = datetime.now() - last_reading_time
                    machine_dict["minutes_since_last_reading"] = int(time_diff.total_seconds() / 60)
                except:
                    machine_dict["minutes_since_last_reading"] = None
            
            enhanced_machines.append(machine_dict)
        
        return {
            "client_id": client_id,
            "machines": enhanced_machines,
            "count": len(enhanced_machines),
            "last_updated": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error getting machines for {client_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        conn.close()

@app.get("/api/iot/clients/{client_id}/status")
async def get_iot_client_status(client_id: str):
    """Get IoT client connection status and health metrics"""
    conn = get_iot_db()
    try:
        # Get client information
        client = conn.execute(
            "SELECT * FROM iot_clients WHERE client_id = ?", (client_id,)
        ).fetchone()
        
        if not client:
            raise HTTPException(status_code=404, detail=f"IoT client '{client_id}' not found")
        
        # Check if client is online (last seen within 5 minutes)
        is_online = False
        minutes_offline = None
        
        if client['last_seen']:
            try:
                last_seen = datetime.fromisoformat(client['last_seen'])
                time_diff = datetime.now() - last_seen
                minutes_offline = int(time_diff.total_seconds() / 60)
                is_online = minutes_offline < 5
            except Exception as e:
                logger.warning(f"Error parsing last_seen time: {e}")
                is_online = False
        
        # Get machine statistics
        machine_stats = conn.execute("""
            SELECT 
                COUNT(DISTINCT machine_id) as total_machines,
                COUNT(CASE WHEN status = 'running' THEN 1 END) as running_machines,
                AVG(temperature) as avg_temperature,
                SUM(power_consumption) as total_power,
                AVG(efficiency) as avg_efficiency,
                MAX(timestamp) as latest_reading
            FROM real_sensor_readings 
            WHERE client_id = ?
        """, (client_id,)).fetchone()
        
        # Count ML anomalies
        anomaly_count = 0
        total_ml_predictions = 0
        for machine_id, prediction in ml_predictions.items():
            if machine_id.startswith(f"{client_id}_"):
                total_ml_predictions += 1
                if prediction.get("anomaly_detected", False):
                    anomaly_count += 1
        
        # Build comprehensive status response
        status_response = {
            "client_id": client_id,
            "company_name": client['company_name'],
            "country": client['country'],
            "timezone": client['timezone'],
            "contact_email": client['contact_email'],
            "is_online": is_online,
            "last_seen": client['last_seen'],
            "minutes_offline": minutes_offline,
            "status": "online" if is_online else "offline",
            "machine_count": machine_stats['total_machines'] or 0,
            "running_machines": machine_stats['running_machines'] or 0,
            "avg_temperature": round(machine_stats['avg_temperature'] or 0, 1),
            "total_power_kw": round(machine_stats['total_power'] or 0, 1),
            "avg_efficiency": round(machine_stats['avg_efficiency'] or 0, 1),
            "latest_reading": machine_stats['latest_reading'],
            "ml_predictions_count": total_ml_predictions,
            "anomaly_count": anomaly_count,
            "health_status": "healthy" if is_online and anomaly_count == 0 else "warning" if is_online else "offline",
            "last_updated": datetime.now().isoformat()
        }
        
        return status_response
        
    except HTTPException:
        raise  # Re-raise HTTP exceptions
    except Exception as e:
        logger.error(f"Error getting status for client {client_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Status check error: {str(e)}")
    finally:
        conn.close()

@app.get("/api/iot/debug/{client_id}")
async def debug_iot_client(client_id: str):
    """Debug endpoint for IoT client troubleshooting"""
    conn = get_iot_db()
    try:
        # Check if client exists
        client = conn.execute(
            "SELECT * FROM iot_clients WHERE client_id = ?", (client_id,)
        ).fetchone()
        
        # Count readings
        reading_count = conn.execute(
            "SELECT COUNT(*) FROM real_sensor_readings WHERE client_id = ?", (client_id,)
        ).fetchone()[0]
        
        # Get latest reading
        latest_reading = conn.execute(
            "SELECT * FROM real_sensor_readings WHERE client_id = ? ORDER BY timestamp DESC LIMIT 1", (client_id,)
        ).fetchone()
        
        # Check ML predictions
        ml_machines = [mid for mid in ml_predictions.keys() if mid.startswith(f"{client_id}_")]
        
        return {
            "client_id": client_id,
            "client_exists": client is not None,
            "client_data": dict(client) if client else None,
            "total_readings": reading_count,
            "latest_reading": dict(latest_reading) if latest_reading else None,
            "ml_predictions_available": len(ml_machines),
            "ml_machine_ids": ml_machines,
            "debug_timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        return {
            "client_id": client_id,
            "error": str(e),
            "debug_timestamp": datetime.now().isoformat()
        }
    finally:
        conn.close()

# ========================================
# EXISTING API ENDPOINTS (Enhanced)
# ========================================

@app.get("/api/v1/health")
async def health():
    """System health check including ML service and IoT clients"""
    # Check ML service health
    ml_status = "unknown"
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(f"{ML_SERVICE_URL}/health", timeout=aiohttp.ClientTimeout(total=3)) as response:
                if response.status == 200:
                    ml_status = "healthy"
                else:
                    ml_status = "error"
    except:
        ml_status = "unavailable"
    
    # Count IoT clients
    iot_clients_count = 0
    iot_online_count = 0
    try:
        conn = get_iot_db()
        iot_clients_count = conn.execute("SELECT COUNT(*) FROM iot_clients WHERE is_active = 1").fetchone()[0]
        
        # Count online clients (last seen within 5 minutes)
        five_minutes_ago = (datetime.now() - timedelta(minutes=5)).isoformat()
        iot_online_count = conn.execute(
            "SELECT COUNT(*) FROM iot_clients WHERE is_active = 1 AND last_seen > ?", 
            (five_minutes_ago,)
        ).fetchone()[0]
        conn.close()
    except Exception as e:
        logger.error(f"Error checking IoT clients: {e}")
    
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "ml_service": ml_status,
        "total_machines": len(latest_sensor_data),
        "ml_predictions_available": len(ml_predictions),
        "iot_clients_total": iot_clients_count,
        "iot_clients_online": iot_online_count,
        "version": "2.0.0"
    }

@app.get("/api/v1/clients")
async def get_clients():
    """Get all clients including static and IoT clients"""
    # Static demo clients
    static_clients = {
        "acme-corp": {
            "name": "ACME Corporation",
            "icon": "🏢",
            "industry": "Manufacturing",
            "description": "Leading manufacturer of industrial equipment",
            "machines": ["acme-pump-01", "acme-motor-02", "acme-comp-03", "acme-fan-04", "acme-mill-05"],
            "type": "static"
        },
        "tech-solutions": {
            "name": "Tech Solutions Inc.",
            "icon": "⚙️",
            "industry": "Industrial Automation", 
            "description": "Advanced industrial automation solutions",
            "machines": ["tech-robot-01", "tech-servo-02", "tech-cnc-03", "tech-laser-04", "tech-press-05"],
            "type": "static"
        },
        "global-motors": {
            "name": "Global Motors Ltd.",
            "icon": "🚗",
            "industry": "Automotive",
            "description": "Automotive manufacturing and assembly",
            "machines": ["gm-engine-01", "gm-weld-02", "gm-paint-03", "gm-press-04", "gm-assembly-05"],
            "type": "static"
        },
        "petro-industries": {
            "name": "Petro Industries",
            "icon": "🛢️",
            "industry": "Oil & Gas",
            "description": "Oil refining and petrochemical processing",
            "machines": ["petro-pump-01", "petro-turbine-02", "petro-comp-03", "petro-reactor-04", "petro-distill-05"],
            "type": "static"
        },
        "food-processing": {
            "name": "Food Processing Co.",
            "icon": "🍎",
            "industry": "Food & Beverage",
            "description": "Food manufacturing and packaging",
            "machines": ["food-mixer-01", "food-oven-02", "food-pack-03", "food-cool-04", "food-belt-05"],
            "type": "static"
        }
    }
    
    # Add IoT clients from database
    try:
        conn = get_iot_db()
        iot_clients = conn.execute("SELECT * FROM iot_clients WHERE is_active = 1").fetchall()
        
        for client in iot_clients:
            # Get machine count and latest activity
            machine_count = conn.execute(
                "SELECT COUNT(DISTINCT machine_id) FROM real_sensor_readings WHERE client_id = ?",
                (client['client_id'],)
            ).fetchone()[0]
            
            # Check online status
            is_online = False
            if client['last_seen']:
                try:
                    last_seen = datetime.fromisoformat(client['last_seen'])
                    is_online = (datetime.now() - last_seen).total_seconds() < 300
                except:
                    pass
            
            # Country to flag mapping
            country_icons = {
                "Egypt": "🇪🇬", "UK": "🇬🇧", "USA": "🇺🇸", "Germany": "🇩🇪", 
                "China": "🇨🇳", "India": "🇮🇳", "Brazil": "🇧🇷", "Canada": "🇨🇦"
            }
            
            static_clients[client['client_id']] = {
                "name": client['company_name'],
                "icon": country_icons.get(client['country'], "🌍"),
                "industry": f"Industrial IoT - {client['country']}",
                "description": f"Real-time IoT monitoring from {client['country']}",
                "machines": [],  # IoT machines are dynamic
                "machine_count": machine_count,
                "country": client['country'],
                "timezone": client['timezone'],
                "type": "iot",
                "is_online": is_online,
                "last_seen": client['last_seen'],
                "contact_email": client['contact_email']
            }
        
        conn.close()
    except Exception as e:
        logger.error(f"Error loading IoT clients: {e}")
    
    return static_clients

@app.get("/api/v1/data/latest")
async def get_latest():
    """Get latest sensor data from all clients with ML predictions"""
    current_time = datetime.utcnow()
    recent_data = []
    
    for machine_id, data in latest_sensor_data.items():
        try:
            received_time = datetime.fromisoformat(data.get("received_at", ""))
            if current_time - received_time <= timedelta(minutes=5):
                enhanced_data = data.copy()
                if machine_id in ml_predictions:
                    enhanced_data["ml_prediction"] = ml_predictions[machine_id]
                recent_data.append(enhanced_data)
        except:
            enhanced_data = data.copy()
            if machine_id in ml_predictions:
                enhanced_data["ml_prediction"] = ml_predictions[machine_id]
            recent_data.append(enhanced_data)
    
    return recent_data

@app.get("/api/v1/clients/{client_id}/summary")
async def get_client_summary(client_id: str):
    """Get comprehensive client summary for both static and IoT clients"""
    # Check if this is an IoT client
    is_iot_client = False
    try:
        conn = get_iot_db()
        iot_client = conn.execute(
            "SELECT * FROM iot_clients WHERE client_id = ?", (client_id,)
        ).fetchone()
        is_iot_client = iot_client is not None
        conn.close()
    except:
        pass
    
    if is_iot_client:
        # IoT client summary
        try:
            conn = get_iot_db()
            
            # Get recent machine data (last 10 minutes)
            machines = conn.execute("""
                SELECT machine_id, temperature, pressure, vibration, power_consumption,
                       efficiency, status, timestamp
                FROM real_sensor_readings 
                WHERE client_id = ? 
                  AND datetime(timestamp) > datetime('now', '-10 minutes')
                GROUP BY machine_id
                HAVING timestamp = MAX(timestamp)
            """, (client_id,)).fetchall()
            
            total_machines = len(machines) if machines else 0
            online_machines = len([m for m in machines if m['status'] == 'running']) if machines else 0
            
            # Calculate metrics
            temps = [m['temperature'] for m in machines if m['temperature'] is not None] if machines else []
            avg_temperature = sum(temps) / len(temps) if temps else 0
            
            power_vals = [m['power_consumption'] for m in machines if m['power_consumption'] is not None] if machines else []
            total_power = sum(power_vals) if power_vals else 0
            
            efficiency_vals = [m['efficiency'] for m in machines if m['efficiency'] is not None] if machines else []
            avg_health = sum(efficiency_vals) / len(efficiency_vals) if efficiency_vals else 100
            
            # Count alerts
            alerts = 0
            if machines:
                for m in machines:
                    if (m['temperature'] and m['temperature'] > 80) or (m['efficiency'] and m['efficiency'] < 70):
                        alerts += 1
            
            # Count ML alerts
            ml_alerts = 0
            anomaly_detected = False
            for machine_id in [f"{client_id}_{m['machine_id']}" for m in machines] if machines else []:
                if machine_id in ml_predictions:
                    prediction = ml_predictions[machine_id]
                    if prediction.get("anomaly_detected", False):
                        ml_alerts += 1
                        anomaly_detected = True
            
            conn.close()
            
            return {
                "client_id": client_id,
                "total_machines": total_machines,
                "online_machines": online_machines,
                "offline_machines": max(0, total_machines - online_machines),
                "avg_temperature": round(avg_temperature, 1),
                "total_power": round(total_power, 1),
                "avg_health_score": round(avg_health, 1),
                "active_alerts": alerts,
                "ml_alerts": ml_alerts,
                "anomaly_detected": anomaly_detected,
                "last_updated": datetime.utcnow().isoformat(),
                "client_type": "iot"
            }
            
        except Exception as e:
            logger.error(f"Error getting IoT client summary: {e}")
            return {
                "client_id": client_id,
                "total_machines": 0,
                "online_machines": 0,
                "offline_machines": 0,
                "avg_temperature": 0,
                "total_power": 0,
                "avg_health_score": 100,
                "active_alerts": 0,
                "ml_alerts": 0,
                "anomaly_detected": False,
                "last_updated": datetime.utcnow().isoformat(),
                "client_type": "iot",
                "error": str(e)
            }
    
    # Static client summary (original logic)
    client_machines = {
        k: v for k, v in latest_sensor_data.items() 
        if v.get("client_id") == client_id
    }
    
    if not client_machines:
        return {
            "client_id": client_id,
            "total_machines": 0,
            "online_machines": 0,
            "offline_machines": 0,
            "avg_temperature": 0,
            "total_power": 0,
            "avg_health_score": 100,
            "active_alerts": 0,
            "ml_alerts": 0,
            "anomaly_detected": False,
            "last_updated": datetime.utcnow().isoformat(),
            "client_type": "static"
        }
    
    total_machines = len(client_machines)
    online_machines = len([
        m for m in client_machines.values() 
        if m.get("metadata", {}).get("status") == "online"
    ])
    
    temperatures = [
        m.get("sensor_data", {}).get("temperature_c", 0) 
        for m in client_machines.values()
    ]
    avg_temperature = sum(temperatures) / len(temperatures) if temperatures else 0
    
    power_values = [
        m.get("sensor_data", {}).get("power_w", 0) 
        for m in client_machines.values()
    ]
    total_power = sum(power_values)
    
    health_scores = [
        m.get("metadata", {}).get("health_score", 100) 
        for m in client_machines.values()
    ]
    avg_health = sum(health_scores) / len(health_scores) if health_scores else 100
    
    alerts = len([
        m for m in client_machines.values() 
        if (m.get("metadata", {}).get("health_score", 100) < 80 or 
            m.get("sensor_data", {}).get("temperature_c", 0) > 80)
    ])
    
    ml_alerts = 0
    anomaly_detected = False
    for machine_id in client_machines.keys():
        if machine_id in ml_predictions:
            prediction = ml_predictions[machine_id]
            if prediction.get("anomaly_detected", False):
                ml_alerts += 1
                anomaly_detected = True
    
    return {
        "client_id": client_id,
        "total_machines": total_machines,
        "online_machines": online_machines,
        "offline_machines": total_machines - online_machines,
        "avg_temperature": round(avg_temperature, 1),
        "total_power": round(total_power, 1),
        "avg_health_score": round(avg_health, 1),
        "active_alerts": alerts,
        "ml_alerts": ml_alerts,
        "anomaly_detected": anomaly_detected,
        "last_updated": datetime.utcnow().isoformat(),
        "client_type": "static"
    }

@app.get("/api/v1/machines/{machine_id}/ml-status")
async def get_machine_ml_status(machine_id: str):
    """Get ML analysis status for a specific machine"""
    ml_status = None
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(f"{ML_SERVICE_URL}/status/{machine_id}") as response:
                if response.status == 200:
                    ml_status = await response.json()
    except:
        pass
    
    return {
        "machine_id": machine_id,
        "latest_prediction": ml_predictions.get(machine_id),
        "ml_service_status": ml_status,
        "total_readings": len(machine_history.get(machine_id, [])),
        "last_updated": latest_sensor_data[machine_id].get("received_at")
    }

@app.post("/api/v1/ingest")
async def ingest(data: Dict[str, Any]):
    """Ingest sensor data for ML analysis (original format)"""
    machine_id = data.get("machine_id")
    if machine_id:
        # Store latest data
        latest_sensor_data[machine_id] = {
            **data, 
            "received_at": datetime.utcnow().isoformat()
        }
        
        # Store in history for ML training
        if machine_id not in machine_history:
            machine_history[machine_id] = deque(maxlen=HISTORY_SIZE)
        machine_history[machine_id].append(data)
        
        # Send to ML service for analysis
        ml_result = await send_to_ml_service("ingest", data)
        
        if ml_result:
            # Store ML prediction
            if "prediction" in ml_result and ml_result["prediction"]:
                ml_predictions[machine_id] = ml_result["prediction"]
                
                # Log ML insights
                prediction = ml_result["prediction"]
                if prediction.get("anomaly_detected"):
                    logger.warning(f"🚨 ANOMALY DETECTED for {machine_id}!")
                    logger.info(f"   Anomaly Score: {prediction.get('anomaly_score', 0):.3f}")
                    logger.info(f"   Confidence: {prediction.get('confidence', 0):.3f}")
                    if prediction.get("alerts"):
                        for alert in prediction["alerts"]:
                            logger.warning(f"   ⚠️ {alert}")
                elif prediction.get("anomaly_score", 0) > 0.5:
                    logger.warning(f"⚠️ Warning for {machine_id}: Anomaly Score {prediction.get('anomaly_score', 0):.3f}")
            
            # Log training status
            if ml_result.get("model_trained"):
                logger.info(f"🤖 ML Model active for {machine_id}")
            elif ml_result.get("total_readings", 0) % 10 == 0:
                logger.info(f"📊 Training data: {ml_result.get('total_readings', 0)} readings for {machine_id}")
    
    # Log the data reception
    sensor_data = data.get("sensor_data", {})
    metadata = data.get("metadata", {})
    
    logger.info(f"📊 Data received for {machine_id}")
    if "temperature_c" in sensor_data:
        logger.info(f"   🌡️ Temperature: {sensor_data['temperature_c']}°C")
    if "power_w" in sensor_data:
        logger.info(f"   ⚡ Power: {sensor_data['power_w']}W")
    if "vibration_x_g" in sensor_data:
        logger.info(f"   📳 Vibration: {sensor_data['vibration_x_g']}g")
    if "health_score" in metadata:
        logger.info(f"   💊 Health: {metadata['health_score']}%")
    
    return {
        "status": "success", 
        "timestamp": datetime.utcnow().isoformat(),
        "ml_analysis": ml_result is not None,
        "anomaly_detected": ml_predictions.get(machine_id, {}).get("anomaly_detected", False)
    }

@app.get("/api/v1/ml/summary")
async def get_ml_summary():
    """Get overall ML system summary"""
    total_machines = len(latest_sensor_data)
    machines_with_models = len([m for m in ml_predictions.keys()])
    anomalies_detected = len([
        m for m, pred in ml_predictions.items() 
        if pred.get("anomaly_detected", False)
    ])
    
    # Get recent anomalies
    recent_anomalies = []
    for machine_id, prediction in ml_predictions.items():
        if prediction.get("anomaly_detected", False):
            recent_anomalies.append({
                "machine_id": machine_id,
                "anomaly_score": prediction.get("anomaly_score", 0),
                "alerts": prediction.get("alerts", []),
                "timestamp": prediction.get("timestamp")
            })
    
    return {
        "total_machines": total_machines,
        "machines_with_ml_models": machines_with_models,
        "current_anomalies": anomalies_detected,
        "ml_coverage_percentage": round((machines_with_models / total_machines * 100) if total_machines > 0 else 0, 1),
        "recent_anomalies": recent_anomalies[:10],
        "last_updated": datetime.utcnow().isoformat()
    }

@app.post("/api/v1/ml/retrain/{machine_id}")
async def retrain_machine_model(machine_id: str):
    """Manually trigger retraining for a specific machine"""
    if machine_id not in machine_history:
        raise HTTPException(status_code=404, detail="No training data available for this machine")
    
    training_data = {
        "machine_id": machine_id,
        "readings": list(machine_history[machine_id])
    }
    
    result = await send_to_ml_service("train", training_data)
    
    if result is None:
        raise HTTPException(status_code=503, detail="ML service unavailable")
    
    return {
        "machine_id": machine_id,
        "training_result": result,
        "timestamp": datetime.utcnow().isoformat()
    }

@app.get("/")
async def root():
    """API root endpoint with system information"""
    # Count active IoT clients
    iot_count = 0
    try:
        conn = get_iot_db()
        iot_count = conn.execute("SELECT COUNT(*) FROM iot_clients WHERE is_active = 1").fetchone()[0]
        conn.close()
    except:
        pass
    
    return {
        "service": "PdM Platform API", 
        "status": "running",
        "version": "2.0.0",
        "features": [
            "Real-time sensor data ingestion",
            "Multi-client dashboard support", 
            "ML-powered anomaly detection",
            "Predictive maintenance insights",
            "International IoT client support",
            "Real-time data from Egypt and other locations"
        ],
        "active_iot_clients": iot_count,
        "total_machines_monitored": len(latest_sensor_data),
        "ml_predictions_available": len(ml_predictions),
        "dashboard_endpoints": {
            "health": "/api/v1/health",
            "clients": "/api/v1/clients", 
            "latest_data": "/api/v1/data/latest",
            "client_summary": "/api/v1/clients/{client_id}/summary"
        },
        "ml_endpoints": {
            "ml_summary": "/api/v1/ml/summary",
            "machine_ml_status": "/api/v1/machines/{machine_id}/ml-status",
            "retrain_model": "/api/v1/ml/retrain/{machine_id}"
        },
        "iot_endpoints": {
            "iot_test": "/api/iot/test",
            "iot_data_ingestion": "/api/iot/data/{client_id}",
            "iot_client_machines": "/api/iot/clients/{client_id}/machines",
            "iot_client_status": "/api/iot/clients/{client_id}/status",
            "iot_debug": "/api/iot/debug/{client_id}"
        },
        "supported_iot_clients": ["egypt_client_001"],
        "last_updated": datetime.utcnow().isoformat()
    }
