import asyncio
import threading
from typing import Callable, Dict, List, Type
from paho.mqtt.client import Client, MQTTMessage

from .constants import SUBSCRIBE_CTRL_MSG_TOPIC, SUBSCRIBE_HEARTBEAT_TOPIC
from .msg import ControlMsg, HeartbeatMsg, MessageType, StatusMsg
from .subscriber import CommandResponseSubscriber, HeartbeatSubscriber, MessageDispatcher
from .publisher import ControlCommandPublisher

class MqttClientWrapper:
    """
    MqttClientWrapper is a wrapper class for managing MQTT client connections and message handling.

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
        self._topic_parsers: Dict[str, Callable[[str], MessageType]] = {} 

    def register_topic_handler(self, topic: str, parser_func: Callable[[str], MessageType]):
        self._topic_parsers[topic] = parser_func
        if self.mqtt_client.is_connected():
            self.mqtt_client.subscribe(topic)

    def _on_connect(self, client: Client, userdata, flags: dict, rc: int):
        if rc == 0:
            for topic in self._topic_parsers.keys():
                client.subscribe(topic)
                print(f"MQTT: Subscribed to topic: {topic}")
        else:
            print(f"MQTT: Connection failed with code {rc}")

    def _on_message(self, client: Client, userdata, msg: MQTTMessage):
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

    def _mqtt_loop_in_thread(self):
        self.mqtt_client.loop_forever() 

    async def start(self):
        self._asyncio_loop = asyncio.get_running_loop() 
        print("MQTT: Connecting to broker...")
        self.mqtt_client.connect(self.mqtt_broker_host, self.mqtt_broker_port, 60)
        self._mqtt_thread = threading.Thread(target=self._mqtt_loop_in_thread, daemon=True)
        self._mqtt_thread.start()
        print("MQTT: Client started in background thread.")
        await asyncio.sleep(0.5) 

    async def stop(self):
        print("MQTT: Stopping client...")
        if self.mqtt_client.is_connected():
            self.mqtt_client.disconnect()
        self.mqtt_client.loop_stop() 

        print("MQTT: Client stopped.")

    def is_connected(self) -> bool:
        return self.mqtt_client.is_connected()
    
class MQTTServiceContext:
    heartbeat_sub: HeartbeatSubscriber
    msg_dispatcher: MessageDispatcher
    publish_client: Client
    control_cmd_pub: ControlCommandPublisher
    command_status_sub: CommandResponseSubscriber

    def __init__(self, borker_host: str, broker_port: int = 1883, client_id: str = "mqtt_client") -> None:
        self.heartbeat_sub = HeartbeatSubscriber()
        self.msg_dispatcher = MessageDispatcher()
        self.publish_client = Client(client_id=f"{client_id}_publisher")
        self.publish_client.connect(borker_host, broker_port, 60)
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

    async def start(self):
        await self.subscribe_client.start()
        await self.msg_dispatcher.start()
        print("MQTT Service Context started.")

    async def stop(self):
        await self.subscribe_client.stop()
        await self.msg_dispatcher.stop()
        print("MQTT Service Context stopped.")

    def alive_devices_sync(self) -> List[int]:
        return asyncio.run(self.heartbeat_sub.get_alive_devices())  
    
    def is_alive_sync(self, board_id: int) -> bool:
        return asyncio.run(self.heartbeat_sub.is_alive(board_id))
    
    async def is_alive(self, board_id: int) -> bool:
        return await self.heartbeat_sub.is_alive(board_id)
    
    async def alive_devices(self) -> List[int]:
        return await self.heartbeat_sub.get_alive_devices()
    
    def is_connected(self) -> bool:
        return self.subscribe_client.is_connected() and self.publish_client.is_connected()
    
    async def publish_control_command(self, message: MessageType):
        if not isinstance(message, ControlMsg):
            raise TypeError("Message must be an instance of StatusMsg")
        await self.control_cmd_pub.add_msg(message, SUBSCRIBE_CTRL_MSG_TOPIC)


    
    

    