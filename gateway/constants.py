
"""
Constants used for MQTT communication in the VerticalFarm gateway.

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
SUBSCRIBE_HEARTBEAT_TIMEOUT_SECONDS = 10
SUBSCRIBE_HEARTBEAT_TOPIC = "cropwaifu/heartbeat"
SUBSCRIBE_CTRL_MSG_TOPIC = "cropwaifu/respond"

PUBLISH_RESENT_MAX_RETRIES = 3
PUBLISH_TIMEOUT_SECONDS = 5
PUBLISH_ERR_MAX_RETRIES = 3
PUBLISH_CTRL_MSG_TPPIC = "cropwaifu/control"
PUBLISH_CTRL_QOS = 0
