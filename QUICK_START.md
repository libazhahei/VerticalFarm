# Vertical Farm MQTT 监控插件 - 快速使用指南

## 简介
这是一个纯监控的Home Assistant插件，用于实时显示垂直农场系统的传感器数据，不提供任何控制功能。

## 快速安装

### 1. 安装插件
```bash
# 复制插件到Home Assistant
cp -r homeassistant_integration /config/custom_components/
```

### 2. 重启Home Assistant
- 进入 **配置** > **系统** > **重启**

### 3. 添加集成
- 进入 **配置** > **设备和服务** > **集成**
- 点击 **添加集成**
- 搜索 "Vertical Farm MQTT Monitor"
- 配置MQTT连接信息

## 配置参数

| 参数 | 说明 | 默认值 |
|------|------|--------|
| MQTT Broker | MQTT代理地址 | localhost |
| MQTT Port | MQTT端口 | 1883 |
| Device IDs | 设备ID列表 | 0,1,2 |

## 可用传感器

每个设备会创建以下传感器：

- `sensor.vertical_farm_0_temperature` - 温度 (°C)
- `sensor.vertical_farm_0_humidity` - 湿度 (%)
- `sensor.vertical_farm_0_light_intensity` - 光照强度 (lux)
- `sensor.vertical_farm_0_fan_speed` - 风扇速度 (PWM)
- `sensor.vertical_farm_0_led_brightness` - LED亮度 (PWM)
- `sensor.vertical_farm_0_status` - 设备状态

## 创建仪表板

在Lovelace中添加传感器卡片：

```yaml
type: entities
title: "Vertical Farm Monitor"
entities:
  - entity: sensor.vertical_farm_0_temperature
  - entity: sensor.vertical_farm_0_humidity
  - entity: sensor.vertical_farm_0_light_intensity
  - entity: sensor.vertical_farm_0_fan_speed
  - entity: sensor.vertical_farm_0_led_brightness
  - entity: sensor.vertical_farm_0_status
```

## 创建自动化示例

```yaml
# 温度过高报警
automation:
  - alias: "Temperature Alert"
    trigger:
      platform: numeric_state
      entity_id: sensor.vertical_farm_0_temperature
      above: 30
    action:
      - service: notify.mobile_app
        data:
          message: "温度过高！当前温度: {{ states('sensor.vertical_farm_0_temperature') }}°C"
```

## 故障排除

### 数据不更新
1. 检查MQTT连接状态
2. 确认设备正在发送数据
3. 查看Home Assistant日志

### 连接失败
1. 检查MQTT代理地址和端口
2. 确认MQTT代理正在运行
3. 验证用户名和密码

## 日志查看

启用调试日志：
```yaml
logger:
  default: info
  logs:
    custom_components.vertical_farm_mqtt: debug
```

## 注意事项

- 此插件仅用于监控，不提供控制功能
- 需要确保MQTT代理正在运行
- 设备ID范围：0-6
- 支持多设备同时监控 