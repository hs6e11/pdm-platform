# backend/iot_gateway/mqtt_client.py
import paho.mqtt.client as mqtt
import json
import asyncio
from datetime import datetime
from app.services.sensor_service import SensorService

class MQTTGateway:
    def __init__(self, broker_host="localhost", broker_port=1883):
        self.client = mqtt.Client()
        self.client.on_connect = self.on_connect
        self.client.on_message = self.on_message
        self.sensor_service = SensorService()
        
    def on_connect(self, client, userdata, flags, rc):
        print(f"Connected to MQTT broker with result code {rc}")
        # Subscribe to all machine topics
        client.subscribe("aispark/machines/+/sensors/+")
        client.subscribe("factory/+/machine/+/data")
        
    async def on_message(self, client, userdata, msg):
        try:
            topic_parts = msg.topic.split('/')
            payload = json.loads(msg.payload.decode())
            
            # Parse machine ID and sensor type from topic
            if "aispark" in topic_parts:
                machine_id = topic_parts[2]
                sensor_type = topic_parts[4]
            else:
                machine_id = f"{topic_parts[1]}_{topic_parts[3]}"
                sensor_type = "multi"
            
            # Process sensor data
            await self.process_sensor_data(machine_id, sensor_type, payload)
            
        except Exception as e:
            print(f"Error processing MQTT message: {e}")
    
    async def process_sensor_data(self, machine_id, sensor_type, data):
        # Standardize data format
        sensor_reading = {
            "machine_id": machine_id,
            "sensor_type": sensor_type,
            "timestamp": datetime.utcnow(),
            "temperature": data.get("temperature"),
            "vibration": data.get("vibration"), 
            "power": data.get("power"),
            "pressure": data.get("pressure"),
            "raw_data": data
        }
        
        # Send to ML service for anomaly detection
        await self.sensor_service.process_reading(sensor_reading)
