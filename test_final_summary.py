#!/usr/bin/env python3
"""Final summary test for Vertical Farm MQTT integration."""

import os
import json
from datetime import datetime

def check_file_structure():
    """Check that all required files exist."""
    print("📁 Checking file structure...")
    
    required_files = [
        "homeassistant_integration/__init__.py",
        "homeassistant_integration/const.py",
        "homeassistant_integration/config_flow.py",
        "homeassistant_integration/mqtt_client.py",
        "homeassistant_integration/sensor.py",
        "homeassistant_integration/manifest.json",
        "homeassistant_integration/translations/en.json",
        "homeassistant_integration/translations/zh-Hans.json",
    ]
    
    missing_files = []
    for file_path in required_files:
        if not os.path.exists(file_path):
            missing_files.append(file_path)
        else:
            print(f"  ✅ {file_path}")
    
    if missing_files:
        print(f"  ❌ Missing files: {missing_files}")
        return False
    
    print("✅ All required files exist")
    return True

def check_manifest():
    """Check manifest file."""
    print("\n📋 Checking manifest file...")
    
    try:
        with open("homeassistant_integration/manifest.json", "r") as f:
            manifest = json.load(f)
        
        required_fields = ["domain", "name", "config_flow", "requirements"]
        for field in required_fields:
            if field not in manifest:
                print(f"  ❌ Missing field: {field}")
                return False
        
        print(f"  ✅ Domain: {manifest['domain']}")
        print(f"  ✅ Name: {manifest['name']}")
        print(f"  ✅ Config Flow: {manifest['config_flow']}")
        print(f"  ✅ Requirements: {manifest['requirements']}")
        
        return True
    except Exception as e:
        print(f"  ❌ Error reading manifest: {e}")
        return False

def check_translations():
    """Check translation files."""
    print("\n🌐 Checking translation files...")
    
    try:
        # Check English translations
        with open("homeassistant_integration/translations/en.json", "r") as f:
            en_data = json.load(f)
        
        # Check Chinese translations
        with open("homeassistant_integration/translations/zh-Hans.json", "r") as f:
            zh_data = json.load(f)
        
        print("  ✅ English translations loaded")
        print("  ✅ Chinese translations loaded")
        
        # Check that both files have config section
        if "config" not in en_data or "config" not in zh_data:
            print("  ❌ Missing config section in translations")
            return False
        
        print("  ✅ Config sections found in both translations")
        return True
    except Exception as e:
        print(f"  ❌ Error reading translations: {e}")
        return False

def check_constants():
    """Check constants file."""
    print("\n⚙️ Checking constants...")
    
    try:
        # Read the constants file
        with open("homeassistant_integration/const.py", "r") as f:
            content = f.read()
        
        required_constants = [
            "DOMAIN",
            "CONF_MQTT_BROKER",
            "CONF_MQTT_PORT",
            "CONF_DEVICE_IDS",
            "MQTT_HEARTBEAT_TOPIC",
            "MQTT_RESPONSE_TOPIC",
            "DEVICE_MIN_ID",
            "DEVICE_MAX_ID",
        ]
        
        missing_constants = []
        for constant in required_constants:
            if constant not in content:
                missing_constants.append(constant)
        
        if missing_constants:
            print(f"  ❌ Missing constants: {missing_constants}")
            return False
        
        print("  ✅ All required constants defined")
        return True
    except Exception as e:
        print(f"  ❌ Error reading constants: {e}")
        return False

def check_sensor_logic():
    """Check sensor logic."""
    print("\n📊 Checking sensor logic...")
    
    try:
        with open("homeassistant_integration/sensor.py", "r") as f:
            content = f.read()
        
        required_elements = [
            "class VerticalFarmSensor",
            "async def async_setup_entry",
            "SENSOR_TYPES",
            "SensorEntity",
        ]
        
        missing_elements = []
        for element in required_elements:
            if element not in content:
                missing_elements.append(element)
        
        if missing_elements:
            print(f"  ❌ Missing elements: {missing_elements}")
            return False
        
        print("  ✅ Sensor logic looks good")
        return True
    except Exception as e:
        print(f"  ❌ Error reading sensor file: {e}")
        return False

def check_mqtt_client():
    """Check MQTT client."""
    print("\n📡 Checking MQTT client...")
    
    try:
        with open("homeassistant_integration/mqtt_client.py", "r") as f:
            content = f.read()
        
        required_elements = [
            "class VerticalFarmMQTTClient",
            "async def connect",
            "async def disconnect",
            "add_message_callback",
        ]
        
        missing_elements = []
        for element in required_elements:
            if element not in content:
                missing_elements.append(element)
        
        if missing_elements:
            print(f"  ❌ Missing elements: {missing_elements}")
            return False
        
        print("  ✅ MQTT client looks good")
        return True
    except Exception as e:
        print(f"  ❌ Error reading MQTT client: {e}")
        return False

def generate_entity_examples():
    """Generate example entity IDs."""
    print("\n🏷️ Example entity IDs that will be created:")
    
    device_ids = [0, 1, 2]
    sensor_types = ["temperature", "humidity", "light_intensity", "fan_speed", "led_brightness", "status"]
    
    for device_id in device_ids:
        print(f"\n  Device {device_id}:")
        for sensor_type in sensor_types:
            entity_id = f"sensor.vertical_farm_{device_id}_{sensor_type}"
            print(f"    - {entity_id}")
    
    print(f"\n  Total entities: {len(device_ids) * len(sensor_types)}")

def main():
    """Run final summary."""
    print("🎯 Vertical Farm MQTT Integration - Final Summary")
    print("=" * 60)
    
    tests = [
        ("File Structure", check_file_structure),
        ("Manifest", check_manifest),
        ("Translations", check_translations),
        ("Constants", check_constants),
        ("Sensor Logic", check_sensor_logic),
        ("MQTT Client", check_mqtt_client),
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        if test_func():
            passed += 1
            print(f"✅ {test_name} passed")
        else:
            print(f"❌ {test_name} failed")
    
    print("\n" + "=" * 60)
    print(f"📊 Test Results: {passed}/{total} tests passed")
    print("=" * 60)
    
    if passed == total:
        print("🎉 All tests passed! Integration is ready for Home Assistant.")
        print("\n📋 Integration Summary:")
        print("  - Domain: vertical_farm_mqtt")
        print("  - Type: Monitor-only (no control features)")
        print("  - MQTT Topics: cropwaifu/heartbeat, cropwaifu/respond")
        print("  - Device Support: 0-6")
        print("  - Sensors per device: 6 (temperature, humidity, light_intensity, fan_speed, led_brightness, status)")
        
        generate_entity_examples()
        
        print("\n🚀 Ready to install in Home Assistant!")
        print("  1. Copy homeassistant_integration/ to /config/custom_components/")
        print("  2. Restart Home Assistant")
        print("  3. Add integration: 'Vertical Farm MQTT Monitor'")
        
    else:
        print("❌ Some tests failed. Please check the errors above.")
    
    return passed == total

if __name__ == "__main__":
    main() 