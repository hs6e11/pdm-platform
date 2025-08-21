#!/usr/bin/env python3
"""
Simple script to send sensor data to the PdM platform.
Usage: python send_payload.py --device-id esp32-001 --interval 5
"""

import requests
import json
import time
import random
import argparse
from datetime import datetime, timezone

def generate_sensor_data():
    """Generate realistic sensor data."""
    # Base values with some variation
    temp_base = 50 + random.normalvariate(0, 5)  # 50°C ± 5°C
    current_base = 5 + random.normalvariate(0, 0.5)  # 5A ± 0.5A
    voltage = 230 + random.normalvariate(0, 2)  # 230V ± 2V
    
    return {
        "tenant_id": "demo-tenant-id",
        "site_id": "demo-site-id",
        "device_id": "esp32-001",
        "machine_id": "pump-01",
        "ts": datetime.now(timezone.utc).isoformat(),
        "sensors": {
            "temp": {"c": max(0, temp_base)},
            "electric": {
                "a": max(0, current_base),
                "v": max(0, voltage),
                "w": max(0, current_base * voltage * 0.85)  # Power factor ~0.85
            },
            "accel": {
                "ax_g": random.normalvariate(0, 0.1),
                "ay_g": random.normalvariate(0, 0.1),
                "az_g": random.normalvariate(1, 0.1)  # Gravity + vibration
            }
        },
        "meta": {
            "fw": "1.0.0",
            "rssi": random.randint(-70, -30),
            "batch": False
        }
    }

def send_data(api_url, api_key, interval):
    """Send sensor data at regular intervals."""
    headers = {
        "Content-Type": "application/json",
        "X-API-Key": api_key
    }
    
    print(f"Sending data to {api_url} every {interval} seconds...")
    print("Press Ctrl+C to stop")
    
    try:
        while True:
            payload = generate_sensor_data()
            
            try:
                response = requests.post(
                    f"{api_url}/api/v1/ingest",
                    headers=headers,
                    json=payload,
                    timeout=10
                )
                
                if response.status_code == 200:
                    print(f"✓ Data sent successfully at {payload['ts']}")
                else:
                    print(f"✗ Error {response.status_code}: {response.text}")
                    
            except requests.exceptions.RequestException as e:
                print(f"✗ Request failed: {e}")
            
            time.sleep(interval)
            
    except KeyboardInterrupt:
        print("\n\nStopped sending data.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Send sensor data to PdM platform")
    parser.add_argument("--api-url", default="http://localhost:8000", help="API base URL")
    parser.add_argument("--api-key", default="demo-api-key", help="Device API key")
    parser.add_argument("--interval", type=int, default=5, help="Interval between sends (seconds)")
    
    args = parser.parse_args()
    
    send_data(args.api_url, args.api_key, args.interval)
