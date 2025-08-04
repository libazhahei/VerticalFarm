import asyncio
import threading
import traceback
from collections.abc import Callable
from datetime import datetime
from typing import Any, List, Optional

from bleak import BleakClient, BleakScanner
from bleak.backends.characteristic import BleakGATTCharacteristic
from bleak.backends.device import BLEDevice
from bleak.exc import BleakError
from paho.mqtt.client import Client, MQTTMessage

from data.tables import BoardData, BoardDataBatchWriter

from .constants import (
    DEVICE_PREFIX,
    EXPOLATION_RETRY_DELAY_SECONDS,
    MAX_EXPLORATION_TRIES,
    MAX_EXPOLATION_TIMEOUT_SECONDS,
    PUBLISH_CTRL_MSG_TOPIC,
    RECONNECTION_DELAY_SECONDS,
    SUBSCRIBE_CTRL_MSG_TOPIC,
    SUBSCRIBE_HEARTBEAT_TOPIC,
    get_characteristic_uuid,
)
from .msg import (
    BLEMessageType,
    ControlMsg,
    HeartbeatMsg,
    Mode,
    MQTTMessageType,
    SensorDataMsg,
    StatusMsg,
)
from .publisher import ControlCommandPublisher
from .subscriber import (
    CommandResponseSubscriber,
    CommonDataRetriver,
    HeartbeatSubscriber,
    MessageDispatcher,
    SensorDataSubscriber,
)


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

    def __init__(
        self,
        dispatcher: MessageDispatcher,
        mqtt_broker_host: str,
        mqtt_broker_port: int = 1883,
        client_id: str = "",
    ):
        self.dispatcher = dispatcher
        self.mqtt_client = Client(client_id=client_id)
        self.mqtt_client.on_connect = self._on_connect
        self.mqtt_client.on_message = self._on_message
        self.mqtt_broker_host = mqtt_broker_host
        self.mqtt_broker_port = mqtt_broker_port
        self._mqtt_thread: threading.Thread | None = None
        self._asyncio_loop: asyncio.AbstractEventLoop | None = None
        self._topic_parsers: dict[str, Callable[[str], MQTTMessageType]] = {}

    def register_topic_handler(
        self, topic: str, parser_func: Callable[[str], MQTTMessageType]
    ) -> None:
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

    def _on_connect(self, client: Client, userdata: Any, flags: dict, rc: int) -> None:
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

    def _on_message(self, client: Client, userdata: Any, msg: MQTTMessage) -> None:
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
        decoded_payload = msg.payload.decode("utf-8")
        parser_func = self._topic_parsers.get(msg.topic)
        if parser_func:
            try:
                internal_msg = parser_func(decoded_payload)
                if self._asyncio_loop and self._asyncio_loop.is_running():
                    asyncio.run_coroutine_threadsafe(
                        self.dispatcher.put_message(internal_msg), self._asyncio_loop
                    )
                else:
                    print(
                        "MQTT: Error: Asyncio loop not running or not set, cannot dispatch message."
                    )
            except Exception as e:
                print(
                    f"MQTT: Error parsing or dispatching message from topic {msg.topic}: {e}"
                )
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

    async def start(self) -> None:
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
        self._mqtt_thread = threading.Thread(
            target=self._mqtt_loop_in_thread, daemon=True
        )
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
    current_msg: Optional[ControlMsg]

    def __init__(
        self, broker_host: str, broker_port: int = 1883, client_id: str = "mqtt_client"
    ) -> None:
        """
        Initializes the service with MQTT clients, message dispatchers, and subscribers.

        Args:
            broker_host (tuple[str, int]): A tuple containing the MQTT broker host and port.
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
        self.borker_info = (broker_host, broker_port)
        self.control_cmd_pub = ControlCommandPublisher(
            mqtt_client=self.publish_client, is_alive_func=self.heartbeat_sub.is_alive
        )
        self.command_status_sub = CommandResponseSubscriber(
            acknowledge_func=self.control_cmd_pub.acknowledge
        )
        self.subscribe_client = MqttClientWrapper(
            dispatcher=self.msg_dispatcher,
            mqtt_broker_host=broker_host,
            mqtt_broker_port=broker_port,
            client_id=f"{client_id}_subscriber",
        )
        self.subscribe_client.register_topic_handler(
            SUBSCRIBE_HEARTBEAT_TOPIC, HeartbeatSubscriber.parse_json
        )
        self.subscribe_client.register_topic_handler(
            SUBSCRIBE_CTRL_MSG_TOPIC, CommandResponseSubscriber.parse_json
        )
        self.msg_dispatcher.register_handler(HeartbeatMsg, self.heartbeat_sub.handle)
        self.msg_dispatcher.register_handler(StatusMsg, self.command_status_sub.handle)
        self.current_msg = None

    async def start(self) -> None:
        """
        Starts the MQTT service context by initializing and starting the
        subscription client and message dispatcher.

        This method is asynchronous and ensures that the necessary components
        for the MQTT service are properly started before proceeding.

        Raises:
            Any exceptions raised by `subscribe_client.start()` or
            `msg_dispatcher.start()` will propagate from this method.
            Connection errors or issues with the MQTT broker may also raise exceptions.

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
        return (
            self.subscribe_client.is_connected() and self.publish_client.is_connected()
        )

    async def publish_control_command(self, message: MQTTMessageType) -> None:
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
        await self.control_cmd_pub.add_msg(message, PUBLISH_CTRL_MSG_TOPIC)

    async def set_board_expect_env(
        self, board_id: int, temperature: float, par: float
    ) -> None:
        """
        Set the expected environment for a board by sending a control command with the given temperature and PAR (light intensity).

        Args:
            board_id (int): The ID of the board to control.
            temperature (float): The target temperature (0-100).
            par (float): The target PAR/light intensity (0-100).
        """
        light_intensity = int(par * 20.105)
        ctrl_msg = ControlMsg(
            board_id=board_id,
            mode=Mode.ABSOLUTE,
            fan=0,
            led=0,
            temperature=temperature,
            light_intensity=light_intensity,
        )
        await self.publish_control_command(ctrl_msg)
        self.current_msg = ctrl_msg

    async def get_current_command(self) -> Optional[ControlMsg]:
        """
        Get the current control command being sent to the board.

        Returns:
            ControlMsg | None: The current control command if available, otherwise None.
        """
        return self.current_msg


