# Vertical Farm MQTT Home Assistant Integration

这是一个用于Home Assistant的垂直农场MQTT监控集成插件，可以实时监控你的垂直农场系统状态。

## 功能特性

- **传感器监控**: 实时监控温度、湿度、光照强度、风扇速度、LED亮度等
- **MQTT通信**: 直接与你的垂直农场MQTT系统通信
- **多设备支持**: 支持多个设备ID (0-6)
- **实时状态**: 显示设备心跳和状态信息
- **纯监控模式**: 只用于显示和监控，不提供控制功能

## 安装方法

### 方法1: 手动安装（推荐）

1. **下载插件文件**
   ```bash
   # 将整个 homeassistant_integration 文件夹复制到你的Home Assistant配置目录
   cp -r homeassistant_integration /config/custom_components/
   ```

2. **重启Home Assistant**
   - 在Home Assistant界面中，进入 **配置** > **系统** > **重启**

3. **添加集成**
   - 进入 **配置** > **设备和服务** > **集成**
   - 点击右下角的 **添加集成**
   - 搜索 "Vertical Farm MQTT Monitor"
   - 点击安装

### 方法2: HACS安装（如果使用HACS）

1. 将插件文件上传到你的HACS自定义仓库
2. 通过HACS安装
3. 重启Home Assistant
4. 添加集成

## 配置说明

### 基本配置

在添加集成时，你需要提供以下信息：

- **MQTT Broker**: MQTT代理地址（默认: localhost）
- **MQTT Port**: MQTT端口（默认: 1883）
- **MQTT Username**: MQTT用户名（可选）
- **MQTT Password**: MQTT密码（可选）
- **Device IDs**: 设备ID列表（0-6，用逗号分隔）

### 配置示例

```
MQTT Broker: localhost
MQTT Port: 1883
Device IDs: 0,1,2
```

## 实体说明

### 传感器实体

每个设备会创建以下传感器：

- **温度传感器**: 显示当前温度（°C）
- **湿度传感器**: 显示当前湿度（%）
- **光照强度传感器**: 显示光照强度（lux）
- **风扇速度传感器**: 显示风扇PWM值
- **LED亮度传感器**: 显示LED PWM值
- **状态传感器**: 显示设备状态（OK/Error/Warning）

## 使用方法

### 1. 监控传感器数据

1. 在Home Assistant仪表板中添加传感器卡片
2. 选择对应的传感器实体
3. 实时查看数据变化

### 2. 创建自动化

你可以基于传感器数据创建自动化：

```yaml
# 示例：温度过高时发送通知
automation:
  - alias: "Temperature Alert"
    trigger:
      platform: numeric_state
      entity_id: sensor.vertical_farm_0_temperature
      above: 30
    action:
      - service: notify.mobile_app
        data:
          message: "Vertical Farm temperature is too high!"
```

### 3. 创建仪表板

在Lovelace中创建垂直农场监控仪表板：

```yaml
# 示例仪表板配置
views:
  - title: "Vertical Farm Monitor"
    path: vertical-farm-monitor
    cards:
      - type: entities
        title: "Device 0 Status"
        entities:
          - entity: sensor.vertical_farm_0_temperature
          - entity: sensor.vertical_farm_0_humidity
          - entity: sensor.vertical_farm_0_light_intensity
          - entity: sensor.vertical_farm_0_fan_speed
          - entity: sensor.vertical_farm_0_led_brightness
          - entity: sensor.vertical_farm_0_status
```

## MQTT主题说明

插件使用以下MQTT主题进行监控：

- **订阅主题**:
  - `cropwaifu/heartbeat`: 设备心跳消息
  - `cropwaifu/respond`: 设备状态响应

## 故障排除

### 常见问题

1. **无法连接到MQTT代理**
   - 检查MQTT代理地址和端口
   - 确认MQTT代理正在运行
   - 检查用户名和密码

2. **传感器数据不更新**
   - 确认设备正在发送数据
   - 检查MQTT主题是否正确
   - 查看Home Assistant日志

### 查看日志

在Home Assistant中查看日志：

1. 进入 **配置** > **系统** > **日志**
2. 搜索 "vertical_farm_mqtt" 相关日志

### 调试模式

启用调试日志：

```yaml
# 在 configuration.yaml 中添加
logger:
  default: info
  logs:
    custom_components.vertical_farm_mqtt: debug
```

## 高级配置

### 自定义MQTT主题

如果需要修改MQTT主题，可以编辑 `const.py` 文件：

```python
# 修改主题
MQTT_HEARTBEAT_TOPIC = "your/heartbeat/topic"
MQTT_RESPONSE_TOPIC = "your/response/topic"
```

### 添加新的传感器类型

在 `sensor.py` 中添加新的传感器类型：

```python
SENSOR_TYPES = {
    # 现有传感器...
    "new_sensor": {
        ATTR_DEVICE_CLASS: None,
        ATTR_UNIT_OF_MEASUREMENT: "unit",
        ATTR_ICON: "mdi:icon",
        ATTR_STATE_CLASS: SensorStateClass.MEASUREMENT,
    },
}
```

## 更新插件

1. 备份当前配置
2. 下载新版本文件
3. 替换旧文件
4. 重启Home Assistant

## 技术支持

如果遇到问题，请：

1. 检查Home Assistant日志
2. 确认MQTT连接正常
3. 验证设备配置正确
4. 查看GitHub Issues（如果有）

## 许可证

本项目采用MIT许可证。 