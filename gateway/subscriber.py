import asyncio
from abc import ABC, abstractmethod
from collections.abc import Callable
from datetime import datetime

from aiorwlock import RWLock

from data.tables import BatchWriter, BoardData

from .constants import DEVICE_MAX_ID, DEVICE_MIN_ID, SUBSCRIBE_HEARTBEAT_TIMEOUT_SECONDS
from .msg import BLEMessageType, HeartbeatMsg, MessageType, MQTTMessageType, SensorDataMsg, StatusMsg


class GenericSubscriber(ABC):
    """
    GenericSubscriber is an abstract base class that defines the interface for a subscriber
    in a message-handling system. Subclasses must implement the following methods.

    Methods
    -------
    - handle(msg: MessageType):
        An asynchronous method that processes a message of type MessageType.
        This method must be implemented by subclasses.
    - parse_json(json_str: str) -> MessageType:
        A static method that parses a JSON string and returns an object of type MessageType.
        This method must be implemented by subclasses.

    Raises
    ------
    - NotImplementedError:
        Raised if the required methods are not implemented by a subclass.

    """

    @abstractmethod
    async def handle(self, msg: MQTTMessageType) -> None:
        """Parses a JSON string into a MessageType object."""
        raise NotImplementedError("Subclasses must implement the handle method.")


class MQTTSubscriber(GenericSubscriber):
    """A subscriber class for handling MQTT messages."""

    @staticmethod
    @abstractmethod
    def parse_json(json_str: str) -> MQTTMessageType:
        """Parses a JSON string into a MessageType object."""
        raise NotImplementedError("Subclasses must implement the parse_json method.")

class BLESubscriber(GenericSubscriber):
    """A subscriber class for handling BLE messages."""

    @staticmethod
    @abstractmethod
    def parse_bytes(mgs_bytes: bytearray) -> BLEMessageType:
        """Parses a JSON string into a MessageType object."""
        raise NotImplementedError("Subclasses must implement the parse_json method.")

