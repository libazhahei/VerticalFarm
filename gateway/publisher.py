import asyncio
from collections.abc import Awaitable, Callable
from dataclasses import dataclass

from paho.mqtt.client import MQTT_ERR_SUCCESS, Client as MQTTClient

from gateway.msg import ControlMsg, MQTTMessageType

from .constants import PUBLISH_CTRL_QOS, PUBLISH_ERR_MAX_RETRIES, PUBLISH_RESENT_MAX_RETRIES, PUBLISH_TIMEOUT_SECONDS


@dataclass
class QueueMessage:
    """QueueMessage is a data class that represents a message to be published to a queue.

    Attributes:
        topic (str): The topic to which the message belongs.
        payload (ControlMsg): The payload of the message, represented as a ControlMsg object.
        stop_event (asyncio.Event): An asyncio event used to signal when the operation should stop.
        retries_left (int): The number of retries left for publishing the message.

    Methods:
        from_dict(cls, data: Dict) -> QueueMessage:
            Creates a QueueMessage instance from a dictionary.

    Args:
                data (Dict): A dictionary containing the keys 'topic', 'payload', 'stop_event', and 'retries_left'.

    Returns:
                QueueMessage: An instance of QueueMessage initialized with the provided data.

    """

    topic: str
    payload: ControlMsg
    stop_event: asyncio.Event
    retries_left: int

    @classmethod
    def from_dict(cls, data: dict) -> 'QueueMessage':
        """Creates a QueueMessage instance from a dictionary."""
        return cls(
            topic=data["topic"],
            payload=data["payload"],
            stop_event=data["stop_event"],
            retries_left=data["retries_left"]
        )

    def get_message_id(self) -> int | None:
        """Returns the message ID from the payload."""
        return self.payload.get_message_id() if self.payload else None




