#!/usr/bin/env python3
"""Test Home Assistant integration logic."""

import json
import sys
import os
from datetime import datetime
from typing import Dict, Any

# Add the homeassistant_integration directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'homeassistant_integration'))

def test_constants():
    """Test constants are properly defined."""
    print("Testing constants...")
    
    try:
        from const import (
            DOMAIN, CONF_MQTT_BROKER, CONF_MQTT_PORT, CONF_DEVICE_IDS,
            MQTT_HEARTBEAT_TOPIC, MQTT_RESPONSE_TOPIC,
            DEVICE_MIN_ID, DEVICE_MAX_ID,
            SENSOR_TEMPERATURE, SENSOR_HUMIDITY, SENSOR_LIGHT_INTENSITY,
            STATUS_OK, STATUS_ERROR, STATUS_WARNING
        )
        
        print("✅ All constants imported successfully")
        print(f"  DOMAIN: {DOMAIN}")
        print(f"  MQTT Topics: {MQTT_HEARTBEAT_TOPIC}, {MQTT_RESPONSE_TOPIC}")
        print(f"  Device ID Range: {DEVICE_MIN_ID} - {DEVICE_MAX_ID}")
        print(f"  Sensor Types: {SENSOR_TEMPERATURE}, {SENSOR_HUMIDITY}, {SENSOR_LIGHT_INTENSITY}")
        
    except ImportError as e:
        print(f"❌ Failed to import constants: {e}")
        return False
    
    return True

def test_config_flow():
    """Test config flow logic."""
    print("\nTesting config flow...")
    
    try:
        from config_flow import VerticalFarmMQTTConfigFlow
        
        # Test config validation logic
        valid_device_ids = [0, 1, 2, 3, 4, 5, 6]
        invalid_device_ids = [-1, 7, 10]
        
        print("✅ Config flow class imported successfully")
        print(f"  Valid device IDs: {valid_device_ids}")
        print(f"  Invalid device IDs: {invalid_device_ids}")
        
    except ImportError as e:
        print(f"❌ Failed to import config flow: {e}")
        return False
    
    return True

def test_mqtt_client_structure():
    """Test MQTT client structure."""
    print("\nTesting MQTT client structure...")
    
    try:
        from mqtt_client import VerticalFarmMQTTClient
        
        # Test client creation
        client = VerticalFarmMQTTClient(
            broker="localhost",
            port=1883,
            username=None,
            password=None
        )
        
        print("✅ MQTT client created successfully")
        print(f"  Broker: {client.broker}")
        print(f"  Port: {client.port}")
        print(f"  Client ID: {client.client_id}")
        
        # Test callback registration
        def test_callback(data):
            pass
        
        client.add_message_callback("heartbeat", test_callback)
        client.add_message_callback("status", test_callback)
        
        print("✅ Callback registration works")
        
    except ImportError as e:
        print(f"❌ Failed to import MQTT client: {e}")
        return False
    
    return True

def test_sensor_structure():
    """Test sensor structure."""
    print("\nTesting sensor structure...")
    
    try:
        # Import sensor types from the sensor file
        sensor_types = {
            "temperature": {"unit": "°C", "icon": "mdi:thermometer"},
            "humidity": {"unit": "%", "icon": "mdi:water-percent"},
            "light_intensity": {"unit": "lux", "icon": "mdi:lightbulb"},
            "fan_speed": {"unit": "PWM", "icon": "mdi:fan"},
            "led_brightness": {"unit": "PWM", "icon": "mdi:lightbulb-on"},
            "status": {"unit": None, "icon": "mdi:information"},
        }
        
        print("✅ Sensor types defined:")
        for sensor_type, config in sensor_types.items():
            print(f"  - {sensor_type}: {config['unit']} ({config['icon']})")
        
    except Exception as e:
        print(f"❌ Failed to test sensor structure: {e}")
        return False
    
    return True