class HeartbeatSubscriber(GenericSubscriber):
    """A subscriber class responsible for handling heartbeat messages from devices
    and maintaining their alive status.

    Attributes:
        alive_devices (List[Tuple[int, float]]): A list of tuples representing the status of devices.
            Each tuple contains the sequence number and the last timestamp of the heartbeat message.
            Default value is a list of 7 tuples initialized to (-1, -1).
        lock (RWLock): A read-write lock to ensure thread-safe access to `alive_devices`.

    Methods:
        __init__():
            Initializes the `alive_devices` list with default values.
        async handle(msg: HeartbeatMsg):
            Handles incoming heartbeat messages and updates the status of the corresponding device.

    Args:
                msg (HeartbeatMsg): The heartbeat message containing device information.
        async is_alive(board_id: int) -> bool:
            Checks if a device is alive based on its last heartbeat timestamp.

    Args:
                board_id (int): The ID of the device to check.

    Returns:
                bool: True if the device is alive, False otherwise.
        async get_alive_devices() -> List[int]:
            Retrieves a list of IDs of devices that are currently alive.

    Returns:
                List[int]: A list of alive device IDs.
        parse_json(json_str: str) -> HeartbeatMsg:
            Parses a JSON string into a `HeartbeatMsg` object.

    Args:
                json_str (str): The JSON string representing a heartbeat message.

    Returns:
                HeartbeatMsg: The parsed heartbeat message object.

    """

    alive_devices: list[tuple[int, float]]  # List of tuples (board_id, seq_no)
    lock: RWLock = RWLock()

    def __init__(self):
        self.alive_devices = [(-1, -1) for _ in range(7)]

    async def handle(self, msg: HeartbeatMsg)-> None:
        """Handles incoming heartbeat messages and updates the status of devices.

        Args:
            msg (HeartbeatMsg): The heartbeat message containing the board ID and sequence number.

        Behavior:
            - Acquires a writer lock to ensure thread-safe access to shared resources.
            - Checks if the device corresponding to the given board ID is marked as inactive (-1).
            - Updates the device's status with the sequence number and the current timestamp.

        """
        async with self.lock.writer_lock:
            if self.alive_devices[msg.board_id][0] == -1:
                self.alive_devices[msg.board_id] = (msg.seq_no, datetime.now().timestamp())

    async def is_alive(self, board_id: int) -> bool:
        """Check if a device with the given board ID is alive based on its last heartbeat timestamp.

        Args:
            board_id (int): The ID of the device board to check. Must be between 0 and 6 inclusive.

        Returns:
            bool: True if the device is alive (heartbeat received within the timeout period), 
                  False otherwise. If the device is determined to be stopped, its status is 
                  updated to (-1, -1) in the `alive_devices` dictionary.

        Notes:
            - The method uses a reader lock to safely read the device status and a writer lock 
              to update the status if the device is stopped.
            - The `SUBSCRIBE_HEARTBEAT_TIMEOUT_SECONDS` constant defines the timeout period 
              for considering a device as alive.

        """
        stoped_devices = -1
        if DEVICE_MIN_ID <= board_id <= DEVICE_MAX_ID:
            async with self.lock.reader_lock:
                device_status = self.alive_devices[board_id]
            if device_status != -1:
                current_time = datetime.now().timestamp()
                _, last_timestamp = device_status
                if current_time - last_timestamp < SUBSCRIBE_HEARTBEAT_TIMEOUT_SECONDS:
                    return True
                else:
                    stoped_devices = board_id
        if stoped_devices != -1:
            async with self.lock.writer_lock:
                self.alive_devices[stoped_devices] = (-1, -1)
        return False

    async def get_alive_devices(self) -> list[int]:
        """Retrieve a list of IDs for devices that are currently alive.

        This asynchronous method acquires a reader lock to ensure thread-safe
        access to the `alive_devices` attribute. It iterates through the list
        of devices and checks if the sequence number (`seq_no`) is not -1,
        indicating that the device is alive. The IDs of such devices are
        collected and returned.

        Returns:
            List[int]: A list of integers representing the IDs of alive devices.

        """
        alive_devices = []
        async with self.lock.reader_lock:
            for board_id, (seq_no, _) in enumerate(self.alive_devices):
                if seq_no != -1:
                    alive_devices.append(board_id)
        return alive_devices

    @staticmethod
    def parse_json(json_str: str) -> HeartbeatMsg:
        """Parse a JSON string into a HeartbeatMsg object."""
        internal_msg = HeartbeatMsg.from_json(json_str)
        return internal_msg

class CommandResponseSubscriber(GenericSubscriber):
    """A subscriber class responsible for handling and acknowledging status messages.

    Attributes:
        acknowledge_func (Callable[[int], None]): A function to acknowledge a message 
            based on its board ID.

    Methods:
        handle(msg: StatusMsg):
            Asynchronously handles a status message by verifying its type and 
            invoking the acknowledge function with the board ID.

        parse_json(json_str: str) -> StatusMsg:
            Converts a JSON string into a StatusMsg instance.

    Raises:
        TypeError: If the provided message is not an instance of StatusMsg.

    """

    def __init__(self, acknowledge_func: Callable[[int], None]):
        self.acknowledge_func = acknowledge_func

    async def handle(self, msg: StatusMsg) -> None:
        """Handles a status message by acknowledging it based on the board ID."""
        if not isinstance(msg, StatusMsg):
            raise TypeError("Message must be an instance of StatusMsg")
        self.acknowledge_func(msg.board_id)

    @staticmethod
    def parse_json(json_str: str) -> StatusMsg:
        """Parse a JSON string into a HeartbeatMsg object."""
        internal_msg = StatusMsg.from_json(json_str)
        return internal_msg

