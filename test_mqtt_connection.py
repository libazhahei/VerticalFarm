#!/usr/bin/env python3
"""
测试MQTT连接和消息接收
"""

import json
import time
import paho.mqtt.client as mqtt

# MQTT配置
MQTT_BROKER = "localhost"
MQTT_PORT = 5001
HEARTBEAT_TOPIC = "cropwaifu/heartbeat"
RESPONSE_TOPIC = "cropwaifu/respond"

def on_connect(client, userdata, flags, rc):
    """连接回调"""
    if rc == 0:
        print("✅ 成功连接到MQTT代理")
        # 订阅主题
        client.subscribe(HEARTBEAT_TOPIC)
        client.subscribe(RESPONSE_TOPIC)
        print(f"📡 已订阅主题: {HEARTBEAT_TOPIC}, {RESPONSE_TOPIC}")
    else:
        print(f"❌ 连接失败: {rc}")

def on_message(client, userdata, msg):
    """消息回调"""
    try:
        topic = msg.topic
        payload = msg.payload.decode('utf-8')
        data = json.loads(payload)
        
        print(f"📨 收到消息: {topic}")
        print(f"   📊 数据: {json.dumps(data, indent=2, ensure_ascii=False)}")
        
    except Exception as e:
        print(f"❌ 处理消息错误: {e}")

def main():
    """主函数"""
    print("🔍 测试MQTT连接...")
    
    # 创建客户端
    client = mqtt.Client()
    client.on_connect = on_connect
    client.on_message = on_message
    
    try:
        # 连接
        client.connect(MQTT_BROKER, MQTT_PORT, 60)
        client.loop_start()
        
        print("⏳ 等待消息... (按 Ctrl+C 停止)")
        
        # 保持运行
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            print("\n⏹️  停止测试")
            
    except Exception as e:
        print(f"❌ 连接错误: {e}")
    finally:
        client.loop_stop()
        client.disconnect()

if __name__ == "__main__":
    main() 