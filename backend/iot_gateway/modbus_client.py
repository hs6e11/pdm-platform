# backend/iot_gateway/modbus_client.py
from pymodbus.client.sync import ModbusTcpClient, ModbusSerialClient
from pymodbus.constants import Endian
from pymodbus.payload import BinaryPayloadDecoder
import asyncio
import time

class ModbusGateway:
    def __init__(self, config_file="modbus_config.json"):
        self.devices = self.load_config(config_file)
        self.clients = {}
        
    def load_config(self, config_file):
        """Load Modbus device configuration"""
        # Example configuration
        return [
            {
                "device_id": "plc_001",
                "type": "tcp",
                "host": "192.168.1.100",
                "port": 502,
                "registers": {
                    "temperature": {"address": 40001, "type": "float"},
                    "vibration": {"address": 40003, "type": "float"},
                    "power": {"address": 40005, "type": "float"}
                }
            },
            {
                "device_id": "sensor_node_001", 
                "type": "rtu",
                "port": "/dev/ttyUSB0",
                "baudrate": 9600,
                "slave_id": 1,
                "registers": {
                    "temperature": {"address": 30001, "type": "int16"},
                    "humidity": {"address": 30002, "type": "int16"}
                }
            }
        ]
    
    async def start_monitoring(self):
        """Start monitoring all Modbus devices"""
        for device in self.devices:
            if device["type"] == "tcp":
                client = ModbusTcpClient(device["host"], port=device["port"])
            else:
                client = ModbusSerialClient(
                    method='rtu',
                    port=device["port"],
                    baudrate=device["baudrate"]
                )
            
            if client.connect():
                self.clients[device["device_id"]] = client
                asyncio.create_task(self.poll_device(device, client))
            
    async def poll_device(self, device, client):
        """Continuously poll a Modbus device"""
        while True:
            try:
                readings = {}
                
                for sensor_name, register_info in device["registers"].items():
                    value = await self.read_register(
                        client, 
                        register_info["address"],
                        register_info["type"],
                        device.get("slave_id", 1)
                    )
                    readings[sensor_name] = value
                
                # Send to processing
                sensor_reading = {
                    "machine_id": device["device_id"],
                    "timestamp": datetime.utcnow(),
                    "source": "modbus",
                    **readings
                }
                
                await self.sensor_service.process_reading(sensor_reading)
                
                # Poll every 2 seconds
                await asyncio.sleep(2)
                
            except Exception as e:
                print(f"Modbus polling error for {device['device_id']}: {e}")
                await asyncio.sleep(5)  # Wait before retry
    
    async def read_register(self, client, address, data_type, slave_id=1):
        """Read a register from Modbus device"""
        try:
            if data_type == "float":
                result = client.read_holding_registers(address, 2, unit=slave_id)
                decoder = BinaryPayloadDecoder.fromRegisters(
                    result.registers, 
                    Endian.Big
                )
                return decoder.decode_32bit_float()
            
            elif data_type == "int16":
                result = client.read_holding_registers(address, 1, unit=slave_id)
                return result.registers[0]
                
        except Exception as e:
            print(f"Register read error: {e}")
            return None
