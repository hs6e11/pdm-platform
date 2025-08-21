# ml_service/models/ensemble_detector.py
import numpy as np
from sklearn.ensemble import IsolationForest
from sklearn.preprocessing import StandardScaler
from tensorflow.keras.models import Sequential
from tensorflow.keras.layers import LSTM, Dense, Dropout
import joblib
from typing import Dict, List, Tuple

class EnsembleAnomalyDetector:
    def __init__(self, machine_id: str):
        self.machine_id = machine_id
        self.models = {
            'isolation_forest': IsolationForest(contamination=0.1, random_state=42),
            'lstm': None,
            'statistical': None
        }
        self.scaler = StandardScaler()
        self.is_trained = False
        
    def prepare_lstm_model(self, input_shape: tuple) -> Sequential:
        """Create LSTM model for time series anomaly detection"""
        model = Sequential([
            LSTM(50, return_sequences=True, input_shape=input_shape),
            Dropout(0.2),
            LSTM(50, return_sequences=False),
            Dropout(0.2),
            Dense(25),
            Dense(1, activation='sigmoid')  # Anomaly probability
        ])
        
        model.compile(optimizer='adam', loss='binary_crossentropy', metrics=['accuracy'])
        return model
    
    def train(self, sensor_data: np.ndarray, anomaly_labels: np.ndarray = None) -> Dict:
        """Train all models in the ensemble"""
        # Prepare data
        scaled_data = self.scaler.fit_transform(sensor_data)
        
        # Train Isolation Forest
        self.models['isolation_forest'].fit(scaled_data)
        
        # Train LSTM if we have enough sequential data
        if len(scaled_data) > 100:
            lstm_data = self.prepare_lstm_data(scaled_data)
            self.models['lstm'] = self.prepare_lstm_model((lstm_data.shape[1], lstm_data.shape[2]))
            
            # If no labels, use isolation forest predictions for LSTM training
            if anomaly_labels is None:
                anomaly_labels = self.models['isolation_forest'].predict(scaled_data)
                anomaly_labels = (anomaly_labels == -1).astype(int)
            
            lstm_labels = self.prepare_lstm_labels(anomaly_labels, lstm_data.shape[0])
            self.models['lstm'].fit(lstm_data, lstm_labels, epochs=50, batch_size=32, verbose=0)
        
        # Train statistical model (moving averages + thresholds)
        self.models['statistical'] = self.train_statistical_model(scaled_data)
        
        self.is_trained = True
        
        return {
            'status': 'trained',
            'models_count': len([m for m in self.models.values() if m is not None]),
            'data_points': len(sensor_data)
        }
    
    def predict(self, sensor_data: np.ndarray) -> Dict:
        """Get ensemble predictions"""
        if not self.is_trained:
            return {'error': 'Models not trained'}
        
        scaled_data = self.scaler.transform(sensor_data)
        predictions = {}
        
        # Isolation Forest prediction
        if self.models['isolation_forest']:
            isolation_pred = self.models['isolation_forest'].decision_function(scaled_data)
            predictions['isolation_forest'] = {
                'anomaly_score': float(np.mean(isolation_pred)),
                'is_anomaly': bool(np.mean(isolation_pred) < 0)
            }
        
        # LSTM prediction
        if self.models['lstm']:
            lstm_data = self.prepare_lstm_data(scaled_data)
            if len(lstm_data) > 0:
                lstm_pred = self.models['lstm'].predict(lstm_data, verbose=0)
                predictions['lstm'] = {
                    'anomaly_probability': float(np.mean(lstm_pred)),
                    'is_anomaly': bool(np.mean(lstm_pred) > 0.5)
                }
        
        # Statistical prediction
        if self.models['statistical']:
            stat_pred = self.predict_statistical(scaled_data)
            predictions['statistical'] = stat_pred
        
        # Ensemble decision (majority vote with confidence weighting)
        ensemble_score = self.calculate_ensemble_score(predictions)
        
        return {
            'machine_id': self.machine_id,
            'predictions': predictions,
            'ensemble_score': ensemble_score,
            'is_anomaly': ensemble_score > 0.6,
            'confidence': min(abs(ensemble_score - 0.5) * 2, 1.0)
        }
    
    def calculate_ensemble_score(self, predictions: Dict) -> float:
        """Calculate weighted ensemble score"""
        scores = []
        weights = {'isolation_forest': 0.4, 'lstm': 0.4, 'statistical': 0.2}
        
        for model_name, pred in predictions.items():
            if 'anomaly_score' in pred:
                # Convert to 0-1 scale
                score = 1 / (1 + np.exp(-pred['anomaly_score']))  # Sigmoid
            elif 'anomaly_probability' in pred:
                score = pred['anomaly_probability']
            else:
                score = 1.0 if pred.get('is_anomaly', False) else 0.0
            
            scores.append(score * weights.get(model_name, 0.33))
        
        return sum(scores)
