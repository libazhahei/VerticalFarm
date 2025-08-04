"""Sensor platform for Vertical Farm MQTT integration."""
from __future__ import annotations

import asyncio
import logging
from datetime import datetime
from typing import Any

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    ATTR_DEVICE_CLASS,
    ATTR_ICON,
    ATTR_UNIT_OF_MEASUREMENT,
    CONF_DEVICE_ID,
    PERCENTAGE,
    UnitOfTemperature,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.typing import StateType

from .const import (
    ATTR_BOARD_ID,
    ATTR_MESSAGE_ID,
    ATTR_STATUS,
    ATTR_TIMESTAMP,
    CONF_DEVICE_IDS,
    DOMAIN,
    SENSOR_FAN_SPEED,
    SENSOR_HUMIDITY,
    SENSOR_LED_BRIGHTNESS,
    SENSOR_LIGHT_INTENSITY,
    SENSOR_STATUS,
    SENSOR_TEMPERATURE,
    STATUS_ERROR,
    STATUS_OK,
    STATUS_WARNING,
    UNIT_FAN_SPEED,
    UNIT_LED_BRIGHTNESS,
    UNIT_LIGHT_INTENSITY,
)

_LOGGER = logging.getLogger(__name__)

SENSOR_TYPES = {
    SENSOR_TEMPERATURE: {
        ATTR_DEVICE_CLASS: SensorDeviceClass.TEMPERATURE,
        ATTR_UNIT_OF_MEASUREMENT: UnitOfTemperature.CELSIUS,
        ATTR_ICON: "mdi:thermometer",
        "state_class": SensorStateClass.MEASUREMENT,
    },
    SENSOR_HUMIDITY: {
        ATTR_DEVICE_CLASS: SensorDeviceClass.HUMIDITY,
        ATTR_UNIT_OF_MEASUREMENT: PERCENTAGE,
        ATTR_ICON: "mdi:water-percent",
        "state_class": SensorStateClass.MEASUREMENT,
    },
    SENSOR_LIGHT_INTENSITY: {
        ATTR_DEVICE_CLASS: None,
        ATTR_UNIT_OF_MEASUREMENT: UNIT_LIGHT_INTENSITY,
        ATTR_ICON: "mdi:lightbulb",
        "state_class": SensorStateClass.MEASUREMENT,
    },
    SENSOR_FAN_SPEED: {
        ATTR_DEVICE_CLASS: None,
        ATTR_UNIT_OF_MEASUREMENT: UNIT_FAN_SPEED,
        ATTR_ICON: "mdi:fan",
        "state_class": SensorStateClass.MEASUREMENT,
    },
    SENSOR_LED_BRIGHTNESS: {
        ATTR_DEVICE_CLASS: None,
        ATTR_UNIT_OF_MEASUREMENT: UNIT_LED_BRIGHTNESS,
        ATTR_ICON: "mdi:lightbulb-on",
        "state_class": SensorStateClass.MEASUREMENT,
    },
    SENSOR_STATUS: {
        ATTR_DEVICE_CLASS: None,
        ATTR_UNIT_OF_MEASUREMENT: None,
        ATTR_ICON: "mdi:information",
        "state_class": None,
    },
}

