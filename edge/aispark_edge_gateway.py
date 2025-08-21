# edge/aispark_edge_gateway.py
import asyncio
import json
import sqlite3
from datetime import datetime, timedelta
import requests
import numpy as np
from typing import Dict, List
import logging

class AISPARKEdgeGateway:
    """
    Lightweight edge computing gateway for factory deployment
    Runs on Raspberry Pi or industrial PC at factory site
    """
    
    def __init__(self, config_file="edge_config.json"):
        self.config = self.load_config(config_file)
        self.local_db = sqlite3.connect('edge_cache.db')
        self.setup_local_storage()
        self.cloud_connection = True
        self.local_models = {}
        
    def load_config(self, config_file):
        """Load edge gateway configuration"""
        default_config = {
            "gateway_id": "edge_001",
            "cloud_endpoint": "https://api.aispark.ai",
            "api_key": "your_api_key",
            "local_processing": True,
            "sync_interval": 30,  # seconds
            "offline_mode": True,
            "protocols": {
                "mqtt": {"enabled": True, "broker": "localhost", "port": 1883},
                "modbus": {"enabled": True, "devices": []},
                "opcua": {"enabled": False, "server": ""}
            }
        }
        
        try:
            with open(config_file, 'r') as f:
                return {**default_config, **json.load(f)}
        except FileNotFoundError:
            return default_config
    
    def setup_local_storage(self):
        """Setup local SQLite database for offline operation"""
        cursor = self.local_db.cursor()
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS sensor_readings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                machine_id TEXT NOT NULL,
                timestamp TEXT NOT NULL,
                sensor_type TEXT NOT NULL,
                value REAL NOT NULL,
                synced INTEGER DEFAULT 0
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS local_alerts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                machine_id TEXT NOT NULL,
                alert_type TEXT NOT NULL,
                severity TEXT NOT NULL,
                message TEXT NOT NULL,
                timestamp TEXT NOT NULL,
                synced INTEGER DEFAULT 0
            )
        ''')
        
        self.local_db.commit()
    
    async def process_sensor_data_locally(self, sensor_data: Dict) -> Dict:
        """Process sensor data on the edge for real-time decisions"""
        machine_id = sensor_data['machine_id']
        
        # Store locally first
        await self.store_locally(sensor_data)
        
        # Load local model if available
        if machine_id not in self.local_models:
            await self.load_local_model(machine_id)
        
        # Run local anomaly detection
        anomaly_result = await self.detect_anomaly_locally(sensor_data)
        
        # Generate immediate alerts if needed
        if anomaly_result['is_anomaly'] and anomaly_result['confidence'] > 0.8:
            await self.generate_local_alert(machine_id, anomaly_result)
        
        # Try to sync with cloud (non-blocking)
        asyncio.create_task(self.sync_with_cloud())
        
        return anomaly_result
    
    async def detect_anomaly_locally(self, sensor_data: Dict) -> Dict:
        """Lightweight anomaly detection on edge device"""
        machine_id = sensor_data['machine_id']
        
        # Get recent readings for this machine
        recent_readings = await self.get_recent_readings(machine_id, hours=24)
        
        if len(recent_readings) < 10:
            return {'is_anomaly': False, 'confidence': 0.0, 'reason': 'insufficient_data'}
        
        # Simple statistical anomaly detection (fast for edge)
        current_values = [
            sensor_data.get('temperature', 0),
            sensor_data.get('vibration', 0),
            sensor_data.get('power', 0)
        ]
        
        historical_values = np.array([[r[3] for r in recent_readings]])  # Simplified
        
        # Z-score based detection
        mean_vals = np.mean(historical_values, axis=0)
        std_vals = np.std(historical_values, axis=0)
        
        z_scores = []
        for i, current_val in enumerate(current_values):
            if std_vals[i] > 0:
                z_score = abs((current_val - mean_vals[i]) / std_vals[i])
                z_scores.append(z_score)
        
        max_z_score = max(z_scores) if z_scores else 0
        is_anomaly = max_z_score > 3.0  # 3-sigma rule
        confidence = min(max_z_score / 5.0, 1.0)  # Normalize confidence
        
        return {
            'is_anomaly': is_anomaly,
            'confidence': confidence,
            'z_score': max_z_score,
            'processing_location': 'edge',
            'timestamp': datetime.utcnow().isoformat()
        }
    
    async def generate_local_alert(self, machine_id: str, anomaly_result: Dict):
        """Generate immediate alert for critical anomalies"""
        alert = {
            'machine_id': machine_id,
            'alert_type': 'anomaly_detected',
            'severity': 'critical' if anomaly_result['confidence'] > 0.9 else 'warning',
            'message': f"Anomaly detected with {anomaly_result['confidence']:.2%} confidence",
            'timestamp': datetime.utcnow().isoformat(),
            'source': 'edge_gateway'
        }
        
        # Store alert locally
        cursor = self.local_db.cursor()
        cursor.execute('''
            INSERT INTO local_alerts 
            (machine_id, alert_type, severity, message, timestamp)
            VALUES (?, ?, ?, ?, ?)
        ''', (alert['machine_id'], alert['alert_type'], 
              alert['severity'], alert['message'], alert['timestamp']))
        self.local_db.commit()
        
        # Send immediate notification (email, SMS, etc.)
        await self.send_immediate_notification(alert)
        
        logging.warning(f"Local alert generated: {alert}")
    
    async def sync_with_cloud(self):
        """Sync local data with cloud when connection available"""
        try:
            # Check cloud connectivity
            response = requests.get(f"{self.config['cloud_endpoint']}/health", timeout=5)
            if response.status_code != 200:
                self.cloud_connection = False
                return
            
            self.cloud_connection = True
            
            # Sync unsynced sensor readings
            await self.sync_sensor_readings()
            
            # Sync unsynced alerts
            await self.sync_alerts()
            
            # Download updated models if available
            await self.sync_models()
            
        except Exception as e:
            self.cloud_connection = False
            logging.error(f"Cloud sync failed: {e}")
    
    async def sync_sensor_readings(self):
        """Upload unsynced sensor readings to cloud"""
        cursor = self.local_db.cursor()
        cursor.execute('SELECT * FROM sensor_readings WHERE synced = 0 LIMIT 1000')
        unsynced_readings = cursor.fetchall()
        
        if not unsynced_readings:
            return
        
        # Batch upload to cloud
        readings_data = []
        for reading in unsynced_readings:
            readings_data.append({
                'machine_id': reading[1],
                'timestamp': reading[2],
                'sensor_type': reading[3],
                'value': reading[4]
            })
        
        try:
            response = requests.post(
                f"{self.config['cloud_endpoint']}/api/sensor-readings/batch",
                json={'readings': readings_data},
                headers={'Authorization': f"Bearer {self.config['api_key']}"},
                timeout=30
            )
            
            if response.status_code == 200:
                # Mark as synced
                reading_ids = [r[0] for r in unsynced_readings]
                cursor.execute(f'''
                    UPDATE sensor_readings 
                    SET synced = 1 
                    WHERE id IN ({','.join(['?'] * len(reading_ids))})
                ''', reading_ids)
                self.local_db.commit()
                
                logging.info(f"Synced {len(unsynced_readings)} sensor readings")
                
        except Exception as e:
            logging.error(f"Failed to sync sensor readings: {e}")
