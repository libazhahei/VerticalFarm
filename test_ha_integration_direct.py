#!/usr/bin/env python3
"""
直接测试Home Assistant集成
模拟MQTT消息处理，不依赖外部MQTT代理
"""

import json
import time
import random
from datetime import datetime
from unittest.mock import Mock, patch

# 模拟Home Assistant环境
class MockHass:
    def __init__(self):
        self.data = {}
        self.states = {}
        
    def async_write_ha_state(self):
        print("📝 状态已更新")
        
    def data(self):
        return self.data

class MockSensor:
    def __init__(self, device_id, sensor_type):
        self.device_id = device_id
        self.sensor_type = sensor_type
        self._state = None
        self._attributes = {}
        self.hass = MockHass()
        
    def _handle_sensor_data(self, data):
        """处理传感器数据"""
        board_id = data.get("board_id")
        if board_id != self.device_id:
            return
            
        # 更新传感器状态
        if self.sensor_type == "temperature":
            self._state = data.get("temperature")
        elif self.sensor_type == "humidity":
            self._state = data.get("humidity")
        elif self.sensor_type == "light_intensity":
            self._state = data.get("light_intensity")
        elif self.sensor_type == "fan_speed":
            self._state = data.get("fans_real")
        elif self.sensor_type == "led_brightness":
            self._state = data.get("led_abs")
        elif self.sensor_type == "status":
            status = data.get("status")
            if status == "ok":
                self._state = "OK"
            elif status == "error":
                self._state = "Error"
            elif status == "warning":
                self._state = "Warning"
            else:
                self._state = "Unknown"
        
        # 更新属性
        self._attributes.update({
            "board_id": board_id,
            "timestamp": data.get("timestamp"),
        })
        
        print(f"📊 设备 {self.device_id} {self.sensor_type}: {self._state}")
        
    def _handle_heartbeat(self, data):
        """处理心跳数据"""
        board_id = data.get("board_id")
        if board_id != self.device_id:
            return
            
        self._attributes.update({
            "last_heartbeat": data.get("timestamp"),
            "seq_no": data.get("seq_no"),
        })
        
        print(f"📡 设备 {self.device_id} 心跳: seq_no={data.get('seq_no')}")

def generate_test_data():
    """生成测试数据"""
    test_data = []
    
    for device_id in [0, 1, 2]:
        # 心跳数据
        heartbeat = {
            "board_id": device_id,
            "seq_no": random.randint(1, 1000),
            "timestamp": datetime.now().isoformat(),
            "status": "ok"
        }
        test_data.append(("heartbeat", heartbeat))
        
        # 传感器数据
        sensor_data = {
            "board_id": device_id,
            "timestamp": datetime.now().isoformat(),
            "temperature": round(22 + random.uniform(-2, 2), 1),
            "humidity": round(60 + random.uniform(-10, 10), 1),
            "light_intensity": round(500 + random.uniform(-100, 100), 0),
            "fans_real": random.randint(0, 100),
            "led_abs": random.randint(0, 100),
            "status": random.choice(["ok", "warning", "error"])
        }
        test_data.append(("sensor_data", sensor_data))
        
    return test_data

def test_sensor_handling():
    """测试传感器数据处理"""
    print("🧪 测试传感器数据处理...")
    
    # 创建测试传感器
    sensors = []
    sensor_types = ["temperature", "humidity", "light_intensity", "fan_speed", "led_brightness", "status"]
    
    for device_id in [0, 1, 2]:
        for sensor_type in sensor_types:
            sensor = MockSensor(device_id, sensor_type)
            sensors.append(sensor)
    
    # 生成并处理测试数据
    test_data = generate_test_data()
    
    print(f"\n📤 处理 {len(test_data)} 条测试数据...")
    
    for msg_type, data in test_data:
        print(f"\n🕐 {datetime.now().strftime('%H:%M:%S')} - 处理 {msg_type}")
        
        for sensor in sensors:
            if msg_type == "heartbeat":
                sensor._handle_heartbeat(data)
            elif msg_type == "sensor_data":
                sensor._handle_sensor_data(data)
    
    print(f"\n✅ 测试完成！")
    print(f"📊 处理了 {len(sensors)} 个传感器")
    print(f"📨 处理了 {len(test_data)} 条消息")

def simulate_mqtt_messages():
    """模拟MQTT消息流"""
    print("🔄 模拟MQTT消息流...")
    
    # 创建传感器
    sensors = []
    sensor_types = ["temperature", "humidity", "light_intensity", "fan_speed", "led_brightness", "status"]
    
    for device_id in [0, 1, 2]:
        for sensor_type in sensor_types:
            sensor = MockSensor(device_id, sensor_type)
            sensors.append(sensor)
    
    print(f"📋 创建了 {len(sensors)} 个传感器")
    print("🚀 开始模拟数据流 (按 Ctrl+C 停止)...\n")
    
    try:
        round_num = 1
        while True:
            print(f"🔄 第 {round_num} 轮数据更新")
            
            # 生成新数据
            test_data = generate_test_data()
            
            for msg_type, data in test_data:
                for sensor in sensors:
                    if msg_type == "heartbeat":
                        sensor._handle_heartbeat(data)
                    elif msg_type == "sensor_data":
                        sensor._handle_sensor_data(data)
            
            print("✅ 本轮完成\n")
            time.sleep(3)  # 每3秒更新一次
            round_num += 1
            
    except KeyboardInterrupt:
        print(f"\n⏹️  模拟结束")

def main():
    """主函数"""
    print("🌱 Home Assistant 集成测试")
    print("=" * 40)
    
    print("选择测试模式:")
    print("1. 单次测试")
    print("2. 持续模拟")
    
    choice = input("请输入选择 (1 或 2): ").strip()
    
    if choice == "1":
        test_sensor_handling()
    elif choice == "2":
        simulate_mqtt_messages()
    else:
        print("❌ 无效选择")

if __name__ == "__main__":
    main() 