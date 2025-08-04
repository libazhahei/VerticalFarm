# 🌱 Home Assistant 集成测试指南

## 📋 概述
本指南详细说明如何测试Vertical Farm的Home Assistant MQTT集成插件，包括环境准备、服务启动和数据验证。

## 🛠️ 环境准备

### 1. 确保在正确的分支
```bash
git checkout ha-integration-clean
```

### 2. 激活虚拟环境
```bash
source ha_test_env/bin/activate
```

## 🚀 启动步骤

### 步骤1: 启动MQTT代理
```bash
python start_mqtt_broker.py
```
**预期输出:**
```
🌱 MQTT代理启动器
==============================
🔧 检查Mosquitto MQTT代理...
✅ Mosquitto已安装
🚀 启动Mosquitto MQTT代理...
✅ Mosquitto已启动在端口5001
📋 进程ID: [进程ID]
⏹️  按 Ctrl+C 停止
```

**注意:** 如果端口5001被占用，会显示"Address already in use"，这是正常的，说明MQTT代理已经在运行。

### 步骤2: 启动Home Assistant
```bash
hass --open-ui
```
**预期输出:**
```
2025-08-05 04:14:28.024 WARNING (SyncWorker_0) [homeassistant.loader] We found a custom integration vertical_farm_mqtt which has not been tested by Home Assistant. This component might cause stability problems, be sure to disable it if you experience issues with Home Assistant
2025-08-05 04:14:28.350 WARNING (MainThread) [aiohttp_fast_zlib] zlib_ng and isal are not available, falling back to zlib, performance will be degraded.
2025-08-05 04:14:28.361 WARNING (Recorder) [homeassistant.components.recorder.util] The system could not validate that the sqlite3 database at //Users/amberhsu/.homeassistant/home-assistant_v2.db was shutdown cleanly
2025-08-05 04:14:30.270 WARNING (MainThread) [homeassistant.bootstrap] Support for the running Python version 3.12.7 is deprecated and will be removed in Home Assistant 2022.2; Please upgrade Python to 3.13
```

**重要:** 警告信息是正常的，不会影响功能。

### 步骤3: 配置Home Assistant集成

1. **打开浏览器** - Home Assistant会自动打开 http://127.0.0.1:8123
2. **添加集成** - 点击"添加集成"
3. **搜索"Vertical Farm"** - 找到"Vertical Farm MQTT Monitor"
4. **配置MQTT连接:**
   - **MQTT Broker:** localhost
   - **MQTT Port:** 5001
   - **Device IDs:** 0,1,2
   - **Username/Password:** 留空（本地测试）
5. **提交配置**

### 步骤4: 发送测试数据
```bash
python test_mqtt_data.py
```
**预期输出:**
```
🌱 Vertical Farm MQTT 数据模拟器
==================================================
🔗 正在连接到MQTT代理 localhost:5001...
✅ 成功连接到MQTT代理 localhost:5001

🚀 开始发送模拟数据...
📋 配置: 3个设备, 每5秒更新
🎯 目标: 在Home Assistant中查看实时数据更新
⏹️  按 Ctrl+C 停止

🕐 [时间] - 发送模拟数据...
  📡 设备 0 心跳: seq_no=[数字]
  📊 设备 0 传感器: 温度=[温度]°C, 湿度=[湿度]%, 光照=[光照]lux
  📡 设备 1 心跳: seq_no=[数字]
  📊 设备 1 传感器: 温度=[温度]°C, 湿度=[湿度]%, 光照=[光照]lux
  📡 设备 2 心跳: seq_no=[数字]
  📊 设备 2 传感器: 温度=[温度]°C, 湿度=[湿度]%, 光照=[光照]lux
✅ 数据发送完成
📤 消息已发布 (ID: [数字])
```

## ✅ 验证结果

### 在Home Assistant界面中应该看到:

1. **三个设备卡片:**
   - Vertical Farm Device 0
   - Vertical Farm Device 1  
   - Vertical Farm Device 2

2. **每个设备显示6个传感器:**
   - **Fan Speed:** [数值] PWM
   - **Humidity:** [数值]%
   - **LED Brightness:** [数值] PWM
   - **Light Intensity:** [数值] lux
   - **Status:** Unknown (正常状态)
   - **Temperature:** [数值] °C

3. **数据实时更新** - 每5秒数值会变化

## 🔧 故障排除

### 问题1: MQTT代理启动失败
**症状:** "Address already in use"
**解决:** 端口5001已被占用，说明MQTT代理已在运行，可以直接进行下一步。

### 问题2: Home Assistant无法加载集成
**症状:** 找不到"Vertical Farm MQTT Monitor"
**解决:** 
1. 确保在`ha-integration-clean`分支
2. 检查`homeassistant_integration/`目录是否存在
3. 重启Home Assistant

### 问题3: 传感器显示"Unknown"
**症状:** 所有传感器值都是"Unknown"
**解决:**
1. 确保MQTT代理正在运行
2. 确保测试数据脚本正在发送数据
3. 检查MQTT连接配置

### 问题4: 数据不更新
**症状:** 传感器值不变化
**解决:**
1. 确保`test_mqtt_data.py`正在运行
2. 检查MQTT主题配置
3. 查看Home Assistant日志

## 📊 测试数据说明

测试脚本会模拟3个设备的数据:
- **设备ID:** 0, 1, 2
- **更新频率:** 每5秒
- **数据类型:** 心跳消息 + 传感器数据
- **数值范围:**
  - 温度: 20-25°C
  - 湿度: 50-70%
  - 光照: 400-600 lux
  - 风扇速度: 30-100 PWM
  - LED亮度: 50-100 PWM

## 🎯 成功标准

✅ **MQTT代理正常运行** - 端口5001可访问
✅ **Home Assistant启动成功** - 界面可访问
✅ **集成配置成功** - 无错误信息
✅ **传感器数据正常显示** - 数值非"Unknown"
✅ **数据实时更新** - 每5秒数值变化
✅ **3个设备都显示** - Device 0, 1, 2

## 🚪 停止服务

1. **停止测试数据:** 在`test_mqtt_data.py`终端按`Ctrl+C`
2. **停止Home Assistant:** 在`hass --open-ui`终端按`Ctrl+C`
3. **停止MQTT代理:** 在`start_mqtt_broker.py`终端按`Ctrl+C`

## 📝 注意事项

- 所有服务都在本地运行，不需要网络连接
- 虚拟环境必须激活才能运行命令
- 测试数据是模拟的，仅用于验证集成功能
- 如果遇到问题，可以查看各服务的日志输出 