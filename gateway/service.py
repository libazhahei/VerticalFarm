import asyncio
import threading
from collections.abc import Callable
from typing import Any

from paho.mqtt.client import Client, MQTTMessage

from .constants import SUBSCRIBE_CTRL_MSG_TOPIC, SUBSCRIBE_HEARTBEAT_TOPIC
from .msg import ControlMsg, HeartbeatMsg, MessageType, StatusMsg
from .publisher import ControlCommandPublisher
from .subscriber import CommandResponseSubscriber, HeartbeatSubscriber, MessageDispatcher


class MqttClientWrapper:
    """MqttClientWrapper is a wrapper class for managing MQTT client connections and message handling.

    Attributes:
        mqtt_client (Client): The MQTT client instance used for communication.
        dispatcher (MessageDispatcher): The dispatcher responsible for handling internal messages.
        mqtt_broker_host (str): The hostname or IP address of the MQTT broker.
        mqtt_broker_port (int): The port number of the MQTT broker (default is 1883).
        _mqtt_thread (threading.Thread | None): The background thread running the MQTT client loop.
        _asyncio_loop (asyncio.AbstractEventLoop | None): The asyncio event loop used for asynchronous operations.
        _topic_parsers (Dict[str, Callable[[str], MessageType]]): A dictionary mapping topics to their respective parser functions.

    Methods:
        __init__(dispatcher: MessageDispatcher, mqtt_broker_host: str, mqtt_broker_port: int = 1883, client_id: str = ""):
            Initializes the MqttClientWrapper instance with the given dispatcher, broker host, port, and client ID.

        register_topic_handler(topic: str, parser_func: Callable[[str], MessageType]):
            Registers a parser function for a specific topic. Automatically subscribes to the topic if the client is connected.

        _on_connect(client: Client, userdata, flags: dict, rc: int):
            Callback function triggered when the MQTT client connects to the broker. Subscribes to registered topics.

        _on_message(client: Client, userdata, msg: MQTTMessage):
            Callback function triggered when a message is received. Parses and dispatches the message using the registered parser.

        _mqtt_loop_in_thread():
            Runs the MQTT client loop in a separate thread.

        async start():
            Starts the MQTT client, connects to the broker, and begins the background thread for the client loop.

        async stop():
            Stops the MQTT client, disconnects from the broker, and terminates the client loop.

        is_connected() -> bool:
            Returns whether the MQTT client is currently connected to the broker.

    """

    mqtt_client: Client
    dispatcher: MessageDispatcher

    def __init__(self, dispatcher: MessageDispatcher, mqtt_broker_host: str, mqtt_broker_port: int = 1883, client_id: str = ""):
        self.dispatcher = dispatcher
        self.mqtt_client = Client(client_id=client_id)
        self.mqtt_client.on_connect = self._on_connect
        self.mqtt_client.on_message = self._on_message
        self.mqtt_broker_host = mqtt_broker_host
        self.mqtt_broker_port = mqtt_broker_port
        self._mqtt_thread: threading.Thread | None = None
        self._asyncio_loop: asyncio.AbstractEventLoop | None = None
        self._topic_parsers: dict[str, Callable[[str], MessageType]] = {}

    def register_topic_handler(self, topic: str, parser_func: Callable[[str], MessageType])-> None:
        """
        Registers a handler function for a specific MQTT topic and subscribes to the topic if the MQTT client is connected.

        Args:
            topic (str): The MQTT topic to register the handler for.
            parser_func (Callable[[str], MessageType]): A function that parses the incoming message payload for the specified topic.
                The function should accept a single string argument (the message payload) and return an instance of MessageType.

        Raises:
            None

        Side Effects:
            - Updates the internal `_topic_parsers` dictionary with the topic and its associated parser function.
            - Subscribes to the specified topic if the MQTT client is currently connected.

        """
        self._topic_parsers[topic] = parser_func
        if self.mqtt_client.is_connected():
            self.mqtt_client.subscribe(topic)

    def _on_connect(self, client: Client, userdata: Any, flags: dict, rc: int)-> None:
        """
        Handles the MQTT connection event.

        This method is called when the MQTT client establishes a connection
        to the broker. If the connection is successful (rc == 0), it subscribes
        to all topics specified in the `_topic_parsers` dictionary and logs
        the subscription. If the connection fails, it logs the failure with
        the corresponding return code.

        Args:
            client (Client): The MQTT client instance that triggered the connection event.
            userdata: User-defined data passed to the callback (unused in this method).
            flags (dict): Response flags sent by the broker.
            rc (int): The connection result code. A value of 0 indicates success, 
                      while other values indicate failure.

        """
        if rc == 0:
            for topic in self._topic_parsers.keys():
                client.subscribe(topic)
                print(f"MQTT: Subscribed to topic: {topic}")
        else:
            print(f"MQTT: Connection failed with code {rc}")

    def _on_message(self, client: Client, userdata: Any, msg: MQTTMessage)-> None:
        """
        Handles incoming MQTT messages, decodes the payload, and processes the message using a registered parser function.

        Args:
            client (Client): The MQTT client instance that received the message.
            userdata: User-defined data passed to the callback (unused in this implementation).
            msg (MQTTMessage): The MQTT message object containing the topic and payload.

        Behavior:
            - Decodes the message payload from UTF-8.
            - Retrieves the parser function associated with the message topic from `_topic_parsers`.
            - If a parser function is found:
                - Attempts to parse the decoded payload into an internal message format.
                - Dispatches the parsed message to the `dispatcher` using an asyncio coroutine if the asyncio loop is running.
                - Logs an error if the asyncio loop is not running or not set.
            - Logs an error if the parser function raises an exception during parsing or dispatching.
            - Logs a warning if no parser function is registered for the message topic.

        Raises:
            Exception: If an error occurs during message parsing or dispatching.

        """
        decoded_payload = msg.payload.decode('utf-8')
        parser_func = self._topic_parsers.get(msg.topic)
        if parser_func:
            try:
                internal_msg = parser_func(decoded_payload)
                if self._asyncio_loop and self._asyncio_loop.is_running():
                    asyncio.run_coroutine_threadsafe(
                        self.dispatcher.put_message(internal_msg), self._asyncio_loop
                    )
                else:
                    print("MQTT: Error: Asyncio loop not running or not set, cannot dispatch message.")
            except Exception as e:
                print(f"MQTT: Error parsing or dispatching message from topic {msg.topic}: {e}")
        else:
            print(f"MQTT: No parser registered for topic: {msg.topic}")

    def _mqtt_loop_in_thread(self) -> None:
        """
        Starts the MQTT client's loop in a separate thread.

        This method runs the MQTT client's `loop_forever` function, which 
        continuously processes network traffic, dispatches callbacks, and 
        handles reconnecting in case of disconnection. It is intended to 
        be executed in a separate thread to ensure non-blocking behavior 
        for the rest of the application.

        Note:
            Ensure that the MQTT client is properly configured before 
            invoking this method.

        """
        self.mqtt_client.loop_forever()

    async def start(self) -> None :
        """
        Starts the MQTT client and initializes the asyncio loop.

        This method performs the following actions:
        1. Retrieves the current asyncio event loop.
        2. Connects the MQTT client to the specified broker using the provided host and port.
        3. Starts the MQTT client in a background thread to handle MQTT operations.
        4. Waits for a short period to ensure the background thread is initialized.

        Note:
            - The MQTT client runs in a separate thread to avoid blocking the asyncio event loop.
            - Ensure that the MQTT broker host and port are correctly configured before calling this method.

        Raises:
            RuntimeError: If the asyncio event loop is not running.

        """
        self._asyncio_loop = asyncio.get_running_loop()
        print("MQTT: Connecting to broker...")
        self.mqtt_client.connect(self.mqtt_broker_host, self.mqtt_broker_port, 60)
        self._mqtt_thread = threading.Thread(target=self._mqtt_loop_in_thread, daemon=True)
        self._mqtt_thread.start()
        print("MQTT: Client started in background thread.")
        await asyncio.sleep(0.5)

    async def stop(self) -> None:
        """
        Stops the MQTT client by disconnecting it and stopping its loop.

        This method ensures that the MQTT client is properly disconnected if it is currently connected,
        and stops the loop to clean up resources. It also logs messages indicating the start and completion
        of the stopping process.

        Raises:
            Exception: If an error occurs during the disconnection or loop stopping process.

        """
        print("MQTT: Stopping client...")
        if self.mqtt_client.is_connected():
            self.mqtt_client.disconnect()
        self.mqtt_client.loop_stop()

        print("MQTT: Client stopped.")

    def is_connected(self) -> bool:
        """
        Check if the MQTT client is connected.

        Returns:
            bool: True if the MQTT client is connected, False otherwise.

        """
        return self.mqtt_client.is_connected()

