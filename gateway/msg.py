import itertools
import json
import threading
from abc import ABC, abstractmethod
from datetime import datetime
from dataclasses import dataclass

class IDGenerator:
    _lock = threading.Lock()
    _counter = itertools.count(1)

    @classmethod
    def next_id(cls):
        with cls._lock:
            return next(cls._counter)

class MessageType(ABC): 

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

# Define a enum for mode: which is abs or relative
class Mode:
    ABSOLUTE: int = 0
    RELATIVE: int = 1

class Status: 
    OK: int = 0
    ERROR: int = 1
    WARNING: int = 2

@dataclass
class ControlMsg(MessageType):
    """
    Control message for the fans and LED.
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
class StatusMsg(MessageType):
    """
    Response message from the board.
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
class HeartbeatMsg(MessageType):
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