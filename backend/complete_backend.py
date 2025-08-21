from fastapi import FastAPI, Header
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
import time
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
import json

app = FastAPI(title='PdM Platform API', version='1.0.0')

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=['*'],
    allow_credentials=True,
    allow_methods=['*'],
    allow_headers=['*'],
)

class SensorData(BaseModel):
    temp: Optional[Dict[str, float]] = None
    electric: Optional[Dict[str, float]] = None
    accel: Optional[Dict[str, float]] = None

class ReadingPayload(BaseModel):
    tenant_id: str
    site_id: str
    device_id: str
    machine_id: str
    ts: str
    sensors: SensorData
    meta: Optional[Dict[str, Any]] = None

@app.get('/health')
def health():
    return {'status': 'healthy', 'timestamp': time.time(), 'version': '1.0.0'}

@app.get('/')
def root():
    return {'service': 'PdM Platform API', 'version': '1.0.0', 'status': 'operational'}

@app.post('/api/v1/ingest')
def ingest_data(payload: ReadingPayload, x_api_key: Optional[str] = Header(None)):
    print(f'📊 Received data from device {payload.device_id} for machine {payload.machine_id}')
    if payload.sensors.temp:
        print(f'   🌡️  Temperature: {payload.sensors.temp["c"]}°C')
    if payload.sensors.electric:
        print(f'   ⚡ Current: {payload.sensors.electric.get("a", 0)}A, Power: {payload.sensors.electric.get("w", 0)}W')
    if payload.sensors.accel:
        print(f'   📳 Vibration: X={payload.sensors.accel.get("ax_g", 0):.3f}g')
    
    return {
        'success': True,
        'message': 'Data ingested successfully',
        'device_id': payload.device_id,
        'machine_id': payload.machine_id,
        'timestamp': payload.ts,
        'readings_stored': 1
    }

@app.get('/api/v1/machines')
def get_machines():
    return [
        {'id': 'pump-01', 'name': 'Main Water Pump', 'status': 'online', 'health_score': 0.85},
        {'id': 'motor-02', 'name': 'Conveyor Motor', 'status': 'online', 'health_score': 0.92}
    ]

if __name__ == '__main__':
    uvicorn.run(app, host='0.0.0.0', port=8000, log_level='info')
