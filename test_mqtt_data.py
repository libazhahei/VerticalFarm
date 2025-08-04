#!/usr/bin/env python3
"""
MQTT测试脚本 - 发送模拟的Vertical Farm数据
用于测试Home Assistant集成
"""

import json
import time
import random
from datetime import datetime
import paho.mqtt.client as mqtt

# MQTT配置
MQTT_BROKER = "localhost"
MQTT_PORT = 5001
HEARTBEAT_TOPIC = "cropwaifu/heartbeat"
RESPONSE_TOPIC = "cropwaifu/respond"

# 模拟数据配置
DEVICE_IDS = [0, 1, 2]  # 测试3个设备
UPDATE_INTERVAL = 5  # 每5秒更新一次数据

class MQTTDataSimulator:
    def __init__(self):
        self.client = mqtt.Client()
        self.client.on_connect = self.on_connect
        self.client.on_publish = self.on_publish
        self.running = False
        
    def on_connect(self, client, userdata, flags, rc):
        """连接回调"""
        if rc == 0:
            print(f"✅ 成功连接到MQTT代理 {MQTT_BROKER}:{MQTT_PORT}")
            self.running = True
        else:
            print(f"❌ 连接失败，错误代码: {rc}")
            
    def on_publish(self, client, userdata, mid):
        """发布回调"""
        print(f"📤 消息已发布 (ID: {mid})")
        
    def connect(self):
        """连接到MQTT代理"""
        try:
            print(f"🔗 正在连接到MQTT代理 {MQTT_BROKER}:{MQTT_PORT}...")
            self.client.connect(MQTT_BROKER, MQTT_PORT, 60)
            self.client.loop_start()
            # 等待连接建立
            time.sleep(2)
            return self.running
        except Exception as e:
            print(f"❌ 连接失败: {e}")
            return False
        
    def disconnect(self):
        """断开连接"""
        self.running = False
        self.client.loop_stop()
        self.client.disconnect()
        print("🔌 已断开MQTT连接")
        
    def generate_heartbeat_data(self, device_id):
        """生成心跳数据"""
        return {
            "board_id": device_id,
            "seq_no": random.randint(1, 1000),
            "timestamp": datetime.now().isoformat(),
            "status": "ok"
        }
        
    def generate_sensor_data(self, device_id):
        """生成传感器数据"""
        # 模拟真实的传感器数据范围
        base_temp = 22 + random.uniform(-2, 2)  # 20-24°C
        base_humidity = 60 + random.uniform(-10, 10)  # 50-70%
        base_light = 500 + random.uniform(-100, 100)  # 400-600 lux
        
        return {
            "board_id": device_id,
            "timestamp": datetime.now().isoformat(),
            "temperature": round(base_temp, 1),
            "humidity": round(base_humidity, 1),
            "light_intensity": round(base_light, 0),
            "fans_real": random.randint(0, 100),  # 风扇速度 0-100%
            "led_abs": random.randint(0, 100),    # LED亮度 0-100%
            "status": random.choice(["ok", "warning", "error"])
        }
        
    def send_data(self):
        """发送数据到所有设备"""
        if not self.running:
            return
            
        print(f"\n🕐 {datetime.now().strftime('%H:%M:%S')} - 发送模拟数据...")
        
        for device_id in DEVICE_IDS:
            # 发送心跳数据
            heartbeat_data = self.generate_heartbeat_data(device_id)
            self.client.publish(HEARTBEAT_TOPIC, json.dumps(heartbeat_data))
            print(f"  📡 设备 {device_id} 心跳: seq_no={heartbeat_data['seq_no']}")
            
            # 发送传感器数据
            sensor_data = self.generate_sensor_data(device_id)
            self.client.publish(RESPONSE_TOPIC, json.dumps(sensor_data))
            print(f"  📊 设备 {device_id} 传感器: "
                  f"温度={sensor_data['temperature']}°C, "
                  f"湿度={sensor_data['humidity']}%, "
                  f"光照={sensor_data['light_intensity']}lux")
            
        print("✅ 数据发送完成")
        
    def run(self):
        """运行模拟器"""
        if not self.connect():
            return
            
        print(f"\n🚀 开始发送模拟数据...")
        print(f"📋 配置: {len(DEVICE_IDS)}个设备, 每{UPDATE_INTERVAL}秒更新")
        print(f"🎯 目标: 在Home Assistant中查看实时数据更新")
        print(f"⏹️  按 Ctrl+C 停止\n")
        
        try:
            while self.running:
                self.send_data()
                time.sleep(UPDATE_INTERVAL)
        except KeyboardInterrupt:
            print(f"\n⏹️  收到停止信号")
        finally:
            self.disconnect()

def main():
    """主函数"""
    print("🌱 Vertical Farm MQTT 数据模拟器")
    print("=" * 50)
    
    simulator = MQTTDataSimulator()
    simulator.run()

if __name__ == "__main__":
    main() 