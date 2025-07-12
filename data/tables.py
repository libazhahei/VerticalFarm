import asyncio
from datetime import datetime
from typing import List, Optional
from tortoise import fields
from tortoise.models import Model
from aiorwlock import RWLock
from .config import BATCH_SIZE, BATCH_TIMEOUT_MS

class BoardData(Model): 
    """
    Represents the data associated with a board in the system.
    
    Attributes:
        id (int): Unique identifier for the board data.
        board_id (int): Identifier for the board.
        temperature (float): Temperature reading from the board.
        light_intensity (int): Light intensity reading from the board.
        humidity (int): Humidity reading from the board.
        timestamp (datetime): Timestamp of when the data was recorded.

    """

    id = fields.IntField(pk=True)
    timestamp = fields.DatetimeField(auto_now_add=True)
    board_id = fields.IntField()
    temperature = fields.FloatField()
    light_intensity = fields.IntField()
    humidity = fields.IntField(default=0)
    class Meta:
        table = "board_data"
        ordering = ["-timestamp"]
        unique_together = (("board_id", "timestamp"),)

class BatchWriter:
   
    def __init__(self, batch_size=BATCH_SIZE, timeout=BATCH_TIMEOUT_MS):
        self.batch_size = batch_size
        self.buffer: List[BoardData] = []
        self.timeout = timeout / 1000  # milliseconds to seconds
        self.lock = RWLock()
        self._flush_worker: Optional[asyncio.Task] = None
        self._stop_event = asyncio.Event()

    async def start(self):
        self._stop_event.clear()
        self._flush_worker = asyncio.create_task(self._flush_loop())

    async def stop(self):
        self._stop_event.set()
        if self._flush_worker:
            await self._flush_worker
        await self.flush()  
        

    async def _flush_loop(self):
        while not self._stop_event.is_set():
            await asyncio.sleep(self.timeout)
            if len(self.buffer) < (self.batch_size / 3):
                continue
            await self.flush()

    async def add(self, data: BoardData):
        should_flush = False

        async with self.lock.writer_lock:
            self.buffer.append(data)
            if len(self.buffer) >= self.batch_size:
                should_flush = True

        if should_flush:
            await self.flush()

    async def flush(self):
        data_to_write = []

        async with self.lock.writer_lock:
            if not self.buffer:
                return
            data_to_write, self.buffer = self.buffer, []

        try:
            await BoardData.bulk_create(data_to_write)
        except Exception as e:
            print(f"Flush failed: {e}")

    async def fetch(self) -> List[BoardData]:
        async with self.lock.reader_lock:
            return list(self.buffer)
        
    async def clear(self):
        async with self.lock.writer_lock:
            self.buffer.clear()
    
    