class MQTTServiceContext:
    """MQTTServiceContext manages the MQTT service context for the VerticalFarm gateway.
    It initializes the necessary MQTT clients, message dispatchers, and subscribers for handling messages.

    Attributes:
        heartbeat_sub (HeartbeatSubscriber): Subscriber for heartbeat messages.
        msg_dispatcher (MessageDispatcher): Dispatcher for handling incoming messages.
        publish_client (Client): MQTT client for publishing messages.
        control_cmd_pub (ControlCommandPublisher): Publisher for control commands.
        command_status_sub (CommandResponseSubscriber): Subscriber for command response messages.
        subscribe_client (MqttClientWrapper): MQTT client for subscribing to topics.

    Methods:
        __init__(borker_host: str, broker_port: int = 1883, client_id: str = "mqtt_client"):
            Initializes the service with MQTT clients, message dispatchers, and subscribers.
        start() -> None:
            Starts the MQTT service context by initializing and starting the subscription client and message dispatcher.
        stop() -> None:
            Stops the MQTT service context by shutting down the subscribe client and message dispatcher.
        alive_devices_sync() -> list[int]:
            Synchronizes and retrieves a list of IDs for devices that are currently alive.
        is_alive_sync(board_id: int) -> bool:
            Checks if the specified board is alive by synchronously running the heartbeat check.
        is_alive(board_id: int) -> bool:
            Asynchronously checks if the specified board is alive by querying the heartbeat subsystem.
        alive_devices() -> list[int]:
            Asynchronously retrieves a list of IDs for devices that are currently alive.
        is_connected() -> bool:
            Checks if both the subscribe client and publish client are connected.
        publish_control_command(message: MessageType) -> None:
            Publishes a control command message to the specified topic.

    """

    borker_info: tuple[str, int]
    heartbeat_sub: HeartbeatSubscriber
    msg_dispatcher: MessageDispatcher
    publish_client: Client
    control_cmd_pub: ControlCommandPublisher
    command_status_sub: CommandResponseSubscriber

    def __init__(self, borker_host: str, broker_port: int = 1883, client_id: str = "mqtt_client") -> None:
        """
        Initializes the service with MQTT clients, message dispatchers, and subscribers.

        Args:
            broker_info (tuple[str, int]): A tuple containing the MQTT broker host and port.
            borker_host (str): The hostname of the MQTT broker.
            broker_port (int, optional): The port of the MQTT broker. Defaults to 1883.
            client_id (str, optional): The client ID for the MQTT clients. Defaults to "mqtt_client".

        Attributes:
            heartbeat_sub (HeartbeatSubscriber): Subscriber for heartbeat messages.
            msg_dispatcher (MessageDispatcher): Dispatcher for handling incoming messages.
            publish_client (Client): MQTT client for publishing messages.
            control_cmd_pub (ControlCommandPublisher): Publisher for control commands.
            command_status_sub (CommandResponseSubscriber): Subscriber for command response messages.
            subscribe_client (MqttClientWrapper): MQTT client for subscribing to topics.

        """
        self.heartbeat_sub = HeartbeatSubscriber()
        self.msg_dispatcher = MessageDispatcher()
        self.publish_client = Client(client_id=f"{client_id}_publisher")
        self.borker_info = (borker_host, broker_port)
        self.control_cmd_pub = ControlCommandPublisher(
            mqtt_client=self.publish_client, is_alive_func=self.heartbeat_sub.is_alive)
        self.command_status_sub = CommandResponseSubscriber(
            acknowledge_func=self.control_cmd_pub.acknowledge
        )
        self.subscribe_client = MqttClientWrapper(
            dispatcher=self.msg_dispatcher,
            mqtt_broker_host=borker_host,
            mqtt_broker_port=broker_port,
            client_id=f"{client_id}_subscriber"
        )
        self.subscribe_client.register_topic_handler(
        SUBSCRIBE_HEARTBEAT_TOPIC, HeartbeatSubscriber.parse_json
        )
        self.subscribe_client.register_topic_handler(
            SUBSCRIBE_CTRL_MSG_TOPIC, CommandResponseSubscriber.parse_json
        )
        self.msg_dispatcher.register_handler(
            HeartbeatMsg, self.heartbeat_sub.handle
        )
        self.msg_dispatcher.register_handler(
            StatusMsg, self.command_status_sub.handle
        )

    async def start(self) -> None:
        """
        Starts the MQTT service context by initializing and starting the 
        subscription client and message dispatcher.

        This method is asynchronous and ensures that the necessary components 
        for the MQTT service are properly started before proceeding.

        Raises:
            Any exceptions raised by `subscribe_client.start()` or 
            `msg_dispatcher.start()` will propagate from this method.

        """
        self.publish_client.connect(*self.borker_info, 60)
        await self.subscribe_client.start()
        await self.msg_dispatcher.start()
        print("MQTT Service Context started.")

    async def stop(self) -> None:
        """
        Stops the MQTT service context by shutting down the subscribe client 
        and message dispatcher.

        This method performs the following actions:
        1. Stops the subscribe client to terminate any ongoing subscriptions.
        2. Stops the message dispatcher to halt message processing.
        3. Prints a confirmation message indicating the service context has stopped.

        This is an asynchronous method and should be awaited to ensure proper 
        shutdown of the components.

        Raises:
            Any exceptions raised during the stopping of the subscribe client 
            or message dispatcher will propagate to the caller.

        """
        await self.subscribe_client.stop()
        await self.msg_dispatcher.stop()
        print("MQTT Service Context stopped.")

    def alive_devices_sync(self) -> list[int]:
        """
        Synchronizes and retrieves a list of IDs for devices that are currently alive.

        This method uses asyncio to run the heartbeat subscription's `get_alive_devices`
        coroutine and returns the result as a list of integers representing device IDs.

        Returns:
            list[int]: A list of integers representing the IDs of devices that are alive.

        """
        return asyncio.run(self.heartbeat_sub.get_alive_devices())

    def is_alive_sync(self, board_id: int) -> bool:
        """
        Checks if the specified board is alive by synchronously running the heartbeat check.

        Args:
            board_id (int): The unique identifier of the board to check.

        Returns:
            bool: True if the board is alive, False otherwise.

        """
        return asyncio.run(self.heartbeat_sub.is_alive(board_id))

    async def is_alive(self, board_id: int) -> bool:
        """
        Check if the specified board is alive by querying the heartbeat subsystem.

        Args:
            board_id (int): The unique identifier of the board to check.

        Returns:
            bool: True if the board is alive, False otherwise.

        """
        return await self.heartbeat_sub.is_alive(board_id)

    async def alive_devices(self) -> list[int]:
        """
        Asynchronously retrieves a list of IDs for devices that are currently alive.

        Returns:
            list[int]: A list of integers representing the IDs of devices that are alive.

        """
        return await self.heartbeat_sub.get_alive_devices()

    def is_connected(self) -> bool:
        """
        Check if both the subscribe client and publish client are connected.

        Returns:
            bool: True if both the subscribe client and publish client are connected, 
                  False otherwise.

        """
        return self.subscribe_client.is_connected() and self.publish_client.is_connected()

    async def publish_control_command(self, message: MessageType) -> None:
        """
        Publishes a control command message to the specified topic.

        Args:
            message (MessageType): The message to be published. Must be an instance of `ControlMsg`.

        Raises:
            TypeError: If the provided message is not an instance of `ControlMsg`.

        Returns:
            None: This method is asynchronous and does not return a value.

        """
        if not isinstance(message, ControlMsg):
            raise TypeError("Message must be an instance of StatusMsg")
        await self.control_cmd_pub.add_msg(message, SUBSCRIBE_CTRL_MSG_TOPIC)





