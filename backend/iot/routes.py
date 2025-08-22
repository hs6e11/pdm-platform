from fastapi import APIRouter, HTTPException, Depends, Header
from typing import Optional
import logging
from datetime import datetime
import json

from .models import IoTDataPayload
from .database import store_sensor_reading, get_client_machines
from .connection_manager import manager

router = APIRouter()

async def verify_api_key(authorization: Optional[str] = Header(None)):
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing API key")
    
    api_key = authorization.replace("Bearer ", "")
    valid_keys = {"egypt_secure_api_key_2024": "egypt_client_001"}
    
    if api_key not in valid_keys:
        raise HTTPException(status_code=401, detail="Invalid API key")
    
    return valid_keys[api_key]

@router.post("/data/{client_id}")
async def receive_iot_data(
    client_id: str,
    data: IoTDataPayload,
    verified_client: str = Depends(verify_api_key)
):
    try:
        if client_id != verified_client:
            raise HTTPException(status_code=403, detail="Client ID mismatch")
        
        await store_sensor_reading(client_id, data)
        
        # Broadcast via WebSocket
        message = {
            "type": "sensor_update",
            "client_id": client_id,
            "machine_id": data.machine_id,
            "machine_name": data.machine_name,
            "timestamp": data.timestamp,
            "sensors": data.sensors.dict(),
            "location": data.location
        }
        
        await manager.broadcast_to_client(json.dumps(message), client_id)
        
        return {
            "status": "success",
            "message": "Data received",
            "client_id": client_id,
            "machine_id": data.machine_id
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/clients/{client_id}/machines")
async def get_machines(client_id: str):
    try:
        machines = await get_client_machines(client_id)
        return {"client_id": client_id, "machines": machines, "count": len(machines)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/test")
async def test_iot():
    return {
        "status": "ok",
        "message": "IoT API is working!",
        "timestamp": datetime.now().isoformat()
    }
