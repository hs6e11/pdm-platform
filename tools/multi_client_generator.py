#!/usr/bin/env python3
"""
Configuration-Based Multi-Client Predictive Maintenance Data Generator
Loads machine configurations from JSON file and generates realistic sensor data
"""

import asyncio
import aiohttp
import json
import random
import time
import os
from datetime import datetime, timezone
import argparse
from typing import Dict, List, Optional, Any
import math
from pathlib import Path

class ConfigurableMachine:
    def __init__(self, machine_config: Dict[str, Any], client_id: str):
        self.id = machine_config["id"]
        self.name = machine_config["name"]
        self.type = machine_config["type"]
        self.client_id = client_id
        self.device_id = machine_config["device_id"]
        
        # Sensor configurations
        sensors = machine_config["sensors"]
        self.temp_base = sensors["temperature"]["base"]
        self.temp_variation = sensors["temperature"]["variation"]
        self.current_base = sensors["current"]["base"]
        self.current_variation = sensors["current"]["variation"]
        self.power_base = sensors["power"]["base"]
        self.power_variation = sensors["power"]["variation"]
        self.vibration_base = sensors["vibration"]["base"]
        self.vibration_variation = sensors["vibration"]["variation"]
        
        # Operational settings
        operational = machine_config["operational"]
        self.status = operational["status"]
        self.health_score = operational["health_score"]
        self.operating_hours = operational["operating_hours"]
        self.weekend_operation = operational["weekend_operation"]
        self.maintenance_schedule = operational["maintenance_schedule"]
        
        # Runtime variables
        self.temp_trend = random.uniform(-0.1, 0.1)  # Gradual temperature drift
        self.last_anomaly_time = 0
        self.wear_accumulation = (100 - self.health_score) / 100

    def is_operational(self, timestamp: datetime) -> bool:
        """Check if machine should be running at given time"""
        if self.status == "offline":
            return False
            
        # Check weekend operation
        if not self.weekend_operation and timestamp.weekday() >= 5:
            return random.random() < 0.2  # 20% chance of weekend operation
            
        # Check operating hours
        current_hour = timestamp.hour
        start_hour, end_hour = self.operating_hours
        
        if start_hour <= end_hour:
            in_hours = start_hour <= current_hour <= end_hour
        else:  # Overnight operation (e.g., 22 to 6)
            in_hours = current_hour >= start_hour or current_hour <= end_hour
            
        if not in_hours:
            return random.random() < 0.1  # 10% chance of off-hours operation
            
        return True

    def simulate_failure_event(self) -> bool:
        """Simulate random failure events based on health score"""
        failure_probability = (100 - self.health_score) * 0.0001  # Scale with health
        return random.random() < failure_probability

    def generate_sensor_reading(self, timestamp: datetime, global_settings: Dict) -> Optional[Dict]:
        """Generate realistic sensor reading"""
        
        if not self.is_operational(timestamp):
            return None
            
        # Time-based factors
        time_factor = time.time() / 3600
        daily_cycle = math.sin((timestamp.hour / 24) * 2 * math.pi)
        
        # Temperature generation with realistic patterns
        temp_noise = random.gauss(0, self.temp_variation * 0.3)
        temp_cycle = daily_cycle * self.temp_variation * 0.2
        temp_wear_effect = self.wear_accumulation * 8
        
        if self.status == "maintenance":
            temp_maintenance_effect = random.gauss(5, 2)
        else:
            temp_maintenance_effect = 0
            
        temperature = (self.temp_base + temp_noise + temp_cycle + 
                      temp_wear_effect + temp_maintenance_effect + self.temp_trend)
        
        # Current with load variations and efficiency
        load_factor = 0.7 + 0.3 * random.random()  # 70-100% load
        current_noise = random.gauss(0, self.current_variation * 0.4)
        current_cycle = daily_cycle * self.current_variation * 0.15
        
        current = max(0.1, (self.current_base * load_factor + 
                           current_noise + current_cycle))
        
        # Power calculation with realistic efficiency curves
        efficiency = 0.85 + 0.1 * random.random() - self.wear_accumulation * 0.1
        power_base = (self.power_base * (current / self.current_base) * 
                     efficiency * load_factor)
        power_noise = random.gauss(0, self.power_variation * 0.3)
        power = max(10, power_base + power_noise)
        
        # Vibration with occasional spikes and wear effects
        vibration_base = (self.vibration_base + 
                         random.gauss(0, self.vibration_variation * 0.3) +
                         self.wear_accumulation * 0.1)
        
        # Simulate vibration spikes
        if random.random() < 0.03:  # 3% chance of spike
            vibration_base += random.uniform(0.1, 0.5)
            
        # Multi-axis vibration
        vibration_x = vibration_base + random.gauss(0, self.vibration_variation * 0.2)
        vibration_y = random.gauss(0, self.vibration_variation * 0.3)
        vibration_z = random.gauss(0, self.vibration_variation * 0.25)
        
        # Simulate failure events
        if self.simulate_failure_event():
            temperature += random.uniform(10, 25)
            vibration_x += random.uniform(0.2, 0.8)
            current *= random.uniform(1.2, 1.8)
            
        # Additional sensor data based on machine type
        additional_sensors = self._generate_type_specific_sensors(temperature, current, power)
        
        # Build payload
        payload = {
            "device_id": self.device_id,
            "machine_id": self.id,
            "client_id": self.client_id,
            "timestamp": timestamp.isoformat(),
            "sensor_data": {
                "temperature_c": round(temperature, 2),
                "current_a": round(current, 3),
                "power_w": round(power, 1),
                "vibration_x_g": round(vibration_x, 3),
                "vibration_y_g": round(vibration_y, 3),
                "vibration_z_g": round(vibration_z, 3),
                **additional_sensors
            },
            "metadata": {
                "machine_type": self.type,
                "machine_name": self.name,
                "status": self.status,
                "health_score": round(self.health_score, 1),
                "load_factor": round(load_factor * 100, 1),
                "maintenance_schedule": self.maintenance_schedule
            }
        }
        
        return payload

    def _generate_type_specific_sensors(self, temperature: float, current: float, power: float) -> Dict:
        """Generate additional sensors based on machine type"""
        additional = {}
        
        if "pump" in self.type.lower():
            # Pumps have pressure and flow rate
            additional["pressure_bar"] = round(2.5 + random.gauss(0, 0.5), 2)
            additional["flow_rate_lpm"] = round(150 + random.gauss(0, 20), 1)
            
        elif "motor" in self.type.lower() or "servo" in self.type.lower():
            # Motors have RPM and torque
            additional["rpm"] = round(1750 + random.gauss(0, 100), 0)
            additional["torque_nm"] = round(power / 100 + random.gauss(0, 5), 2)
            
        elif "compressor" in self.type.lower():
            # Compressors have inlet/outlet pressure
            additional["inlet_pressure_bar"] = round(1.0 + random.gauss(0, 0.1), 2)
            additional["outlet_pressure_bar"] = round(7.5 + random.gauss(0, 1.0), 2)
            
        elif "fan" in self.type.lower():
            # Fans have airflow and static pressure
            additional["airflow_cfm"] = round(2500 + random.gauss(0, 300), 0)
            additional["static_pressure_pa"] = round(250 + random.gauss(0, 50), 1)
            
        elif "robot" in self.type.lower():
            # Robots have position and joint data
            additional["position_x_mm"] = round(random.uniform(-500, 500), 1)
            additional["position_y_mm"] = round(random.uniform(-500, 500), 1)
            additional["position_z_mm"] = round(random.uniform(0, 800), 1)
            
        elif "oven" in self.type.lower():
            # Ovens have humidity and airflow
            additional["humidity_percent"] = round(random.uniform(10, 30), 1)
            additional["exhaust_temp_c"] = round(temperature * 0.7 + random.gauss(0, 5), 1)
            
        elif "chiller" in self.type.lower():
            # Chillers have coolant data
            additional["coolant_temp_c"] = round(temperature - 20 + random.gauss(0, 2), 1)
            additional["coolant_flow_lpm"] = round(80 + random.gauss(0, 10), 1)
            
        return additional

