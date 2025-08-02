from enum import Enum
import itertools
import json
import threading
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from typing import Any
import struct


class IDGenerator:
    _lock = threading.Lock()
    _counter = itertools.count(1)

    @classmethod
    def next_id(cls):
        with cls._lock:
            return next(cls._counter)
        
class MessageType(ABC):
    pass 

class MQTTMessageType(MessageType):

    @abstractmethod
    def get_message_id(self) -> int:
        pass

    @abstractmethod
    def to_dict(self) -> dict:
        pass

    def to_json(self, **kwargs) -> str:
        return json.dumps(self.to_dict(), **kwargs)

    # @abstractmethod
    def parse_json(self, json_str: str):
        data = json.loads(json_str)
        return self.from_dict(data)

    @classmethod
    @abstractmethod
    def from_dict(cls, data: dict):
        raise NotImplementedError("Subclasses must implement from_dict method.")

    @classmethod
    def from_json(cls, json_str: str) :
        data = json.loads(json_str)
        return cls.from_dict(data)
    
class BLEMessageType(MessageType):

    @classmethod
    @abstractmethod
    def from_byte_array(cls, byte_array: bytes):
        """Parse a byte array into the message type."""
        pass

    @abstractmethod
    def to_byte_array(self) -> bytes:
        """Convert the message type to a byte array."""
        pass


# Define a enum for mode: which is abs or relative
class Mode(int, Enum):
    ABSOLUTE = 0
    RELATIVE = 1

class Status(int, Enum):
    OK = 0
    ERROR = 1
    WARNING = 2

@dataclass
class ControlMsg(MQTTMessageType):
    """Control message for the fans and LED.
    """

    message_id: int
    board_id: int
    mode: int
    fan: int
    led: int
    temperature: float
    light_intensity: float
    timestamp: float

    def __init__(self, board_id, mode: int = Mode.ABSOLUTE, fan: int = 0,
                 led: int = 0, temperature: float = 0.0, light_intensity: float = 0.0,
                 message_id = 0, timestamp: float = 0.0):
        self.board_id = board_id
        self.mode = mode
        self.fan = fan
        self.led = led
        self.temperature = temperature
        self.light_intensity = light_intensity
        self.message_id = message_id
        self.timestamp = timestamp

    def __post_init__(self):
        if self.mode not in (Mode.ABSOLUTE, Mode.RELATIVE):
            raise ValueError(f"Invalid mode: {self.mode}. Must be either ABSOLUTE or RELATIVE.")
        if not (0 <= self.board_id <= 6):
            raise ValueError(f"Board ID must be between 0 and 6, got {self.board_id}.")
        if not (0 <= self.fan <= 255 and self.mode == Mode.ABSOLUTE):
            raise ValueError(f"Fan value must be between 0 and 255, got {self.fan}.")
        if not (0 <= self.led <= 255 and self.mode == Mode.ABSOLUTE ):
            raise ValueError(f"LED value must be between 0 and 255, got {self.led}.")
        if not (0 <= self.temperature <= 100):
            raise ValueError(f"Temperature must be between 0 and 100, got {self.temperature}.")
        if not (0 <= self.light_intensity <= 100):
            raise ValueError(f"Light intensity must be between 0 and 100, got {self.light_intensity}.")
        self.message_id = IDGenerator.next_id()
        self.timestamp = datetime.now().timestamp()


    def to_dict(self) -> dict:
        return {
            "messageID": self.message_id,
            "boardID": self.board_id,
            "mode": self.mode,
            "fan": self.fan,
            "led": self.led,
            "temperature": self.temperature,
            "lightIntensity": self.light_intensity,
            "timestamp": self.timestamp
        }

    @classmethod
    def from_dict(cls, data: dict):
        return cls(
            message_id=data["messageID"],
            board_id=data["boardID"],
            mode=data["mode"],
            fan=data["fan"],
            led=data["led"],
            temperature=data["temperature"],
            light_intensity=data["lightIntensity"],
            timestamp=data["timestamp"]
        )

    def get_message_id(self) -> int:
        return self.message_id

    def parse_json(self, json_str: str):
        return super().parse_json(json_str)

    def __eq__(self, value: object) -> bool:
        if not isinstance(value, ControlMsg):
            return False
        return (self.board_id == value.board_id and
                self.mode == value.mode and
                self.fan == value.fan and
                self.led == value.led and
                self.temperature == value.temperature and
                self.light_intensity == value.light_intensity)

    def __hash__(self) -> int:
        return hash((self.board_id, self.mode, self.fan, self.led, self.temperature, self.light_intensity))

    def __str__(self) -> str:
        return (f"ControlMsg(board_id={self.board_id}, mode={self.mode}, "
                f"fan={self.fan}, led={self.led}, temperature={self.temperature}, "
                f"light_intensity={self.light_intensity}, message_id={self.message_id}, "
                f"timestamp={self.timestamp})")

    def __repr__(self) -> str:
        return (f"ControlMsg(board_id={self.board_id}, mode={self.mode}, "
                f"fan={self.fan}, led={self.led}, temperature={self.temperature}, "
                f"light_intensity={self.light_intensity}, message_id={self.message_id}, "
                f"timestamp={self.timestamp})")

