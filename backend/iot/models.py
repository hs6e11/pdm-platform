from pydantic import BaseModel, validator
from typing import Optional, Dict, Any
from datetime import datetime

class SensorData(BaseModel):
    temperature: Optional[float] = None
    pressure: Optional[float] = None
    vibration: Optional[float] = None
    power_consumption: Optional[float] = None
    spindle_speed: Optional[int] = None
    conveyor_speed: Optional[float] = None
    efficiency: Optional[float] = None
    status: Optional[str] = "running"
    
    @validator('temperature')
    def validate_temperature(cls, v):
        if v is not None and (v < -50 or v > 200):
            raise ValueError('Temperature out of valid range (-50 to 200°C)')
        return v

class IoTDataPayload(BaseModel):
    client_id: str
    machine_id: str
    machine_name: str
    timestamp: str
    location: str
    timezone: str
    sensors: SensorData