async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the Vertical Farm MQTT sensors."""
    config = config_entry.data
    device_ids = config[CONF_DEVICE_IDS]
    
    # Parse device IDs if they're in string format
    if isinstance(device_ids, str):
        device_ids = [int(x.strip()) for x in device_ids.split(",")]
    
    # Get the MQTT client from the integration data
    mqtt_client = hass.data[DOMAIN].get("mqtt_client")
    
    sensors = []
    for device_id in device_ids:
        for sensor_type in SENSOR_TYPES:
            sensor = VerticalFarmSensor(
                device_id, sensor_type, mqtt_client, config_entry
            )
            sensors.append(sensor)
    
    async_add_entities(sensors)

class VerticalFarmSensor(SensorEntity):
    """Representation of a Vertical Farm sensor."""

    def __init__(
        self,
        device_id: int,
        sensor_type: str,
        mqtt_client: Any,
        config_entry: ConfigEntry,
    ) -> None:
        """Initialize the sensor."""
        self._device_id = device_id
        self._sensor_type = sensor_type
        self._mqtt_client = mqtt_client
        self._config_entry = config_entry
        self._state: StateType = None
        self._attributes: dict[str, Any] = {}
        
        # Set up unique ID
        self._attr_unique_id = f"vertical_farm_{device_id}_{sensor_type}"
        self._attr_name = f"Vertical Farm {device_id} {sensor_type.replace('_', ' ').title()}"
        
        # Set up device info
        self._attr_device_info = {
            "identifiers": {(DOMAIN, f"vertical_farm_{device_id}")},
            "name": f"Vertical Farm Device {device_id}",
            "manufacturer": "Vertical Farm",
            "model": "CropWaifu",
        }
        
        # Set up sensor properties
        sensor_config = SENSOR_TYPES[sensor_type]
        self._attr_device_class = sensor_config[ATTR_DEVICE_CLASS]
        self._attr_native_unit_of_measurement = sensor_config[ATTR_UNIT_OF_MEASUREMENT]
        self._attr_icon = sensor_config[ATTR_ICON]
        self._attr_state_class = sensor_config["state_class"]
        
        # Register for MQTT callbacks if client is available
        if mqtt_client:
            mqtt_client.add_message_callback("sensor_data", self._handle_sensor_data)
            mqtt_client.add_message_callback("heartbeat", self._handle_heartbeat)

    def _handle_sensor_data(self, data: dict[str, Any]) -> None:
        """Handle incoming sensor data."""
        board_id = data.get("board_id")
        if board_id != self._device_id:
            return
            
        # Update sensor state based on type
        if self._sensor_type == SENSOR_TEMPERATURE:
            self._state = data.get("temperature")
        elif self._sensor_type == SENSOR_HUMIDITY:
            self._state = data.get("humidity")
        elif self._sensor_type == SENSOR_LIGHT_INTENSITY:
            self._state = data.get("light_intensity")
        elif self._sensor_type == SENSOR_FAN_SPEED:
            self._state = data.get("fans_real")
        elif self._sensor_type == SENSOR_LED_BRIGHTNESS:
            self._state = data.get("led_abs")
        elif self._sensor_type == SENSOR_STATUS:
            status = data.get("status")
            if status == STATUS_OK:
                self._state = "OK"
            elif status == STATUS_ERROR:
                self._state = "Error"
            elif status == STATUS_WARNING:
                self._state = "Warning"
            else:
                self._state = "Unknown"
        
        # Update attributes
        self._attributes.update({
            ATTR_BOARD_ID: board_id,
            ATTR_TIMESTAMP: data.get("timestamp"),
        })
        
        # Schedule state update in the main event loop
        if self.hass:
            asyncio.run_coroutine_threadsafe(
                self._async_update_state(), self.hass.loop
            )

    def _handle_heartbeat(self, data: dict[str, Any]) -> None:
        """Handle heartbeat data."""
        board_id = data.get("board_id")
        if board_id != self._device_id:
            return
            
        # Update heartbeat info in attributes
        self._attributes.update({
            "last_heartbeat": data.get("timestamp"),
            "seq_no": data.get("seq_no"),
        })
        
        # Schedule state update in the main event loop
        if self.hass:
            asyncio.run_coroutine_threadsafe(
                self._async_update_state(), self.hass.loop
            )

    async def _async_update_state(self) -> None:
        """Update the entity state in the main event loop."""
        self.async_write_ha_state()

    @property
    def native_value(self) -> StateType:
        """Return the state of the sensor."""
        return self._state

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return the state attributes."""
        return self._attributes

    async def async_will_remove_from_hass(self) -> None:
        """Clean up when entity is removed."""
        if self._mqtt_client:
            self._mqtt_client.remove_message_callback("sensor_data", self._handle_sensor_data)
            self._mqtt_client.remove_message_callback("heartbeat", self._handle_heartbeat) 