class BLEClientWrapper:
    """
    BLEClientWrapper is a class designed to manage Bluetooth Low Energy (BLE) connections and notifications
    for multiple devices. It provides functionality to connect to BLE devices, subscribe to notifications,
    and handle incoming data.

    Attributes:
        dispatcher (MessageDispatcher): An instance of MessageDispatcher used to handle parsed BLE messages.
        device_id_lists (set[int]): A set of device IDs to manage connections for.
        ble_clients (dict[int, BleakClient]): A dictionary mapping device IDs to their respective BleakClient instances.
        is_running (bool): Indicates whether the BLE client wrapper is actively running.
        ble_devices (dict[int, BLEDevice]): A dictionary mapping device IDs to their respective BLEDevice instances.
        connection_tasks (dict[int, asyncio.Task]): A dictionary mapping device IDs to their respective asyncio tasks for connection management.

    Methods:
        __init__(device_id_lists: list[int], dispatcher: MessageDispatcher) -> None:
            Initializes the BLEClientWrapper with a list of device IDs and a message dispatcher.
        register_notification_handler(board_id: int, handler: Callable[[bytearray], BLEMessageType]) -> None:
            Registers a handler function for processing notifications from a specific BLE device.
        on_ble_notification(characteristic: BleakGATTCharacteristic, data: bytearray) -> None:
            Handles incoming BLE notifications, parses the data using registered handlers, and dispatches messages.
        connect_and_subscribe(board_id: int, device: BLEDevice) -> None:
            Manages the connection and subscription process for a specific BLE device, including reconnection logic.
        start() -> None:
            Starts the BLE client wrapper, discovers devices, and initializes connections.
        stop() -> None:
            Stops the BLE client wrapper, cancels connection tasks, and disconnects all BLE clients.
        is_connected() -> bool:
            Checks if any BLE client is currently connected.

    """

    dispatcher: MessageDispatcher
    device_id_lists: set[int]
    ble_clients: dict[int, BleakClient]
    is_running: bool
    ble_devices: dict[int, BLEDevice | None]
    connection_tasks: dict[int, asyncio.Task]

    def __init__(
        self, device_id_lists: list[int], dispatcher: MessageDispatcher
    ) -> None:
        """
        Initializes the service with the provided device IDs and message dispatcher.

        Args:
            device_id_lists (list[int]): A list of device IDs to be managed by the service.
            dispatcher (MessageDispatcher): An instance of MessageDispatcher to handle message dispatching.

        Attributes:
            device_id_lists (set[int]): A set of unique device IDs.
            dispatcher (MessageDispatcher): The message dispatcher instance.
            ble_clients (dict): A dictionary to store BLE clients.
            ble_devices (dict): A dictionary to store BLE devices.
            _asyncio_loop (asyncio.AbstractEventLoop | None): The asyncio event loop, initialized as None.
            is_running (bool): A flag indicating whether the service is running.
            _characteristic_parsers (dict): A dictionary to store characteristic parsers.
            connection_tasks (dict): A dictionary to store connection tasks.

        """
        self.device_id_lists = set(device_id_lists)
        self.dispatcher = dispatcher
        self.ble_clients = {}
        # Initialize ble_devices with all device IDs set to None
        self.ble_devices = dict.fromkeys(self.device_id_lists)
        self._asyncio_loop: asyncio.AbstractEventLoop | None = None
        self.is_running = False
        self._characteristic_parsers = {}
        self.connection_tasks = {}

    def register_notification_handler(
        self, board_id: int, handler: Callable[[bytearray], BLEMessageType]
    ) -> None:
        """
        Registers a notification handler for a specific board ID.

        This method associates a handler function with a given board ID. The handler
        function will be invoked whenever a notification is received for the specified
        board. The handler is expected to process the incoming data and return a
        BLEMessageType.

        Args:
            board_id (int): The unique identifier of the board for which the handler
                is being registered.
            handler (Callable[[bytearray], BLEMessageType]): A callable function that
                takes a bytearray as input and returns a BLEMessageType. This function
                will handle notifications for the specified board.

        Returns:
            None

        """
        self._characteristic_parsers[get_characteristic_uuid(board_id)] = handler

    async def on_ble_notification(
        self, characteristic: BleakGATTCharacteristic, data: bytearray
    ) -> None:
        """
        Handles BLE notifications received from a specific characteristic.

        This method is triggered when a BLE notification is received. It identifies
        the characteristic UUID, retrieves the corresponding parser function, and processes
        the notification data. If a parser function is registered for the characteristic,
        it parses the data and dispatches the resulting internal message. If no parser is
        registered, it logs a message indicating the absence of a parser.

        Args:
            characteristic (BleakGATTCharacteristic): The BLE characteristic that triggered the notification.
            data (bytearray): The raw data received from the BLE notification.

        Raises:
            Exception: If an error occurs during parsing or dispatching the BLE notification.

        Notes:
            - The characteristic UUID is used to look up the appropriate parser function.
            - If no parser function is found for the characteristic UUID, a message is logged.
            - Errors during parsing or dispatching are caught and logged for debugging purposes.

        """
        char_uuid = str(characteristic.uuid)
        parser_func = self._characteristic_parsers.get(char_uuid)
        if parser_func:
            try:
                internal_msg = parser_func(data)
                await self.dispatcher.put_message(internal_msg)
            except Exception as e:
                print(
                    f"BLE: Error parsing or dispatching BLE notification for {char_uuid} (data: {data.hex()}): {e}"
                )
        else:
            print(f"BLE: No parser registered for characteristic: {char_uuid}")

    async def connect_and_subscribe(self, board_id: int, device: BLEDevice) -> None:
        """
        Establishes a connection to a BLE device and subscribes to its notifications.

        This asynchronous method attempts to connect to the specified BLE device and
        subscribes to notifications for characteristics associated with the given board ID.
        It handles reconnection attempts in case of errors or disconnections and ensures
        proper cleanup during shutdown.

        Args:
            board_id (int): The unique identifier for the board associated with the BLE device.
            device (BLEDevice): The BLE device to connect to.

        Raises:
            BleakError: If there is an error during connection or subscription.
            asyncio.CancelledError: If the connection task is cancelled.
            Exception: For any unexpected errors during the connection process.

        Notes:
            - The method uses a reconnection delay defined by `RECONNECTION_DELAY_SECONDS`
              to retry connections in case of failures.
            - Subscriptions are attempted for all characteristics defined in
              `self._characteristic_parsers`.
            - The `disconnected_callback` is used to handle disconnection events.
            - Proper cleanup is performed by disconnecting the client during shutdown.

        """
        client: BleakClient | None = None
        while self.is_running:
            try:
                if client is None:
                    print(device.address)
                    client = BleakClient(
                        device,
                        disconnected_callback=lambda c: print(
                            f"BLE: Disconnected from {device.name} (ID: {board_id})"
                        ),
                    )
                    self.ble_clients[board_id] = client  # Store the client instance

                if not client.is_connected:
                    print(
                        f"BLE: Connecting to device {device.name} (ID: {board_id})..."
                    )
                    await client.connect()
                    print(f"BLE: Connected to device {device.name} (ID: {board_id}).")

                    """
                    for _board_id in self._characteristic_parsers.keys():
                    """

                    try:
                        for char_uuid in self._characteristic_parsers.keys():
                            # char_uuid = get_characteristic_uuid(board_id)
                            print(char_uuid)
                            await client.start_notify(char_uuid, self.on_ble_notification)
                        print(f"BLE: Subscribed to {char_uuid} on {device.name}.")
                    except BleakError as e:
                        print(
                            f"BLE: Could not subscribe to {char_uuid} on {device.name}: {e}"
                        )
                await asyncio.sleep(10)

            except BleakError as e:
                print(
                    f"BLE: Connection/subscription error with {device.name} (ID: {board_id}): {e}. Retrying in {RECONNECTION_DELAY_SECONDS}s..."
                )
                if client and client.is_connected:
                    await client.disconnect()
                client = None
                await asyncio.sleep(RECONNECTION_DELAY_SECONDS)
            except asyncio.CancelledError:
                print(
                    f"BLE: Connection task for {device.name} (ID: {board_id}) cancelled."
                )
                break
            except Exception as e:
                print(
                    f"BLE: Unexpected error in connection task for {device.name} (ID: {board_id}): {e}. Retrying in {RECONNECTION_DELAY_SECONDS}s..."
                )
                traceback.print_exception(e)
                if client and client.is_connected:
                    await client.disconnect()
                client = None
                await asyncio.sleep(RECONNECTION_DELAY_SECONDS)
        if client and client.is_connected:
            print(
                f"BLE: Disconnecting client for {device.name} (ID: {board_id}) during shutdown."
            )
            await client.disconnect()
        print(f"BLE: Connection task for {device.name} (ID: {board_id}) finished.")

    async def start(self) -> None:
        """
        Starts the BLE (Bluetooth Low Energy) client discovery and connection process.

        This asynchronous method initializes BLE clients for devices specified in `self.device_id_lists`.
        It performs device discovery using the `BleakScanner` and attempts to connect and subscribe to
        the discovered devices.

        Raises:
            ValueError: If a device name cannot be parsed to extract a valid board ID.

        Attributes:
            self.is_running (bool): Indicates whether the BLE service is currently running.
            self.device_id_lists (set): Set of expected device IDs to discover and connect.
            self.ble_devices (dict): Dictionary mapping board IDs to their corresponding BLE devices.
            self.connection_tasks (dict): Dictionary mapping board IDs to their connection tasks.
            self._asyncio_loop (asyncio.AbstractEventLoop): The asyncio event loop used for asynchronous operations.

        Note:
            - `MAX_EXPOLATION_TIMEOUT_SECONDS`, `EXPOLATION_RETRY_DELAY_SECONDS`, and `DEVICE_PREFIX` are constants
              used for device discovery and retry logic.
            - This method is designed to run within an asyncio event loop.

        """
        if self.is_running:
            print("BLE: Already running, cannot start again.")
            return
        self.is_running = True
        self._asyncio_loop = asyncio.get_running_loop()
        print("BLE: Starting BLE clients...")
        founded_devices = set()
        max_explore_tries = MAX_EXPLORATION_TRIES
        while founded_devices != self.device_id_lists and max_explore_tries > 0:
            max_explore_tries -= 1
            print(f"BLE: Exploring devices, remaining tries: {max_explore_tries}")
            devices = await BleakScanner.discover(
                timeout=MAX_EXPOLATION_TIMEOUT_SECONDS
            )
            for device in devices:
                if device.name and device.name.startswith(DEVICE_PREFIX):
                    try:
                        board_id = int(device.name.split("-")[-1], 16)
                        if board_id in self.device_id_lists:
                            founded_devices.add(board_id)
                            if self.ble_devices[board_id] is None:
                                self.ble_devices[board_id] = device
                                print(
                                    f"BLE: Found and initialized client for board ID {board_id}."
                                )
                    except ValueError as e:
                        print(
                            f"BLE: Error parsing board ID from device name '{device.name}': {e}"
                        )
            if founded_devices != self.device_id_lists and max_explore_tries > 0:
                print(
                    f"BLE: Not all devices found yet, retrying in {EXPOLATION_RETRY_DELAY_SECONDS}s..."
                )
                await asyncio.sleep(EXPOLATION_RETRY_DELAY_SECONDS)
        if founded_devices != self.device_id_lists:
            print(
                f"BLE: Not all devices found after exploration: {self.device_id_lists - founded_devices}."
            )
            self.is_running = False
            return
        for board_id, device in self.ble_devices.items():
            if board_id in founded_devices and device is not None:
                task = asyncio.create_task(self.connect_and_subscribe(board_id, device)) 
                self.connection_tasks[board_id] = task

    async def stop(self) -> None:
        """
        Stops the BLE (Bluetooth Low Energy) service and disconnects all active clients.

        This method performs the following actions:
        1. Checks if the service is running; if not, logs a message and exits.
        2. Cancels all ongoing connection tasks.
        3. Awaits the completion of all connection tasks, handling exceptions.
        4. Disconnects all connected BLE clients.
        5. Clears the BLE clients, devices, and connection tasks.

        This ensures that the BLE service is properly shut down and all resources are released.

        Returns:
            None

        """
        if not self.is_running:
            print("BLE: Not running, cannot stop.")
            return
        self.is_running = False
        print("BLE: Stopping BLE clients...")
        for _, task in self.connection_tasks.items():
            if task and hasattr(task, "done") and not task.done():
                task.cancel()
        # Only gather tasks that are not None and are awaitable
        tasks_to_await = [task for task in self.connection_tasks.values() if task is not None and hasattr(task, "__await__")]
        if tasks_to_await:
            await asyncio.gather(*tasks_to_await, return_exceptions=True)
        for client in self.ble_clients.values():
            if client and client.is_connected:
                await client.disconnect()
        self.ble_clients.clear()
        self.ble_devices.clear()
        self.connection_tasks.clear()
        print("BLE: All BLE clients stopped.")

    def is_connected(self) -> bool:
        """
        Check if any BLE client is currently connected.

        Returns:
            bool: True if at least one BLE client is connected, False otherwise.

        """
        return any(client.is_connected for client in self.ble_clients.values())


