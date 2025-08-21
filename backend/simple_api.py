from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from typing import Dict, Any, Optional
from datetime import datetime, timedelta
import aiohttp
import asyncio
from collections import deque
import json

app = FastAPI(title="PdM Platform API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Store latest sensor data and ML results
latest_sensor_data = {}
ml_predictions = {}  # Store ML predictions for each machine
machine_history = {}  # Store recent history for each machine (for ML training)

# Configuration
ML_SERVICE_URL = "http://localhost:8001"
HISTORY_SIZE = 100  # Keep last 100 readings per machine for ML

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
                    print(f"ML service error: {response.status}")
                    return None
    except Exception as e:
        print(f"ML service unavailable: {e}")
        return None

@app.get("/api/v1/health")
async def health():
    # Also check ML service health
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
    
    return {
        "status": "healthy", 
        "timestamp": datetime.utcnow().isoformat(),
        "ml_service": ml_status,
        "total_machines": len(latest_sensor_data),
        "ml_predictions_available": len(ml_predictions)
    }

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
    # Return recent data (last 5 minutes) with ML predictions
    current_time = datetime.utcnow()
    recent_data = []
    
    for machine_id, data in latest_sensor_data.items():
        try:
            received_time = datetime.fromisoformat(data.get("received_at", ""))
            if current_time - received_time <= timedelta(minutes=5):
                # Enhance data with ML predictions
                enhanced_data = data.copy()
                if machine_id in ml_predictions:
                    enhanced_data["ml_prediction"] = ml_predictions[machine_id]
                recent_data.append(enhanced_data)
        except:
            # Include if timestamp parsing fails
            enhanced_data = data.copy()
            if machine_id in ml_predictions:
                enhanced_data["ml_prediction"] = ml_predictions[machine_id]
            recent_data.append(enhanced_data)
    
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
            "ml_alerts": 0,
            "anomaly_detected": False,
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
    
    # Count traditional alerts
    alerts = len([
        m for m in client_machines.values() 
        if (m.get("metadata", {}).get("health_score", 100) < 80 or 
            m.get("sensor_data", {}).get("temperature_c", 0) > 80)
    ])
    
    # Count ML alerts and check for anomalies
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
        "last_updated": datetime.utcnow().isoformat()
    }

@app.get("/api/v1/machines/{machine_id}/ml-status")
async def get_machine_ml_status(machine_id: str):
    """Get ML analysis status for a specific machine"""
    if machine_id not in latest_sensor_data:
        raise HTTPException(status_code=404, detail="Machine not found")
    
    # Get ML status from ML service
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
                    print(f"🚨 ANOMALY DETECTED for {machine_id}!")
                    print(f"   Anomaly Score: {prediction.get('anomaly_score', 0):.3f}")
                    print(f"   Confidence: {prediction.get('confidence', 0):.3f}")
                    if prediction.get("alerts"):
                        for alert in prediction["alerts"]:
                            print(f"   ⚠️ {alert}")
                elif prediction.get("anomaly_score", 0) > 0.5:
                    print(f"⚠️ Warning for {machine_id}: Anomaly Score {prediction.get('anomaly_score', 0):.3f}")
            
            # Log training status
            if ml_result.get("model_trained"):
                print(f"🤖 ML Model active for {machine_id}")
            elif ml_result.get("total_readings", 0) % 10 == 0:  # Log every 10 readings
                print(f"📊 Training data: {ml_result.get('total_readings', 0)} readings for {machine_id}")
    
    # Log the data reception
    sensor_data = data.get("sensor_data", {})
    metadata = data.get("metadata", {})
    
    print(f"📊 Data received for {machine_id}")
    if "temperature_c" in sensor_data:
        print(f"   🌡️  Temperature: {sensor_data['temperature_c']}°C")
    if "power_w" in sensor_data:
        print(f"   ⚡ Power: {sensor_data['power_w']}W")
    if "vibration_x_g" in sensor_data:
        print(f"   📳 Vibration: {sensor_data['vibration_x_g']}g")
    if "health_score" in metadata:
        print(f"   💊 Health: {metadata['health_score']}%")
    
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
        "recent_anomalies": recent_anomalies[:10],  # Last 10 anomalies
        "last_updated": datetime.utcnow().isoformat()
    }

@app.post("/api/v1/ml/retrain/{machine_id}")
async def retrain_machine_model(machine_id: str):
    """Manually trigger retraining for a specific machine"""
    if machine_id not in machine_history:
        raise HTTPException(status_code=404, detail="No training data available for this machine")
    
    # Send training request to ML service
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
    return {
        "service": "PdM Platform API", 
        "status": "running",
        "version": "1.0.0",
        "features": [
            "Real-time sensor data ingestion",
            "Multi-client dashboard support", 
            "ML-powered anomaly detection",
            "Predictive maintenance insights"
        ],
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
        }
    }
