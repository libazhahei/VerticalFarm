"""Config flow for Vertical Farm MQTT integration."""
from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.data_entry_flow import FlowResult

from .const import (
    CONF_DEVICE_IDS,
    CONF_MQTT_BROKER,
    CONF_MQTT_PASSWORD,
    CONF_MQTT_PORT,
    CONF_MQTT_USERNAME,
    DEFAULT_MQTT_BROKER,
    DEFAULT_MQTT_PORT,
    DOMAIN,
)

_LOGGER = logging.getLogger(__name__)

class VerticalFarmMQTTConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Vertical Farm MQTT."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle the initial step."""
        if user_input is not None:
            return self.async_create_entry(
                title=f"Vertical Farm MQTT ({user_input[CONF_MQTT_BROKER]})",
                data=user_input,
            )

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_MQTT_BROKER, default=DEFAULT_MQTT_BROKER): str,
                    vol.Required(CONF_MQTT_PORT, default=DEFAULT_MQTT_PORT): int,
                    vol.Optional(CONF_MQTT_USERNAME): str,
                    vol.Optional(CONF_MQTT_PASSWORD): str,
                    vol.Required(CONF_DEVICE_IDS, default="0,1,2"): str,
                }
            ),
        ) 