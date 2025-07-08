import asyncio
from dataclasses import dataclass
from typing import Awaitable, Callable, Dict
from paho.mqtt.client import Client as MQTTClient
from paho.mqtt.client import MQTT_ERR_SUCCESS

from gateway.msg import ControlMsg, MessageType
from .constants import PUBLISH_ERR_MAX_RETRIES, PUBLISH_CTRL_QOS, PUBLISH_RESENT_MAX_RETRIES, PUBLISH_TIMEOUT_SECONDS

@dataclass
class QueueMessage:
    topic: str
    payload: ControlMsg
    stop_event: asyncio.Event
    retries_left: int

    @classmethod
    def from_dict(cls, data: Dict) -> 'QueueMessage':
        return cls(
            topic=data["topic"],
            payload=ControlMsg.from_dict(data["payload"]),
            stop_event=data["stop_event"],
            retries_left=data["retries_left"]
        )
    

class ControlCommandPublisher: 
    mqtt_client: MQTTClient
    max_retries: int 
    timeout: int
    msgs: Dict[int, QueueMessage]

    def __init__(self, mqtt_client: MQTTClient, is_alive_func: Callable[[int], Awaitable[bool]], max_retries: int = PUBLISH_RESENT_MAX_RETRIES, timeout: int = PUBLISH_TIMEOUT_SECONDS):
        self.mqtt_client = mqtt_client
        self.max_retries = max_retries
        self.timeout = timeout
        self.msgs = {}
        self.is_alive_func = is_alive_func

    async def add_msg(self, message: MessageType, topic: str) -> None:
        if not isinstance(message, ControlMsg):
            raise TypeError("Message must be an instance of ControlMsg")
        
        stop_event = asyncio.Event() 
        self.msgs[message.get_message_id()] = QueueMessage.from_dict({
            "topic": topic,
            "payload": message,
            "stop_event": stop_event,
            "retries_left": self.max_retries
        })
        asyncio.create_task(self.try_publish(message.get_message_id()))

    def acknowledge(self, message_id: int) -> None:
        if message_id in self.msgs:
            msg_info = self.msgs[message_id]
            msg_info.stop_event.set()  # Signal the stop event to stop waiting
            del self.msgs[message_id]

    def fail_msg(self, message_id: int) -> None:
        if message_id in self.msgs:
            msg_info = self.msgs[message_id]
            msg_info.stop_event.set()
            del self.msgs[message_id]


    def safe_publish(self, message: MessageType, topic: str) -> bool:
        for attempt in range(PUBLISH_ERR_MAX_RETRIES):
            try:
                info = self.mqtt_client.publish(topic, message.to_json(), qos= PUBLISH_CTRL_QOS)
                if info.rc == MQTT_ERR_SUCCESS:
                    return True
                else:
                    print(f"[MQTT ERROR] Publish attempt {attempt+1} failed for message {message.get_message_id()}: rc={info.rc}")
            except Exception as e:
                print(f"[EXCEPTION] Publish attempt {attempt+1} failed for message {message.get_message_id()}: {e}")
        return False

    async def try_publish(self, message_id: int) -> None:
        if message_id not in self.msgs:
            return
        msg_info = self.msgs[message_id]

        while msg_info.retries_left > 0:
            if self.is_alive_func is None or not await self.is_alive_func(msg_info.payload.board_id):
                print(f"[DEVICE NOT ALIVE] Cannot publish message {message_id}, device {msg_info.payload.board_id} is not alive.")
                break
            published = self.safe_publish(msg_info.payload, msg_info.topic)
            if not published:
                print(f"[PUBLISH FAILED] Retrying message {message_id}, retries left: {msg_info.retries_left}")
                self.fail_msg(message_id)
                return
            try:
                await asyncio.wait_for(msg_info.stop_event.wait(), timeout=self.timeout)
                return  # Acknowledged, exit the loop
            except asyncio.TimeoutError:
                msg_info.retries_left -= 1
                if msg_info.retries_left == 0:
                    self.fail_msg(message_id)
                    raise TimeoutError(f"Message with ID {message_id} could not be acknowledged after {self.max_retries} retries.")
                else:
                    print(f"[TIMEOUT] Message {message_id} not acknowledged, retries left: {msg_info.retries_left}")
                    continue

    