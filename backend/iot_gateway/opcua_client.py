# backend/iot_gateway/opcua_client.py
from asyncua import Client, ua
import asyncio
import json
from datetime import datetime

class OPCUAGateway:
    def __init__(self, server_url="opc.tcp://localhost:4840"):
        self.server_url = server_url
        self.client = None
        
    async def connect_and_monitor(self):
        """Connect to OPC-UA server and start monitoring"""
        self.client = Client(url=self.server_url)
        
        try:
            await self.client.connect()
            print(f"Connected to OPC-UA server: {self.server_url}")
            
            # Get root node
            root = self.client.get_root_node()
            
            # Find all machine nodes
            machines = await self.discover_machines(root)
            
            # Subscribe to all machine variables
            for machine in machines:
                await self.subscribe_to_machine(machine)
                
        except Exception as e:
            print(f"OPC-UA connection error: {e}")
            
    async def discover_machines(self, root_node):
        """Auto-discover machine nodes in OPC-UA server"""
        machines = []
        try:
            # Navigate to typical industrial paths
            paths_to_check = [
                ["Objects", "Machines"],
                ["Objects", "Factory", "Equipment"],
                ["Objects", "Production", "Lines"]
            ]
            
            for path in paths_to_check:
                try:
                    current_node = root_node
                    for segment in path:
                        current_node = await current_node.get_child(segment)
                    
                    # Get all child machines
                    children = await current_node.get_children()
                    machines.extend(children)
                    
                except:
                    continue
                    
        except Exception as e:
            print(f"Machine discovery error: {e}")
            
        return machines
    
    async def subscribe_to_machine(self, machine_node):
        """Subscribe to all variables of a machine"""
        try:
            machine_name = await machine_node.read_display_name()
            print(f"Monitoring machine: {machine_name}")
            
            # Get all variables
            variables = await self.get_machine_variables(machine_node)
            
            # Create subscription
            handler = MachineDataHandler(machine_name, self.sensor_service)
            subscription = await self.client.create_subscription(500, handler)
            
            # Subscribe to all variables
            for var in variables:
                await subscription.subscribe_data_change(var)
                
        except Exception as e:
            print(f"Subscription error: {e}")

class MachineDataHandler:
    def __init__(self, machine_name, sensor_service):
        self.machine_name = machine_name
        self.sensor_service = sensor_service
        
    async def datachange_notification(self, node, val, data):
        """Handle data changes from OPC-UA"""
        try:
            variable_name = await node.read_display_name()
            
            # Map OPC-UA variables to our sensor types
            sensor_mapping = {
                "Temperature": "temperature",
                "Vibration": "vibration", 
                "Power": "power",
                "Pressure": "pressure",
                "Speed": "speed"
            }
            
            sensor_type = sensor_mapping.get(variable_name.Text, "other")
            
            reading = {
                "machine_id": self.machine_name.Text,
                "sensor_type": sensor_type,
                "value": val,
                "timestamp": datetime.utcnow(),
                "source": "opcua"
            }
            
            await self.sensor_service.process_reading(reading)
            
        except Exception as e:
            print(f"Data handling error: {e}")