class SensorDataSubscriber(BLESubscriber):
    """
    A subscriber class responsible for handling sensor data messages and inserting them into the database.

    Attributes:
        db_writer (BatchWriter): An instance of BatchWriter to handle database operations.

    Methods:
        handle(msg: SensorDataMsg):
            Asynchronously handles a sensor data message by inserting the data into the database.
        parse_bytes(msg_bytes: bytearray) -> SensorDataMsg:
            Parses a byte array into a SensorDataMsg object.
    """

    def __init__(self, db_writer: BatchWriter) -> None:
        """Initializes the SensorDataSubscriber with a BatchWriter instance."""
        self.db_writer = db_writer

    async def handle(self, msg: SensorDataMsg) -> None:
        """Handles a BLE message by inserting the data into the database."""
        if not isinstance(msg, SensorDataMsg):
            raise TypeError("Message must be an instance of BLEMessageType")
        await self.db_writer.add(
            BoardData(
                board_id=msg.board_id,
                temperature=msg.temperature,
                light_intensity=msg.light_intensity,
                humidity=msg.humidity,
            )
        )

    @staticmethod
    def parse_bytes(msg_bytes: bytearray) -> SensorDataMsg:
        """Parses a byte array into a BLEMessageType object."""
        internal_msg = SensorDataMsg.from_byte_array(msg_bytes)
        return internal_msg

