# backend/ml_service/main.py - FIXED JSON SERIALIZATION
"""
Fixed ML Service - Resolves numpy JSON serialization issues
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
import numpy as np
import pandas as pd
from collections import deque
import json
import traceback

app = FastAPI(title="PdM ML Service", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Try to import ML libraries with fallback
try:
    from sklearn.ensemble import IsolationForest
    from sklearn.preprocessing import StandardScaler
    import joblib
    ML_AVAILABLE = True
except ImportError as e:
    print(f"⚠️ ML libraries not available: {e}")
    ML_AVAILABLE = False

# Global storage
sensor_history = {}
trained_models = {}
baseline_stats = {}

# Configuration
HISTORY_SIZE = 100
TRAINING_SIZE = 30
ANOMALY_THRESHOLD = 0.7

def convert_numpy_types(obj):
    """Convert numpy types to Python native types for JSON serialization"""
    if isinstance(obj, np.integer):
        return int(obj)
    elif isinstance(obj, np.floating):
        return float(obj)
    elif isinstance(obj, np.bool_):
        return bool(obj)
    elif isinstance(obj, np.ndarray):
        return obj.tolist()
    elif isinstance(obj, dict):
        return {key: convert_numpy_types(value) for key, value in obj.items()}
    elif isinstance(obj, list):
        return [convert_numpy_types(item) for item in obj]
    return obj

class SimpleMLEngine:
    def __init__(self):
        self.models = {}
        self.scalers = {}
        
    def safe_extract_features(self, readings: List[Dict]) -> Optional[np.ndarray]:
        """Safely extract features"""
        try:
            if len(readings) < 3:
                return None
                
            df_data = []
            for reading in readings:
                sensor_data = reading.get('sensor_data', {})
                row = {
                    'temperature_c': self._safe_float(sensor_data.get('temperature_c')),
                    'current_a': self._safe_float(sensor_data.get('current_a')),
                    'power_w': self._safe_float(sensor_data.get('power_w')),
                    'vibration_x_g': self._safe_float(sensor_data.get('vibration_x_g'))
                }
                df_data.append(row)
            
            df = pd.DataFrame(df_data)
            df = df.dropna(axis=1, how='all')
            
            if df.empty or len(df.columns) == 0:
                return None
            
            df = df.fillna(df.mean()).fillna(0)
            
            features = []
            for col in df.columns:
                values = df[col]
                if len(values) > 0:
                    features.extend([
                        float(values.mean()),
                        float(values.std()) if len(values) > 1 else 0.0,
                        float(values.min()),
                        float(values.max())
                    ])
            
            return np.array(features).reshape(1, -1) if features else None
            
        except Exception as e:
            print(f"❌ Feature extraction error: {e}")
            return None
    
    def _safe_float(self, value) -> float:
        """Safely convert value to float"""
        try:
            if value is None:
                return 0.0
            return float(value)
        except (ValueError, TypeError):
            return 0.0
    
    def train_model(self, machine_id: str, readings: List[Dict]) -> Dict:
        """Train model with JSON-safe return values"""
        try:
            if not ML_AVAILABLE:
                return {
                    "status": "ml_unavailable",
                    "message": "ML libraries not installed"
                }
            
            if len(readings) < TRAINING_SIZE:
                return {
                    "status": "insufficient_data",
                    "required": int(TRAINING_SIZE),
                    "available": int(len(readings))
                }
            
            print(f"🤖 Training model for {machine_id}...")
            
            # Prepare training data
            training_features = []
            window_size = min(5, len(readings) // 5)
            
            for i in range(len(readings) - window_size + 1):
                batch = readings[i:i+window_size]
                features = self.safe_extract_features(batch)
                if features is not None and not np.isnan(features).any():
                    training_features.append(features.flatten())
            
            if len(training_features) < 5:
                return {
                    "status": "insufficient_features",
                    "features_extracted": int(len(training_features)),
                    "minimum_required": 5
                }
            
            X = np.array(training_features)
            X = np.nan_to_num(X, nan=0.0, posinf=1e6, neginf=-1e6)
            
            # Train model
            scaler = StandardScaler()
            X_scaled = scaler.fit_transform(X)
            
            model = IsolationForest(
                contamination=0.1,
                random_state=42,
                n_estimators=50
            )
            model.fit(X_scaled)
            
            # Store model and scaler
            self.models[machine_id] = model
            self.scalers[machine_id] = scaler
            
            # Calculate baseline stats
            self._calculate_baseline_stats(machine_id, readings)
            
            print(f"✅ Model trained successfully for {machine_id}")
            
            return {
                "status": "success",
                "model_type": "IsolationForest",
                "training_samples": int(len(training_features)),
                "features": int(X.shape[1]),
                "baseline_calculated": bool(machine_id in baseline_stats)
            }
            
        except Exception as e:
            error_msg = f"Training failed: {str(e)}"
            print(f"❌ {error_msg}")
            return {
                "status": "training_error",
                "error": error_msg
            }
    
    def _calculate_baseline_stats(self, machine_id: str, readings: List[Dict]):
        """Calculate baseline statistics"""
        try:
            temps, powers, vibs = [], [], []
            
            for reading in readings:
                sensor_data = reading.get('sensor_data', {})
                temp = self._safe_float(sensor_data.get('temperature_c'))
                power = self._safe_float(sensor_data.get('power_w'))
                vib = self._safe_float(sensor_data.get('vibration_x_g'))
                
                if temp > 0:
                    temps.append(temp)
                if power > 0:
                    powers.append(power)
                if abs(vib) < 10:
                    vibs.append(abs(vib))
            
            baseline_stats[machine_id] = {
                'temperature_mean': float(np.mean(temps)) if temps else 0.0,
                'temperature_std': float(np.std(temps)) if len(temps) > 1 else 0.0,
                'power_mean': float(np.mean(powers)) if powers else 0.0,
                'power_std': float(np.std(powers)) if len(powers) > 1 else 0.0,
                'vibration_mean': float(np.mean(vibs)) if vibs else 0.0,
                'vibration_std': float(np.std(vibs)) if len(vibs) > 1 else 0.0,
                'trained_at': datetime.utcnow().isoformat(),
                'training_samples': int(len(readings))
            }
            
        except Exception as e:
            print(f"⚠️ Baseline calculation error: {e}")
    
    def predict_anomaly(self, machine_id: str, recent_readings: List[Dict]) -> Dict:
        """Predict anomaly with JSON-safe return values"""
        try:
            if not ML_AVAILABLE or machine_id not in self.models:
                return self._simple_rule_based_prediction(machine_id, recent_readings)
            
            features = self.safe_extract_features(recent_readings)
            if features is None:
                return self._simple_rule_based_prediction(machine_id, recent_readings)
            
            # ML prediction
            scaler = self.scalers[machine_id]
            features_scaled = scaler.transform(features)
            
            model = self.models[machine_id]
            anomaly_score = model.decision_function(features_scaled)[0]
            is_anomaly = model.predict(features_scaled)[0] == -1
            
            # Convert to JSON-safe types
            normalized_score = float(max(0, min(1, (0.5 - anomaly_score) * 2)))
            
            # Combine with rule-based checks
            rule_based = self._simple_rule_based_prediction(machine_id, recent_readings)
            final_score = max(normalized_score, rule_based.get('anomaly_score', 0))
            
            return {
                "anomaly_detected": bool(final_score > ANOMALY_THRESHOLD),
                "anomaly_score": round(float(final_score), 3),
                "confidence": round(float(min(1.0, len(recent_readings) / 10)), 3),
                "ml_prediction": bool(is_anomaly),
                "ml_score": round(float(anomaly_score), 3),
                "alerts": rule_based.get('alerts', []),
                "method": "ml_with_rules",
                "timestamp": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            print(f"⚠️ ML prediction error: {e}")
            return self._simple_rule_based_prediction(machine_id, recent_readings)
    
    def _simple_rule_based_prediction(self, machine_id: str, recent_readings: List[Dict]) -> Dict:
        """Rule-based anomaly detection with JSON-safe return values"""
        try:
            if not recent_readings:
                return {
                    "anomaly_detected": False,
                    "anomaly_score": 0.0,
                    "confidence": 0.0,
                    "alerts": [],
                    "method": "rule_based",
                    "timestamp": datetime.utcnow().isoformat()
                }
            
            latest_reading = recent_readings[-1]
            sensor_data = latest_reading.get('sensor_data', {})
            alerts = []
            score = 0.0
            
            # Temperature checks
            temp = self._safe_float(sensor_data.get('temperature_c'))
            if temp > 150:
                alerts.append("Critical temperature detected")
                score = max(score, 0.9)
            elif temp > 100:
                alerts.append("High temperature warning")
                score = max(score, 0.7)
            
            # Vibration checks
            vib = abs(self._safe_float(sensor_data.get('vibration_x_g')))
            if vib > 1.0:
                alerts.append("Critical vibration detected")
                score = max(score, 0.8)
            elif vib > 0.5:
                alerts.append("High vibration warning")
                score = max(score, 0.6)
            
            # Power checks
            power = self._safe_float(sensor_data.get('power_w'))
            if power > 5000 or power < 10:
                alerts.append("Power consumption anomaly")
                score = max(score, 0.5)
            
            return {
                "anomaly_detected": bool(score > ANOMALY_THRESHOLD),
                "anomaly_score": round(float(score), 3),
                "confidence": 0.8,
                "alerts": alerts,
                "method": "rule_based",
                "timestamp": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            print(f"❌ Rule-based prediction error: {e}")
            return {
                "anomaly_detected": False,
                "anomaly_score": 0.0,
                "confidence": 0.0,
                "alerts": [f"Prediction error: {str(e)}"],
                "method": "error_fallback",
                "timestamp": datetime.utcnow().isoformat()
            }

# Initialize ML engine
ml_engine = SimpleMLEngine()

@app.post("/train")
async def train_machine_model(data: Dict[str, Any]):
    """Train ML model"""
    try:
        machine_id = data.get("machine_id")
        readings = data.get("readings", [])
        
        if not machine_id:
            return {"error": "machine_id is required"}
        
        result = ml_engine.train_model(machine_id, readings)
        return convert_numpy_types(result)
        
    except Exception as e:
        return {"error": f"Training failed: {str(e)}", "status": "error"}

@app.post("/predict")
async def predict_anomaly(data: Dict[str, Any]):
    """Predict anomaly"""
    try:
        machine_id = data.get("machine_id")
        readings = data.get("readings", [])
        
        if not machine_id:
            return {"error": "machine_id is required"}
        
        result = ml_engine.predict_anomaly(machine_id, readings)
        return convert_numpy_types(result)
        
    except Exception as e:
        return {"error": f"Prediction failed: {str(e)}", "status": "error"}

@app.post("/ingest")
async def ingest_sensor_data(data: Dict[str, Any]):
    """Ingest sensor data - FIXED JSON SERIALIZATION"""
    try:
        machine_id = data.get("machine_id")
        
        if not machine_id:
            return {"error": "machine_id is required"}
        
        # Initialize history
        if machine_id not in sensor_history:
            sensor_history[machine_id] = deque(maxlen=HISTORY_SIZE)
        
        # Add new reading
        sensor_history[machine_id].append(data)
        
        # Auto-train if needed
        if (machine_id not in ml_engine.models and 
            len(sensor_history[machine_id]) >= TRAINING_SIZE):
            
            print(f"🤖 Auto-training model for {machine_id}")
            train_result = ml_engine.train_model(machine_id, list(sensor_history[machine_id]))
            print(f"Training result: {train_result.get('status')}")
        
        # Predict
        prediction = None
        if machine_id in ml_engine.models and len(sensor_history[machine_id]) >= 3:
            recent_readings = list(sensor_history[machine_id])[-5:]
            prediction = ml_engine.predict_anomaly(machine_id, recent_readings)
        elif len(sensor_history[machine_id]) >= 1:
            recent_readings = list(sensor_history[machine_id])[-1:]
            prediction = ml_engine._simple_rule_based_prediction(machine_id, recent_readings)
        
        # Ensure all return values are JSON-serializable
        result = {
            "status": "success",
            "machine_id": str(machine_id),
            "total_readings": int(len(sensor_history[machine_id])),
            "model_trained": bool(machine_id in ml_engine.models),
            "prediction": convert_numpy_types(prediction) if prediction else None
        }
        
        return result
        
    except Exception as e:
        print(f"❌ Ingest error: {e}")
        print(traceback.format_exc())
        return {"error": f"Ingestion failed: {str(e)}", "status": "error"}

@app.get("/status/{machine_id}")
async def get_machine_status(machine_id: str):
    """Get machine status"""
    try:
        result = {
            "machine_id": str(machine_id),
            "total_readings": int(len(sensor_history.get(machine_id, []))),
            "model_trained": bool(machine_id in ml_engine.models),
            "baseline_stats": baseline_stats.get(machine_id),
            "ml_available": bool(ML_AVAILABLE)
        }
        return convert_numpy_types(result)
    except Exception as e:
        return {"error": f"Status check failed: {str(e)}"}

@app.get("/health")
async def health_check():
    """Health check"""
    return {
        "status": "healthy",
        "service": "PdM ML Service",
        "ml_libraries_available": bool(ML_AVAILABLE),
        "models_loaded": int(len(ml_engine.models)),
        "machines_tracked": int(len(sensor_history)),
        "timestamp": datetime.utcnow().isoformat()
    }

@app.get("/")
async def root():
    return {
        "service": "PdM ML Service",
        "version": "1.0.0",
        "ml_available": bool(ML_AVAILABLE),
        "endpoints": {
            "train": "/train",
            "predict": "/predict", 
            "ingest": "/ingest",
            "status": "/status/{machine_id}",
            "health": "/health"
        }
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)
