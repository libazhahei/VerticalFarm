"""Vertical Farm MQTT integration for Home Assistant."""
from __future__ import annotations

import logging
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant

from .const import DOMAIN
from .mqtt_client import VerticalFarmMQTTClient

_LOGGER = logging.getLogger(__name__)

PLATFORMS: list[Platform] = [
    Platform.SENSOR,
]

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Vertical Farm MQTT from a config entry."""
    hass.data.setdefault(DOMAIN, {})
    
    # Get configuration
    config = entry.data
    broker = config.get("mqtt_broker", "localhost")
    port = config.get("mqtt_port", 5001)
    username = config.get("mqtt_username")
    password = config.get("mqtt_password")
    
    # Create and initialize MQTT client
    mqtt_client = VerticalFarmMQTTClient(
        broker=broker,
        port=port,
        username=username,
        password=password,
    )
    
    # Connect to MQTT broker
    if await mqtt_client.connect():
        _LOGGER.info("Successfully connected to MQTT broker")
        hass.data[DOMAIN]["mqtt_client"] = mqtt_client
    else:
        _LOGGER.error("Failed to connect to MQTT broker")
        return False
    
    # Store the config entry
    hass.data[DOMAIN][entry.entry_id] = entry.data
    
    # Forward the setup to the relevant platforms
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    
    entry.async_on_unload(entry.add_update_listener(async_reload_entry))
    
    return True

async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    
    if unload_ok:
        # Disconnect MQTT client
        if "mqtt_client" in hass.data[DOMAIN]:
            await hass.data[DOMAIN]["mqtt_client"].disconnect()
            del hass.data[DOMAIN]["mqtt_client"]
        
        hass.data[DOMAIN].pop(entry.entry_id)
    
    return unload_ok

async def async_reload_entry(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Reload config entry."""
    await hass.config_entries.async_reload(entry.entry_id) 