class MultiClientDataGenerator:
    def __init__(self, config_path: str = "machine_config.json", api_base_url: str = "http://localhost:8000"):
        self.config_path = Path(config_path)
        self.api_base_url = api_base_url
        self.session: Optional[aiohttp.ClientSession] = None
        self.machines: List[ConfigurableMachine] = []
        self.config: Dict = {}
        self.running = False
        self.data_points_sent = 0
        
        self.load_configuration()

    def load_configuration(self):
        """Load machine configuration from JSON file"""
        try:
            with open(self.config_path, 'r') as f:
                self.config = json.load(f)
                
            # Load machines from configuration
            for client_id, client_config in self.config["clients"].items():
                for machine_config in client_config["machines"]:
                    machine = ConfigurableMachine(machine_config, client_id)
                    self.machines.append(machine)
                    
            print(f"🏭 Loaded {len(self.machines)} machines across {len(self.config['clients'])} clients")
            
            # Display client summary
            for client_id, client_config in self.config["clients"].items():
                active_count = sum(1 for m in client_config["machines"] 
                                 if m["operational"]["status"] != "offline")
                print(f"   📊 {client_config['name']}: {active_count}/{len(client_config['machines'])} active")
                
        except FileNotFoundError:
            print(f"❌ Configuration file {self.config_path} not found!")
            print("Creating sample configuration file...")
            self.create_sample_config()
            exit(1)
        except json.JSONDecodeError as e:
            print(f"❌ Invalid JSON in configuration file: {e}")
            exit(1)

    def create_sample_config(self):
        """Create a sample configuration file"""
        sample_config = {
            "clients": {
                "sample-client": {
                    "name": "Sample Client",
                    "industry": "Manufacturing",
                    "description": "Sample manufacturing client",
                    "icon": "🏭",
                    "cost_savings_target": 100,
                    "machines": [
                        {
                            "id": "sample-machine-01",
                            "name": "Sample Machine",
                            "type": "Generic Machine",
                            "device_id": "esp32-sample-001",
                            "sensors": {
                                "temperature": {"base": 45, "variation": 8, "unit": "°C"},
                                "current": {"base": 5.0, "variation": 1.0, "unit": "A"},
                                "power": {"base": 1000, "variation": 200, "unit": "W"},
                                "vibration": {"base": 0.05, "variation": 0.3, "unit": "g"}
                            },
                            "operational": {
                                "status": "online",
                                "health_score": 85,
                                "operating_hours": [6, 22],
                                "weekend_operation": true,
                                "maintenance_schedule": "monthly"
                            }
                        }
                    ]
                }
            },
            "global_settings": {
                "data_generation": {
                    "default_interval": 2.0,
                    "anomaly_probability": 0.05,
                    "failure_simulation": true
                },
                "api_settings": {
                    "base_url": "http://localhost:8000",
                    "timeout": 30,
                    "retry_attempts": 3
                }
            }
        }
        
        with open(self.config_path, 'w') as f:
            json.dump(sample_config, f, indent=2)
        print(f"✅ Created sample configuration at {self.config_path}")

    async def __aenter__(self):
        timeout = aiohttp.ClientTimeout(total=self.config["global_settings"]["api_settings"]["timeout"])
        self.session = aiohttp.ClientSession(timeout=timeout)
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()

    async def send_data_point(self, payload: Dict) -> bool:
        """Send a single data point to the API with retry logic"""
        retry_attempts = self.config["global_settings"]["api_settings"]["retry_attempts"]
        
        for attempt in range(retry_attempts):
            try:
                async with self.session.post(
                    f"{self.api_base_url}/api/v1/ingest",
                    json=payload,
                    headers={"Content-Type": "application/json"}
                ) as response:
                    if response.status == 200:
                        return True
                    else:
                        print(f"❌ Error {response.status}: {await response.text()}")
                        
            except Exception as e:
                if attempt == retry_attempts - 1:
                    print(f"❌ Network error after {retry_attempts} attempts: {e}")
                else:
                    await asyncio.sleep(1)  # Brief pause before retry
                    
        return False

    async def generate_and_send_batch(self) -> int:
        """Generate and send data for all operational machines"""
        timestamp = datetime.now(timezone.utc)
        global_settings = self.config["global_settings"]
        sent_count = 0
        
        # Generate data for all machines
        tasks = []
        for machine in self.machines:
            payload = machine.generate_sensor_reading(timestamp, global_settings)
            if payload:  # Only send if machine is operational
                tasks.append(self.send_data_point(payload))
        
        # Send all data points concurrently
        if tasks:
            results = await asyncio.gather(*tasks, return_exceptions=True)
            sent_count = sum(1 for result in results if result is True)
            
        return sent_count

    def print_status_summary(self):
        """Print detailed status summary"""
        print("\n📊 Client Status Summary:")
        for client_id, client_config in self.config["clients"].items():
            client_machines = [m for m in self.machines if m.client_id == client_id]
            online = sum(1 for m in client_machines if m.status == "online")
            maintenance = sum(1 for m in client_machines if m.status == "maintenance")
            offline = sum(1 for m in client_machines if m.status == "offline")
            avg_health = sum(m.health_score for m in client_machines) / len(client_machines)
            
            print(f"   {client_config['icon']} {client_config['name']}:")
            print(f"      🟢 Online: {online} | 🟡 Maintenance: {maintenance} | 🔴 Offline: {offline}")
            print(f"      💊 Avg Health: {avg_health:.1f}% | 🎯 Target Savings: ${client_config['cost_savings_target']}K")

    async def run_continuous(self, interval: float = None):
        """Run continuous data generation"""
        if interval is None:
            interval = self.config["global_settings"]["data_generation"]["default_interval"]
            
        print(f"🚀 Starting multi-client data generation every {interval} seconds...")
        self.print_status_summary()
        print(f"\n🌐 API Endpoint: {self.api_base_url}/api/v1/ingest")
        print("Press Ctrl+C to stop\n")
        
        self.running = True
        last_status_time = time.time()
        
        try:
            while self.running:
                start_time = time.time()
                
                sent_count = await self.generate_and_send_batch()
                self.data_points_sent += sent_count
                
                # Status update
                timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%fZ")
                active_machines = sum(1 for m in self.machines if m.status != "offline")
                
                print(f"✅ {sent_count}/{active_machines} data points sent at {timestamp[11:19]} "
                      f"(Total: {self.data_points_sent})")
                
                # Detailed status every 30 seconds
                if time.time() - last_status_time > 30:
                    self.print_detailed_metrics()
                    last_status_time = time.time()
                
                # Wait for next interval
                elapsed = time.time() - start_time
                sleep_time = max(0, interval - elapsed)
                if sleep_time > 0:
                    await asyncio.sleep(sleep_time)
                    
        except KeyboardInterrupt:
            print(f"\n🛑 Stopping data generation...")
            print(f"📈 Final Statistics:")
            print(f"   • Total data points sent: {self.data_points_sent}")
            print(f"   • Average per machine: {self.data_points_sent / len(self.machines):.1f}")
            print(f"   • Runtime: {time.time() - start_time:.1f} seconds")
            self.running = False

    def print_detailed_metrics(self):
        """Print detailed operational metrics"""
        print("\n📊 Detailed Metrics:")
        for client_id, client_config in self.config["clients"].items():
            client_machines = [m for m in self.machines if m.client_id == client_id]
            print(f"   {client_config['name']}:")
            for machine in client_machines:
                status_emoji = {"online": "🟢", "maintenance": "🟡", "offline": "🔴"}[machine.status]
                print(f"     {status_emoji} {machine.name} ({machine.id}) - {machine.health_score:.1f}% health")

    async def test_single_machine(self, machine_id: str):
        """Test data generation for a single machine"""
        machine = next((m for m in self.machines if m.id == machine_id), None)
        if not machine:
            print(f"❌ Machine {machine_id} not found!")
            return
            
        print(f"🧪 Testing data generation for {machine.name} ({machine_id})")
        
        timestamp = datetime.now(timezone.utc)
        payload = machine.generate_sensor_reading(timestamp, self.config["global_settings"])
        
        if payload:
            print("✅ Generated payload:")
            print(json.dumps(payload, indent=2))
            
            # Send test data
            success = await self.send_data_point(payload)
            if success:
                print("✅ Successfully sent to API")
            else:
                print("❌ Failed to send to API")
        else:
            print("❌ Machine not operational at this time")

    def list_machines(self):
        """List all available machines"""
        print("🏭 Available Machines:")
        for client_id, client_config in self.config["clients"].items():
            print(f"\n   {client_config['icon']} {client_config['name']}:")
            client_machines = [m for m in self.machines if m.client_id == client_id]
            for machine in client_machines:
                status_emoji = {"online": "🟢", "maintenance": "🟡", "offline": "🔴"}[machine.status]
                print(f"     {status_emoji} {machine.id} - {machine.name} ({machine.type})")

