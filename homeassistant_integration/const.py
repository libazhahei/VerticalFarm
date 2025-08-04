"""Constants for the Vertical Farm MQTT integration."""
from typing import Final

DOMAIN: Final = "vertical_farm_mqtt"

# Configuration keys
CONF_MQTT_BROKER: Final = "mqtt_broker"
CONF_MQTT_PORT: Final = "mqtt_port"
CONF_MQTT_USERNAME: Final = "mqtt_username"
CONF_MQTT_PASSWORD: Final = "mqtt_password"
CONF_DEVICE_IDS: Final = "device_ids"

# Default values
DEFAULT_MQTT_BROKER: Final = "localhost"
DEFAULT_MQTT_PORT: Final = 1883

# MQTT Topics (matching your gateway constants)
MQTT_HEARTBEAT_TOPIC: Final = "cropwaifu/heartbeat"
MQTT_RESPONSE_TOPIC: Final = "cropwaifu/respond"

# Device configuration
DEVICE_MIN_ID: Final = 0
DEVICE_MAX_ID: Final = 6

# Sensor types
SENSOR_TEMPERATURE: Final = "temperature"
SENSOR_HUMIDITY: Final = "humidity"
SENSOR_LIGHT_INTENSITY: Final = "light_intensity"
SENSOR_FAN_SPEED: Final = "fan_speed"
SENSOR_LED_BRIGHTNESS: Final = "led_brightness"
SENSOR_STATUS: Final = "status"

# Status values
STATUS_OK: Final = 0
STATUS_ERROR: Final = 1
STATUS_WARNING: Final = 3

# Units
UNIT_TEMPERATURE: Final = "°C"
UNIT_HUMIDITY: Final = "%"
UNIT_LIGHT_INTENSITY: Final = "lux"
UNIT_FAN_SPEED: Final = "PWM"
UNIT_LED_BRIGHTNESS: Final = "PWM"

# Entity attributes
ATTR_BOARD_ID: Final = "board_id"
ATTR_MESSAGE_ID: Final = "message_id"
ATTR_TIMESTAMP: Final = "timestamp"
ATTR_STATUS: Final = "status" 