class ControlCommandPublisher:
    """A class responsible for publishing control commands to an MQTT broker and managing message acknowledgments.

    Attributes:
        mqtt_client (MQTTClient): The MQTT client used for publishing messages.
        max_retries (int): Maximum number of retries for publishing a message.
        timeout (int): Timeout duration (in seconds) for waiting for message acknowledgment.
        msgs (Dict[int, QueueMessage]): A dictionary storing messages being published, keyed by their message IDs.
        is_alive_func (Callable[[int], Awaitable[bool]]): A function to check if a device is alive, given its board ID.

    Methods:
        __init__(mqtt_client, is_alive_func, max_retries, timeout):
            Initializes the ControlCommandPublisher instance with the given MQTT client, device status function, 
            maximum retries, and timeout.
        add_msg(message, topic):
            Adds a message to the publishing queue and starts the publishing process asynchronously.
            Raises a TypeError if the message is not an instance of ControlMsg.
        acknowledge(message_id):
            Acknowledges a message by its ID, signaling its stop event and removing it from the queue.
        fail_msg(message_id):
            Marks a message as failed by its ID, signaling its stop event and removing it from the queue.
        safe_publish(message, topic):
            Attempts to publish a message to the specified topic with a maximum number of retries.
            Returns True if the message is successfully published, otherwise False.
        try_publish(message_id):
            Asynchronously attempts to publish a message by its ID, retrying if necessary and handling acknowledgment 
            or timeout scenarios.

    """

    mqtt_client: MQTTClient
    max_retries: int
    timeout: float
    msgs: dict[int, QueueMessage]

    def __init__(self, mqtt_client: MQTTClient, is_alive_func: Callable[[int], Awaitable[bool]], 
                 max_retries: int = PUBLISH_RESENT_MAX_RETRIES, timeout: float = PUBLISH_TIMEOUT_SECONDS) -> None:
        self.mqtt_client = mqtt_client
        self.max_retries = max_retries
        self.timeout = timeout
        self.msgs = {}
        self.is_alive_func = is_alive_func

    async def add_msg(self, message: MQTTMessageType, topic: str) -> None:
        """Adds a message to the publishing queue and initiates the publishing process.

        Args:
            message (MessageType): The message to be published. Must be an instance of `ControlMsg`.
            topic (str): The topic to which the message will be published.

        Raises:
            TypeError: If the provided `message` is not an instance of `ControlMsg`.

        Notes:
            - The message is stored in the `msgs` dictionary with its unique message ID as the key.
            - A `QueueMessage` object is created from the provided message and topic, 
              along with a stop event and the maximum number of retries.
            - A background task is created to attempt publishing the message using `try_publish`.

        """
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
        """Acknowledges the receipt of a message by its ID and stops any associated waiting process.

        Args:
            message_id (int): The unique identifier of the message to acknowledge.

        Behavior:
            - If the message ID exists in the `msgs` dictionary, it retrieves the associated
              message information, signals the stop event to halt any waiting process, and
              removes the message from the dictionary.
            - If the message ID does not exist, no action is taken.

        """
        if message_id in self.msgs:
            msg_info = self.msgs[message_id]
            msg_info.stop_event.set()  # Signal the stop event to stop waiting
            del self.msgs[message_id]

    def fail_msg(self, message_id: int) -> None:
        """Handles the failure of a message by stopping its associated event and removing it from the message tracking dictionary.

        Args:
            message_id (int): The unique identifier of the message to be marked as failed.

        Returns:
            None

        """
        if message_id in self.msgs:
            msg_info = self.msgs[message_id]
            msg_info.stop_event.set()
            del self.msgs[message_id]


    def safe_publish(self, message: MQTTMessageType, topic: str) -> bool:
        """Safely publishes a message to a specified MQTT topic with retry logic.

        Args:
            message (MessageType): The message object to be published. It must have a `to_json()` method 
                                   to convert the message to a JSON string and a `get_message_id()` method 
                                   for identifying the message.
            topic (str): The MQTT topic to which the message will be published.

        Returns:
            bool: True if the message is successfully published, False otherwise.

        Raises:
            Exception: If an unexpected error occurs during publishing.

        Notes:
            - The function attempts to publish the message up to `PUBLISH_ERR_MAX_RETRIES` times.
            - If the `publish()` method of the MQTT client returns a non-success return code (`info.rc`), 
              the function logs the error and retries.
            - Exceptions during publishing are caught and logged, and the function retries until the 
              maximum number of attempts is reached.

        """
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
        """Attempts to publish a message with the given message ID. Retries the operation
        if the message fails to publish or is not acknowledged within the timeout period.

        Args:
            message_id (int): The ID of the message to be published.

        Returns:
            None

        Raises:
            TimeoutError: If the message could not be acknowledged after the maximum number of retries.

        Behavior:
            - Checks if the message ID exists in the `msgs` dictionary. If not, exits early.
            - Verifies if the device associated with the message is alive using `is_alive_func`.
              If the device is not alive, logs the issue and exits.
            - Attempts to publish the message using `safe_publish`. If publishing fails, logs the failure,
              marks the message as failed using `fail_msg`, and exits.
            - Waits for an acknowledgment signal (`stop_event`) within the specified timeout.
              If the timeout is exceeded, decrements the retry count and retries the operation.
            - If the retry count reaches zero, marks the message as failed and raises a `TimeoutError`.

        """
        if message_id not in self.msgs:
            raise ValueError(f"Message ID {message_id} not found in msgs.")
        msg_info = self.msgs[message_id]

        while msg_info.retries_left > 0:
            # print(await self.is_alive_func(msg_info.payload.board_id))
            if self.is_alive_func is None or not await self.is_alive_func(msg_info.payload.board_id):
                print(f"[DEVICE NOT ALIVE] Cannot publish message {message_id}, device {msg_info.payload.board_id} is not alive.")
                self.fail_msg(message_id)
                break
            published = self.safe_publish(msg_info.payload, msg_info.topic)
            if not published:
                print(f"[PUBLISH FAILED] Retrying message {message_id}, retries left: {msg_info.retries_left}. This may indicate publish failure.")
                self.fail_msg(message_id)
                await asyncio.sleep(self.timeout)  # Wait before retrying
                continue
            try:
                await asyncio.wait_for(msg_info.stop_event.wait(), timeout=self.timeout)
                return  # Acknowledged, exit the loop
            except TimeoutError:
                msg_info.retries_left -= 1
                if msg_info.retries_left == 0:
                    self.fail_msg(message_id)
                    raise TimeoutError(f"Message with ID {message_id} could not be acknowledged after {self.max_retries} retries.")
                else:
                    print(f"[TIMEOUT] Message {message_id} not acknowledged, retries left: {msg_info.retries_left}")
                    continue

