from fastapi import FastAPI
from pydantic import BaseModel
from typing import List, Dict
import numpy as np
from datetime import datetime

app = FastAPI(title="PdM ML Service", version="1.0.0")

class InferenceRequest(BaseModel):
    machine_id: str
    readings: List[Dict[str, float]]
    model_version: str = "latest"

class InferenceResponse(BaseModel):
    machine_id: str
    anomaly_score: float
    is_anomalous: bool
    confidence: float
    model_version: str
    timestamp: datetime

@app.get("/health")
async def health_check():
    return {"status": "healthy", "timestamp": datetime.now()}

@app.post("/inference/anomaly", response_model=InferenceResponse)
async def predict_anomaly(request: InferenceRequest):
    # Placeholder ML inference
    anomaly_score = np.random.random()
    
    return InferenceResponse(
        machine_id=request.machine_id,
        anomaly_score=anomaly_score,
        is_anomalous=anomaly_score > 0.7,
        confidence=0.8,
        model_version="v1.0",
        timestamp=datetime.now()
    )