async def main():
    parser = argparse.ArgumentParser(description="Configuration-Based Multi-Client PdM Data Generator")
    parser.add_argument("--config", type=str, default="machine_config.json",
                       help="Configuration file path (default: machine_config.json)")
    parser.add_argument("--interval", type=float,
                       help="Data generation interval in seconds (overrides config)")
    parser.add_argument("--url", type=str,
                       help="API base URL (overrides config)")
    parser.add_argument("--clients", nargs="*",
                       help="Specific clients to generate data for (default: all)")
    parser.add_argument("--test-machine", type=str,
                       help="Test data generation for a specific machine ID")
    parser.add_argument("--list-machines", action="store_true",
                       help="List all available machines and exit")
    
    args = parser.parse_args()
    
    # Determine API URL
    api_url = args.url or "http://localhost:8000"
    
    # Create generator
    try:
        generator = MultiClientDataGenerator(args.config, api_url)
        
        # List machines if requested
        if args.list_machines:
            generator.list_machines()
            return
            
        # Filter clients if specified
        if args.clients:
            filtered_clients = {k: v for k, v in generator.config["clients"].items() 
                              if k in args.clients}
            if not filtered_clients:
                print(f"❌ No valid clients found. Available: {list(generator.config['clients'].keys())}")
                return
            generator.config["clients"] = filtered_clients
            # Reload machines
            generator.machines = []
            for client_id, client_config in generator.config["clients"].items():
                for machine_config in client_config["machines"]:
                    machine = ConfigurableMachine(machine_config, client_id)
                    generator.machines.append(machine)
        
        async with generator:
            # Test single machine if requested
            if args.test_machine:
                await generator.test_single_machine(args.test_machine)
                return
                
            # Run continuous generation
            await generator.run_continuous(args.interval)
            
    except Exception as e:
        print(f"❌ Error: {e}")
        return 1

if __name__ == "__main__":
    asyncio.run(main())