class MessageDispatcher:
    """A class responsible for dispatching messages to registered handlers asynchronously.

    Attributes:
        subscribers (Dict[Type[MessageType], List[Callable]]): 
            A dictionary mapping message types to lists of subscriber handler functions.
        message_queue (asyncio.Queue): 
            A queue for storing messages to be dispatched.
        running (bool): 
            Indicates whether the dispatcher is currently running.
        dispatch_task (asyncio.Task | None): 
            The asyncio task running the dispatch loop, or None if not running.
        processing_task (Set[asyncio.Task]): 
            A set of asyncio tasks currently processing messages.

    Methods:
        register_handler(msg_type: Type[MessageType], subscriber_handle: Callable) -> None:
            Registers a handler function for a specific message type.
        async dispatch(msg: MessageType) -> None:
            Dispatches a message to all registered handlers for its type.
        async dispatch_loop() -> None:
            Continuously processes messages from the queue and dispatches them to handlers.
        async start() -> None:
            Starts the dispatcher, initializing the dispatch loop.
        async stop() -> None:
            Stops the dispatcher, ensuring all pending messages are processed.
        async put_message(msg: MessageType) -> None:
            Adds a message to the queue for dispatching. Requires the dispatcher to be running.

    """

    def __init__(self) -> None:
        self.subscribers : dict[type[MessageType], list[Callable]] = {}
        self.message_queue: asyncio.Queue = asyncio.Queue()
        self.running: bool = False
        self.dispatch_task: asyncio.Task | None = None
        self.processing_task: set[asyncio.Task]  = set()


    def register_handler(self, msg_type: type[MessageType], subscriber_handle: Callable) -> None:
        """Registers a handler for a specific message type.

        Args:
            msg_type (Type[MessageType]): The type of message to associate with the handler.
            subscriber_handle (Callable): The function or callable object to handle messages of the specified type.

        Returns:
            None

        """
        if msg_type not in self.subscribers:
            self.subscribers[msg_type] = []
        self.subscribers[msg_type].append(subscriber_handle)

    async def dispatch(self, msg: MessageType) -> None:
        """Dispatches a message to the appropriate handlers based on its type.

        This method retrieves the handlers registered for the type of the given 
        message and asynchronously executes them. If no handlers are registered 
        for the message type, a message is printed indicating this.

        Args:
            msg (MessageType): The message to be dispatched.

        Behavior:
            - If no handlers are registered for the message type, a message is 
              printed and the method returns.
            - For each registered handler, an asyncio task is created to process 
              the message. These tasks are tracked in `self.processing_task`.
            - Once a task is completed, it is removed from `self.processing_task`.
            - All tasks are awaited concurrently using `asyncio.gather`.

        Note:
            Exceptions raised by handlers are not propagated; instead, they are 
            collected and returned as part of `asyncio.gather`.

        """
        msg_type = type(msg)
        handlers = self.subscribers.get(msg_type, None)
        if handlers is None:
            print(f"No handler registered for message type {msg_type}.")
            return
        tasks = []
        for handler in handlers:
            task = asyncio.create_task(handler(msg))
            self.processing_task.add(task)
            task.add_done_callback(self.processing_task.discard)
            tasks.append(task)

        await asyncio.gather(*tasks, return_exceptions=True)

    async def dispatch_loop(self) -> None:
        """Asynchronous method that continuously processes messages from a queue and dispatches them
        to appropriate subscribers based on their type.

        This method runs in a loop while the `running` attribute is True. It retrieves messages
        from the `message_queue`, checks if there are subscribers for the message type, and creates
        a task to dispatch the message to those subscribers. If no subscribers are found for the
        message type, it logs a message indicating this.

        Exceptions are handled gracefully:
        - If the loop is cancelled via `asyncio.CancelledError`, it logs the cancellation and exits.
        - Any other exceptions are caught and logged without interrupting the loop.

        The `message_queue.task_done()` is called in the `finally` block to indicate that the
        retrieved message has been processed.

        Attributes:
            running (bool): A flag indicating whether the loop should continue running.
            message_queue (asyncio.Queue): A queue from which messages are retrieved.
            subscribers (dict): A dictionary mapping message types to their respective subscribers.

        Raises:
            asyncio.CancelledError: If the loop is cancelled.

        """
        while self.running:
            try:
                msg: MQTTMessageType = await self.message_queue.get()
                print(f"Dispatching message: {msg}")
                if type(msg) in self.subscribers:
                    asyncio.create_task(self.dispatch(msg))
                else:
                    print(f"No subscribers for message type {type(msg)}")
                self.message_queue.task_done()
            except asyncio.CancelledError:
                print("Dispatch loop cancelled.")
                break
            except Exception as e:
                print(f"Error in dispatch loop: {e}")
            finally:
                print(f"Message {msg} processed.")

    async def start(self) -> None:
        """Starts the MessageDispatcher if it is not already running.

        This method initializes the dispatcher by setting the `running` flag to True
        and creating an asynchronous task for the dispatch loop. If the dispatcher
        is already running, a RuntimeError is raised.

        Raises:
            RuntimeError: If the dispatcher is already running.

        """
        if self.running:
            raise RuntimeError("Dispatcher is already running.")
        self.running = True
        self.dispatch_task = asyncio.create_task(self.dispatch_loop())
        print("MessageDispatcher started.")

    async def stop(self) -> None:
        """Stops the MessageDispatcher gracefully.

        This method stops the dispatcher if it is currently running. It cancels the dispatch task,
        waits for all messages in the queue to be processed, and ensures that any processing tasks
        are completed or handled with exceptions.

        Raises:
            RuntimeError: If the dispatcher is not running.

        Behavior:
            - Sets the `running` flag to False.
            - Cancels the `dispatch_task` and waits for its completion.
            - Waits for all messages in the `message_queue` to be processed.
            - Gathers and handles exceptions for any tasks in `processing_task`.

        """
        if not self.running:
            raise RuntimeError("Dispatcher is not running.")
        self.running = False
        print("Stopping MessageDispatcher...")
        if self.dispatch_task:
            self.dispatch_task.cancel()
            try:
                await self.dispatch_task
            except asyncio.CancelledError:
                pass
        await self.message_queue.join()  # Wait for all messages to be processed
        if self.processing_task:
            await asyncio.gather(*self.processing_task, return_exceptions=True)
        print("MessageDispatcher stopped.")

    async def put_message(self, msg: MessageType) -> None:
        """
        Asynchronously adds a message to the message queue.

        Args:
            msg (MessageType): The message to be added to the queue.

        Raises:
            RuntimeError: If the dispatcher is not running. Ensure `start()` is called before using this method.

        """
        if not self.running:
            raise RuntimeError("Dispatcher is not running. Call start() before putting messages.")
        await self.message_queue.put(msg)


