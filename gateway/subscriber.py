from abc import ABC, abstractmethod
import asyncio
from datetime import datetime
from typing import Callable, List, Set, Tuple, Dict, Type
from aiorwlock import RWLock
from .msg import HeartbeatMsg, MessageType, StatusMsg
from .constants import SUBSCRIBE_HEARTBEAT_TIMEOUT_SECONDS

class GenericSubscriber(ABC):
    @abstractmethod
    async def handle(self, msg: MessageType):
        raise NotImplementedError("Subclasses must implement the handle method.")
    
    @staticmethod
    @abstractmethod
    def parse_json(json_str: str) -> MessageType:
        raise NotImplementedError("Subclasses must implement the parse_json method.")

class HeartbeatSubscriber(GenericSubscriber): 
    alive_devices: List[Tuple[int, float]] = []  # List of tuples (board_id, seq_no)
    lock: RWLock = RWLock()

    def __init__(self):
        self.alive_devices = [(-1, -1) for _ in range(7)]  

    async def handle(self, msg: HeartbeatMsg):
        async with self.lock.writer_lock:
            if self.alive_devices[msg.board_id][0] == -1:
                self.alive_devices[msg.board_id] = (msg.seq_no, datetime.now().timestamp())

    async def is_alive(self, board_id: int) -> bool:
        stoped_devices = -1
        if 0 <= board_id and board_id <= 6:
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
    
    async def get_alive_devices(self) -> List[int]:
        alive_devices = []
        async with self.lock.reader_lock:
            for board_id, (seq_no, timestamp) in enumerate(self.alive_devices):
                if seq_no != -1:
                    alive_devices.append(board_id)
        return alive_devices
    
    @staticmethod
    def parse_json(json_str: str) -> HeartbeatMsg:
        internal_msg = HeartbeatMsg.from_json(json_str)
        return internal_msg
    
class CommandResponseSubscriber(GenericSubscriber):
    def __init__(self, acknowledge_func: Callable[[int], None]):
        self.acknowledge_func = acknowledge_func

    async def handle(self, msg: StatusMsg):
        if not isinstance(msg, StatusMsg):
            raise TypeError("Message must be an instance of StatusMsg")
        self.acknowledge_func(msg.board_id)

    @staticmethod
    def parse_json(json_str: str) -> StatusMsg:
        internal_msg = StatusMsg.from_json(json_str)
        return internal_msg

class MessageDispatcher: 
    def __init__(self) -> None:
        self.subscribers : Dict[Type[MessageType], List[Callable]] = {}
        self.message_queue: asyncio.Queue = asyncio.Queue()
        self.running: bool = False
        self.dispatch_task: asyncio.Task | None = None
        self.processing_task: Set[asyncio.Task]  = set() 
        
    
    def register_handler(self, msg_type: Type[MessageType], subscriber_handle: Callable) -> None:
        if msg_type not in self.subscribers:
            self.subscribers[msg_type] = []
        self.subscribers[msg_type].append(subscriber_handle)
    
    async def dispatch(self, msg: MessageType) -> None:
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

    async def dispatch_loop(self):
        while self.running:
            try:
                msg: MessageType = await self.message_queue.get()
                if type(msg) in self.subscribers:
                    asyncio.create_task(self.dispatch(msg))
                else:
                    print(f"No subscribers for message type {type(msg)}")
            except asyncio.CancelledError:
                print("Dispatch loop cancelled.")
                break
            except Exception as e:
                print(f"Error in dispatch loop: {e}")
            finally:
                self.message_queue.task_done()

    async def start(self):
        if self.running:
            raise RuntimeError("Dispatcher is already running.")
        self.running = True
        self.dispatch_task = asyncio.create_task(self.dispatch_loop())
        print("MessageDispatcher started.")

    async def stop(self):
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
        if not self.running:
            raise RuntimeError("Dispatcher is not running. Call start() before putting messages.")
        await self.message_queue.put(msg)