@dataclass
class StatusMsg(MQTTMessageType):
    """Response message from the board.
    """

    message_id: int
    board_id: int
    status: int
    timestamp: float

    def __init__(self, board_id: int, status: int, message_id: int = 0, timestamp: float = 0.0):
        self.board_id = board_id
        self.status = status
        self.message_id = message_id
        self.timestamp = timestamp


    def __post_init__(self):
        if not (0 <= self.board_id <= 6):
            raise ValueError(f"Board ID must be between 0 and 6, got {self.board_id}.")
        if self.status not in (Status.OK, Status.ERROR, Status.WARNING):
            raise ValueError(f"Invalid status: {self.status}. Must be either OK, ERROR, or WARNING.")
        self.message_id = IDGenerator.next_id()
        self.timestamp = datetime.now().timestamp()

    def to_dict(self) -> dict:
        return {
            "messageID": self.message_id,
            "boardID": self.board_id,
            "status": self.status,
            "timestamp": self.timestamp
        }

    @classmethod
    def from_dict(cls, data: dict):
        return cls(
            message_id=data["messageID"],
            board_id=data["boardID"],
            status=data["status"],
            timestamp=data["timestamp"]
        )

    def get_message_id(self) -> int:
        return self.message_id

    def parse_json(self, json_str: str):
        return super().parse_json(json_str)
@dataclass
class HeartbeatMsg(MQTTMessageType):
    board_id: int
    seq_no: int

    def __post_init__(self):
        if not (0 <= self.board_id <= 6):
            raise ValueError(f"Board ID must be between 0 and 6, got {self.board_id}.")

    def to_dict(self) -> dict:
        raise ValueError("HeartbeatMsg does not support to_dict method.")

    @classmethod
    def from_dict(cls, data: dict):
        return cls(
            board_id=data["boardID"],
            seq_no=data["seqNo"]
        )

    def get_message_id(self) -> int:
        return self.seq_no

class SensorStatus(int, Enum):
    IDLE = 0
    RUNNING = 1
    ERROR = 2

@dataclass 
class SensorDataMsg(BLEMessageType):
    board_id: int
    temperature: float 
    light_intensity: int 
    fans_real: int 
    humidity: float
    status: SensorStatus 
    fans_abs: int  
    led_abs: int
    timestamp: float


    def __post_init__(self):
        if not (0 <= self.board_id <= 6):
            raise ValueError(f"Board ID must be between 0 and 6, got {self.board_id}.")
        if not (0 <= self.temperature <= 100):
            raise ValueError(f"Temperature must be between 0 and 100, got {self.temperature}.")
        if not (0 <= self.light_intensity <= 65535):
            raise ValueError(f"Light intensity must be between 0 and 65535, got {self.light_intensity}.")
        if not (0 <= self.fans_real <= 65535):
            raise ValueError(f"Fans value must be between 0 and 65535, got {self.fans_real}.")
        if not (0 <= self.humidity <= 100):
            raise ValueError(f"Humidity must be between 0 and 100, got {self.humidity}.")
        if not (0 <= self.fans_abs <= 255):
            raise ValueError(f"Fans absolute value must be between 0 and 255, got {self.fans_abs}.")
        if not (0 <= self.led_abs <= 255):
            raise ValueError(f"LED absolute value must be between 0 and 255, got {self.led_abs}.")
        self.timestamp = int(datetime.now().timestamp())

    def to_byte_array(self) -> bytearray:
        byte_array = bytearray(20)
        byte_array[0] = self.board_id
        temp = int(self.temperature * 100)
        byte_array[1] = temp & 0xFF
        byte_array[2] = (temp >> 8) & 0xFF
        byte_array[3] = self.light_intensity & 0xFF
        byte_array[4] = (self.light_intensity >> 8) & 0xFF
        byte_array[5] = self.fans_real & 0xFF
        byte_array[6] = (self.fans_real >> 8) & 0xFF
        byte_array[7] = int(self.humidity * 100) & 0xFF
        byte_array[8] = (int(self.humidity * 100) >> 8) & 0xFF
        byte_array[9] = self.status.value
        byte_array[10] = self.fans_abs
        byte_array[11] = self.led_abs
        for i in range(12, 20):
            byte_array[i] = 0
        return byte_array

    @classmethod
    def from_byte_array(cls, data: bytearray) -> 'SensorDataMsg':

        board_id = data[0]
        temp_raw = struct.unpack('>H', data[1:3])[0]
        light = struct.unpack('>H', data[3:5])[0]
        fan = struct.unpack('>H', data[5:7])[0]
        humidity_raw = struct.unpack('>H', data[7:9])[0]
        status = data[9]
        fan_pwm = data[10]
        light_pwm = data[11]

        return cls(
            board_id=board_id,
            temperature=temp_raw / 100.0,
            light_intensity=light,
            fans_real=fan,
            humidity=humidity_raw / 100.0,
            status=SensorStatus(status),
            fans_abs=fan_pwm,
            led_abs=light_pwm,
            timestamp=datetime.now().timestamp()
        )

        

