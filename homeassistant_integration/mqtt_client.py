"""MQTT client for Vertical Farm integration."""
from __future__ import annotations

import asyncio
import json
import logging
from datetime import datetime
from typing import Any, Callable

import paho.mqtt.client as mqtt

from .const import (
    MQTT_HEARTBEAT_TOPIC,
    MQTT_RESPONSE_TOPIC,
)

_LOGGER = logging.getLogger(__name__)

class VerticalFarmMQTTClient:
    """MQTT client for Vertical Farm system - Monitor Only."""

    def __init__(
        self,
        broker: str,
        port: int,
        username: str | None = None,
        password: str | None = None,
        client_id: str = "vertical_farm_ha_monitor",
    ) -> None:
        """Initialize the MQTT client."""
        self.broker = broker
        self.port = port
        self.username = username
        self.password = password
        self.client_id = client_id
        
        self.client = mqtt.Client(client_id=client_id)
        self.client.on_connect = self._on_connect
        self.client.on_message = self._on_message
        self.client.on_disconnect = self._on_disconnect
        
        if username and password:
            self.client.username_pw_set(username, password)
        
        self._message_callbacks: dict[str, list[Callable]] = {
            "heartbeat": [],
            "sensor_data": [],
            "status": [],
        }
        
        self._connected = False

    def _on_connect(self, client: mqtt.Client, userdata: Any, flags: dict, rc: int) -> None:
        """Handle MQTT connection."""
        if rc == 0:
            _LOGGER.info("Connected to MQTT broker")
            self._connected = True
            
            # Subscribe to topics for monitoring only
            client.subscribe(MQTT_HEARTBEAT_TOPIC)
            client.subscribe(MQTT_RESPONSE_TOPIC)
        else:
            _LOGGER.error("Failed to connect to MQTT broker: %s", rc)
            self._connected = False

    def _on_disconnect(self, client: mqtt.Client, userdata: Any, rc: int) -> None:
        """Handle MQTT disconnection."""
        _LOGGER.info("Disconnected from MQTT broker")
        self._connected = False

    def _on_message(self, client: mqtt.Client, userdata: Any, msg: mqtt.MQTTMessage) -> None:
        """Handle incoming MQTT messages."""
        try:
            topic = msg.topic
            payload = msg.payload.decode("utf-8")
            
            _LOGGER.debug("Received message on topic %s: %s", topic, payload)
            
            if topic == MQTT_HEARTBEAT_TOPIC:
                self._handle_heartbeat(payload)
            elif topic == MQTT_RESPONSE_TOPIC:
                self._handle_status_response(payload)
            else:
                _LOGGER.warning("Unknown topic: %s", topic)
                
        except Exception as e:
            _LOGGER.error("Error handling MQTT message: %s", e)

    def _handle_heartbeat(self, payload: str) -> None:
        """Handle heartbeat messages."""
        try:
            data = json.loads(payload)
            # 支持两种字段名格式
            board_id = data.get("boardID") or data.get("board_id")
            seq_no = data.get("seqNo") or data.get("seq_no")
            
            if board_id is not None and seq_no is not None:
                message_data = {
                    "type": "heartbeat",
                    "board_id": board_id,
                    "seq_no": seq_no,
                    "timestamp": data.get("timestamp") or datetime.now().isoformat(),
                }
                
                for callback in self._message_callbacks["heartbeat"]:
                    if asyncio.iscoroutinefunction(callback):
                        asyncio.create_task(callback(message_data))
                    else:
                        callback(message_data)
                        
        except json.JSONDecodeError as e:
            _LOGGER.error("Invalid JSON in heartbeat message: %s", e)

    def _handle_status_response(self, payload: str) -> None:
        """Handle status response messages."""
        try:
            data = json.loads(payload)
            # 支持两种字段名格式
            board_id = data.get("boardID") or data.get("board_id")
            status = data.get("status")
            message_id = data.get("messageID") or data.get("message_id")
            timestamp = data.get("timestamp")
            
            if board_id is not None:
                message_data = {
                    "type": "sensor_data",
                    "board_id": board_id,
                    "status": status,
                    "message_id": message_id,
                    "timestamp": timestamp or datetime.now().isoformat(),
                    # 添加传感器数据字段
                    "temperature": data.get("temperature"),
                    "humidity": data.get("humidity"),
                    "light_intensity": data.get("light_intensity"),
                    "fans_real": data.get("fans_real"),
                    "led_abs": data.get("led_abs"),
                }
                
                for callback in self._message_callbacks["sensor_data"]:
                    if asyncio.iscoroutinefunction(callback):
                        asyncio.create_task(callback(message_data))
                    else:
                        callback(message_data)
                        
        except json.JSONDecodeError as e:
            _LOGGER.error("Invalid JSON in status message: %s", e)

    def add_message_callback(self, message_type: str, callback: Callable) -> None:
        """Add a callback for message handling."""
        if message_type in self._message_callbacks:
            self._message_callbacks[message_type].append(callback)

    def remove_message_callback(self, message_type: str, callback: Callable) -> None:
        """Remove a callback for message handling."""
        if message_type in self._message_callbacks:
            try:
                self._message_callbacks[message_type].remove(callback)
            except ValueError:
                pass

    async def connect(self) -> bool:
        """Connect to the MQTT broker."""
        try:
            self.client.connect(self.broker, self.port, 60)
            self.client.loop_start()
            return True
        except Exception as e:
            _LOGGER.error("Failed to connect to MQTT broker: %s", e)
            return False

    async def disconnect(self) -> None:
        """Disconnect from the MQTT broker."""
        if self._connected:
            self.client.loop_stop()
            self.client.disconnect()
            self._connected = False

    def is_connected(self) -> bool:
        """Check if connected to MQTT broker."""
        return self._connected 