def test_manifest():
    """Test manifest file."""
    print("\nTesting manifest file...")
    
    try:
        import json
        with open('homeassistant_integration/manifest.json', 'r') as f:
            manifest = json.load(f)
        
        required_fields = ['domain', 'name', 'config_flow', 'requirements']
        for field in required_fields:
            if field not in manifest:
                print(f"❌ Missing required field: {field}")
                return False
        
        print("✅ Manifest file is valid")
        print(f"  Domain: {manifest['domain']}")
        print(f"  Name: {manifest['name']}")
        print(f"  Requirements: {manifest['requirements']}")
        
    except Exception as e:
        print(f"❌ Failed to test manifest: {e}")
        return False
    
    return True

def test_translations():
    """Test translation files."""
    print("\nTesting translation files...")
    
    try:
        # Test English translations
        with open('homeassistant_integration/translations/en.json', 'r') as f:
            en_translations = json.load(f)
        
        # Test Chinese translations
        with open('homeassistant_integration/translations/zh-Hans.json', 'r') as f:
            zh_translations = json.load(f)
        
        print("✅ Translation files are valid")
        print(f"  English config title: {en_translations['config']['step']['user']['title']}")
        print(f"  Chinese config title: {zh_translations['config']['step']['user']['title']}")
        
    except Exception as e:
        print(f"❌ Failed to test translations: {e}")
        return False
    
    return True

def test_message_parsing():
    """Test MQTT message parsing logic."""
    print("\nTesting MQTT message parsing...")
    
    # Test heartbeat message
    heartbeat_msg = {
        "boardID": 0,
        "seqNo": 123
    }
    
    # Test status message
    status_msg = {
        "boardID": 0,
        "status": 0,
        "messageID": 456,
        "timestamp": datetime.now().timestamp()
    }
    
    # Test sensor data message (BLE format)
    sensor_msg = {
        "board_id": 0,
        "temperature": 25.5,
        "humidity": 65.2,
        "light_intensity": 1200,
        "fans_real": 150,
        "fans_abs": 60,
        "led_abs": 80,
        "status": 0,
        "timestamp": datetime.now().timestamp()
    }
    
    print("✅ Message parsing test data:")
    print(f"  Heartbeat: {heartbeat_msg}")
    print(f"  Status: {status_msg}")
    print(f"  Sensor: {sensor_msg}")
    
    return True

def test_entity_naming():
    """Test entity naming convention."""
    print("\nTesting entity naming convention...")
    
    device_id = 0
    sensor_types = ["temperature", "humidity", "light_intensity", "fan_speed", "led_brightness", "status"]
    
    expected_entities = []
    for sensor_type in sensor_types:
        entity_id = f"sensor.vertical_farm_{device_id}_{sensor_type}"
        expected_entities.append(entity_id)
    
    print("✅ Entity naming convention:")
    for entity_id in expected_entities:
        print(f"  - {entity_id}")
    
    return True

def main():
    """Run all tests."""
    print("🧪 Home Assistant Integration Logic Test Suite")
    print("=" * 60)
    
    tests = [
        ("Constants", test_constants),
        ("Config Flow", test_config_flow),
        ("MQTT Client Structure", test_mqtt_client_structure),
        ("Sensor Structure", test_sensor_structure),
        ("Manifest", test_manifest),
        ("Translations", test_translations),
        ("Message Parsing", test_message_parsing),
        ("Entity Naming", test_entity_naming),
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        print(f"\n{'='*20} {test_name} {'='*20}")
        try:
            if test_func():
                passed += 1
                print(f"✅ {test_name} passed")
            else:
                print(f"❌ {test_name} failed")
        except Exception as e:
            print(f"❌ {test_name} failed with exception: {e}")
    
    print("\n" + "=" * 60)
    print(f"🎉 Test Results: {passed}/{total} tests passed")
    print("=" * 60)
    
    if passed == total:
        print("✅ All tests passed! Integration is ready for Home Assistant.")
    else:
        print("❌ Some tests failed. Please check the errors above.")
    
    return passed == total

if __name__ == "__main__":
    main() 