class BLEServiceContext:
    """
    BLEServiceContext manages the lifecycle of BLE connections and message dispatching
    for the VerticalFarm system.
    """

    ble_sub: SensorDataSubscriber
    msg_dispatcher: MessageDispatcher
    ble_client: BLEClientWrapper
    is_running: bool
    _asyncio_loop: asyncio.AbstractEventLoop | None
    batch_writer: BoardDataBatchWriter
    device_data_retrivers: List[CommonDataRetriver]

    def __init__(self, device_id_list: list[int]) -> None:
        self.msg_dispatcher = MessageDispatcher()
        self.batch_writer = BoardDataBatchWriter.get_instance()
        self.ble_sub = SensorDataSubscriber(self.batch_writer)
        self.ble_client = BLEClientWrapper(
            device_id_lists=device_id_list, dispatcher=self.msg_dispatcher
        )
        self.device_data_retrivers = [
            CommonDataRetriver.get_instance(board_id=device_id, time_window=15)
            for device_id in device_id_list
        ]
        self.msg_dispatcher.register_handler(SensorDataMsg, self.ble_sub.handle)
        for retriver in self.device_data_retrivers:
            self.msg_dispatcher.register_handler(SensorDataMsg, retriver.handle)
        for device_id in device_id_list:
            self.ble_client.register_notification_handler(
                device_id, self.ble_sub.parse_bytes
            )
        self._asyncio_loop = None
        self.is_running = False

    async def start(self) -> None:
        """
        Starts the BLE service context by initializing the BLE client,
        batch writer, and message dispatcher.
        """
        if self.is_running:
            print("BLE Service Context: Already running, cannot start again.")
            return
        self._asyncio_loop = asyncio.get_running_loop()
        self.is_running = True
        print("BLE Service Context: Starting BLE clients...")
        await self.msg_dispatcher.start()
        await self.batch_writer.start()
        await self.ble_client.start()
        print("BLE Service Context started.")

    async def stop(self) -> None:
        """
        Stops the BLE service context and its associated components.

        This method ensures that the BLE service context is properly stopped
        by halting its batch writer, message dispatcher, and BLE client. If
        the service is not running, it logs a message and exits without performing
        any actions.

        Returns:
            None

        """
        if not self.is_running:
            print("BLE Service Context: Not running, cannot stop.")
            return
        self.is_running = False
        print("BLE Service Context: Stopping BLE clients...")
        await self.batch_writer.stop()
        await self.msg_dispatcher.stop()
        await self.ble_client.stop()
        await BoardDataBatchWriter.get_instance().flush()
        print("BLE Service Context stopped.")

    def is_connected(self) -> bool:
        """
        Check if the BLE client is currently connected.

        Returns:
            bool: True if the BLE client is connected, False otherwise.

        """
        return self.ble_client.is_connected()

    def connected_devices(self) -> list[int]:
        """
        Asynchronously retrieves a list of IDs for devices that are currently connected.

        Returns:
            List[int]: A list of integers representing the IDs of devices that are connected.

        """
        return list(self.ble_client.ble_devices.keys())

    async def fetch_data(
        self, since: datetime, board_ids: list[int] | None
    ) -> list[BoardData]:
        """
        Fetches all data since a timestamp, optionally filtered by board_ids.

        Args:
            since (datetime): The earliest timestamp.
            board_ids (Optional[List[int]]): List of board_ids to filter by.

        Returns:
            List[BoardData]: Sorted (descending) BoardData list.

        """
        return await self.batch_writer.fetch_since(since, board_ids)
