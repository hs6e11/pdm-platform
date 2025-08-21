from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from typing import Dict, Any, Optional
from datetime import datetime, timedelta

app = FastAPI(title="PdM Platform API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Store latest sensor data
latest_sensor_data = {}

@app.get("/api/v1/health")
async def health():
    return {"status": "healthy", "timestamp": datetime.utcnow().isoformat()}

@app.get("/api/v1/clients")
async def get_clients():
    return {
        "acme-corp": {
            "name": "ACME Corporation", 
            "icon": "🏢", 
            "industry": "Manufacturing",
            "description": "Leading manufacturer of industrial equipment",
            "machines": ["acme-pump-01", "acme-motor-02", "acme-comp-03", "acme-fan-04", "acme-mill-05"]
        },
        "tech-solutions": {
            "name": "Tech Solutions Inc.", 
            "icon": "⚙️", 
            "industry": "Industrial Automation",
            "description": "Advanced industrial automation solutions",
            "machines": ["tech-robot-01", "tech-servo-02", "tech-cnc-03", "tech-laser-04", "tech-press-05"]
        },
        "global-motors": {
            "name": "Global Motors Ltd.", 
            "icon": "🚗", 
            "industry": "Automotive",
            "description": "Automotive manufacturing and assembly",
            "machines": ["gm-engine-01", "gm-weld-02", "gm-paint-03", "gm-press-04", "gm-assembly-05"]
        },
        "petro-industries": {
            "name": "Petro Industries", 
            "icon": "🛢️", 
            "industry": "Oil & Gas",
            "description": "Oil refining and petrochemical processing",
            "machines": ["petro-pump-01", "petro-turbine-02", "petro-comp-03", "petro-reactor-04", "petro-distill-05"]
        },
        "food-processing": {
            "name": "Food Processing Co.", 
            "icon": "🍎", 
            "industry": "Food & Beverage", 
            "description": "Food manufacturing and packaging",
            "machines": ["food-mixer-01", "food-oven-02", "food-pack-03", "food-cool-04", "food-belt-05"]
        }
    }

@app.get("/api/v1/data/latest")
async def get_latest():
    # Return recent data (last 5 minutes)
    current_time = datetime.utcnow()
    recent_data = []
    
    for machine_id, data in latest_sensor_data.items():
        try:
            received_time = datetime.fromisoformat(data.get("received_at", ""))
            if current_time - received_time <= timedelta(minutes=5):
                recent_data.append(data)
        except:
            recent_data.append(data)  # Include if timestamp parsing fails
    
    return recent_data

@app.get("/api/v1/clients/{client_id}/summary")
async def get_client_summary(client_id: str):
    # Filter data for this client
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
            "last_updated": datetime.utcnow().isoformat()
        }
    
    # Calculate summary statistics
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
    
    # Count alerts
    alerts = len([
        m for m in client_machines.values() 
        if (m.get("metadata", {}).get("health_score", 100) < 80 or 
            m.get("sensor_data", {}).get("temperature_c", 0) > 80)
    ])
    
    return {
        "client_id": client_id,
        "total_machines": total_machines,
        "online_machines": online_machines,
        "offline_machines": total_machines - online_machines,
        "avg_temperature": round(avg_temperature, 1),
        "total_power": round(total_power, 1),
        "avg_health_score": round(avg_health, 1),
        "active_alerts": alerts,
        "last_updated": datetime.utcnow().isoformat()
    }

@app.post("/api/v1/ingest")
async def ingest(data: Dict[str, Any]):
    machine_id = data.get("machine_id")
    if machine_id:
        latest_sensor_data[machine_id] = {
            **data, 
            "received_at": datetime.utcnow().isoformat()
        }
    
    # Log the data reception
    sensor_data = data.get("sensor_data", {})
    print(f"📊 Data received for {machine_id}")
    if "temperature_c" in sensor_data:
        print(f"   🌡️  Temperature: {sensor_data['temperature_c']}°C")
    if "power_w" in sensor_data:
        print(f"   ⚡ Power: {sensor_data['power_w']}W")
    
    return {"status": "success", "timestamp": datetime.utcnow().isoformat()}

@app.get("/")
async def root():
    return {
        "service": "PdM Platform API", 
        "status": "running",
        "version": "1.0.0",
        "dashboard_endpoints": {
            "health": "/api/v1/health",
            "clients": "/api/v1/clients", 
            "latest_data": "/api/v1/data/latest",
            "client_summary": "/api/v1/clients/{client_id}/summary"
        }
    }
