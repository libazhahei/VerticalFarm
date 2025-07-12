
"""Constants used for MQTT communication in the VerticalFarm gateway.

Attributes:
    SUBSCRIBE_HEARTBEAT_TIMEOUT_SECONDS (int): Timeout duration in seconds for heartbeat subscription.
    SUBSCRIBE_HEARTBEAT_TOPIC (str): MQTT topic for receiving heartbeat messages.
    SUBSCRIBE_CTRL_MSG_TOPIC (str): MQTT topic for receiving control messages.

    PUBLISH_RESENT_MAX_RETRIES (int): Maximum number of retries for resending a publish message.
    PUBLISH_TIMEOUT_SECONDS (int): Timeout duration in seconds for publishing messages.
    PUBLISH_ERR_MAX_RETRIES (int): Maximum number of retries for publishing messages in case of errors.
    PUBLISH_CTRL_MSG_TPPIC (str): MQTT topic for sending control messages.
    PUBLISH_CTRL_QOS (int): Quality of Service level for control message publishing.

"""
# Core constants
DEVICE_MIN_ID = 0
DEVICE_MAX_ID = 6

# MQTT
SUBSCRIBE_HEARTBEAT_TIMEOUT_SECONDS = 10
SUBSCRIBE_HEARTBEAT_TOPIC = "cropwaifu/heartbeat"
SUBSCRIBE_CTRL_MSG_TOPIC = "cropwaifu/respond"

PUBLISH_RESENT_MAX_RETRIES = 3
PUBLISH_TIMEOUT_SECONDS = 5
PUBLISH_ERR_MAX_RETRIES = 3
PUBLISH_CTRL_MSG_TPPIC = "cropwaifu/control"
PUBLISH_CTRL_QOS = 0

# BLE
SERVICE_UUID_PREFIX = "11451411-4514-1145-1411-"
CHARACTERISTIC_UUID_PREFIX = "19198101-9198-1019-1981-"
MAX_EXPLORATION_TRIES = 3
MAX_EXPOLATION_TIMEOUT_SECONDS = 5
EXPOLATION_RETRY_DELAY_SECONDS = 2
DEVICE_PREFIX = "CropWaifu-Board-"
RECONNECTION_DELAY_SECONDS = 5


def get_service_uuid(board_id: int) -> str:
    """Generates a service UUID based on the board ID."""
    if not (DEVICE_MIN_ID <= board_id <= DEVICE_MAX_ID):
        raise ValueError(f"Board ID must be between {DEVICE_MIN_ID} and {DEVICE_MAX_ID}, got {board_id}.")
    return f"{SERVICE_UUID_PREFIX}{board_id:012x}"

def get_characteristic_uuid(board_id: int) -> str:
    """Generates a characteristic UUID based on the board ID."""
    if not (DEVICE_MIN_ID <= board_id <= DEVICE_MAX_ID):
        raise ValueError(f"Board ID must be between {DEVICE_MIN_ID} and {DEVICE_MAX_ID}, got {board_id}.")
    return f"{CHARACTERISTIC_UUID_PREFIX}{board_id:012x}"

def get_device_name(board_id: int) -> str:
    """Generates a device name based on the board ID."""
    if not (DEVICE_MIN_ID <= board_id <= DEVICE_MAX_ID):
        raise ValueError(f"Board ID must be between {DEVICE_MIN_ID} and {DEVICE_MAX_ID}, got {board_id}.")
    return f"{DEVICE_PREFIX}{board_id}"