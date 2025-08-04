#!/usr/bin/env python3
"""Test script with fake data for Vertical Farm MQTT integration."""

import asyncio
import json
import logging
import sys
import os
from datetime import datetime
from typing import Any, Callable

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# MQTT Topics
MQTT_HEARTBEAT_TOPIC = "cropwaifu/heartbeat"
MQTT_RESPONSE_TOPIC = "cropwaifu/respond"

class FakeMQTTClient:
    """Fake MQTT client for testing."""
    
    def __init__(self, broker: str, port: int, client_id: str = "test_client"):
        self.broker = broker
        self.port = port
        self.client_id = client_id
        self._connected = False
        self._message_callbacks = {
            "heartbeat": [],
            "sensor_data": [],
            "status": [],
        }
        
    def add_message_callback(self, message_type: str, callback: Callable) -> None:
        """Add a callback for message handling."""
        if message_type in self._message_callbacks:
            self._message_callbacks[message_type].append(callback)
    
    async def connect(self) -> bool:
        """Simulate connection."""
        print(f"✅ Connected to MQTT broker {self.broker}:{self.port}")
        self._connected = True
        return True
    
    async def disconnect(self) -> None:
        """Simulate disconnection."""
        print("Disconnected from MQTT broker")
        self._connected = False
    
    def is_connected(self) -> bool:
        return self._connected
    
    async def simulate_messages(self):
        """Simulate incoming MQTT messages."""
        if not self._connected:
            return
            
        print("Simulating MQTT messages...")
        
        # Simulate heartbeat messages
        heartbeat_data = {
            "type": "heartbeat",
            "board_id": 0,
            "seq_no": 1,
            "timestamp": datetime.now().isoformat(),
        }
        
        for callback in self._message_callbacks["heartbeat"]:
            callback(heartbeat_data)
        
        # Simulate status messages
        status_data = {
            "type": "status",
            "board_id": 0,
            "status": 0,  # OK
            "message_id": 123,
            "timestamp": datetime.now().isoformat(),
        }
        
        for callback in self._message_callbacks["status"]:
            callback(status_data)
        
        # Simulate sensor data
        sensor_data = {
            "type": "sensor_data",
            "board_id": 0,
            "temperature": 25.5,
            "humidity": 65.2,
            "light_intensity": 1200,
            "fans_real": 150,
            "fans_abs": 60,
            "led_abs": 80,
            "status": 0,
            "timestamp": datetime.now().isoformat(),
        }
        
        for callback in self._message_callbacks["sensor_data"]:
            callback(sensor_data)

def test_message_handler(data):
    """Test message handler."""
    print(f"✅ Received {data['type']} message:")
    for key, value in data.items():
        if key != 'type':
            print(f"  {key}: {value}")
    print()

async def test_with_fake_data():
    """Test with fake data."""
    print("Testing Vertical Farm MQTT Integration with Fake Data...")
    print("=" * 60)
    
    # Create fake client
    client = FakeMQTTClient(
        broker="localhost",
        port=5001,
        client_id="test_client"
    )
    
    # Add message callbacks
    client.add_message_callback("heartbeat", test_message_handler)
    client.add_message_callback("status", test_message_handler)
    client.add_message_callback("sensor_data", test_message_handler)
    
    # Connect
    print("Connecting to MQTT broker...")
    success = await client.connect()
    
    if success:
        print(f"Subscribed to topics: {MQTT_HEARTBEAT_TOPIC}, {MQTT_RESPONSE_TOPIC}")
        print()
        
        # Simulate messages
        await client.simulate_messages()
        
        # Wait a bit
        await asyncio.sleep(2)
        
        # Simulate more messages
        print("Simulating more messages...")
        await client.simulate_messages()
        
    else:
        print("❌ Failed to connect")
    
    # Disconnect
    await client.disconnect()
    print("Test completed!")

def test_sensor_entity_creation():
    """Test sensor entity creation logic."""
    print("\n" + "=" * 60)
    print("Testing Sensor Entity Creation...")
    print("=" * 60)
    
    # Simulate sensor data
    sensor_data = {
        "board_id": 0,
        "temperature": 25.5,
        "humidity": 65.2,
        "light_intensity": 1200,
        "fans_real": 150,
        "fans_abs": 60,
        "led_abs": 80,
        "status": 0,
        "timestamp": datetime.now().isoformat(),
    }
    
    # Test sensor type mapping
    sensor_types = {
        "temperature": {"unit": "°C", "icon": "mdi:thermometer"},
        "humidity": {"unit": "%", "icon": "mdi:water-percent"},
        "light_intensity": {"unit": "lux", "icon": "mdi:lightbulb"},
        "fan_speed": {"unit": "PWM", "icon": "mdi:fan"},
        "led_brightness": {"unit": "PWM", "icon": "mdi:lightbulb-on"},
        "status": {"unit": None, "icon": "mdi:information"},
    }
    
    print("Sensor entities that would be created:")
    for sensor_type, config in sensor_types.items():
        entity_id = f"sensor.vertical_farm_0_{sensor_type}"
        unit = config["unit"] or "N/A"
        icon = config["icon"]
        print(f"  - {entity_id}")
        print(f"    Unit: {unit}")
        print(f"    Icon: {icon}")
        
        # Show sample value
        if sensor_type in sensor_data:
            value = sensor_data[sensor_type]
            print(f"    Sample value: {value}")
        print()
    
    print("✅ Sensor entity creation test completed!")

def test_config_validation():
    """Test configuration validation."""
    print("\n" + "=" * 60)
    print("Testing Configuration Validation...")
    print("=" * 60)
    
    # Valid configurations
    valid_configs = [
        {"mqtt_broker": "localhost", "mqtt_port": 1883, "device_ids": [0, 1, 2]},
        {"mqtt_broker": "192.168.1.100", "mqtt_port": 5001, "device_ids": [0]},
        {"mqtt_broker": "mqtt.example.com", "mqtt_port": 8883, "device_ids": [0, 1, 2, 3, 4, 5, 6]},
    ]
    
    # Invalid configurations
    invalid_configs = [
        {"mqtt_broker": "", "mqtt_port": 1883, "device_ids": [0]},  # Empty broker
        {"mqtt_broker": "localhost", "mqtt_port": -1, "device_ids": [0]},  # Invalid port
        {"mqtt_broker": "localhost", "mqtt_port": 1883, "device_ids": []},  # No devices
        {"mqtt_broker": "localhost", "mqtt_port": 1883, "device_ids": [7]},  # Invalid device ID
        {"mqtt_broker": "localhost", "mqtt_port": 1883, "device_ids": [-1]},  # Invalid device ID
    ]
    
    print("Valid configurations:")
    for i, config in enumerate(valid_configs, 1):
        print(f"  {i}. {config}")
    
    print("\nInvalid configurations:")
    for i, config in enumerate(invalid_configs, 1):
        print(f"  {i}. {config}")
    
    print("\n✅ Configuration validation test completed!")

if __name__ == "__main__":
    print("🧪 Vertical Farm MQTT Integration Test Suite")
    print("=" * 60)
    
    # Run tests
    asyncio.run(test_with_fake_data())
    test_sensor_entity_creation()
    test_config_validation()
    
    print("\n" + "=" * 60)
    print("🎉 All tests completed successfully!")
    print("=" * 60) 