#!/bin/bash

# Vertical Farm MQTT Monitor Home Assistant Integration Installer
# 垂直农场MQTT监控 Home Assistant集成安装脚本

echo "=========================================="
echo "Vertical Farm MQTT Monitor Integration"
echo "垂直农场MQTT监控集成安装"
echo "=========================================="

# 检查是否在Home Assistant环境中
if [ ! -d "/config" ]; then
    echo "错误: 未检测到Home Assistant配置目录"
    echo "请确保在Home Assistant环境中运行此脚本"
    exit 1
fi

# 创建custom_components目录（如果不存在）
if [ ! -d "/config/custom_components" ]; then
    echo "创建 custom_components 目录..."
    mkdir -p /config/custom_components
fi

# 复制集成文件
echo "复制集成文件..."
cp -r homeassistant_integration /config/custom_components/

# 检查复制是否成功
if [ $? -eq 0 ]; then
    echo "✅ 集成文件复制成功"
else
    echo "❌ 集成文件复制失败"
    exit 1
fi

# 设置文件权限
echo "设置文件权限..."
chmod -R 755 /config/custom_components/homeassistant_integration

echo ""
echo "=========================================="
echo "安装完成！"
echo ""
echo "⚠️  注意：这是一个纯监控插件，不提供控制功能"
echo ""
echo "下一步操作："
echo "1. 重启Home Assistant"
echo "2. 进入 配置 > 设备和服务 > 集成"
echo "3. 点击 '添加集成'"
echo "4. 搜索 'Vertical Farm MQTT Monitor'"
echo "5. 按照配置向导完成设置"
echo ""
echo "配置示例："
echo "- MQTT Broker: localhost"
echo "- MQTT Port: 1883"
echo "- Device IDs: 0,1,2"
echo ""
echo "可用传感器："
echo "- 温度、湿度、光照强度、风扇速度、LED亮度、设备状态"
echo "==========================================" 